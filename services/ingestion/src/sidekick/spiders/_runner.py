"""Run one or more spiders to completion inside a single Scrapy CrawlerProcess."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from scrapy.crawler import CrawlerProcess

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.object_store import ObjectStore
from sidekick.registry.registry import SourceRegistry
from sidekick.spiders._base import SidekickSpider
from sidekick.spiders._context import deregister, get, register

logger = logging.getLogger(__name__)


@dataclass
class ArtifactRef:
    """Minimal per-artifact routing metadata emitted after a spider run."""

    artifact_id: str
    stage: str
    content_type: str
    media_type: str
    status: str
    processing_profile: str | None = None


@dataclass
class RunResult:
    """Result of a single spider run."""

    source_id: str
    artifacts: list[ArtifactRef]
    count: int


def _abort_request(request: Any) -> bool:
    """Abort resource types that are not needed for DOM rendering."""
    return request.resource_type in {"image", "media", "font"}


def _make_settings(token: str, verbose: bool) -> dict[str, Any]:
    return {
        "ITEM_PIPELINES": {
            "sidekick.spiders._pipeline.ArtifactWriterPipeline": 300,
        },
        "SPIDER_MIDDLEWARES": {
            "sidekick.spiders._middleware.DeduplicationMiddleware": 543,
        },
        "DOWNLOADER_MIDDLEWARES": {
            "sidekick.spiders._middleware.PlaywrightMiddleware": 100,
        },
        "SIDEKICK_RUN_TOKEN": token,
        "LOG_LEVEL": "DEBUG" if verbose else "WARNING",
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "TELNETCONSOLE_ENABLED": False,
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "PLAYWRIGHT_ABORT_REQUEST": _abort_request,
    }


def run_spiders(
    spider_classes: list[type[SidekickSpider]],
    artifact_store: ArtifactStore,
    object_store: ObjectStore,
    registry: SourceRegistry,
    verbose: bool = False,
    max_items: int | None = None,
    min_date: date | None = None,
) -> dict[str, RunResult]:
    """Run multiple spiders in one ``CrawlerProcess`` session.

    All spiders are started before the Twisted reactor runs so they execute
    concurrently (one reactor run per CLI invocation).

    Args:
        max_items: When set, each spider stops emitting new ``RawItem``s and
            ``Request``s after this many non-deduplicated items for that spider
            (same limit value for every spider in the batch).
        min_date: When set, items and requests whose date is known and falls
            before this cutoff are dropped without downloading the asset body.

    Returns:
        Mapping of ``source_id`` → ``RunResult`` with artifact metadata and count.
    """
    if not spider_classes:
        return {}

    token = register(
        artifact_store=artifact_store,
        object_store=object_store,
        max_items=max_items,
        min_date=min_date,
    )
    artifact_results: dict[str, list[dict]] = {}
    try:
        settings = _make_settings(token, verbose)
        process = CrawlerProcess(settings=settings)

        if verbose:
            # scrapy.core.scraper logs every item at DEBUG including raw body bytes
            logging.getLogger("scrapy.core.scraper").setLevel(logging.INFO)

        crawlers: dict[str, Any] = {}
        for cls in spider_classes:
            crawler = process.create_crawler(cls)
            crawlers[cls.source_id] = crawler
            process.crawl(crawler)

        process.start()
        artifact_results = dict(get(token).artifact_results)
    finally:
        deregister(token)

    results: dict[str, RunResult] = {}
    for source_id, crawler in crawlers.items():
        count = int(crawler.stats.get_value("item_scraped_count", 0) or 0)
        success = crawler.stats.get_value("finish_reason") == "finished"
        spider_cls = next(
            c for c in spider_classes if c.source_id == source_id)
        _update_health(spider_cls, registry, success=success, new_items=count)
        artifacts = [
            ArtifactRef(**a) for a in artifact_results.get(source_id, [])
        ]
        results[source_id] = RunResult(
            source_id=source_id, artifacts=artifacts, count=count)

    return results


def run_spider(
    spider_cls: type[SidekickSpider],
    artifact_store: ArtifactStore,
    object_store: ObjectStore,
    registry: SourceRegistry,
    verbose: bool = False,
    max_items: int | None = None,
    min_date: date | None = None,
) -> RunResult:
    """Run a single spider. Returns a ``RunResult`` with artifact metadata and count."""
    results = run_spiders(
        [spider_cls],
        artifact_store,
        object_store,
        registry,
        verbose=verbose,
        max_items=max_items,
        min_date=min_date,
    )
    return results.get(
        spider_cls.source_id,
        RunResult(source_id=spider_cls.source_id, artifacts=[], count=0),
    )


def _update_health(
    spider_cls: type[SidekickSpider],
    registry: SourceRegistry,
    *,
    success: bool,
    new_items: int,
) -> None:
    now = datetime.now(UTC).isoformat()
    health_update: dict[str, Any] = {
        "last_checked": now,
        "status": "active" if success else "error",
    }
    if success and new_items > 0:
        health_update["last_new_item"] = now
    try:
        registry.update_health(spider_cls.source_id, health_update)
    except Exception:
        logger.exception(
            "Failed to update health for source %s", spider_cls.source_id
        )
