"""Spider base class, item type, and metadata model."""

from __future__ import annotations

import scrapy
from pydantic import BaseModel
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier, ProcessingProfile, SourceTier


class RawItem(scrapy.Item):
    """A single document or media asset discovered by a spider.

    The spider downloads the body in its own callbacks and populates ``body``
    directly — the pipeline only persists, it does not re-download.

    ``format_id`` is the spider's declaration of how the body should be stored
    and interpreted at ingest (e.g. ``"pdf"``, ``"txt"``, ``"hls"``, ``"mp4"``).
    It must match a key in ``FORMAT_REGISTRY``. When present the pipeline uses
    it directly and treats ``detect_format`` as a validation step. When absent
    the pipeline falls back to signal-based detection.

    ``media_type`` is the raw ``Content-Type`` response header, preserved for
    validation comparison even when ``format_id`` is declared.

    ``period_start`` / ``period_end`` are ISO date strings (``"YYYY-MM-DD"``)
    for the period the document *covers* — the meeting date, report date, etc.
    Set both to the same value for point-in-time documents.  Leave as ``None``
    when the date cannot be reliably extracted from the source.

    ``processing_profile`` is optional; when omitted, :attr:`SidekickSpider.default_processing_profile`
    or ``full`` is used (see ingestion pipeline).
    """

    url = scrapy.Field(
        required=True,
    )          # direct document/media URL (str, required)
    title = scrapy.Field(
        required=True,
    )        # human-readable title (str)
    format_id = scrapy.Field()    # declared format from FORMAT_REGISTRY (str | None)
    media_type = scrapy.Field()   # observed Content-Type header (str | None)
    body = scrapy.Field()         # raw bytes downloaded by the spider callback (bytes)
    meta = scrapy.Field()         # extra metadata dict (dict | None)
    # ISO date the document covers, e.g. "2026-03-11" (str | None)
    period_start = scrapy.Field()
    # ISO date end of covered period (str | None); equals period_start for point-in-time docs
    period_end = scrapy.Field()
    event_group = scrapy.Field()  # event group identifier (str | None)
    # ProcessingProfile value (str) — full | structured | index | evidence
    processing_profile = scrapy.Field(
        required=True,
    )
    # Optional canonical beat classification for this specific artifact.
    beat = scrapy.Field()


class SpiderMeta(BaseModel):
    """Pydantic model for validating spider class attributes.

    Used by ``SidekickSpider.get_meta()`` and by ``discover_spiders()`` to
    ensure every generated spider carries the required registration fields.
    """

    name: str
    source_id: str
    endpoint: str
    beat: BeatIdentifier | None = None
    geo: GeoIdentifier
    schedule: str | None = None          # cron expression (e.g. "0 8 * * MON")
    source_tier: SourceTier = SourceTier.PRIMARY
    outlet: str | None = None            # required when source_tier=SECONDARY


def spider_beat_geo_str(spider: "SidekickSpider") -> tuple[str | None, str]:
    """Canonical beat/geo strings for Artifact rows, registry sync, and object keys."""
    beat = str(spider.beat) if spider.beat is not None else None
    return beat, str(spider.geo)


class SidekickSpider(scrapy.Spider):
    """Base class for all sidekick spiders.

    Subclasses **must** define these class attributes::

        name: str               — Scrapy spider name (unique across project)
        source_id: str          — matches Source.id in the registry
        endpoint: str           — the listing/feed URL to start from
        beat: BeatIdentifier | None — optional default beat for items emitted by this source
        geo: GeoIdentifier    — e.g. ``GeoIdentifier("country:state:county:city")``

    Optional::

        schedule: str | None    — cron expression; None = no scheduled run
        default_processing_profile: ProcessingProfile | None — default when RawItem omits it
        wait_for_selector: str | None — optional Playwright selector to wait for before parse

    The ``parse`` method must yield ``RawItem`` instances or ``scrapy.Request``
    objects. Each ``RawItem`` must have ``url``, ``body`` (bytes), and optionally
    ``title`` and ``media_type`` set before being yielded. Use ``format_id="txt"``
    only when ``body`` is already canonical enrichment-ready plain text; markup or
    binary source material should keep its source format.
    """

    source_id: str
    endpoint: str
    beat: BeatIdentifier | None = None
    geo: GeoIdentifier
    schedule: str | None = None
    default_processing_profile: ProcessingProfile | None = None
    wait_for_selector: str | None = None
    source_tier: SourceTier = SourceTier.PRIMARY
    outlet: str | None = None            # required when source_tier=SECONDARY

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "source_tier", SourceTier.PRIMARY) == SourceTier.SECONDARY:
            if not getattr(cls, "outlet", None):
                raise ValueError(
                    f"{cls.__name__}: source_tier=SECONDARY requires outlet to be set "
                    "(e.g. outlet = 'Associated Press')"
                )

    @classmethod
    def get_meta(cls) -> SpiderMeta:
        """Validate and return spider metadata.

        Raises:
            pydantic.ValidationError: if required attributes are missing or invalid.
        """
        return SpiderMeta(
            name=cls.name,
            source_id=cls.source_id,
            endpoint=cls.endpoint,
            beat=cls.beat,  # type: ignore[arg-type]
            geo=cls.geo,  # type: ignore[arg-type]
            schedule=getattr(cls, "schedule", None),
            source_tier=cls.source_tier,
            outlet=cls.outlet,
        )

    async def start(self):
        if self.wait_for_selector:
            from scrapy_playwright.page import PageMethod

            yield scrapy.Request(
                self.endpoint,
                callback=self.parse,
                meta={
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", self.wait_for_selector),
                    ],
                },
            )
            return

        yield scrapy.Request(self.endpoint, callback=self.parse)
