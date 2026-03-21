"""Run one or more spiders to completion inside a single Scrapy CrawlerProcess."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from scrapy.crawler import CrawlerProcess

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.event_bus import EventBus
from sidekick.core.object_store import ObjectStore
from sidekick.registry.registry import SourceRegistry
from sidekick.spiders._base import SidekickSpider
from sidekick.spiders._context import deregister, register

logger = logging.getLogger(__name__)


def _make_settings(token: str, verbose: bool) -> dict[str, Any]:
    return {
        "ITEM_PIPELINES": {
            "sidekick.spiders._pipeline.ArtifactWriterPipeline": 300,
        },
        "SPIDER_MIDDLEWARES": {
            "sidekick.spiders._middleware.DeduplicationMiddleware": 543,
        },
        "SIDEKICK_RUN_TOKEN": token,
        "LOG_LEVEL": "DEBUG" if verbose else "WARNING",
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "TELNETCONSOLE_ENABLED": False,
    }


def run_spiders(
    spider_classes: list[type[SidekickSpider]],
    artifact_store: ArtifactStore,
    object_store: ObjectStore,
    registry: SourceRegistry,
    event_bus: EventBus,
    verbose: bool = False,
) -> dict[str, int]:
    """Run multiple spiders in one ``CrawlerProcess`` session.

    All spiders are started before the Twisted reactor runs so they execute
    concurrently (one reactor run per CLI invocation).

    Returns:
        Mapping of ``source_id`` → count of new artifacts written.
    """
    if not spider_classes:
        return {}

    token = register(artifact_store=artifact_store, object_store=object_store, event_bus=event_bus)
    try:
        settings = _make_settings(token, verbose)
        process = CrawlerProcess(settings=settings)

        crawlers: dict[str, Any] = {}
        for cls in spider_classes:
            crawler = process.create_crawler(cls)
            crawlers[cls.source_id] = crawler
            process.crawl(crawler)

        process.start()
    finally:
        deregister(token)

    results: dict[str, int] = {}
    for source_id, crawler in crawlers.items():
        count = int(crawler.stats.get_value("item_scraped_count", 0) or 0)
        success = crawler.stats.get_value("finish_reason") == "finished"
        spider_cls = next(c for c in spider_classes if c.source_id == source_id)
        _update_health(spider_cls, registry, success=success, new_items=count)
        results[source_id] = count

    return results


def run_spider(
    spider_cls: type[SidekickSpider],
    artifact_store: ArtifactStore,
    object_store: ObjectStore,
    registry: SourceRegistry,
    event_bus: EventBus,
    verbose: bool = False,
) -> int:
    """Run a single spider. Returns count of new artifacts written."""
    results = run_spiders(
        [spider_cls], artifact_store, object_store, registry, event_bus=event_bus, verbose=verbose
    )
    return results.get(spider_cls.source_id, 0)


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
