# Source Registry Design

> **Status**: stable
> **Scope**: Source registry schema, spider-as-source-of-truth model, schedule handling, and trust model — authoritative for how recurring sources are described, fetched, and maintained
> **Last updated**: 2026-03-27 (`sources.status` active/inactive; list-due filter)

---

## Overview

A "source" is not a URL — it's a **recurring information channel**: something that produces documents over time. The source registry is a catalog of these channels, each described with enough metadata to drive automated fetching without human intervention.

The registry answers three questions for each source:
1. **Where** to look (endpoint, page, channel)
2. **When** to look (schedule, polling interval)
3. **How** to extract new items (Scrapy spider — hand-authored, committed to the repo)

---

## Two-Level Structure

There is a natural split between what the registry tracks and what the artifact store tracks:

- **Source** (registry): "Springfield City Council agenda page" — a channel that produces items
- **Item** (artifact store): "March 12 2026 council meeting agenda PDF" — a specific output

A source entry must contain enough information to schedule and identify the source; the spider class is the authoritative description of how to fetch from it.

### Source Entry Schema

```yaml
source:
  id: src_springfield_council_agendas
  name: Springfield City Council Agendas

  # Where to look
  endpoint: https://springfield.gov/council/agendas

  # When to check
  schedule:
    type: cron
    expr: "0 8 * * MON"
    learned: true                  # system-inferred vs. human-specified

  # What it produces (classification)
  beat: government:city-council
  geo: us:il:springfield:springfield

  # Tier — primary (default) or secondary
  source_tier: primary             # primary | secondary
  outlet: null                     # required when source_tier=secondary (e.g. "Associated Press")

  # Scheduled ingestion (inactive sources are skipped by list-due / Step Functions map)
  status: active                   # active | inactive

  # Provenance
  registered_at: 2026-01-15

  # Relationships
  related_sources:
    - src_springfield_council_videos
    - src_springfield_council_minutes

  # Spider file: services/ingestion/src/sidekick/spiders/{source_id}.py

  # Health (maintained by Scrapy spider runner)
  health:
    last_checked: 2026-03-17T08:00:00Z
    last_new_item: 2026-03-10
    error_rate_30d: 0.02
```

---

## Spider Files (Source of Truth for Fetch Logic)

Each source has a corresponding Scrapy spider file committed to the repository. The spider is the authoritative, executable description of how to fetch from the source — replacing the old playbook model.

**Spider location**: `services/ingestion/src/sidekick/spiders/{source_id}.py`

**Authoring**: `sidekick spiders scaffold …` produces a stub; you implement `parse()` and callbacks, then review and commit. Use `sidekick fetch-url` to inspect JS-rendered pages. See `services/ingestion/SPIDERS.md` for `RawItem` fields and patterns.

**Activated by**: `sidekick spiders sync` (upserts the `Source` DB row; new rows default to `status=active`)

### What a spider encodes

A spider subclasses `SidekickSpider` and sets these class attributes (also stored in the DB via `spiders sync`):

```python
from sidekick.core.vocabulary import BeatIdentifier, GeoIdentifier, SourceTier
from sidekick.spiders._base import RawItem

class SpringfieldCouncilAgendasSpider(SidekickSpider):
    name = "springfield-council-agendas"
    source_id = "src_springfield_council_agendas"
    endpoint = "https://springfield.gov/council/agendas"
    beat = BeatIdentifier("government:city-council")
    geo = GeoIdentifier("us:il:springfield:springfield")
    schedule = "0 8 * * MON"
    source_tier = SourceTier.PRIMARY   # PRIMARY (default) or SECONDARY
    # outlet = "Springfield Gazette"  # required when source_tier=SECONDARY

    def parse(self, response):
        # Follow links, then in a leaf callback download the body and yield one RawItem per asset.
        # RawItem MUST set format_id (a key in FORMAT_REGISTRY) on every yield — the pipeline
        # drops items without it. Download bytes into `body` before yielding; the pipeline
        # persists to object storage (or writes an async stub for HLS, etc.).
        ...
```

The spider's `parse` method (and any follow-up callbacks) contain the selector logic, pagination, and multi-asset handling for that specific source. If a detail page carries both a PDF and a video, the spider yields both as separate `RawItem`s. Optional `RawItem` fields include `period_start` / `period_end` (ISO dates the document covers), `event_group`, and `title`. Full field list, `format_id` table, and patterns live in `services/ingestion/SPIDERS.md`.

### Source of truth split

| Concern | Authoritative location |
|---|---|
| Fetch logic, selectors, pagination | Spider file (`.py`) |
| Endpoint, beat, geo, schedule, source_tier, outlet | Spider class attributes (synced to DB) |
| Lifecycle (`status` active/inactive — excludes inactive from scheduled list-due) | DB (`sources.status`); patch via API |
| Health (last_checked, last_new_item, crawl status) | DB (`sources.health`) |

### Spider maintenance

If a source's structure changes and the spider starts failing, edit the spider implementation (or regenerate a stub with `spiders scaffold` under a new filename and merge), review the diff, commit, and redeploy. The DB row's health fields are preserved when you keep the same `source_id`.

---

## Schedule Handling

Three scheduling modes, which can evolve over a source's lifetime:

- **Explicit cron**: Human or agent specifies the schedule directly. `learned: false`.
- **Learned schedule**: The system observes when new items tend to appear and infers a schedule. `learned: true` distinguishes this from human-specified so it can be revised automatically.
- **Reactive/ad-hoc**: No fixed schedule. Source is polled at a default interval or checked on demand when an agent requests it. Starting point for newly discovered sources.

Sources typically start as reactive and are promoted to a learned or explicit schedule over time.

---

## Source Relationships

Sources naturally cluster around real-world events. A city council meeting produces multiple artifacts via multiple sources:

```
springfield-council-meeting  (event group)
  ├── agendas       document/pdf     published ~1 week before
  ├── video         video/mp4        published ~1 day after
  ├── minutes       document/pdf     published ~2 weeks after
  └── public-comments  text/html    published same day
```

These are distinct sources with different spiders and schedules, but they share a common event context. Grouping them in the registry enables:

- Beat agents to see a complete picture of a meeting across media types
- The pipeline to anticipate expected items (e.g., video should follow an agenda)
- Health alerting when one item in a group goes stale without the others being affected

---

## Source Tier

`source_tier` distinguishes the nature of what a source produces:

| Value | Meaning | Examples |
|---|---|---|
| `primary` | The issuing organization itself. Default. | Government portals, agency releases, court filings, official video streams |
| `secondary` | Another newsroom or analyst reporting on primary events. Requires `outlet`. | Newspapers, wire services, think tanks |

`source_tier` is orthogonal to provenance trust — both primary and secondary sources can be high-trust if a human wrote and committed the spider.

**`outlet`** must be set when `source_tier=secondary` (e.g. `outlet = "Associated Press"`). The base class raises `ValueError` at subclass definition time if this constraint is violated.

**Attribution**: agents follow `artifact.source_id → source.outlet` when citing secondary-sourced artifacts. Beat and editor agents must attribute claims from secondary sources to the outlet ("According to [outlet]…"), not state them as direct fact. If both a primary and secondary artifact support the same claim, prefer the primary.

**Secondary as discovery signal**: a secondary artifact that references a primary document not yet in the pipeline should generate a source discovery proposal — the secondary article is effectively a tip.

**Default `processing_profile` for secondary sources**: spider authors should default to `processing_profile: index` for secondary sources (searchable and linkable, no narrative summary). Use `full` only when the article itself is the newsworthy artifact (e.g. an investigative piece or an editorial).

---

## Trust Model

All sources in the registry have a committed, human-authored spider — that is the trust gate. Writing and committing a spider is what makes a source trusted. **`sources.status`** (`active` \| `inactive`) is an editorial lifecycle flag: inactive sources are omitted from `spiders list-due` and the ingestion Step Functions map, but can still be run on demand (`spiders run`). The **`health`** JSON column (maintained by the spider runner) tracks runtime reliability (`last_checked`, `last_new_item`, and a crawl-level `status` such as `active` or `error` — distinct from `sources.status`).

---

## Ingestion Feedback Loop

The Scrapy spider runner (`run_spider`) updates the registry after each crawl:

- **Health fields**: `last_checked`, `last_new_item`, `status` (`active` or `error`)
- **Error surfacing**: if a spider consistently raises exceptions, `status` flips to `error` — a signal to re-examine the source and regenerate the spider

**Dedup and run controls**: `DeduplicationMiddleware` loads existing raw artifact URLs for the `source_id` from the artifact store at crawl start and skips already-ingested URLs. `sidekick spiders run` accepts `--max-items` (cap new emissions per run) and `--min-date` (drop items before a cutoff when the date is known).

Future: spiders could surface newly encountered URLs that don't match any known source as discovery proposals (the same pathway used by the discovery search agent).

---

## One-Off Documents (Not in the Registry)

The source registry only tracks **recurring channels**. When the Research Search agent fetches a single document (a blog post, a specific article, an ad-hoc FOIA response) in response to an assignment, that document is a raw artifact with no corresponding source row:

- `source_id` is null
- `created_by` is `"research-search-agent"`
- Attribution metadata will live on the artifact itself (`artifact.attribution`) — this field is not yet in the schema and will be designed when the one-off document pattern is formalized.

---

## Assignments

Sources can be fetched on-schedule (the normal pipeline) or on-demand via an **assignment**: a human or agent request to look for something specific. An assignment may:

- Target an existing source ("re-check the Springfield budget portal now")
- Trigger the research search agent to find a source that doesn't yet exist in the registry
- Result in a new source being added if the lookup proves recurring

Assignments are covered in more detail in the assignments design document.

---

## Decision log

Record significant design changes here. Keep the doc body current; use this log to explain why it changed.

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-18 | Replaced fetch strategy vocabulary + `fetch_config` with playbook model | Real-world government sources are too structurally varied for a fixed strategy DSL |
| 2026-03-18 | Added source examination agent; split ingestion into examination + ingestion worker | Understanding a source (rare) and fetching from it (frequent) are distinct problems |
| 2026-03-19 | Replaced playbook model with Scrapy spider files | A playbook requires either a DSL interpreter or LLM reasoning at every crawl. A committed spider file is deterministic, versionable, and runs without LLM involvement. The examination agent now generates code, not a JSON description |
| 2026-03-26 | Documented authoring path (`spiders scaffold` + hand implementation); required `format_id` on every `RawItem`; pipeline drops undeclared formats | `ArtifactWriterPipeline` requires `format_id` and trusts the spider to download `body` before yield |
| 2026-03-26 | Removed references to `sidekick examine` and code-gen examination | Command and flow were removed intentionally; spiders are hand-authored |
| 2026-03-27 | Removed `expected_content` from `Source` and spider metadata | Field duplicated `format_id` / `FORMAT_REGISTRY` without enforcement; drifted easily at scale |
| 2026-03-27 | Added `source_tier` (primary/secondary) and `outlet` to Source and SidekickSpider | Newsrooms follow other outlets as secondary sources; need a way to distinguish issuing organizations from reporters and enforce attribution in downstream agents |
| 2026-03-27 | Removed `discovered_by` and `examination_status` from Source | Neither field was actionable — `sync` always set them to the same values, `get_due_sources()` filter on `examination_status` was broken, and the trust model is implicit in the spider commit itself |
| 2026-03-27 | Added `sources.status` (`active` \| `inactive`, default `active`) | Lets editors pause scheduled ingestion without deleting the row or the spider; `get_due_sources()` / list-due only include `active` |
