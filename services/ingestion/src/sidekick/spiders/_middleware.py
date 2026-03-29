"""Scrapy spider middleware — deduplicates items and optional per-run emission cap."""

from __future__ import annotations

import logging
from datetime import date

from scrapy import Request, signals

from sidekick.spiders._base import SidekickSpider, RawItem
from sidekick.spiders._context import get as get_context

logger = logging.getLogger(__name__)


class PlaywrightMiddleware:
    """Downloader middleware that routes every request through Playwright.

    Injects ``meta["playwright"] = True`` so the scrapy-playwright download
    handler renders the page in a headless browser. This is a no-op for requests
    that already carry the flag.
    """

    def process_request(self, request: Request, spider) -> None:
        request.meta.setdefault("playwright", True)


def _parse_iso_date(value: object) -> date | None:
    """Parse an ISO date string to a ``date``, or return ``None``."""
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


class DeduplicationMiddleware:
    """Spider middleware that drops ``RawItem``s whose URL was already ingested.

    On ``spider_opened`` it queries the artifact store for existing raw artifacts
    for the current ``source_id`` and extracts ``source-url`` entity values into
    an in-memory ``seen`` set.  Items whose ``url`` is in ``seen`` are dropped;
    new URLs are added to ``seen`` to prevent duplicates within a single run.

    When ``RunContext.max_items`` is set (e.g. via ``--max-items`` on ``spiders run``),
    after that many *new* (non-deduplicated) ``RawItem`` emissions the middleware
    stops yielding further ``RawItem``s and ``Request``s so the crawl drains
    naturally with a normal ``finished`` finish reason. URLs skipped due to the
    cap are not added to ``seen`` so a later run can ingest them.

    When ``RunContext.min_date`` is set (e.g. via ``--min-date`` on ``spiders run``),
    items and requests whose date is known and falls before that cutoff are dropped
    without downloading the asset body.  The date is read from
    ``request.cb_kwargs["iso_date"]`` for outgoing ``Request``s (preventing the
    download entirely) and from ``RawItem.period_end`` as a backstop for items
    whose date was only available after fetching the detail page.  When the date
    is ``None`` (unknown), the item or request is allowed through.
    """

    @classmethod
    def from_crawler(cls, crawler):
        ctx = get_context(crawler.settings["SIDEKICK_RUN_TOKEN"])
        instance = cls(ctx.artifact_store,
                       max_items=ctx.max_items, min_date=ctx.min_date)
        crawler.signals.connect(instance.spider_opened,
                                signal=signals.spider_opened)
        return instance

    def __init__(
        self,
        artifact_store,
        *,
        max_items: int | None = None,
        min_date: date | None = None,
    ) -> None:
        self._artifact_store = artifact_store
        self._max_items = max_items
        self._min_date = min_date
        self._seen: set[str] = set()
        self._emitted_new: int = 0
        self._cap_reached: bool = False

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

    def _is_too_old(self, item_date: date | None) -> bool:
        """Return True if ``item_date`` is known and before ``self._min_date``."""
        if self._min_date is None or item_date is None:
            return False
        return item_date < self._min_date

    async def process_spider_output(self, response, result):
        async for item in result:
            if isinstance(item, Request):
                if self._cap_reached:
                    continue
                iso_date = _parse_iso_date(item.cb_kwargs.get("iso_date"))
                if self._is_too_old(iso_date):
                    logger.debug(
                        "Min-date filter: skipping request %s (date=%s < %s)",
                        item.url, iso_date, self._min_date,
                    )
                    continue
                yield item
                continue

            if isinstance(item, RawItem):
                url = item.get("url")
                if url and url in self._seen:
                    logger.debug("Dedup: skipping already-seen URL %s", url)
                    continue
                period_end = _parse_iso_date(item.get("period_end"))
                if self._is_too_old(period_end):
                    logger.debug(
                        "Min-date filter: dropping item %s (period_end=%s < %s)",
                        url, period_end, self._min_date,
                    )
                    continue
                if self._max_items is not None and self._emitted_new >= self._max_items:
                    self._cap_reached = True
                    logger.debug(
                        "Max-items cap reached (%d); suppressing further emissions",
                        self._max_items,
                    )
                    continue
                if url:
                    self._seen.add(url)
                self._emitted_new += 1
                yield item
                if self._max_items is not None and self._emitted_new >= self._max_items:
                    self._cap_reached = True
                continue

            yield item
