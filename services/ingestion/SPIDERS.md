# Writing Sidekick Spiders

Sidekick spiders are standard Scrapy spiders with a thin base class that registers them in the source registry. This guide covers everything you need to write one by hand.

---
 ## https://docs.python.org/3/library/datetime.html#format-codes 

## Quick start

```bash
# 1. Generate a stub
sidekick spiders scaffold us:ca:shasta:redding https://example.gov/meetings agendas \
  --beat government:city-council \
  --schedule "0 8 * * MON"

# 2. Inspect the page
sidekick fetch-url https://example.gov/meetings

# 3. Edit the stub — implement parse() and callbacks
# 4. Test without writing artifacts
sidekick spiders test <source_id> --dry-run

# 5. Register in the database
sidekick spiders sync
```

---

## Naming convention

All names are derived from **geo** and **source slug**. Beat is optional metadata, not part of spider identity.

| Component | Definition | Example |
|---|---|---|
| geo | full geo identifier | `us:ca:shasta:redding` |
| source slug | short descriptor you supply | `agendas` |

| Artefact | Pattern | Example |
|---|---|---|
| Filename | `{source_snake}.py` | `agendas.py` |
| `source_id` | `src_{geo_snake}_{source_snake}` | `src_us_ca_shasta_redding_agendas` |
| Scrapy `name` | `{geo_city}-{source_slug}` | `redding-agendas` |
| Class name | `{GeoCity}{Source}Spider` | `ReddingAgendasSpider` |

Multiple sources for the same geo are distinguished by source slug:
- `agendas.py`
- `videos.py`
- `minutes.py`

The scaffold command derives everything automatically — just pass the slug.

## File conventions

- One spider class per file, no exceptions.
- Filename follows the naming convention above — the scaffold generates this for you.
- Do **not** prefix the filename with `_` (reserved for harness files).

---

## Required class attributes

```python
class MySpider(SidekickSpider):
    name = "redding-agendas"                 # unique Scrapy name, hyphen-separated
    source_id = "src_us_ca_shasta_redding_agendas"  # unique source registry ID, snake_case
    endpoint = "https://example.gov/meetings"  # listing/feed URL
    beat = BeatIdentifier("government:city-council")  # optional default beat
    geo  = GeoIdentifier("us:ca:shasta:redding")
    schedule = "0 8 * * MON"  # cron expression; None = no scheduled run
    # default_processing_profile = "full"  # optional; see RawItem
```

### Valid beats

```
government:city-council
government:city-council:budget
government:board-of-supervisors
government:board-of-supervisors:budget
education:school-board
education:school-board:budget
housing-zoning:zoning-board
public-safety:police-department
budget-finance
```

### Valid geos

```
us:ca:tulare:visalia
us:ca:san-bernardino:san-bernardino
us:ca:shasta:redding
us:il:springfield:springfield
```

Add new geos/beats to `packages/core/src/sidekick/core/vocabulary.py` — both the tree and the design doc must be updated together.

---

## RawItem fields

Every `yield` from a spider must be either a `scrapy.Request` or a fully populated `RawItem`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `url` | `str` | yes | Direct URL of the document/media asset |
| `format_id` | `str` | yes | Must be a key in `FORMAT_REGISTRY` (see below) |
| `body` | `bytes` | yes | Raw response bytes — download in the callback |
| `title` | `str \| None` | no | Human-readable title from the source |
| `media_type` | `str \| None` | no | Raw `Content-Type` header value |
| `period_start` | `str \| None` | no | ISO date the document covers (`"2026-03-11"`) |
| `period_end` | `str \| None` | no | Same as `period_start` for point-in-time docs |
| `event_group` | `str \| None` | no | Event grouping tag stored on the artifact |
| `beat` | `str \| None` | no | Canonical beat for this specific artifact. When omitted, pipeline falls back to spider `beat`, then leaves it null |
| `processing_profile` | `str \| None` | no | `full` \| `structured` \| `index` \| `evidence` — downstream CPU/LLM routing (see `docs/ARTIFACT_STORE.md`). Omitted → spider `default_processing_profile` or `full` |
| `meta` | `dict \| None` | no | Any extra metadata you want to preserve |

Optional on the spider class: `default_processing_profile` — same values as above; used when a `RawItem` omits `processing_profile`.

Optional on the spider class: `wait_for_selector` — CSS selector string for Playwright-backed spiders. When set, `SidekickSpider` automatically adds `PageMethod("wait_for_selector", selector)` in `start()` before calling `parse()`, so you usually do not need to override `start()` just to wait for dynamic content.

### Valid format_ids

| `format_id` | Acquisition | stored contract |
|---|---|---|
| `"txt"` | Inline text | `processed` + `document-text` |
| `"pdf"` | HTTP download | `document-raw` |
| `"html"` | Inline text | `document-raw` |
| `"xlsx"` | HTTP download | `document-raw` |
| `"csv"` | Inline text | `document-raw` |
| `"docx"` | HTTP download | `document-raw` |
| `"mp3"` | HTTP download | `audio-raw` |
| `"wav"` | HTTP download | `audio-raw` |
| `"hls"` | ffmpeg (async) | `audio-raw` |
| `"mp4"` | HTTP download | `video-raw` |

Async formats (`hls`, `mpeg-ts`) write a stub artifact and trigger acquisition — you still yield them the same way.

Use `format_id="txt"` only when the body is already canonical enrichment-ready plain text. If you are storing markup or binary source material, keep the source format instead.

---

## Common patterns

### Pattern A: Listing → detail → PDF

```python
def parse(self, response):
    for href in response.css("table.meetings a::attr(href)").getall():
        yield scrapy.Request(response.urljoin(href), callback=self.parse_detail)

    next_page = response.css("a.next-page::attr(href)").get()
    if next_page:
        yield scrapy.Request(response.urljoin(next_page), callback=self.parse)

def parse_detail(self, response):
    title = response.css("h1::text").get("").strip()
    iso_date = self._parse_date(response.css(".meeting-date::text").get(""))
    for pdf_href in response.css("a[href$='.pdf']::attr(href)").getall():
        yield scrapy.Request(
            response.urljoin(pdf_href),
            callback=self.parse_pdf,
            cb_kwargs={"title": title, "iso_date": iso_date},
        )

def parse_pdf(self, response, title=None, iso_date=None):
    ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
    yield RawItem(
        url=response.url, title=title, format_id="pdf",
        media_type=ct, body=response.body,
        period_start=iso_date, period_end=iso_date,
    )
```

### Pattern B: JSON API / feed

```python
def parse(self, response):
    data = response.json()
    for item in data["results"]:
        yield scrapy.Request(
            item["document_url"],
            callback=self.parse_pdf,
            cb_kwargs={"title": item.get("title"), "iso_date": item.get("date")},
        )
    if data.get("next"):
        yield scrapy.Request(data["next"], callback=self.parse)
```

### Pattern C: Inline HTML (store the page itself)

```python
def parse(self, response):
    for href in response.css("a.agenda::attr(href)").getall():
        yield scrapy.Request(response.urljoin(href), callback=self.parse_html_page)

def parse_html_page(self, response, title=None, iso_date=None):
    ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
    yield RawItem(
        url=response.url, title=title, format_id="html",
        media_type=ct, body=response.body,
        period_start=iso_date, period_end=iso_date,
    )
```

### Pattern D: HLS video manifest

```python
def parse_show(self, response, title=None, iso_date=None):
    m3u8_url = response.css("video source::attr(src)").get()
    if m3u8_url:
        yield scrapy.Request(
            response.urljoin(m3u8_url),
            callback=self.parse_hls,
            cb_kwargs={"title": title, "iso_date": iso_date},
        )

def parse_hls(self, response, title=None, iso_date=None):
    ct = response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
    yield RawItem(
        url=response.url, title=title, format_id="hls",
        media_type=ct, body=response.body,
        period_start=iso_date, period_end=iso_date,
        meta={"source": "video manifest"},
    )
```

---

## Selectors

Scrapy exposes the parsed DOM as a `response` object. Two query languages are available: CSS (default, recommended) and XPath (for things CSS cannot express). Both return `SelectorList` objects with `.get()` / `.getall()`.

### Reference DOM

All examples below target this HTML:

```html
<div class="meetings-list">

  <div class="meeting-row featured">
    <h2><a href="/meetings/42">City Council — March 11, 2026</a></h2>
    <span class="date">March 11, 2026</span>
    <span class="status">Approved</span>
    <ul class="documents">
      <li><a href="/files/agenda-42.pdf" data-type="agenda">Agenda</a></li>
      <li><a href="/files/minutes-42.pdf" data-type="minutes">Minutes</a></li>
    </ul>
    <a class="video-link" href="https://video.example.com/watch?v=abc">Watch</a>
  </div>

  <div class="meeting-row">
    <h2><a href="/meetings/41">City Council — Feb 25, 2026</a></h2>
    <span class="date">Feb 25, 2026</span>
    <span class="status">Approved</span>
    <ul class="documents">
      <li><a href="/files/agenda-41.pdf" data-type="agenda">Agenda</a></li>
    </ul>
  </div>

</div>

<nav class="pagination">
  <a href="/meetings?page=2" rel="next">Next</a>
</nav>
```

---

### CSS selectors — the basics

**Select by element, class, id, attribute:**

```python
response.css("div")                  # all <div> elements
response.css(".meeting-row")         # class="meeting-row" (or contains it)
response.css("#main-content")        # id="main-content"
response.css("a[rel='next']")        # attribute equals value
response.css("a[href]")              # attribute exists
```

**Scrapy pseudo-elements** — these are Scrapy extensions, not standard CSS:

```python
response.css("span.date::text")         # text node directly inside the element
response.css("a::attr(href)")           # value of the href attribute
response.css("div::attr(data-id)")      # any attribute works
```

**`.get()` vs `.getall()`:**

```python
response.css("span.date::text").get()           # first match or None
response.css("span.date::text").get("")         # first match or "" (safe default)
response.css(".meeting-row h2 a::attr(href)").getall()  # all matches as list
```

---

### Navigating the tree — combinators

The combinator goes between two parts of the selector and controls how they relate in the DOM.

| Combinator | Syntax | Meaning |
|---|---|---|
| Descendant | `A B` | B anywhere inside A (any depth) |
| Child | `A > B` | B is a direct child of A |
| Adjacent sibling | `A + B` | B immediately after A, same parent |
| General sibling | `A ~ B` | B anywhere after A, same parent |

```python
# Descendant — <a> anywhere inside .meeting-row
response.css(".meeting-row a::attr(href)").getall()
# → ['/meetings/42', '/files/agenda-42.pdf', '/files/minutes-42.pdf',
#    'https://video.example.com/watch?v=abc', '/meetings/41', ...]

# Child — only direct children
response.css(".documents > li > a::attr(href)").getall()
# → ['/files/agenda-42.pdf', '/files/minutes-42.pdf', '/files/agenda-41.pdf']

# Adjacent sibling — span.status immediately after span.date
response.css("span.date + span.status::text").getall()
# → ['Approved', 'Approved']

# General sibling — .video-link after .documents, same parent
response.css(".documents ~ .video-link::attr(href)").getall()
# → ['https://video.example.com/watch?v=abc']
```

---

### Attribute filters

```python
# exact match
response.css("a[data-type='agenda']::attr(href)").getall()
# → ['/files/agenda-42.pdf', '/files/agenda-41.pdf']

# starts with
response.css("a[href^='/files/']::attr(href)").getall()
# → ['/files/agenda-42.pdf', '/files/minutes-42.pdf', '/files/agenda-41.pdf']

# ends with
response.css("a[href$='.pdf']::attr(href)").getall()
# → ['/files/agenda-42.pdf', '/files/minutes-42.pdf', '/files/agenda-41.pdf']

# contains substring
response.css("a[href*='agenda']::attr(href)").getall()
# → ['/files/agenda-42.pdf', '/files/agenda-41.pdf']
```

---

### Scoping: running a selector inside a result

`.css()` can be called on any `Selector`, not just `response`. Use this to scope a query to a specific node, which is much cleaner than building a single long selector.

```python
# Iterate rows, then query within each row
for row in response.css(".meeting-row"):
    title = row.css("h2 a::text").get("").strip()
    date  = row.css("span.date::text").get("").strip()
    pdfs  = row.css("a[href$='.pdf']::attr(href)").getall()
    # title, date, and pdfs are all scoped to this one row
```

This is the primary pattern for pages with repeated structures. Prefer it over trying to zip together parallel `.getall()` lists.

---

### Collecting all text inside an element

`::text` only captures direct text nodes. For elements with mixed content (text inside child tags), use `*::text`:

```html
<p class="summary">Agenda item: <strong>Budget</strong> discussion and <em>vote</em>.</p>
```

```python
response.css(".summary::text").getall()
# → ['Agenda item: ', ' discussion and ', '.']   ← misses 'Budget' and 'vote'

" ".join(response.css(".summary *::text").getall()).strip()
# → 'Agenda item:  Budget  discussion and  vote .'  ← all text, some extra spaces

" ".join(response.css(".summary *::text").getall()).split()
# → ['Agenda', 'item:', 'Budget', 'discussion', 'and', 'vote.']
```

---

### XPath — when CSS isn't enough

CSS cannot traverse upward or filter by text content. Use XPath for those cases. You can mix `.css()` and `.xpath()` freely.

**Find a node by its text content:**

```python
# Find the <li> that contains the word "Minutes"
response.xpath("//li[contains(., 'Minutes')]")

# Get its link href
response.xpath("//li[contains(., 'Minutes')]/a/@href").get()
# → '/files/minutes-42.pdf'
```

**Navigate to a parent (`.`/`..`):**

```python
# Start from a known child, walk up to the row, then find the date
response.xpath("//a[@class='video-link']/ancestor::div[@class='meeting-row']//span[@class='date']/text()").get()
# → 'March 11, 2026'

# Simpler: just go up one level with ..
response.xpath("//span[@class='status'][.='Approved']/../span[@class='date']/text()").getall()
# → ['March 11, 2026', 'Feb 25, 2026']
```

**Filter by multiple classes** (CSS `.a.b` works; XPath requires `contains`):

```python
# CSS — element that has both classes
response.css(".meeting-row.featured h2 a::text").get()
# → 'City Council — March 11, 2026'

# XPath equivalent (needed if you're already in XPath context)
response.xpath("//div[contains(@class,'meeting-row') and contains(@class,'featured')]//h2/a/text()").get()
```

**Combining: scope with CSS, then XPath for the hard part:**

```python
for row in response.css(".meeting-row"):
    # XPath relative to the scoped selector — note the leading dot
    video = row.xpath(".//a[contains(@class,'video-link')]/@href").get()
```

---

### Script tag extraction (last resort)

When data is embedded in JavaScript, use regex against `<script>` text:

```python
import re, json

for script in response.css("script::text").getall():
    # Pattern 1: JSON blob assigned to a variable
    m = re.search(r'window\.__DATA__\s*=\s*(\{.*?\});', script, re.DOTALL)
    if m:
        data = json.loads(m.group(1))

    # Pattern 2: single string value
    m = re.search(r'"videoUrl"\s*:\s*"([^"]+)"', script)
    if m:
        video_url = m.group(1)
```

---

### Resolving URLs

Always resolve hrefs before yielding requests — many sites use relative paths:

```python
href = response.css("a.meeting-link::attr(href)").get()
# href might be "/meetings/42" or "../files/doc.pdf" or "https://full.url/..."
yield scrapy.Request(response.urljoin(href), callback=self.parse_detail)
# urljoin handles all three cases correctly
```

---

### Quick-reference

```python
# ── finding elements ─────────────────────────────────────────────────────────
response.css("div.meetings")                  # by element + class
response.css("#sidebar")                      # by id
response.css("a[rel='next']")                 # by attribute
response.css("a[href$='.pdf']")               # attribute ends-with
response.css("a[href^='https']")              # attribute starts-with
response.css("a[href*='agenda']")             # attribute contains

# ── extracting values ────────────────────────────────────────────────────────
.css("h1::text").get("")                      # direct text, safe default
.css("a::attr(href)").get()                   # attribute value
.css("a::attr(href)").getall()                # all matches
" ".join(.css(".body *::text").getall())      # all nested text

# ── combinators ──────────────────────────────────────────────────────────────
"div a"                                       # descendant (any depth)
"ul > li"                                     # direct child only
"h2 + p"                                      # immediately after, same parent
"h2 ~ p"                                      # anywhere after, same parent

# ── scoping ──────────────────────────────────────────────────────────────────
for row in response.css(".meeting-row"):      # iterate repeated structures
    row.css("span.date::text").get()          # queries are relative to row

# ── xpath escapes ────────────────────────────────────────────────────────────
.xpath(".//a/@href").get()                    # leading dot = relative to current node
.xpath("//li[contains(.,'Minutes')]/a/@href").get()  # filter by text content
.xpath("//span[@class='date']/../a/@href").get()     # walk up with ..

# ── headers ──────────────────────────────────────────────────────────────────
response.headers.get(b"Content-Type", b"").decode().split(";")[0].strip() or None
```

---

## Date parsing helper

Include this in your spider when you need to parse dates from text:

```python
def _parse_date(self, raw: str) -> str | None:
    """Return ISO date string or None."""
    from datetime import datetime
    raw = (raw or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None
```

For dates embedded in text (e.g. a title like `"City Council 03/11/2026"`):

```python
import re
m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", title or "")
iso_date = self._parse_date(m.group(1)) if m else None
```

---

## Passing data between callbacks

Use `cb_kwargs` — Scrapy serializes these safely across the crawl:

```python
yield scrapy.Request(
    url,
    callback=self.parse_detail,
    cb_kwargs={"title": title, "iso_date": iso_date},
)

def parse_detail(self, response, title=None, iso_date=None):
    ...
```

Do not use `response.meta` for passing structured data — it requires manual dict access and is error-prone.

---

## Pagination

```python
# CSS-based next link
next_href = response.css("a[rel='next']::attr(href)").get()
if next_href:
    yield scrapy.Request(response.urljoin(next_href), callback=self.parse)

# Offset/page parameter
import urllib.parse
parsed = urllib.parse.urlparse(response.url)
params = dict(urllib.parse.parse_qsl(parsed.query))
current_page = int(params.get("page", 1))
# ... if there are more results:
params["page"] = current_page + 1
next_url = parsed._replace(query=urllib.parse.urlencode(params)).geturl()
yield scrapy.Request(next_url, callback=self.parse)
```

---

## Deduplication

The pipeline deduplicates at the artifact level by `source_id` + `url`. You do not need to deduplicate in the spider. Scrapy also deduplicates requests by URL within a single run.

---

## Workflow checklist

- [ ] `sidekick spiders scaffold ...` to generate the stub
- [ ] `sidekick fetch-url <endpoint>` to inspect what the spider sees
- [ ] Implement `parse()` — yield Requests or RawItems
- [ ] All `RawItem`s have `url`, `format_id`, and `body` set
- [ ] Dates are ISO strings (`"YYYY-MM-DD"`) or `None`
- [ ] `sidekick spiders test <source_id> --dry-run` passes without errors
- [ ] `sidekick spiders sync` to register the source in the DB
- [ ] `sidekick spiders run <source_id>` to confirm real artifacts are written
