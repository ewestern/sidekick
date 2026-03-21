"""Scrapy item pipeline — converts RawItems to Artifacts and writes to the store."""

from __future__ import annotations

import logging

import ulid
from scrapy.exceptions import DropItem

from sidekick.core.models import Artifact
from sidekick.spiders._base import SidekickSpider, RawItem, spider_beat_geo_str
from sidekick.spiders._context import get as get_context
from sidekick.core.object_store import S3ObjectStore
from sidekick.spiders._format_registry import (
    FORMAT_REGISTRY,
    UnknownFormatError,
    detect_format,
)

logger = logging.getLogger(__name__)


class ArtifactWriterPipeline:
    """Scrapy item pipeline that persists ``RawItem``s as ``Artifact`` rows.

    Format resolution — two paths:

    **Declared** (``RawItem.format_id`` is set): the spider asserts what format
    this URL produces.  The pipeline looks up the ``FormatSpec`` directly from
    ``FORMAT_REGISTRY``.  ``detect_format`` is still run as a validation step;
    a mismatch emits a warning but does not drop the item — the spider's
    declaration is trusted over signal inference.  An unknown ``format_id``
    (not in ``FORMAT_REGISTRY``) is a spider bug and drops the item.

    **Undeclared** (``format_id`` is ``None``): the item is dropped immediately.
    Every spider must declare ``format_id`` on every ``RawItem`` it yields.

    Async formats (HLS, mpeg-ts) produce stub artifacts with
    ``status="pending_acquisition"`` regardless of which path resolved them.
    """

    @classmethod
    def from_crawler(cls, crawler):
        ctx = get_context(crawler.settings["SIDEKICK_RUN_TOKEN"])
        instance = cls(ctx.artifact_store, ctx.object_store, ctx.event_bus)
        instance._crawler = crawler
        return instance

    def __init__(self, artifact_store, object_store, event_bus) -> None:
        self._artifact_store = artifact_store
        self._object_store = object_store
        self._event_bus = event_bus
        self._crawler = None  # set by from_crawler

    def process_item(self, item: RawItem) -> RawItem:
        spider: SidekickSpider = self._crawler.spider
        url: str = item["url"]
        body: bytes = item.get("body") or b""
        media_type: str | None = item.get("media_type")
        format_id: str | None = item.get("format_id")
        title: str | None = item.get("title")

        spec = self._resolve_format(url, format_id, media_type, body)

        entities: list[dict] = [{"type": "source-url", "name": url}]
        if title:
            entities.append({"type": "title", "name": title})

        topics: list[str] | None = None
        if spider.expected_content:
            topics = [
                ec["content_type"]
                for ec in spider.expected_content
                if "content_type" in ec
            ] or None

        artifact_id = f"art_{ulid.new()}"
        beat_str, geo_str = spider_beat_geo_str(spider)
        artifact = Artifact(
            id=artifact_id,
            content_type=spec.content_type,
            stage="raw",
            media_type=spec.stored_mime_type,
            source_id=spider.source_id,
            beat=beat_str,
            geo=geo_str,
            entities=entities,
            topics=topics,
            created_by=f"spider:{spider.name}",
        )

        if spec.is_async:
            artifact.status = "pending_acquisition"
            artifact.acquisition_url = url
            self._artifact_store.write(artifact)
            self._event_bus.publish("acquisition_needed", {
                "artifact_id": artifact_id,
                "format_id": spec.format_id,
                "source_url": url,
            })
            logger.debug(
                "Wrote stub artifact %s for async format %s: %s",
                artifact_id, spec.format_id, url,
            )
            return item

        key = S3ObjectStore.artifact_key("raw", beat_str, geo_str, artifact_id)
        artifact.content_uri = self._object_store.put(
            key, body, content_type=spec.stored_mime_type
        )

        self._artifact_store.write(artifact)
        logger.debug("Wrote artifact %s for %s", artifact_id, url)
        return item

    def _resolve_format(self, url, format_id, media_type, body):
        """Return a FormatSpec from the spider's declaration; drop if undeclared."""
        if format_id is not None:
            spec = FORMAT_REGISTRY.get(format_id)
            if spec is None:
                logger.warning(
                    "Dropping item — unknown format_id %r declared by spider for %s",
                    format_id, url,
                )
                raise DropItem(f"Unknown format_id declared by spider: {format_id!r}")

            # Validate: run detection and warn on mismatch, but trust the declaration
            try:
                detected = detect_format(url, media_type, body[:128] if body else None)
                if detected.format_id != format_id:
                    logger.warning(
                        "Format mismatch for %s: spider declared %r, signals suggest %r"
                        " — trusting declaration",
                        url, format_id, detected.format_id,
                    )
            except UnknownFormatError:
                pass  # detection failed; trust spider declaration

            return spec

        # No declaration — spiders must declare format_id for every RawItem
        logger.warning(
            "Dropping item — no format_id declared by spider for %s", url
        )
        raise DropItem(f"Spider must declare format_id for every RawItem (url={url!r})")
