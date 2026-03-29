# Agent Inventory

> **Status**: stable
> **Scope**: Agent roles, capabilities, topology, and memory patterns — authoritative for what each agent does, what it reads/writes, and how agents relate to each other
> **Last updated**: 2026-03-29 (scope-oriented analysis workflow; summary/entity-extract contract)

---

## Overview

The pipeline uses eight distinct agent roles. They divide naturally into three tiers:

| Tier | Agents | Characteristic |
|---|---|---|
| **Ingestion** | Ingestion worker, Discovery search, Research search | Face the external world; produce raw artifacts |
| **Analysis** | Processing, Transcription (STT), Beat, Research, Connection | Transform and interpret; read/write the artifact store |
| **Editorial** | Editor | Produce publishable output; interface with humans |

Assignment orchestration sits across all tiers: it is not a separate agent but a coordination layer described at the end.

---

## Ingestion Worker (Scrapy Spiders)

**Activation**: Cron (`sidekick spiders due`) or on-demand (`sidekick spiders run SOURCE_ID`).

**Reads**: External sources plus artifact-store URL history for deduplication.

**Retrieval strategy**: Deterministic spider traversal; no LLM planning.

**Durable state**: None beyond persisted health and dedup references already in data stores.

**Writes**: `raw` artifacts (including pending-acquisition stubs when needed) and source-health updates.

**Why this agent exists**: Provide low-cost, reproducible raw acquisition at schedule scale.

---

## Discovery Search Agent

**Activation**: Periodic run or assignment-triggered discovery sweep.

**Reads**: Source registry plus external web.

**Retrieval strategy**: Open-ended search + fetch + cluster; compares candidates against known registry entries.

**Durable state**: Minimal memory of explored domains/proposals to reduce repeats.

**Writes**: Source proposals for human review (not auto-activation).

**Why this agent exists**: Expand source coverage without manual source hunting.

---

## Research Search Agent

**Activation**: On-demand from assignments or explicit beat/research requests.

**Reads**: Request payload (URL/query/description), plus external sources.

**Retrieval strategy**: Targeted fetch + relevance verification before write.

**Durable state**: Stateless by default.

**Writes**: Assignment-tagged `raw` artifacts with `source_id=null` and `created_by="research-search-agent"`; optional source proposal side effect when a recurring source is discovered.

**One-off documents**: when fetching a single document with no recurring channel, there is no source row. Attribution metadata for these artifacts (`artifact.attribution`) is not yet in the schema — to be designed when this pattern is formalized.

**Why this agent exists**: Fill specific evidence gaps without waiting for scheduled ingestion.

---

## Processing Agents

**Activation**:
- `acquisition_needed` for stub completion
- `artifact_written` where `stage="raw"` and `status="active"` and media is PDF — normalization to `document-text`, **unless** `processing_profile="evidence"` (archive-only; no PDF text extraction)
- `artifact_written` where `stage="raw"` and `status="active"` and media is audio/video — **Transcription** to `document-text`, **unless** `processing_profile="evidence"`
- `artifact_written` where `stage="processed"` and `content_type = "document-text"` for enrichment — fan-out depends on `processing_profile`: `full` → `entity-extract` then `summary`; `structured` → structured-data; `index` → `entity-extract` only; `evidence` → none (should not occur on text rows if raw was evidence-only)

**Reads**: `raw` artifacts (`pending_acquisition` for acquisition workers; `active` for PDF processors) and enrichable processed text artifacts.

**Retrieval strategy**: Direct ID-based reads; normalization by media/status; enrichment order by `processing_profile`. The enrichment commands do not self-validate `content_type`; orchestration is responsible for routing the correct artifact into each node.

**Durable state**: None. Normalization processors are stateless plain functions. Enrichment processors (summary, entity-extract) are ephemeral DeepAgents — skills are loaded into an `InMemoryStore` for the duration of a single invocation and discarded.

**Writes**: `processed` contracts (`document-text`, `summary`, `entity-extract`, optional `structured-data`) and raw completion via `ArtifactStore.complete_acquisition()`.

**Contract notes**:
- `entity-extract` is the canonical extraction/index artifact. It owns row-level `entities` and `topics`.
- `summary` is the canonical synthesis artifact. It reads normalized text as the primary source plus the sibling `entity-extract` as support context.
- In the normal `full` flow, a summary artifact derives from both its normalized text parent and the sibling `entity-extract` artifact. It mirrors the sibling extraction artifact's `entities` and `topics` onto the summary row for convenience.
- Summary bodies are stored as Markdown with a `Sources` section rather than JSON.

**Why this agent exists**: Convert raw bytes into reusable normalized and extraction contracts so downstream agents can stay retrieval-first instead of reprocessing raw media. Enrichment processors use domain skills (news-values, entity-and-actor-tracking, etc.) for extraction quality that plain functions cannot achieve.

---

## Transcription (STT)

**Activation**: `artifact_written` where `stage="raw"` and `status="active"` and `media_type` is `audio/*` or `video/*`, and `processing_profile != "evidence"` (same routing metadata as before; different deployable).

**Reads**: Active raw audio/video artifacts and object-storage bytes.

**Retrieval strategy**: Direct ID-based read; WhisperX pipeline.

**Durable state**: Stateless per artifact transformation.

**Writes**: `document-text` processed artifacts (WhisperX dialog text in object storage).

**Why this exists**: GPU-heavy STT is isolated in **`services/transcription`** (`sidekick-transcribe`) with its own image and dependencies; CPU processing stays in **`services/processing`**.

---

## Beat Agents

**Activation**: Event-reactive through the scope-oriented `analysis` workflow. Relevant processed contracts (primarily `summary` and `entity-extract`) mark an event-group scope dirty; the workflow debounces, runs the beat agent for that scope, reruns if new inputs arrive during execution, then performs a quiet-period reevaluation before releasing the scope.

**Reads**:
- Beat/geo-scoped processed artifacts
- Relevant analysis artifacts
- Raw/normalized artifacts via lineage only when needed for fidelity

**Retrieval strategy**: Artifact-store structured query + semantic search + lineage traversal. The default processed inputs are `summary` and `entity-extract`; raw or normalized text is a fallback for fidelity, not the normal beat input path.

**Durable state**: Currently stateless per run — each invocation is a fresh ephemeral DeepAgents run. Scope coordination state (dirty flag, revision counter, active execution) is owned by `AnalysisScope`, not the agent. Cross-run investigation memory (open threads, de-dup markers, developing story pointers) is a future addition once the base pipeline is running on real data.

**Writes**: `beat-brief`, `flag`, `trend-note` artifacts.

**Primary vs. secondary source handling**:
- Prefer primary artifact chains for factual claims. Use secondary artifacts for framing, context, and "what is the public narrative?" signals.
- Resolve `source_tier` by following `artifact.source_id → source.source_tier`.
- A secondary artifact that references a primary document not yet in the pipeline should generate a source discovery proposal — the article is a tip.

**Why this agent exists**: Maintain continuous beat-level synthesis and editorial signaling over time.

---

## Research Agents

**Activation**: Event-reactive and assignment-driven for cross-cutting policy/budget domains.

**Reads**:
- Domain-scoped processed artifacts
- Relevant beat/research analysis artifacts
- Source artifacts via lineage when deeper validation is needed

**Retrieval strategy**: Same architecture as beat agents (structured + semantic + lineage), but scoped by research domain rather than beat/geo.

**Durable state**: Minimal cross-thread state, same pattern as beat agents.

**Writes**: `budget-comparison`, `policy-diff`, `trend-note` artifacts.

**Why this agent exists**: Provide domain-depth analysis (policy/budget/regulatory) that cuts across event-centric beat boundaries.

---

## Connection Agent

**Activation**: Batch/scheduled or threshold-triggered over accumulated analysis deltas (not per-artifact critical-path processing).

**Reads**: Analysis artifacts across beats/geos plus prior connection outputs.

**Retrieval strategy**: Semantic clustering + entity cross-reference over broad artifact slices.

**Durable state**: Minimal cross-run memory for surfaced-pattern registry and suppression of repeat flags.

**Writes**: `connection-memo`, `cross-beat-flag`; may trigger assignments per policy rules.

**Why this agent exists**: Surface cross-beat patterns no single scoped agent would observe.

---

## Editor Agents

**Activation**: Triggered by editorially relevant flags or story-assignment dispatch completion.

**Reads**: Analysis + connection artifacts first, with lineage traversal to supporting source material.

**Retrieval strategy**: Retrieval-first drafting flow: gather cited evidence from artifacts, then compose narrative.

**Durable state**: Ephemeral per draft/revision cycle; no broad long-term memory requirement.

**Writes**: `story-draft` artifacts with sourcing confidence cues.

**Attribution rule**: before including a claim from any artifact, resolve its source tier via `artifact.source_id → source.source_tier`. Claims from secondary sources must be attributed to `source.outlet` in the draft ("According to [outlet]…"), not stated as direct fact. If a primary and secondary artifact support the same claim, cite the primary; use the secondary as context or omit it.

**Why this agent exists**: Convert analysis signals into grounded story drafts for human editorial decisions.

**Editorial/public API auth model**: FastAPI routes that expose editorial resources use dual authentication — Cognito JWTs for public users and scoped API keys for machine callers. Authorization is centralized with role/scope guards.

---

## Assignment Orchestration

Assignments are not a separate agent — they are a coordination protocol executed by the assignment system. But they interact with agents in specific ways worth capturing here:

**What triggers it**: Human editorial, connection agent, beat agent, research agent, or schedule

**What it does**:
1. Queries artifact store (structured + semantic) for existing coverage
2. Runs gap analysis against expected artifact chain
3. Dispatches to agents (beat agents for analysis, research search for missing docs, connection agent for cross-beat coverage)
4. Tracks artifact completion against assignment scope
5. Routes results back to the triggering entity

**Agent interactions**:
- Sends context (assignment ID, scope, query params) to whichever agents it dispatches to
- Agents tag their output with the assignment ID — this is how the collect step works
- Beat and research agents can spawn sub-assignments; connection agent can create top-level assignments

The assignment system acts as a lightweight orchestrator that coordinates agents without owning any analytical capability itself.

---
## Agent x Skill Matrix

| Skill | Disc | R.Search | Proc | Beat | Research | Conn | Editor |
|-------|:----:|:--------:|:----:|:----:|:--------:|:----:|:------:|
| news-values | | | summ | **Y** | | **Y** | **Y** |
| verification | | **Y** | | **Y** | | | **Y** |
| source-assessment | **Y** | **Y** | | **Y** | | | |
| attribution-and-quoting | | | | **Y** | | | **Y** |
| ethics-and-fairness | | | | **Y** | | **Y** | **Y** |
| story-structure | | | | | | | **Y** |
| editorial-judgment | | | | **Y** | | | **Y** |
| numbers-and-data-literacy | | | summ | **Y** | **Y** | | **Y** |
| investigative-methodology | | | | **Y** | **Y** | **Y** | |
| entity-and-actor-tracking | | | ent | **Y** | | **Y** | |
| government-proceedings | | | summ | **Y**gov | | | |
| public-finance | | | | **Y**fin | **Y** | | |
| public-records-and-foia | **Y** | **Y** | | **Y** | | | |
| cross-domain-pattern-rec | | | | | **Y** | **Y** | |
| document-assessment | **Y** | **Y** | **Y** | **Y** | | | |

*Disc = Discovery Search, R.Search = Research Search, Proc = Processing, Conn = Connection*
*summ/ent = used by the summary or entity-extract processor specifically*

## Capability Matrix

| Agent | Durable state profile | Triggers others | Can spawn assignments | Runs on schedule | Runs on demand |
|---|---|---|---|---|---|
| Ingestion worker (Scrapy) | — | — | — | Yes (cron via `spiders due`) | Yes (`spiders run`) |
| Discovery search | Light (exploration memory) | — | — | Yes | Yes |
| Research search | — | — | — | — | Yes |
| Processing | — | — | — | Reactive | Via assignment |
| Transcription (STT) | — | — | — | Reactive | Via assignment |
| Beat agents | Stateless per run (coordination in `AnalysisScope`; cross-run memory deferred) | Research search | Sub-assignments | Reactive | Via assignment |
| Research agents | Minimal durable state + checkpoint working state | Research search | Sub-assignments | Reactive | Via assignment |
| Connection agent | Minimal durable state + checkpoint working state | Assignment system | Top-level | Async/periodic or threshold batch | — |
| Editor agents | Ephemeral | — | — | Reactive | Via assignment |

**Reactive** = wakes up when new relevant artifacts appear in the store, not on a fixed schedule.

---

## Decision log

Record significant design changes here. Keep the doc body current; use this log to explain why it changed.

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-18 | Split "Ingestion agents" into Source Examination Agent + Ingestion Worker | Understanding a source and fetching from it are distinct concerns with different triggers and success conditions |
| 2026-03-19 | Examination agent writes Scrapy spider code, not a playbook | Code is deterministic and reviewable; a playbook would require a DSL interpreter or LLM reasoning at every crawl. Spider files are committed to the repo and run without LLM involvement |
| 2026-03-19 | Ingestion worker replaced by deterministic Scrapy spiders | Eliminates LLM cost and non-determinism at crawl time. Playbook-guided agentic fetching was complex to debug and test; a committed spider file is explicit, versionable, and cheap to run |
| 2026-03-19 | Examination agent configured inline, not via `agent_configs` | Examination is a developer-only tool run manually; DB-managed config adds no value for this usage pattern |
| 2026-03-26 | Removed **Source Examination Agent** from the inventory; no `sidekick examine` | Spiders are hand-authored (`spiders scaffold` + implementation). The code-gen examination flow was removed intentionally |
| 2026-03-20 | Processing: acquisition + `document-text`; processors only on `raw`+`active` | Matches two-phase raw model; STT and PDF text run only after bytes exist |
| 2026-03-22 | Reframed agent sections to activation/read/retrieval/state/write template and aligned beat/research memory model | Separates trigger semantics from output semantics and removes ambiguity between persistent memory and artifact-store retrieval |
| 2026-03-22 | Split STT into dedicated **Transcription** service (`services/transcription`, `sidekick-transcribe`) | GPU image and torch/whisperx deps are independent from CPU processing; artifact contracts unchanged |
| 2026-03-26 | Documented `processing_profile` for processing/transcription activation | Downstream enrichment is driven by ingest-time profile, not `media_type` inference alone |
| 2026-03-23 | Standardized on DeepAgents for all agent roles; removed LangGraph Graph API | Beat/research/connection agents make real decisions (`write_brief`, `flag_item`, entity lookups) — these are tool calls made when warranted, not predetermined graph nodes. DeepAgents covers all agent needs uniformly |
| 2026-03-23 | Enrichment processors (summary, entity-extract) reclassified as ephemeral DeepAgents with skills | Enrichment quality improves with domain skill files. Processors are still stateless per-artifact — skills are loaded into an ephemeral `InMemoryStore` and discarded after each invocation |
| 2026-03-27 | Added primary/secondary handling to beat and editor agents; attribution rule to editor agent; one-off document note to research search | `source_tier` model requires agents to resolve attribution before citing artifacts and prefer primary sources for factual claims |
| 2026-03-29 | Beat agent durable state updated to reflect stateless-per-run implementation | Step Functions + `AnalysisScope` coordination removes the need for agent-owned cross-run state at this stage; cross-run memory deferred until base pipeline is proven on real data |
