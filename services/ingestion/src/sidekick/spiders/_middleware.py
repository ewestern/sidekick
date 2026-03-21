"""Scrapy spider middleware — deduplicates items against already-ingested URLs."""

from __future__ import annotations

import logging

from scrapy import signals

from sidekick.spiders._base import SidekickSpider, RawItem
from sidekick.spiders._context import get as get_context

logger = logging.getLogger(__name__)


class DeduplicationMiddleware:
    """Spider middleware that drops ``RawItem``s whose URL was already ingested.

    On ``spider_opened`` it queries the artifact store for existing raw artifacts
    for the current ``source_id`` and extracts ``source-url`` entity values into
    an in-memory ``seen`` set.  Items whose ``url`` is in ``seen`` are dropped;
    new URLs are added to ``seen`` to prevent duplicates within a single run.
    """

    @classmethod
    def from_crawler(cls, crawler):
        ctx = get_context(crawler.settings["SIDEKICK_RUN_TOKEN"])
        instance = cls(ctx.artifact_store)
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def __init__(self, artifact_store) -> None:
        self._artifact_store = artifact_store
        self._seen: set[str] = set()

    def spider_opened(self, spider: SidekickSpider) -> None:
        """Load existing URLs from the artifact store before crawling starts."""
        artifacts = self._artifact_store.query(
            filters={"source_id": spider.source_id, "stage": "raw"},
            limit=10_000,
        )
        for art in artifacts:
            if art.entities:
                for entity in art.entities:
                    if entity.get("type") == "source-url":
                        self._seen.add(entity["name"])
        logger.debug(
            "DeduplicationMiddleware: %d seen URLs loaded for source %s",
            len(self._seen),
            spider.source_id,
        )

    async def process_spider_output(self, response, result):
        async for item in result:
            if isinstance(item, RawItem):
                url = item.get("url")
                if url and url in self._seen:
                    logger.debug("Dedup: skipping already-seen URL %s", url)
                    continue
                if url:
                    self._seen.add(url)
            yield item
