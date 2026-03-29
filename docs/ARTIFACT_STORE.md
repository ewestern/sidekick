# Unified Artifact Store Design

> **Status**: stable
> **Scope**: Artifact schema, stage and content-type vocabulary, lineage model, and query patterns — authoritative for what goes in the store and how agents interact with it
> **Last updated**: 2026-03-29

---

## Overview

The artifact store is the architectural center of the pipeline. Rather than a waypoint between processing stages, it is the shared data layer that every agent reads from and writes to. Pipeline stages are defined by what agents produce and consume, not by data moving through a linear chain.

This means any agent can reach back to any prior stage when needed — a beat agent can re-examine a raw transcript if a summary lost nuance; a connection agent can read raw budget documents, not just the research agent's analysis of them.

---

## Stage vs contract taxonomy

Artifacts combine:

- **`stage`** = lifecycle placement (`raw`, `processed`, `analysis`, `connections`, `draft`)
- **`content_type`** = contract describing what the artifact means, who produces it, and who consumes it
- **`processing_profile`** = ingest-time routing intent for downstream CPU/LLM work (`full`, `structured`, `index`, `evidence`). Set on raw rows by the spider (or spider default); copied to derived processed artifacts. Does not replace `content_type` or `stage`. `null` on legacy rows means the same as `full`.

Treat `content_type` as an operational contract, not a casual label. It should only distinguish artifacts when the distinction changes routing, downstream consumption, retrieval defaults, or artifact invariants. Producer identity alone is provenance, not contract.

### Profile meanings

`processing_profile` is the spider's statement of what the processing service should do with a raw item after it has been written.

| Profile | Meaning | Expected chain |
|---|---|---|
| `full` | The default newsroom path. Use this for documents where both retrieval value and narrative understanding matter. The goal is to end up with both machine-queryable facts and a human-readable synthesis. | normalize to text if needed → `entity-extract` → `summary` |
| `structured` | Use this when the important output is tabular or record-like data rather than a narrative summary. Typical examples would be agendas, budget tables, roll calls, or other documents where downstream consumers want rows and fields more than prose. | normalize to text if needed → `structured-data` |
| `index` | Use this when the document should be searchable and linkable, but does not need a narrative summary. This is for material that is useful as supporting context or retrieval input, but not important enough to justify synthesis. | normalize to text if needed → `entity-extract` |
| `evidence` | Use this when the document should be preserved as source material only. The system keeps the raw artifact available for lineage and sourcing, but does not spend compute on normalization or enrichment beyond acquisition. | archive raw body only |

The raw artifact is the source of truth for `processing_profile`. Spiders may set it per `RawItem`, or provide a source-level default. Derived processed artifacts copy the same value forward so the routing intent remains visible without walking lineage back to the raw parent.

`processing_profile=null` on older rows should be treated as `full`.

### Contract families

| Family | Typical content types | Main purpose | Primary consumers |
|---|---|---|---|
| **Normalization** | `document-text` | Canonical enrichment-ready text, regardless of origin | Enrichment processors, analysts |
| **Extraction / index** | `entity-extract`, `structured-data` | Extract structured facts/indexes to improve retrieval and linking | Beat/research/connection agents, assignments |
| **Synthesis** | `summary`, `beat-brief`, `trend-note`, `budget-comparison`, `policy-diff` | Produce interpreted, narrative, or comparative outputs | Editors, connection agent, humans |
| **Routing / editorial signal** | `flag`, `cross-beat-flag`, `connection-memo` | Route attention and cross-beat follow-up | Editors, assignment orchestrator |
| **Publication** | `story-draft` | Publishable story candidate | Human editorial |

### Stage overview

| Stage | Typical contracts | Produced by |
|---|---|---|
| **raw** | `document-raw`, `audio-raw`, `video-raw` | Ingestion agents, research search |
| **processed** | Normalization + extraction contracts | Processing, transcription, or direct text ingestion |
| **analysis** | Synthesis + routing signals | Beat and research agents |
| **connections** | Cross-beat routing/synthesis contracts | Connection agent |
| **draft** | Publication contracts | Editor agent |

---

## Artifact Schema

Every artifact — regardless of stage or content type — carries a consistent envelope:

```yaml
artifact:
  id: art_a1b2c3
  title: "Springfield Council approves zoning ordinance 2026-14"
  content_type: beat-brief          # controlled vocabulary
  stage: analysis                    # raw | processed | analysis | connections | draft
  media_type: text/markdown
  processing_profile: full          # full | structured | index | evidence | null (legacy → full)

  # Lineage — the most important field
  derived_from:
    - art_x9y8z7                     # processed summary
    - art_m3n4p5                     # raw transcript

  # Context
  source_id: src_springfield_council_agendas
  event_group: springfield-council-2026-03-11
  beat: government:city-council
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
  # Attribution — how to cite this artifact's source in drafts.
  # For spider-backed secondary sources: follow source_id → source.outlet (no field needed here).
  # For one-off agent-fetched documents (no source row): artifact.attribution will carry this
  # when that feature is designed. Not yet in the schema.

  # Content — always object storage (see below); no inline column
  content_uri: s3://bucket/artifacts/...

  # Status (artifact envelope — not the same as pipeline stage)
  status: active                     # active | pending_acquisition | superseded | retracted
  acquisition_url: null              # set only while status=pending_acquisition (two-phase raw)
  superseded_by: null
```

---

## Contract: `entity-extract`

`entity-extract` is an **extraction/index contract** derived from normalized text (`document-text`). Its job is to make key facts queryable and linkable across artifacts. It is not just a byproduct blob.

### Required row-level projection

The following must be queryable from artifact metadata (row fields):

- **Core entities** in `entities`: person/organization/place/document/topic references with optional role/context
- **Topics** in `topics`: normalized topical tags for filtering and retrieval
- **Provenance marker** in a dedicated provenance field (preferred direction) rather than mixed into semantic entity entries

### Allowed body-only payload

The artifact body (`content_uri`) may carry richer structured payload that is too detailed for top-level row projection, such as:

- detailed financial figures
- motions/votes with expanded context
- extraction confidence and parser diagnostics

### Search contract

- Row projection supports fast filtering and cross-artifact joins.
- Body payload supports deep inspection and downstream structured transforms.
- If a field is required for assignment gap analysis or frequent agent retrieval, promote it from body-only to row-level projection in a future schema iteration.

## Contract: `summary`

`summary` is a **synthesis contract** derived from normalized text plus its sibling `entity-extract`. Its job is to give downstream agents a readable, attribution-aware narrative artifact without making them reread the full normalized document by default.

### Primary and supporting inputs

- The primary semantic source is the normalized text artifact (`document-text`).
- The sibling `entity-extract` artifact is support context for name consistency, topics, and structured references.
- In the normal `full` flow, the summary artifact's `derived_from` should contain both parents:
  - normalized text artifact ID first
  - sibling `entity-extract` artifact ID second

### Required row-level projection

- `entities` should mirror the sibling `entity-extract.entities`
- `topics` should mirror the sibling `entity-extract.topics`

This keeps `entity-extract` as the canonical extraction/index contract while allowing summary rows to remain searchable and convenient for downstream retrieval.

### Body format

- Persist summary bodies as `text/markdown`
- Include a readable narrative body plus a final `Sources` section
- The `Sources` section should include enough lineage/provenance detail to let downstream article-writing agents trace back to original material

Summary is not the canonical owner of extracted entities or topics. It mirrors extraction metadata for convenience; the sibling `entity-extract` remains the authoritative structured source.

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
- "All `beat-brief` artifacts on beat `government:city-council` in geo `us:il:springfield:springfield` in the last 30 days"
- "All artifacts in event group `springfield-council-2026-03-11`"
- "All `flag` artifacts not yet consumed by an editor agent"
- For extraction contracts, row-level projection fields are the fast-path query surface; body payload is read only when needed.

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
- **`document-text`** — canonical enrichment-ready text in object storage. It may be written directly by ingestion when the spider already has plain text, by `processor:marker` for PDFs (Markdown preserving structure), or by the transcription service for audio/video (plain dialog text).

Subscribers to `artifact_written` filter stubs with `event["status"] == "pending_acquisition"` and skip until acquisition completes. Downstream enrichment routing is owned by orchestration; enrichment commands themselves should not be treated as authoritative validators of `content_type`.

---

## Versioning and Supersession

Completed artifacts (rows whose content is final for their version) are immutable: corrections produce a new artifact with `superseded_by` on the old one. **Exception:** raw artifacts in `status="pending_acquisition"` are incomplete stubs; completing them via **`ArtifactStore.complete_acquisition()`** (same `id`, new `content_uri`, `status → active`) is the defined way to attach bytes. No other in-place updates are allowed — use a new `id` or supersession for any other change.

---

## Preventing Data Swamp

Three practices keep the store usable as volume grows:

1. **Controlled contract vocabulary** — a new content type requires a deliberate decision, not just a new string
2. **Mandatory lineage** — every artifact except raw must declare what it was derived from; this is enforced at write time
3. **Event group tagging** — artifacts without an event group should be rare; this tag is the primary organizing unit for human-readable browsing

### Validation direction (implementation follow-up)

Vocabulary discipline must be enforced in code, not only in docs:

- validate `content_type` on write using a controlled allowlist
- validate contract-specific projection requirements (for example, required `entity-extract` row fields)
- reject unknown contract values unless explicitly introduced through a design update

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
| 2026-03-29 | Added explicit `summary` contract and clarified sibling relationship with `entity-extract` | Summary now consumes normalized text as primary input plus sibling extraction support, persists Markdown, and mirrors extraction metadata while leaving canonical entities/topics with `entity-extract` |
| 2026-03-29 | Clarified orchestration-owned enrichment routing | Processing commands no longer self-validate enrichable content types; Step Functions routing is the source of truth for which node runs on which artifact |
| 2026-03-27 | Added attribution note to artifact schema; documented spider-backed vs one-off attribution paths | Secondary sources need clear attribution rules; spider-backed secondary sources use `source_id → source.outlet` lineage; one-off artifact attribution is deferred to a future design |
| 2026-03-19 | Added `pending_acquisition` status and Two-Phase Acquisition section | HLS and yt-dlp formats cannot be acquired inline in Scrapy's synchronous pipeline; a stub-then-update model lets the spider discover URLs immediately while deferred workers handle async capture |
| 2026-03-19 | Added `status` to `artifact_written` NOTIFY payload | Lets downstream subscribers filter stub artifacts before acquisition is complete without a separate DB read |
| 2026-03-20 | Added `acquisition_url` field; stop overloading `content_inline` for async stubs | `content_inline` is for actual text content — storing a pointer there was confusing. `acquisition_url` is a dedicated field that the acquisition worker reads and clears on completion |
| 2026-03-20 | Document-text vocabulary; raw lifecycle table; `complete_acquisition`; processing only on raw+active | Aligns Phase 3 triggers with `pending_acquisition`; adds LLM-friendly text stage before summarization |
| 2026-03-20 | Removed `content_inline`; all bodies use `content_uri` | Avoids split-brain storage; processed text (e.g. `document-text`) is always in object storage |
| 2026-03-22 | Reframed content types as contracts and added explicit `entity-extract` row/body semantics | Removes ambiguity around processed artifact meaning, defines what must be queryable, and sets a clear validation direction for controlled vocabulary enforcement |
| 2026-03-26 | Added `processing_profile` for ingest-time downstream routing | Spiders declare intent (`full`, `structured`, `index`, `evidence`) so processing does not infer enrichment from `media_type` alone; orthogonal to `content_type` / `stage` / `status` |
| 2026-03-27 | Added required `title` field | Editorial UI needs a human-readable label for artifact lists without fetching content bodies; spider authors are always able to supply a meaningful string from source metadata |
| 2026-03-27 | Switched `document-text` from `text/plain` (pypdf text-layer) to `text/markdown` (Marker OCR) | Scanned PDFs were silently skipped; Marker handles both native and scanned pages, preserves table structure, and produces LLM-ready Markdown |
