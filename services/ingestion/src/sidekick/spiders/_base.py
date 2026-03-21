"""Spider base class, item type, and metadata model."""

from __future__ import annotations

import scrapy
from pydantic import BaseModel, field_validator

from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier


class RawItem(scrapy.Item):
    """A single document or media asset discovered by a spider.

    The spider downloads the body in its own callbacks and populates ``body``
    directly — the pipeline only persists, it does not re-download.

    ``format_id`` is the spider's declaration of what content type this URL is
    expected to produce (e.g. ``"pdf"``, ``"hls"``, ``"mp4"``).  It must match
    a key in ``FORMAT_REGISTRY``.  When present the pipeline uses it directly
    and treats ``detect_format`` as a validation step.  When absent the pipeline
    falls back to signal-based detection.

    ``media_type`` is the raw ``Content-Type`` response header, preserved for
    the validation comparison even when ``format_id`` is declared.
    """

    url = scrapy.Field()        # direct document/media URL (str, required)
    title = scrapy.Field()      # human-readable title (str | None)
    format_id = scrapy.Field()  # declared format from FORMAT_REGISTRY (str | None)
    media_type = scrapy.Field() # observed Content-Type header (str | None)
    body = scrapy.Field()       # raw bytes downloaded by the spider callback (bytes)
    meta = scrapy.Field()       # extra metadata dict (dict | None)


class SpiderMeta(BaseModel):
    """Pydantic model for validating spider class attributes.

    Used by ``SidekickSpider.get_meta()`` and by ``discover_spiders()`` to
    ensure every generated spider carries the required registration fields.
    """

    name: str
    source_id: str
    endpoint: str
    beat: str
    geo: str
    schedule: str | None = None          # cron expression (e.g. "0 8 * * MON")
    expected_content: list[dict] | None = None

    @field_validator("beat", mode="before")
    @classmethod
    def _beat_to_str(cls, v: object) -> str:
        if not isinstance(v, BeatIdentifier):
            raise TypeError(f"beat must be BeatIdentifier, got {type(v).__name__}")
        return str(v)

    @field_validator("geo", mode="before")
    @classmethod
    def _geo_to_str(cls, v: object) -> str:
        if not isinstance(v, GeoIdentifier):
            raise TypeError(f"geo must be GeoIdentifier, got {type(v).__name__}")
        return str(v)


def spider_beat_geo_str(spider: "SidekickSpider") -> tuple[str, str]:
    """Canonical beat/geo strings for Artifact rows, registry sync, and object keys."""
    return str(spider.beat), str(spider.geo)


class SidekickSpider(scrapy.Spider):
    """Base class for all sidekick spiders.

    Subclasses **must** define these class attributes::

        name: str               — Scrapy spider name (unique across project)
        source_id: str          — matches Source.id in the registry
        endpoint: str           — the listing/feed URL to start from
        beat: BeatIdentifier    — e.g. ``BeatIdentifier("domain:subdomain")``
        geo: GeoIdentifier    — e.g. ``GeoIdentifier("country:state:county:city")``

    Optional::

        schedule: str | None    — cron expression; None = no scheduled run
        expected_content: list[dict] | None  — [{media_type, content_type}]

    The ``parse`` method must yield ``RawItem`` instances or ``scrapy.Request``
    objects. Each ``RawItem`` must have ``url``, ``body`` (bytes), and optionally
    ``title`` and ``media_type`` set before being yielded.
    """

    source_id: str
    endpoint: str
    beat: BeatIdentifier
    geo: GeoIdentifier
    schedule: str | None = None
    expected_content: list[dict] | None = None

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
            beat=cls.beat,
            geo=cls.geo,
            schedule=getattr(cls, "schedule", None),
            expected_content=getattr(cls, "expected_content", None),
        )

    async def start(self):
        yield scrapy.Request(self.endpoint, callback=self.parse)
