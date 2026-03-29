"""Generate stub spider files from a template.

Spiders are placed under a geo-derived subdirectory of the spiders package:

  geo "us:ca:shasta:redding"  →  spiders/us/ca/shasta/redding/
  geo "us:ca:shasta"          →  spiders/us/ca/shasta/

Filename convention within that directory: ``{source_slug}.py``

  source_slug — short descriptor supplied by the caller (e.g. "agendas", "videos", "packets")

Usage::

    from sidekick.spiders._scaffold import scaffold_spider
    path = scaffold_spider(
        geo="us:ca:shasta:redding",
        source="agendas",
        endpoint="https://example.gov/meetings",
        # schedule omitted → daily at local wall time when this runs
        beat="government:city-council",
    )
"""

from __future__ import annotations

import pathlib
import re
from datetime import datetime

_SPIDERS_DIR = pathlib.Path(__file__).parent


def _cron_daily_at_local(dt: datetime) -> str:
    """Return a 5-field cron expression that runs every day at *dt*'s local time.

    Format: ``minute hour * * *`` (standard cron, local timezone interpretation
    depends on the runtime that evaluates the schedule).
    """
    return f"{dt.minute} {dt.hour} * * *"


_TEMPLATE = '''\
"""Spider stub — {class_label}.

TODO: implement parse() and any helper callbacks.
Run `sidekick fetch-url {endpoint}` to inspect the page before writing selectors.
"""

from __future__ import annotations
from datetime import datetime

import scrapy
from sidekick.core.vocabulary import {vocabulary_imports}
from sidekick.spiders._base import RawItem, SidekickSpider


class {class_name}(SidekickSpider):
    """{class_label}."""

    name = "{spider_name}"
    source_id = "{source_id}"
    endpoint = "{endpoint}"
{beat_assignment}
    geo = GeoIdentifier("{geo}")
    schedule = {schedule_repr}
    # Change to SourceTier.SECONDARY and set outlet = "Outlet Name" for news sources
    source_tier = SourceTier.PRIMARY

    def parse(self, response):
        """Parse the listing page and yield Requests or RawItems.

        Typical patterns — pick one:

        A) Paginated listing → detail page → asset:
            for href in response.css("a.meeting-link::attr(href)").getall():
                yield scrapy.Request(response.urljoin(href), callback=self.parse_detail)
            next_page = response.css("a.next::attr(href)").get()
            if next_page:
                yield scrapy.Request(response.urljoin(next_page), callback=self.parse)

        B) Listing page with direct asset links:
            for href in response.css("a[href$=\\".pdf\\"]::attr(href)").getall():
                yield scrapy.Request(response.urljoin(href), callback=self.parse_pdf)

        C) Single-page app / JSON feed:
            data = response.json()
            for item in data["items"]:
                yield scrapy.Request(item["url"], callback=self.parse_pdf)
        """
        raise NotImplementedError("Implement parse() — see comments above")

    # ── asset callbacks ──────────────────────────────────────────────────────

    def _parse_date(self, raw: str) -> str | None:
        """Return ISO date string from a raw date string, or None."""
        raw = (raw or "").strip()
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    def parse_pdf(self, response, title=None, iso_date=None, event_group=None):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            processing_profile=ProcessingProfile.FULL,
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
            period_start=iso_date,
            period_end=iso_date,
            event_group=event_group,
        )

    # Add more callbacks here as needed (parse_detail, parse_video, etc.)
'''


def _to_snake(text: str) -> str:
    """Convert a hyphenated or colon-delimited string to snake_case."""
    return re.sub(r"[-: ]+", "_", text).lower()


def _to_pascal(text: str) -> str:
    """Convert a hyphenated/colon/space string to PascalCase."""
    words = re.sub(r"[^a-zA-Z0-9]+", " ", text).split()
    return "".join(w.capitalize() for w in words)


def _geo_to_dir(geo: str) -> pathlib.Path:
    """Convert a geo identifier to a relative directory path.

    Each colon-delimited segment becomes a directory level; hyphens are
    converted to underscores so the result is a valid Python package path.

    Examples::

        "us:ca:shasta"                    → Path("us/ca/shasta")
        "us:ca:san-bernardino:san-bernardino" → Path("us/ca/san_bernardino/san_bernardino")
    """
    parts = [seg.replace("-", "_").lower() for seg in geo.split(":")]
    return pathlib.Path(*parts)


def _names_from_parts(geo: str, source: str) -> dict:
    """Derive all naming artefacts from the two canonical inputs.

    Returns a dict with keys:
      geo_dir     — pathlib.Path relative to _SPIDERS_DIR (e.g. ``us/ca/shasta``)
      filename    — ``{source_snake}.py``
      spider_name — ``{geo_city}-{source_slug}``  (Scrapy name, hyphenated)
      source_id   — ``src_{geo_snake}_{source_snake}``
      class_name  — ``{GeoCity}{Source}Spider``
      class_label — human-readable ``"{GeoCity} — {Source}"``
    """
    geo_city = geo.split(":")[-1]     # "us:ca:shasta:redding"   → "redding"

    geo_snake = _to_snake(geo)               # "us:ca:shasta:redding" → "us_ca_shasta_redding"
    source_snake = _to_snake(source)         # "meeting-agendas" → "meeting_agendas"

    geo_city_slug = geo_city
    source_slug = source.lower().strip()

    geo_dir = _geo_to_dir(geo)
    filename = f"{source_snake}.py"
    spider_name = f"{geo_city_slug}-{source_slug}"
    source_id = f"src_{geo_snake}_{source_snake}"

    geo_city_label = geo_city.replace("-", " ").title()
    source_label = source.replace("-", " ").replace("_", " ").title()

    class_name = f"{_to_pascal(geo_city)}{_to_pascal(source)}Spider"
    class_label = f"{geo_city_label} — {source_label}"

    return {
        "geo_dir": geo_dir,
        "filename": filename,
        "spider_name": spider_name,
        "source_id": source_id,
        "class_name": class_name,
        "class_label": class_label,
    }


def scaffold_spider(
    *,
    geo: str,
    source: str,
    endpoint: str,
    schedule: str | None = None,
    beat: str | None = None,
) -> pathlib.Path:
    """Write a stub spider file to the spiders package directory.

    Args:
        geo: Validated geo identifier (e.g. ``"us:ca:shasta:redding"``).
        source: Short source descriptor slug (e.g. ``"agendas"``, ``"videos"``).
        endpoint: Starting URL for the spider.
        schedule: Cron expression (e.g. ``"0 8 * * MON"``). If omitted (``None``),
            uses daily at the local wall-clock time when this function runs.
            Pass ``""`` explicitly to omit a schedule in the stub.
        beat: Optional default beat identifier for items that do not specify one.

    Returns:
        Path to the written file.

    Raises:
        ValueError: If source slug is empty or contains invalid characters.
        FileExistsError: If the target file already exists.
    """
    source = source.strip()
    if not source or not re.match(r"^[a-z0-9][a-z0-9 _-]*$", source, re.IGNORECASE):
        raise ValueError(
            f"source slug {source!r} is invalid. "
            "Use short lowercase words, hyphens, or underscores (e.g. 'agendas', 'meeting-videos')."
        )

    names = _names_from_parts(geo, source)
    dest_dir = _SPIDERS_DIR / names["geo_dir"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / names["filename"]
    if dest.exists():
        raise FileExistsError(
            f"Spider file already exists: {dest}\n"
            "Choose a different source slug or delete the existing file."
        )

    if schedule is None:
        schedule = _cron_daily_at_local(datetime.now())
    elif schedule == "":
        schedule = None
    schedule_repr = f'"{schedule}"' if schedule else "None"
    vocabulary_imports = "GeoIdentifier, ProcessingProfile, SourceTier"
    beat_assignment = '    # Set `beat = BeatIdentifier("domain:subdomain")` if this source has a default beat'
    if beat is not None:
        vocabulary_imports = f"BeatIdentifier, {vocabulary_imports}"
        beat_assignment = f'    beat = BeatIdentifier("{beat}")'

    content = _TEMPLATE.format(
        vocabulary_imports=vocabulary_imports,
        class_label=names["class_label"],
        class_name=names["class_name"],
        spider_name=names["spider_name"],
        source_id=names["source_id"],
        endpoint=endpoint,
        beat_assignment=beat_assignment,
        geo=geo,
        schedule_repr=schedule_repr,
    )

    dest.write_text(content, encoding="utf-8")
    return dest
