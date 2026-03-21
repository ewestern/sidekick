# Unified Artifact Store Design

> **Status**: stable
> **Scope**: Artifact schema, stage and content-type vocabulary, lineage model, and query patterns — authoritative for what goes in the store and how agents interact with it
> **Last updated**: 2026-03-20

---

## Overview

The artifact store is the architectural center of the pipeline. Rather than a waypoint between processing stages, it is the shared data layer that every agent reads from and writes to. Pipeline stages are defined by what agents produce and consume, not by data moving through a linear chain.

This means any agent can reach back to any prior stage when needed — a beat agent can re-examine a raw transcript if a summary lost nuance; a connection agent can read raw budget documents, not just the research agent's analysis of them.

---

## Artifact Layers

Every artifact belongs to one of five content stages. These form a logical progression but are stored together, linked by lineage:

| Stage | Content types | Produced by |
|---|---|---|
| **raw** | transcript-raw, document-raw, video-raw, audio-raw | Ingestion agents, research search agent |
| **processed** | document-text, transcript-clean, summary, entity-extract, structured-data | Processing agents |
| **analysis** | beat-brief, trend-note, flag, budget-comparison, policy-diff | Beat agents, research agents |
| **connections** | connection-memo, cross-beat-flag | Connection agent |
| **draft** | story-draft | Editor agents |

The content type vocabulary is a **controlled list**, not free-form. Discipline here is what keeps the store legible as it grows.

---

## Artifact Schema

Every artifact — regardless of stage or content type — carries a consistent envelope:

```yaml
artifact:
  id: art_a1b2c3
  content_type: beat-brief          # controlled vocabulary
  stage: analysis                    # raw | processed | analysis | connections | draft
  media_type: text/markdown

  # Lineage — the most important field
  derived_from:
    - art_x9y8z7                     # processed summary
    - art_m3n4p5                     # raw transcript

  # Context
  source_id: src_springfield_council_agendas
  event_group: springfield-council-2026-03-11
  beat: government:city_council
  geo: us:il:springfield:springfield
  period:
    start: 2026-03-11
    end: 2026-03-11

  # Discovery (for search)
  entities:
    - {name: "Jane Smith", type: person, role: council-member}
    - {name: "Springfield", type: place}
    - {name: "Zoning Ordinance 2026-14", type: document}
  topics: [zoning, housing, land-use]
  embedding: [...]                   # vector for semantic search

  # Provenance
  created_by: beat-agent-housing
  created_at: 2026-03-17T14:22:00Z

  # Content — always object storage (see below); no inline column
  content_uri: s3://bucket/artifacts/...

  # Status (artifact envelope — not the same as pipeline stage)
  status: active                     # active | pending_acquisition | superseded | retracted
  acquisition_url: null              # set only while status=pending_acquisition (two-phase raw)
  superseded_by: null
```

---

## Lineage

The `derived_from` field creates a directed acyclic graph (DAG) from raw source material through to story drafts. This graph is the most valuable structural element in the store. It enables:

- **Traceability**: any claim in a draft can be walked back to the source document that supports it
- **Invalidation**: when a new raw item arrives (e.g., corrected minutes), downstream artifacts that derived from the old version can be flagged for re-analysis
- **Gap detection**: the expected artifact chain for an event group can be compared against what actually exists ("we have an agenda and a video, but no minutes yet")
- **Assignment targeting**: when a human or agent triggers a lookup, the store can show what is already known vs. what needs to be fetched

---

## Querying

Agents find artifacts through three complementary mechanisms:

**Structured queries** — filter by any metadata field or combination:
- "All `beat-brief` artifacts on beat `government:city_council` in geo `us:il:springfield:springfield` in the last 30 days"
- "All artifacts in event group `springfield-council-2026-03-11`"
- "All `flag` artifacts not yet consumed by an editor agent"

**Semantic search** — vector similarity on the embedding field:
- "Find analysis artifacts thematically similar to this budget cut announcement"
- Used heavily by the connection agent to find non-obvious cross-beat overlaps

**Lineage traversal** — follow `derived_from` links forward or backward:
- "What raw artifacts support this story draft?"
- "What analysis artifacts derive from this source document?"

---

## Agent Access Patterns

| Agent | Reads | Writes |
|---|---|---|
| Ingestion | nothing (reads external sources) | raw |
| Acquisition (processing service) | raw stubs (`pending_acquisition`) | same row completed → `active` raw with `content_uri` |
| Processing | raw (`active`, content present) | processed |
| Beat agents | processed (their beat/geo) | analysis |
| Research agents | processed (policy/budget focus) | analysis |
| Connection agent | analysis (all beats/geos) | connections |
| Editor agents | analysis, connections, raw (for sourcing) | draft |
| Research search | nothing (reads external sources) | raw |
| Human editorial | draft | — (publishes or triggers assignments) |

---

## Two-Phase Acquisition

Some formats (HLS streams, yt-dlp sources) cannot be acquired inline in Scrapy's synchronous pipeline. For these, ingestion follows a two-phase model:

1. **Spider discovers the URL** and calls `detect_format()`, which returns a `FormatSpec` with `is_async=True`.
2. **Pipeline writes a stub artifact** with:
   - `status="pending_acquisition"` — signals the artifact is not yet fully acquired
   - `acquisition_url=<source_url>` — the URL the acquisition worker must fetch
   - `content_uri=None` — not yet populated
3. **`acquisition_needed` event published** with `artifact_id`, `format_id`, and `source_url`.
4. **Acquisition worker** runs ffmpeg/yt-dlp against `acquisition_url`, writes bytes to object storage, then calls **`ArtifactStore.complete_acquisition()`**, which sets `status="active"`, `content_uri=<s3_key>`, `acquisition_url=None`, and publishes **`artifact_written`** again with `status="active"`.

### Raw lifecycle and processing triggers

| `stage` | `status` | Meaning | Process further? |
|---|---|---|---|
| raw | `pending_acquisition` | URL recorded; bytes not in object store | No — run acquisition first |
| raw | `active` | Body in object storage (`content_uri`) | Yes — if media/content type matches a processor |
| processed | `active` | Normal processed artifact | Downstream analysis |

- **`acquisition_needed`** — dispatch acquisition work (maps cleanly to a Step Functions / Batch task in production).
- **`artifact_written`** — general notify; **processors must only handle `stage="raw"` and `status="active"`** so stubs are never transcribed or summarized before bytes exist.
- **`document-text`** — optional first processed step for PDFs and similar: UTF-8 text in object storage (`content_uri`, `media_type=text/plain`). PDFs without a text layer are not complete until OCR exists; today we record `entities` with `type=pdf-extraction` and `ocr=not_applied` when using text-layer extraction only.

Subscribers to `artifact_written` filter stubs with `event["status"] == "pending_acquisition"` and skip until acquisition completes.

---

## Versioning and Supersession

Completed artifacts (rows whose content is final for their version) are immutable: corrections produce a new artifact with `superseded_by` on the old one. **Exception:** raw artifacts in `status="pending_acquisition"` are incomplete stubs; completing them via **`ArtifactStore.complete_acquisition()`** (same `id`, new `content_uri`, `status → active`) is the defined way to attach bytes. No other in-place updates are allowed — use a new `id` or supersession for any other change.

---

## Preventing Data Swamp

Three practices keep the store usable as volume grows:

1. **Controlled content type vocabulary** — a new content type requires a deliberate decision, not just a new string
2. **Mandatory lineage** — every artifact except raw must declare what it was derived from; this is enforced at write time
3. **Event group tagging** — artifacts without an event group should be rare; this tag is the primary organizing unit for human-readable browsing

---

## Relationship to Assignments

Assignments are essentially structured queries against the store plus gap analysis. When a human or agent triggers an assignment ("find everything about the proposed school closure"), the assignment system:

1. Queries the store for existing artifacts matching the topic/beat/geo
2. Identifies gaps in the lineage chain (missing processed artifacts, no analysis yet, etc.)
3. Issues fetch or analysis requests to fill those gaps
4. Tags resulting artifacts with the assignment ID for traceability

Assignments are covered in detail in the assignments design document.

---

## Decision log

Record significant design changes here. Keep the doc body current; use this log to explain why it changed.

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-19 | Added `pending_acquisition` status and Two-Phase Acquisition section | HLS and yt-dlp formats cannot be acquired inline in Scrapy's synchronous pipeline; a stub-then-update model lets the spider discover URLs immediately while deferred workers handle async capture |
| 2026-03-19 | Added `status` to `artifact_written` NOTIFY payload | Lets downstream subscribers filter stub artifacts before acquisition is complete without a separate DB read |
| 2026-03-20 | Added `acquisition_url` field; stop overloading `content_inline` for async stubs | `content_inline` is for actual text content — storing a pointer there was confusing. `acquisition_url` is a dedicated field that the acquisition worker reads and clears on completion |
| 2026-03-20 | Document-text vocabulary; raw lifecycle table; `complete_acquisition`; processing only on raw+active | Aligns Phase 3 triggers with `pending_acquisition`; adds LLM-friendly text stage before summarization |
| 2026-03-20 | Removed `content_inline`; all bodies use `content_uri` | Avoids split-brain storage; processed text (e.g. `document-text`) is always in object storage |
