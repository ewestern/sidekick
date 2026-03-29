"""Scrapy item pipeline — converts RawItems to Artifacts and writes to the store."""

from __future__ import annotations

import logging
from datetime import date as _date
from sidekick.spiders._context import RunContext

import ulid
from scrapy.exceptions import DropItem

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ArtifactStatus, ProcessingProfile, Stage
from sidekick.spiders._base import SidekickSpider, RawItem, spider_beat_geo_str
from sidekick.spiders._context import get as get_context
from sidekick.core.object_store import S3ObjectStore
from sidekick.spiders._format_registry import (
    FORMAT_REGISTRY,
    UnknownFormatError,
    detect_format,
)

logger = logging.getLogger(__name__)


def _resolve_item_beat(item: RawItem, spider: SidekickSpider) -> str | None:
    """Item beat overrides spider beat; both are optional."""
    raw = item.get("beat")
    if raw is not None and raw != "":
        return str(raw)
    return str(spider.beat) if spider.beat is not None else None


def _resolve_processing_profile(item: RawItem, spider: SidekickSpider) -> ProcessingProfile:
    """Item override, then spider default, then ``full``."""
    raw = item.get("processing_profile")
    if raw is not None and raw != "":
        return ProcessingProfile(str(raw))
    dp = getattr(spider, "default_processing_profile", None)
    if dp is not None:
        return ProcessingProfile(dp) if isinstance(dp, str) else dp
    return ProcessingProfile.FULL


def _parse_period_date(value: object) -> _date | None:
    """Convert an ISO date string from RawItem to a date, or return None."""
    if value is None:
        return None
    try:
        return _date.fromisoformat(str(value))
    except (ValueError, TypeError):
        logger.warning("Invalid period date value %r — skipping", value)
        return None


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
    _ctx: RunContext

    @classmethod
    def from_crawler(cls, crawler):
        ctx = get_context(crawler.settings["SIDEKICK_RUN_TOKEN"])
        instance = cls(ctx.artifact_store, ctx.object_store)
        instance._ctx = ctx
        instance._crawler = crawler # type: ignore[reportAttributeAccessIssue]
        return instance

    def __init__(self, artifact_store, object_store) -> None:
        self._artifact_store = artifact_store
        self._object_store = object_store
        # _ctx and _crawler are injected by from_crawler(); __getattr__ below
        # raises a clear error if they are accessed before that happens.

    def __getattr__(self, name: str) -> object:
        if name in ("_ctx", "_crawler"):
            raise AttributeError(
                f"'{name}' is not set — create this pipeline via "
                "ArtifactWriterPipeline.from_crawler(), not __init__() directly."
            )
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'")

    def process_item(self, item: RawItem) -> RawItem:
        spider: SidekickSpider = self._crawler.spider # type: ignore[reportAttributeAccessIssue]
        url: str = item["url"]
        body: bytes = item.get("body") or b""
        media_type: str | None = item.get("media_type")
        format_id: str | None = item.get("format_id")
        title: str = item.get("title") or ""

        spec = self._resolve_format(url, format_id, media_type, body)

        entities: list[dict] = [{"type": "source-url", "name": url}]
        if title:
            entities.append({"type": "title", "name": title})

        topics: list[str] | None = None

        artifact_id = f"art_{ulid.new()}"
        _, geo_str = spider_beat_geo_str(spider)
        beat_str = _resolve_item_beat(item, spider)
        period_start = _parse_period_date(item.get("period_start"))
        period_end = _parse_period_date(item.get("period_end"))
        event_group = item.get("event_group")
        profile = _resolve_processing_profile(item, spider)
        artifact = Artifact(
            id=artifact_id,
            title=title,
            content_type=spec.content_type,
            stage=spec.stage,
            media_type=spec.stored_mime_type,
            processing_profile=profile,
            source_id=spider.source_id,
            event_group=event_group,
            beat=beat_str,
            geo=geo_str,
            entities=entities,
            topics=topics,
            created_by=f"spider:{spider.name}",
            period_start=period_start,
            period_end=period_end,
        )

        if spec.is_async:
            artifact.status = ArtifactStatus.PENDING_ACQUISITION
            artifact.acquisition_url = url
            self._artifact_store.write(artifact)
            self._ctx.artifact_results.setdefault(spider.source_id, []).append({
                "artifact_id": artifact_id,
                "stage": spec.stage,
                "content_type": spec.content_type,
                "media_type": spec.stored_mime_type,
                "status": "pending_acquisition",
                "processing_profile": profile,
            })
            logger.debug(
                "Wrote stub artifact %s for async format %s: %s",
                artifact_id, spec.format_id, url,
            )
            return item

        key = S3ObjectStore.artifact_key(str(spec.stage), beat_str, geo_str, artifact_id)
        artifact.content_uri = self._object_store.put(
            key, body, content_type=spec.stored_mime_type
        )

        self._artifact_store.write(artifact)
        self._ctx.artifact_results.setdefault(spider.source_id, []).append({
            "artifact_id": artifact_id,
            "stage": spec.stage,
            "content_type": spec.content_type,
            "media_type": spec.stored_mime_type,
            "status": "active",
            "processing_profile": profile,
        })
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
                raise DropItem(
                    f"Unknown format_id declared by spider: {format_id!r}")

            # Validate: run detection and warn on mismatch, but trust the declaration
            try:
                detected = detect_format(
                    url, media_type, body[:128] if body else None)
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
        raise DropItem(
            f"Spider must declare format_id for every RawItem (url={url!r})")
