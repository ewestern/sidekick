"""Source Examination Agent — code-gen agent that writes Scrapy spiders."""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from sidekick.agents.tools.http import fetch_url as http_fetch, strip_html_noise
from sidekick.spiders._format_registry import FORMAT_REGISTRY, AcquisitionMethod

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai:gpt-5.4-mini"

# Resolved at import time — spiders always live next to this package.
_SPIDERS_DIR = Path(__file__).parent.parent.parent / "spiders"

_EXAMINATION_MAX_BYTES = 200_000

def _resolve_spider_destination(filename: str) -> Path | None:
    """Return a safe destination path for a generated spider filename."""
    candidate = Path(filename)
    if candidate.suffix != ".py" or candidate.name.startswith("_"):
        return None
    if candidate.name != filename:
        return None
    return _SPIDERS_DIR / candidate.name


def _validate_spider_code(code: str, filename: str) -> str | None:
    """Return an error string if the code is invalid, else None.

    Checks:
    - Valid Python syntax (ast.parse)
    - Safe module structure (restricted imports; no top-level executable code)
    - Contains at least one class that inherits from SidekickSpider
    - That class has source_id, endpoint, beat, geo class attributes
    """
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as exc:
        return f"Syntax error: {exc}"

    spider_classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [
            (b.id if isinstance(b, ast.Name) else getattr(b, "attr", None))
            for b in node.bases
        ]
        if "SidekickSpider" in bases:
            spider_classes.append(node)

    if not spider_classes:
        return "No class inheriting from SidekickSpider found"

    required_attrs = {"name", "source_id", "endpoint", "beat", "geo"}
    for cls_node in spider_classes:
        defined = set()
        for item in cls_node.body:
            if isinstance(item, ast.Assign):
                for t in item.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
        missing = required_attrs - defined
        if missing:
            return f"Class {cls_node.name} is missing required attributes: {missing}"

    return None


def _has_detail_callback_method(code: str, filename: str) -> bool:
    """Return True if a SidekickSpider class defines parse_* callbacks."""
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [
            (b.id if isinstance(b, ast.Name) else getattr(b, "attr", None))
            for b in node.bases
        ]
        if "SidekickSpider" not in bases:
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name.startswith("parse_"):
                return True
    return False

@tool
def fetch_url(page_url: str) -> str:
    """GET a URL to inspect its structure.

    Returns JSON: status_code, final_url, content_type, body_encoding, body,
    truncated, error, candidate_asset_urls. Text body is capped at 200 KB;
    HTML has scripts, styles, and comments stripped to reduce noise, but
    candidate_asset_urls preserves likely raw media/document links found in
    the full HTML (including script/config blocks). Binary responses return
    an empty body with the content_type so you can identify the format.
    """
    result = http_fetch(page_url, max_bytes=_EXAMINATION_MAX_BYTES)
    d = result.to_dict()
    if d.get("content_type", "").split(";")[0].strip() == "text/html":
        raw_body = d.get("body", "")
        d["body"] = strip_html_noise(raw_body)
    else:
        d["body"] = ""
    return json.dumps(d)

@tool
def write_spider(filename: str, code: str) -> str:
    """Write a generated Scrapy spider to the spiders package.

    ``filename`` must end in ``.py`` and must not start with ``_``.
    ``code`` must be valid Python defining a class that inherits from
    ``SidekickSpider`` with required attributes: name, source_id,
    endpoint, beat, geo.

    Returns JSON with ``ok`` (bool) and either a success message or an
    ``error`` string describing what failed validation.
    """
    dest = _resolve_spider_destination(filename)
    if dest is None:
        return json.dumps(
            {
                "ok": False,
                "error": "filename must be a simple .py basename and not start with _",
            }
        )

    error = _validate_spider_code(code, filename)
    if error:
        return json.dumps({"ok": False, "error": error})

    if not _has_detail_callback_method(code, filename):
        return json.dumps(
            {
                "ok": False,
                "error": (
                    "Observed detail pages with assets, but spider has no parse_* detail callback. "
                    "Follow detail pages and extract assets there."
                ),
            }
        )
    try:
        dest.write_text(code, encoding="utf-8")
    except OSError as exc:
        return json.dumps({"ok": False, "error": f"Write failed: {exc}"})

    logger.info("Wrote spider to %s", dest)
    return json.dumps({"ok": True, "path": str(dest)})


async def examine_source(
    goal: str,
    url: str,
    beat: str,
    geo: str,
    name: str | None,
) -> str | None:
    """Run the code-gen examination agent.

    Browses ``url``, understands its structure, and writes a Scrapy spider
    to ``sidekick/spiders/``.

    Args:
        model: LangChain model string (e.g. ``"openai:gpt-5.4-mini"``).

    Returns:
        The path of the written spider file, or ``None`` if the agent did not
        call ``write_spider`` successfully.
    """

    system = CODEGEN_SYSTEM + (
        "\n\n## Source to examine\n"
        f"url={url}\nbeat={beat}\ngeo={geo}\n"
        f"name={name or '(derive from site)'}\n"
    )

    agent = create_agent(
        model=DEFAULT_MODEL,
        tools=[fetch_url, write_spider],
        system_prompt=system,
    )

    user = (
        f"Examine this source and call write_spider when finished.\n"
        f"Goal: {goal}\n"
        f"Start from: {url}"
    )

    written_path: list[str] = []

    def _run() -> None:
        invoke_config: dict[str, Any] = {"recursion_limit": 75}
        result = agent.invoke(
            {"messages": [HumanMessage(content=user)]},
            config=invoke_config,
        )
        # Scan tool messages for a successful write_spider call
        for msg in result.get("messages", []):
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and data.get("ok") and data.get("path"):
                        written_path.append(data["path"])
                except (json.JSONDecodeError, ValueError):
                    pass

    await asyncio.to_thread(_run)

    if not written_path:
        logger.warning(
            "Examination agent did not write a spider for %s", url
        )
        return None

    return written_path[-1]

def _build_format_id_table() -> str:
    """Generate the format_id reference table from FORMAT_REGISTRY (single source of truth)."""
    lines = [
        "| format_id | stored_mime_type | content_type | acquisition |",
        "|---|---|---|---|",
    ]
    for fid, spec in FORMAT_REGISTRY.items():
        acq = spec.acquisition.value
        if spec.is_async:
            acq += " *(async — stub written; worker acquires later)*"
        lines.append(f'| `"{fid}"` | {spec.stored_mime_type} | {spec.content_type} | {acq} |')
    return "\n".join(lines)


_FORMAT_ID_TABLE = _build_format_id_table()

_BASE_CLASS_SOURCE = '''
# BeatIdentifier, GeoIdentifier — import from sidekick.core.vocabulary
class RawItem(scrapy.Item):
    url = scrapy.Field()        # direct document/media URL (str, required)
    title = scrapy.Field()      # human-readable title (str | None)
    format_id = scrapy.Field()  # format from FORMAT_REGISTRY — REQUIRED, see valid values below
    media_type = scrapy.Field() # observed Content-Type header (str | None)
    body = scrapy.Field()       # raw bytes downloaded by the spider (bytes, required)
    meta = scrapy.Field()       # extra dict (dict | None)

class SidekickSpider(scrapy.Spider):
    # Required class attributes
    name: str          # unique Scrapy spider name
    source_id: str     # matches Source.id in the registry (e.g. "src_springfield_council")
    endpoint: str      # listing/feed URL to start from
    beat: BeatIdentifier    # e.g. BeatIdentifier("government:city_council")
    geo: GeoIdentifier      # e.g. GeoIdentifier("us:il:springfield:springfield")
    # Optional
    schedule: str | None = None           # cron expression (e.g. "0 8 * * MON")
    expected_content: list[dict] | None = None  # [{media_type, content_type}]
'''.strip()

# ── Example spiders ───────────────────────────────────────────────────────────

_EXAMPLE_FLAT_LIST = '''
# Example 1: flat PDF listing — items are direct PDF links on the listing page
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class SpringfieldAgendaSpider(SidekickSpider):
    """City council agendas — flat list of PDF links."""

    name = "springfield-council-agendas"
    source_id = "src_springfield_council_agendas"
    endpoint = "https://springfield.gov/council/agendas"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:springfield:springfield")
    schedule = "0 8 * * MON"
    expected_content = [{"media_type": "application/pdf", "content_type": "agenda"}]

    def parse(self, response):
        for link in response.css("a[href$=\'.pdf\']"):
            url = response.urljoin(link.attrib["href"])
            title = link.css("::text").get(default="").strip() or None
            yield scrapy.Request(
                url,
                callback=self.parse_pdf,
                cb_kwargs={"title": title},
            )

    def parse_pdf(self, response, title=None):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
        )
'''.strip()

_EXAMPLE_TWO_PAGE = '''
# Example 2: two-page crawl — listing of item detail pages, each with an embedded PDF
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class RivertonMinutesSpider(SidekickSpider):
    """City council minutes — listing page links to detail pages that embed PDFs."""

    name = "riverton-council-minutes"
    source_id = "src_riverton_council_minutes"
    endpoint = "https://riverton.gov/city-clerk/minutes"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:riverton:riverton")
    schedule = "0 10 1 * *"
    expected_content = [{"media_type": "application/pdf", "content_type": "minutes"}]

    def parse(self, response):
        # Each row in the table links to a detail page
        for row in response.css("table.meetings-table tr"):
            href = row.css("a::attr(href)").get()
            title = row.css("td.meeting-date::text").get(default="").strip()
            if href:
                yield scrapy.Request(
                    response.urljoin(href),
                    callback=self.parse_detail,
                    cb_kwargs={"title": title},
                )

    def parse_detail(self, response, title=None):
        # Detail page has a direct PDF link
        pdf_href = response.css("a.document-download::attr(href)").get()
        if pdf_href:
            yield scrapy.Request(
                response.urljoin(pdf_href),
                callback=self.parse_pdf,
                cb_kwargs={"title": title},
            )

    def parse_pdf(self, response, title=None):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
        )
'''.strip()

_EXAMPLE_MULTI_ASSET = '''
# Example 3: multi-asset detail page — each meeting has BOTH a PDF agenda and a video recording.
# The spider yields one RawItem per asset; both are ingested independently.
# Note: separate parse_* callbacks per content type so format_id is set correctly.
import scrapy
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier
from sidekick.spiders._base import SidekickSpider, RawItem

class OakfieldCouncilSpider(SidekickSpider):
    """City council meetings — each item page has a PDF agenda AND a video recording."""

    name = "oakfield-council-meetings"
    source_id = "src_oakfield_council_meetings"
    endpoint = "https://oakfield.gov/council/meetings"
    beat = BeatIdentifier("government:city_council")
    geo = GeoIdentifier("us:il:oakfield:oakfield")
    schedule = "0 9 * * WED"
    expected_content = [
        {"media_type": "application/pdf", "content_type": "agenda"},
        {"media_type": "video/mp4", "content_type": "video-raw"},
    ]

    def parse(self, response):
        for link in response.css("ul.meeting-list a.meeting-link"):
            yield scrapy.Request(
                response.urljoin(link.attrib["href"]),
                callback=self.parse_meeting,
                cb_kwargs={"title": link.css("::text").get(default="").strip()},
            )
        # Pagination: follow "Next" link if present
        next_href = response.css("a.pagination-next::attr(href)").get()
        if next_href:
            yield scrapy.Request(response.urljoin(next_href), callback=self.parse)

    def parse_meeting(self, response, title=None):
        # 1. Yield the PDF agenda — use href$=".pdf" to avoid matching video links
        pdf_href = response.css("a[href$=\'.pdf\']::attr(href)").get()
        if pdf_href:
            yield scrapy.Request(
                response.urljoin(pdf_href),
                callback=self.parse_pdf,
                cb_kwargs={"title": title},
            )

        # 2. Yield the video recording — do NOT skip it because a PDF was found
        video_href = response.css("a[href$=\'.mp4\'], a.video-download::attr(href)").get()
        if video_href:
            yield scrapy.Request(
                response.urljoin(video_href),
                callback=self.parse_mp4,
                cb_kwargs={"title": title},
            )

    def parse_pdf(self, response, title=None):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            url=response.url,
            title=title,
            format_id="pdf",
            media_type=ct,
            body=response.body,
        )

    def parse_mp4(self, response, title=None):
        ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
        yield RawItem(
            url=response.url,
            title=title,
            format_id="mp4",
            media_type=ct,
            body=response.body,
        )
'''.strip()

# ── Code-gen system prompt ─────────────────────────────────────────────────────

CODEGEN_SYSTEM = f"""You are the source examination agent for a local news pipeline. \
Your job is to browse a government or public-interest source and write a **Scrapy spider** \
that will fetch new items from it on every scheduled run.

## Your tools
- **fetch_url**: GET a URL. Returns JSON with status_code, final_url, content_type, \
body_encoding, body, truncated, error, candidate_asset_urls. \
HTML has scripts, styles, and comments stripped. Binary responses return an empty body with \
the content_type.
- **write_spider**: Write the generated spider Python file to the spiders package. \
Call exactly once when you have a complete, valid spider ready.

## Base class API

```python
{_BASE_CLASS_SOURCE}
```

## Valid format_id values

Every `RawItem` **must** set `format_id` to one of these values.
Items without `format_id` are dropped by the pipeline.

{_FORMAT_ID_TABLE}

Choose the format_id based on what the URL **produces**, not the page's label for it.

## Allowed imports inside a spider file
- `scrapy` — Scrapy itself
- `re` — regex fallback extraction for script-embedded asset URLs
- `sidekick.spiders._base` — `SidekickSpider` and `RawItem`
- `sidekick.core.vocabulary` — `BeatIdentifier` and `GeoIdentifier` (REQUIRED for beat/geo attributes)

## Examination workflow

1. **Fetch the listing page** (the source endpoint). Identify how items are listed — \
direct PDF links, links to detail pages, an RSS/Atom feed, etc.
2. **Follow 2–3 sample item links** to understand item page structure. For each detail page, \
catalogue **every** downloadable asset: PDFs, videos, audio files, and any other documents. \
Do not stop after finding the first asset type. When `fetch_url` returns \
`candidate_asset_urls`, inspect those URLs too — they often surface assets hidden in scripts.
3. **Check for pagination** — next/previous links, ?page= params, load-more buttons. \
If pagination exists, implement it in the spider.
4. **Infer a publication schedule** from date patterns (weekly agendas, monthly reports). \
Set the ``schedule`` attribute as a cron expression if you can determine one.
5. **Run a pre-write verification pass**:
   - If detail pages exist, confirm you inspected at least 2 distinct detail pages.
   - Confirm spider logic extracts assets from both visible DOM elements and any \
     script/config URL tokens surfaced by `candidate_asset_urls`.
   - Confirm pagination is implemented when present.
   - Confirm all discovered asset classes are represented in parsing logic and \
     ``expected_content``.
6. **Write the spider** using ``write_spider``. The filename should be \
``{{beat}}_{{geo_slug}}_{{content_type}}.py``, e.g. ``city_council_springfield_il_agendas.py``.

## Spider rules
- Spiders must inherit from ``SidekickSpider`` and set all required class attributes.
- **Beat and geo MUST use identifier objects**: Import `BeatIdentifier` and `GeoIdentifier` from \
  `sidekick.core.vocabulary`, then set `beat = BeatIdentifier("domain:subdomain")` and \
  `geo = GeoIdentifier("country:state:county:city")`. Use canonical colon-delimited IDs \
  that exist in the vocabulary trees. The pipeline and registry serialize with `str()` where needed.
- **Every ``RawItem`` must set ``format_id``** to a value from the table above. Items without \
  ``format_id`` are dropped by the pipeline. Choose based on what the URL produces, \
  not what the page says — a Cablecast player link ending in `.m3u8` → `"hls"`, a \
  `/publicfiles/123.pdf` link → `"pdf"`.
- **Use separate ``parse_*`` callbacks per content type** so ``format_id`` can be set \
  correctly at yield time. Do not share a generic ``parse_asset`` callback across content types.
- **Target content types by page context, not URL shape alone.** URL paths and extensions \
  are often shared across content types. When examining a detail page, identify the \
  semantic signals that reliably distinguish each type: the element tag and attributes \
  (`embed[type]`, `object[type]`, `source[type]`), the surrounding container or heading, \
  ARIA labels, link text, or button labels. Write selectors that exploit whatever distinguishes \
  the assets on *this specific page* — do not assume a file extension or path prefix is unique. \
  However, whatever rule you discover should generalize to other pages of the same source.
- ``RawItem.body`` must always be set to the raw response bytes (``response.body``).
- Set ``media_type`` from the response Content-Type header when possible.
- Use ``response.css()`` or ``response.xpath()`` for selector-based extraction.
- **XPath does not support wildcard attribute-name suffixes.** ``//@data-*`` is invalid. \
- Use ``response.urljoin()`` to resolve relative URLs.
- Do not hardcode dates or time-sensitive state in selectors.
- **Yield one ``RawItem`` per asset, not one per page.** The pipeline stores and processes each asset \
independently downstream.
- When listings link to detail pages, follow those detail pages and extract assets from BOTH \
visible links/media tags and script/config URL tokens (for example `.pdf`, `.mp4`, `.m3u8`, \
or download-style URLs).
- List all discovered content types in ``expected_content`` (one entry per type).
- If the source requires JS rendering or authentication, call ``write_spider`` with a \
spider whose ``parse`` method yields no items and has a docstring explaining why \
(so the developer knows to handle it manually).

## Failure conditions
If the source requires login, serves no parseable content, or is clearly not a \
recurring public-interest source, write a minimal spider with a ``parse`` that \
yields nothing and a class-level ``notes`` string explaining the failure.

## Examples

### Example 1 — flat PDF listing
```python
{_EXAMPLE_FLAT_LIST}
```

### Example 2 — two-page crawl (single asset per detail page)
```python
{_EXAMPLE_TWO_PAGE}
```

### Example 3 — multi-asset detail page (PDF + video on the same page)
```python
{_EXAMPLE_MULTI_ASSET}
```
"""