# Assignments Design

> **Status**: stable
> **Scope**: Assignment types, execution flow, sub-assignment rules, and monitor lifecycle — authoritative for how targeted investigation requests are created, dispatched, and closed
> **Last updated**: 2026-03-22

---

## Overview

Assignments are the pull complement to the push pipeline. The main pipeline is broad — process everything that comes in from known sources. Assignments are targeted — investigate this specific thing, now, to a specific depth.

Together they give the system both breadth (catching everything) and depth (pursuing what matters). An assignment is a first-class entity that orchestrates a mini-pipeline: query the artifact store, identify gaps, dispatch work to fill them, collect results, and surface them to whoever triggered the assignment.

---

## Assignment Schema

Assignments are not artifacts — they are task entities that produce artifacts. They live in their own store, adjacent to the artifact store.

```yaml
assignment:
  id: asgn_a1b2c3
  type: research                    # research | story | monitor
  status: in-progress               # open | in-progress | complete | cancelled

  # Intent — preserved exactly as specified
  query_text: "proposed school closure on Maple Street"

  # Structured parameters extracted from intent at creation time
  query_params:
    beat: education:school_board
    geo: us:il:springfield:springfield
    entities:
      - {name: "Maple Street Elementary", type: place}
      - {name: "school closure", type: topic}
    time_range:
      start: 2025-12-01
      end: 2026-03-18

  # Provenance
  triggered_by: human               # human | connection-agent | beat-agent | schedule
  triggered_by_id: user_editor_01
  triggered_at: 2026-03-18T09:00:00Z
  parent_assignment: null           # set if this is a sub-assignment

  # Execution
  artifacts_in:                     # artifacts from the store used as input
    - art_x9y8z7
    - art_m3n4p5
  artifacts_out:                    # artifacts produced by this assignment
    - art_r5s6t7
  sub_assignments:
    - asgn_d4e5f6

  # For monitor type only
  monitor:
    schedule: "0 9 * * MON"        # re-run weekly
    last_run: 2026-03-11T09:00:00Z
    close_if_stale_days: 42        # auto-close if nothing new in 6 weeks
```

---

## Assignment Types

### Research
"What do we know about X?"

Queries the store for existing artifacts, fetches missing documents if gaps exist, runs analysis. Output is an enriched set of analysis artifacts — not necessarily a publishable story, but a complete picture of what is known. The natural output of an agent saying "I need more context."

### Story
"Write a story about X."

Like research, but goes all the way to an editor agent producing a draft. The natural output of a human editor saying "pursue this." A story assignment may spawn research sub-assignments for specific angles or historical context.

### Monitor
"Keep watching X."

An ongoing assignment that re-runs on a schedule or when new relevant artifacts arrive. Produces periodic update artifacts (e.g., a weekly brief on a developing story). Runs until explicitly closed by human editorial or auto-closed after a configurable staleness period.

---

## Execution

When an assignment is triggered, it runs through five steps:

### 1. Store Query
Search the artifact store for what already exists on the topic. This combines:
- **Structured filtering** on `query_params` (beat, geo, entities, time range)
- **Semantic search** on `query_text` embedding — to catch related coverage that isn't obviously tagged

If existing artifacts are sufficient to answer the question, the assignment may complete here without dispatching any new work.

### Artifact-chain templates (deterministic gap rules)

Gap analysis uses explicit templates rather than ad hoc expectations:

| Input artifact class | Required downstream chain |
|---|---|
| `raw` PDF (`status=active`) | `document-text` -> `entity-extract` -> `summary` |
| `raw` audio/video (`status=active`) | `document-text` -> `entity-extract` -> `summary` |
| `raw` with `status=pending_acquisition` | `complete_acquisition` first, then evaluate media template above |
| Assignment requiring numeric/policy comparison | include `structured-data` when source content supports extraction |

Event-group completeness is measured against these templates for all artifacts sharing the same `event_group`.

### 2. Gap Analysis
Compare what exists against template requirements and assignment scope:
- Missing raw source artifacts (no source coverage for target entities/event window)
- **Raw incomplete**: `raw` exists with `status="pending_acquisition"` -> dispatch acquisition only
- Missing normalization contract (`document-text`) for `raw` + `active`
- Missing extraction/synthesis contracts (`entity-extract`, `summary`, and optionally `structured-data` when required by assignment type)
- Missing analysis artifacts (`beat-brief`, `trend-note`, etc.) after required processed contracts exist
- Missing cross-geo/cross-beat coverage required by scope
- Missing time slices in requested period

Deterministic rule: a processed gap is only closed when every required contract in the applicable chain template exists for the same lineage branch.

### 3. Dispatch
For each identified gap, issue a targeted request:

| Gap type | Dispatched to |
|---|---|
| Missing raw documents | Research search agent (fetch specific docs) |
| Raw pending acquisition (`status=pending_acquisition`) | Acquisition worker (processing service — completes raw via `ArtifactStore.complete_acquisition`) |
| Missing processed artifacts (`raw` active, needs `document-text` / STT / etc.) | Processing agents |
| Missing analysis | Beat agent (with assignment ID and scope as context) |
| Missing cross-beat or cross-geo coverage | Connection agent |

Dispatched work is tagged with the assignment ID so resulting artifacts are automatically associated with the assignment.

### 4. Collect
As artifacts are written to the store, the assignment tracks them against its expected outputs. For story assignments, draft completion signals the assignment is ready for human review. For research assignments, completion is when gap analysis finds no remaining gaps above a threshold.

### 5. Surface
Results are routed back to the triggering entity:
- **Human-triggered**: surfaced in the editorial queue, grouped by assignment
- **Agent-triggered**: returned as input to the triggering agent's next reasoning step
- **Monitor**: produces a periodic update artifact; no active surfacing unless a significant development is detected

---

## Who Can Trigger Assignments

| Trigger | Typical type | Example |
|---|---|---|
| Human editorial | Story or Research | "Follow up on the school closure vote" |
| Connection agent | Research or Monitor | "Budget cuts in three cities may be linked — investigate" |
| Beat agent | Research | "I need the original ordinance text to complete this brief" |
| Schedule | Monitor | "Weekly check on stadium construction budget" |

The connection agent triggering assignments is where the system develops genuine initiative. Rather than just surfacing patterns for humans, it can autonomously dispatch investigation and bring a near-complete package to human editorial for a kill/pursue decision.

---

## The Query Specification Problem

Natural language intent must become executable search. Two representations are maintained:

**`query_text`** — the original natural language statement, preserved exactly. This is the source of truth and is used to generate the semantic embedding.

**`query_params`** — structured parameters extracted from the query text by an LLM at assignment creation time. These drive efficient store filtering. They are a best-effort extraction, not authoritative — the semantic search on `query_text` catches what structured params miss.

When a human creates an assignment through editorial tooling, the system should preview the extracted `query_params` and any immediately matched artifacts before the assignment is committed, so the human can verify the interpretation is correct.

---

## Sub-Assignments

Assignments can spawn sub-assignments. A story assignment might generate:
- A research sub-assignment for historical context
- A monitor sub-assignment to track new developments while the story is being drafted

Sub-assignments form a tree. Two constraints keep this manageable:
1. **Depth cap**: sub-assignments are limited to two levels (assignment → sub-assignment → no further nesting)
2. **Human gate on escalation**: a sub-assignment cannot escalate to a story type without human approval — an agent cannot autonomously commission a story

---

## Monitor Lifecycle

Monitor assignments run indefinitely and require explicit close conditions to prevent accumulation:

**Human close**: an editor marks the monitor complete ("we've published, stop tracking")

**Auto-close on staleness**: if no new relevant artifacts have appeared within `close_if_stale_days`, the monitor closes itself and notifies editorial

**Auto-close on story publication**: if a story assignment completes and is published, any monitor assignments covering the same topic can be automatically closed or downgraded to a lower-frequency schedule

The assignment queue should surface monitors with recent activity separately from those approaching their staleness threshold, so editors can make informed keep/close decisions.

---

## Relationship to the Main Pipeline

The main pipeline and assignments share the artifact store but operate differently:

| | Main pipeline | Assignments |
|---|---|---|
| Direction | Push (sources → store) | Pull (question → store → gaps → fetch) |
| Scope | Broad (everything from known sources) | Targeted (specific topic, entity, or event) |
| Trigger | Scheduled / continuous | On-demand or periodic |
| Output | Artifacts at each stage | A collection of artifacts grouped by assignment ID |

An assignment is not a replacement for the main pipeline — it depends on the main pipeline having already ingested and processed source material. The gap analysis step identifies what the pipeline hasn't covered, and the assignment fills those gaps on demand.

---

## Decision log

Record significant design changes here. Keep the doc body current; use this log to explain why it changed.

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-20 | Gap analysis distinguishes `pending_acquisition` from process-ready raw | Prevents assigning STT/summarization when bytes are not in object storage yet |
| 2026-03-22 | Added explicit artifact-chain templates and event_group completeness rules for gap analysis | Makes assignment dispatch deterministic and implementable without implicit “as required” interpretation |
