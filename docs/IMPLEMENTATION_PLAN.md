# Implementation Plan

> **Status**: stable
> **Scope**: Stack decisions and build phases — authoritative for technology choices, local/production environment split, and build order
> **Last updated**: 2026-03-29 (Phase 4 complete; Phase 5 API layer built; Terraform expanded)

---

> See `AGENT_DESIGN_PATTERNS.md` for framework selection rationale, state design, memory architecture, structured output conventions, and error handling patterns. This doc covers stack and build order; that doc covers implementation patterns.

## AWS infrastructure (Terraform)

- Module: [`infrastructure/modules/newsroom`](../infrastructure/modules/newsroom/README.md) — ECS Fargate task definitions (ingestion / processing / transcription / analysis), Lambda container images (`packages/lambda-handlers/Dockerfile` → ECR), RDS PostgreSQL, S3 artifact bucket, EFS (for agent skills), AWS Batch (GPU transcription), and four Step Functions state machines: `ingestion`, `processing`, `analysis`, and `orchestration`. The `analysis` machine is event-driven via EventBridge: a `summary` or `entity-extract` artifact write triggers the scope workflow (debounce → claim → run beat agent on Fargate → record → check for new inputs → quiet period → release). See [step_functions.tf](../infrastructure/modules/newsroom/step_functions.tf).
- Module: [`infrastructure/modules/api`](../infrastructure/modules/api/README.md) — ECS Fargate service for the FastAPI API, ALB, and supporting IAM/security group config.
- Module: [`infrastructure/modules/cognito`](../infrastructure/modules/cognito/README.md) — Cognito user pool and app client for human editorial authentication.
- Production root: [`infrastructure/environments/production/`](../infrastructure/environments/production/) — wires all modules to the existing VPC and ECS cluster; set `newsroom_private_subnet_ids` via `terraform.tfvars` (see `terraform.tfvars.example`).

## Stack

| Concern | Local | Production (AWS) |
|---|---|---|
| All agent roles (Beat, Research, Connection, Editor, Discovery, Research search) | DeepAgents (built on LangGraph) | DeepAgents (built on LangGraph) |
| Scheduled ingestion | Scrapy (`CrawlerProcess`) | Scrapy (`CrawlerProcess`) |
| Artifact metadata + vector index | Postgres + pgvector | Postgres + pgvector (RDS) |
| Document / media storage | MinIO (S3-compatible) | S3 |
| Inter-agent messaging | Postgres LISTEN/NOTIFY | EventBridge / SQS |
| Assignment store | Postgres (separate table) | Postgres (RDS) |
| Schema management | SQLModel + Alembic | SQLModel + Alembic |
| STT | WhisperX on CPU via **`sidekick-transcribe`** (`services/transcription`) | WhisperX on AWS Batch (g4dn.xlarge spot) with **sidekick-transcription** image |
| Long-running agents (beat, connection) | Local processes | Fargate |
| Short-lived jobs (ingestion, processing) | Local processes | Lambda or Fargate |

---

## Phases

### Phase 1 — Data layer and pub/sub infrastructure

Everything else depends on this. Build it before any agent code.

**Postgres schema**

```sql
-- Source registry
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    endpoint TEXT,
    schedule JSONB,
    beat TEXT,
    geo TEXT,
    related_sources TEXT[],
    discovered_by TEXT,
    registered_at TIMESTAMPTZ,
    examination_status TEXT NOT NULL DEFAULT 'pending',  -- pending | active | failed | paused
    health JSONB
);

-- Artifact store
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    content_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    media_type TEXT,
    -- Lineage
    derived_from TEXT[],
    -- Context
    source_id TEXT REFERENCES sources(id),
    event_group TEXT,
    beat TEXT,
    geo TEXT,
    period_start DATE,
    period_end DATE,
    -- Discovery
    entities JSONB,
    topics TEXT[],
    embedding vector(1536),
    -- Content pointer (all bodies; small and large)
    content_uri TEXT,       -- s3://... object storage key
    -- Provenance
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    assignment_id TEXT,
    -- Status
    status TEXT DEFAULT 'active',
    superseded_by TEXT REFERENCES artifacts(id)
);

CREATE INDEX ON artifacts USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON artifacts (stage, beat, geo);
CREATE INDEX ON artifacts (event_group);
CREATE INDEX ON artifacts (assignment_id);

-- Assignments
CREATE TABLE assignments (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    query_text TEXT NOT NULL,
    query_params JSONB,
    triggered_by TEXT,
    triggered_by_id TEXT,
    triggered_at TIMESTAMPTZ DEFAULT now(),
    parent_assignment TEXT REFERENCES assignments(id),
    artifacts_in TEXT[],
    artifacts_out TEXT[],
    sub_assignments TEXT[],
    monitor JSONB
);

-- Agent configs
CREATE TABLE agent_configs (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL UNIQUE,
    model TEXT NOT NULL,
    prompts JSONB NOT NULL,           -- slot_name -> prompt text
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT
);
```

**Artifact store service**

A Python module (`artifact_store.py`) that is the *only* path for reading and writing artifacts. Direct DB access from agents is a code smell.

```python
class ArtifactStore:
    def write(self, artifact: Artifact) -> str:
        # 1. Validate required fields (stage, content_type, derived_from if not raw)
        # 2. Generate embedding if not provided
        # 3. Write large content to S3; store key in content_uri
        # 4. Insert row to artifacts table
        # 5. NOTIFY 'artifact_written' with JSON payload
        # Returns artifact ID

    def read(self, artifact_id: str) -> Artifact:
        # Fetch metadata from DB; fetch content from S3 if content_uri set

    def query(
        self,
        filters: dict,           # structured: stage, beat, geo, content_type, etc.
        embedding: list[float] | None = None,  # semantic similarity
        limit: int = 20
    ) -> list[Artifact]:
        # Build SQL combining WHERE clauses + ORDER BY embedding <=> $vec

    def lineage(self, artifact_id: str, direction: str = "up") -> list[Artifact]:
        # Traverse derived_from links; direction="up" goes toward raw
```

**Pub/sub**

`write()` fires a NOTIFY after every successful artifact insert:

```python
NOTIFY artifact_written, '{"id": "art_a1b2c3", "stage": "processed", "beat": "government:city-council", "geo": "us:il:springfield:springfield", "content_type": "summary"}';
```

Agents subscribe via a `NotifyListener` wrapper that:
- Opens a persistent Postgres connection with `LISTEN artifact_written`
- Parses the JSON payload
- Calls a registered handler if the payload matches the agent's filter (stage, beat, geo)

Keep the payload small — just IDs and routing metadata. Agents fetch the full artifact via `ArtifactStore.read()` when they wake up.

**S3 key convention**

```
s3://bucket/artifacts/{stage}/{beat}/{geo}/{artifact_id}
```

**Schema management**

Use **SQLModel + Alembic**. SQLModel (by the FastAPI author) lets you define Pydantic models that double as SQLAlchemy table definitions — one schema definition used for validation, querying, and migrations. Alembic auto-generates migration files from schema diffs and maintains a versioned migration history. Run `alembic upgrade head` on both local and production.

**Environment abstraction**

The object store differs between local and AWS. Define interfaces up front so agent code never imports environment-specific libraries directly:

```python
class ObjectStore(Protocol):
    def put(self, key: str, content: bytes) -> str: ...   # returns URI
    def get(self, key: str) -> bytes: ...
```

Implementation:
- `MinIOObjectStore` / `S3ObjectStore`: identical boto3 code, different `endpoint_url`. Set `AWS_ENDPOINT_URL=http://localhost:9000` locally; unset in production.

Agent code only ever sees the `ObjectStore` protocol. Swap implementations via dependency injection at startup.

For event handlers, use a decorator that works in both environments:

```python
@event_handler("artifact_written", stage="processed", beat="government:city-council")
def handle_new_processed_artifact(event: ArtifactEvent):
    ...
```

Locally: the framework registers this and calls it when the pg NOTIFY fires. On AWS: the decorator metadata drives CDK/Terraform to generate the EventBridge rule; the Lambda/Fargate entrypoint calls the same function when invoked.

**Local development environment**

Docker Compose with three services:
- `postgres`: Postgres 16 with pgvector extension
- `minio`: MinIO with a pre-created `artifacts` bucket
- `app`: the pipeline processes (or run these outside Docker for easier debugging)

One command to get a fully functional local environment: `docker compose up`.

**Deliverable** ✓: artifact store service with write/read/query/lineage, pub/sub listener, `AgentConfigRegistry` with TTL cache, Alembic migrations, environment abstraction layer, Docker Compose local dev setup, and basic tests against a local Postgres + MinIO instance.

Additional items built beyond the original Phase 1 scope:
- `AssignmentStore` (`packages/core/src/sidekick/core/assignment_store.py`) — CRUD wrapper for the assignments table; used by beat agents to create research follow-up assignments.
- `vocabulary.py` — controlled `ContentType`, `Stage`, and `ArtifactStatus` enums shared across all services.
- `skills.py` — utility to build a DeepAgents `InMemoryStore` from flat skill text files.
- `embeddings.py` — thin wrapper around OpenAI embeddings.
- Migration 003: `api_clients` table (hashed API keys for machine auth).
- Migration 004: `processing_profile` column on `artifacts` (controls which processors run).
- Migration 005: `analysis_scopes` table — scope coordinator for the Step Functions beat-agent workflow (tracks dirty state, active execution ARN, revision counter, last brief artifact ID).

---

### Phase 2 — Ingestion pipeline ✓ (complete)

**Source registry service**

CRUD operations on the `sources` table. Thin layer — no complex logic.

**Spider authoring**

New sources use `sidekick spiders scaffold` to generate a stub, then developers implement `SidekickSpider` subclasses under `services/ingestion/src/sidekick/spiders/`. `sidekick spiders sync` upserts registry rows after review. There is no separate code-gen CLI.

**Spider harness**

Scrapy-based deterministic ingestion. No LLM at crawl time. Components:
- `SidekickSpider` base class — required class attributes validated via `SpiderMeta` (Pydantic)
- `ArtifactWriterPipeline` — converts `RawItem` → `Artifact`; stores all payloads in object storage via `content_uri`
- `DeduplicationMiddleware` — loads seen URLs from artifact store on `spider_opened`; drops duplicates
- `run_spider()` / `run_spiders()` — wires `CrawlerProcess`; updates source health afterward

**CLI commands** (all under `sidekick spiders`):
- `spiders list` — show all discovered spiders with health from DB
- `spiders sync` — upsert `Source` rows from spider class attributes
- `spiders run SOURCE_ID` — run a specific spider
- `spiders due` — run all spiders whose cron schedule is due
- `spiders test SPIDER_NAME` — dry-run (no artifact writes)

**Deliverable** ✓: committed spider files; `spiders sync` registers the source; `spiders run` / `spiders due` fetch from it; `raw` artifacts appear in the store and fire `artifact_written` notifications.

---

### Phase 3 — Processing agents ✓ (complete)

Phase 3 spans **`services/processing/`** and **`services/transcription/`**: acquisition (complete async raw stubs), **PDF text normalization**, **speech-to-text** (WhisperX in the transcription service), and **LLM enrichment**. Orchestration in production uses Step Functions / Batch; locally, use **`sidekick-process`** (processing) and **`sidekick-transcribe <artifact_id>`** (STT).

Phase 3 must complete the full processing chain through `summary` and `entity-extract` before beat agents (Phase 4) are built. Beat agents' primary input is these enrichment contracts — not raw text or full transcripts. This keeps beat agents focused on longitudinal synthesis rather than per-document extraction, and means a single enrichment pass serves multiple downstream agents independently.

**Event triggers**

- **`acquisition_needed`** (from ingestion for HLS / yt-dlp stubs): dispatch acquisition — ffmpeg / yt-dlp, then `ArtifactStore.complete_acquisition()`.
- **`artifact_written`** with `stage="raw"` and `status="active"`: triggers PDF → `document-text` (processing) and audio/video → `document-text` (transcription service). Ignore `pending_acquisition` stubs (no bytes yet).
- **`artifact_written`** with `stage="processed"` and `content_type = "document-text"`: triggers enrichment through orchestration. For `full`, run `entity-extract` first and `summary` second; for `index`, run `entity-extract`; for `structured`, run `structured-data`.

**Processors**

Processing runs in two passes. The first pass normalizes bytes to text; the second enriches text into extraction/synthesis contracts.

| Step / processor | Triggers on | Produces |
|---|---|---|
| Acquisition (HLS, etc.) | `acquisition_needed` + raw stub | Completes same raw row (`active`, `content_uri` set) |
| PDF text extraction | `raw` + `active` + `media_type = application/pdf` | `document-text` |
| Transcript (STT) | `raw` + `active` + `audio/*` or `video/*` | `document-text` ( **`services/transcription`** ) |
| Entity extraction | `processed` + `document-text` | `entity-extract` |
| Summarization | `processed` + `document-text` + sibling `entity-extract` | `summary` |
| Structured data extractor | `processed` + `document-text` where `content_type = budget` or `agenda` | `structured-data` |

Normalization to `document-text` is done by plain functions — stateless transforms with no decision-making — or by direct text ingestion when the spider already has canonical plain text. **Enrichment processors** (`summary`, `entity-extract`) **are DeepAgents** — they use the skills system for domain-informed extraction. Skills are loaded from the agent config row into an ephemeral `InMemoryStore` and exposed via `StoreBackend`. Structured output is produced via `response_format=ToolStrategy(PydanticModel)` — see `AGENT_DESIGN_PATTERNS.md`. **`document-text`** is the required intermediate for LLM-friendly plain text before enrichment.

**Transcript processor (STT)**

Implemented in **`services/transcription/`** — **WhisperX** (Faster-Whisper / CTranslate2 backend) with pyannote.audio for speaker diarization. CLI: **`sidekick-transcribe <artifact_id>`**. CPU locally, GPU on Batch in production.

Context prompts are constructed per-source from source registry metadata:
```
"Springfield City Council meeting. Members: Jane Smith, Bob Jones, Alice Chen.
Topics may include: Zoning Ordinance 2026-14, FY2027 budget, Maple Street Elementary."
```
The source registry entry provides beat/geo context. Optional named-entity hints can come from recent `entity-extract` artifacts on the same source/event group; do not couple STT bootstrapping to beat-agent internal state.

*Locally*: run a small model on CPU. Keep a short test clip (5-10 min) for iteration.

*On AWS*: AWS Batch job on a **g4dn.xlarge spot instance** (~$0.16/hr spot) using the **sidekick-transcription** container image. Flow: **`raw` + `active`** audio/video artifact → job → WhisperX large-v3 → **`document-text`** artifact written. A typical 2-hour council meeting costs ~$0.32 in GPU time.

Use `large-v3` in production. The T4 GPU on g4dn.xlarge handles it at roughly real-time speed.

**Deliverable** ✓: Async raw stubs are acquired; `active` raw artifacts and direct-ingested text artifacts produce `document-text`; those in turn produce `summary` and `entity-extract`. Each step fires another `artifact_written` notification. Processing runnable locally and deployable as container/Batch jobs.

---

### Phase 4 — Beat agents ✓ (complete)

Beat agents are DeepAgents — see `AGENT_DESIGN_PATTERNS.md` for the full pattern.

**Primary input**: `summary` and `entity-extract` artifacts from Phase 3 enrichment. Beat agents read full `document-text` artifacts only as an exception — when a summary is too lossy for a specific analytical question.

**Tools** (actual): `query_artifacts`, `write_beat_brief`, `flag_item`, `create_research_assignment`. The agent decides which tools to call based on the artifact content.

**Production orchestration** (event-driven via Step Functions + EventBridge):
A `summary` or `entity-extract` artifact write fires an EventBridge event (`artifact_written`, `stage=processed`). The `analysis` Step Functions state machine handles:
1. `UpsertScopeState` (Lambda) — creates or updates the `AnalysisScope` row for the event group; increments revision; marks dirty.
2. `WaitDebounce` — configurable wait to absorb bursts of enrichment writes for the same event group.
3. `ClaimScope` (Lambda) — acquires exclusive ownership; skips if another execution holds the lock.
4. `RunBeatAgent` — launches the analysis ECS Fargate task running `sidekick-beat brief --beat … --geo … --event-group … --output-json`. Task token used for async completion.
5. `RecordRunResult` (Lambda) — persists written artifact IDs and marks revision completed.
6. `CheckForNewInputs` / `NeedsFollowupRun` — reruns if new enrichment arrived during execution.
7. `WaitQuietPeriod` / `CheckQuietPeriod` / `QuietPeriodStable` — quiet-period reevaluation before releasing the scope.
8. `ReleaseScope` (Lambda) — clears the execution lock.

Locally: run directly with `sidekick-beat brief --beat <beat> --geo <geo> --event-group <id>` (event-group scope) or `--since <date> --until <date>` (date window scope, used for assignment-driven runs).

The `AnalysisScope` table (`analysis_scopes`, migration 005) is the coordination layer — it tracks `dirty`, `revision`, `active_execution_arn`, and `last_brief_artifact_id`. Scope coordination Lambdas live in `packages/lambda-handlers/`.

**Agent state**: each beat-agent run is stateless (ephemeral DeepAgents run). No durable `/memories/` state is persisted between runs. Coordination state is fully captured by `AnalysisScope`.

**Reference implementation** ✓: `government` beat agent (`beat-agent:government` config) for `us:ca:shasta` sources.

**Deliverable** ✓: processed artifacts on a beat produce `beat-brief` and `flag` analysis artifacts; the analysis Step Functions workflow debounces, coordinates, and retries runs correctly.

---

### Phase 5 — Editor agents and human editorial interface (API layer complete; editor agent pending)

**API service** ✓ (`services/api/`)

FastAPI REST API with authentication built and deployed:
- **Authentication**: Cognito JWT Bearer tokens (public users) + `X-API-Key` hashed in `api_clients` (machine/process clients). Route authorization via shared role guards: `reader`, `editor`, `admin`, `machine`.
- **Routers built**: sources (CRUD), artifacts (list/get/patch/retract), assignments (CRUD), agent_configs (CRUD), api_clients (create/list/rotate/revoke).
- **Terraform**: `infrastructure/modules/api/` (ECS Fargate service, ALB) and `infrastructure/modules/cognito/` (user pool + app client).
- **Generated client**: `packages/api-client/` — typed Python client generated from the OpenAPI schema; used by agents and CLI tooling to call the API.

**Remaining (editor agent and editorial workflow)**

The editorial draft-review workflow is not yet built. What remains:

*Editor agent* (`services/editor/` — not yet created):

DeepAgents — drafting and revision involve an open-ended multi-step loop whose length isn't known at design time. Each draft is an independent run (ephemeral `StateBackend`; no persistent state).

```
receive_flag → [DeepAgents: gather context, draft, iterate on feedback] → write_draft_artifact
```

`gather_context` reads the flagged analysis artifact, then uses lineage traversal to pull in the supporting processed and raw artifacts (for quotes and sourcing).

Triggered when a `flag` artifact is written, or when a story assignment completes dispatch.

*Draft review routes* (not yet added to `services/api/`):
- `GET /queue` — drafts awaiting review, grouped by assignment if applicable
- `POST /draft/{id}/approve` — publishes or moves to publication layer
- `POST /draft/{id}/reject` — archives with reason
- `POST /draft/{id}/send-back` — returns to editor agent with feedback note

The send-back flow: the feedback note is appended to the editor agent's context, and it re-runs from `draft`.

**Deliverable**: flags become draft artifacts; a human can approve, reject, or send back. End-to-end pipeline is now testable on real data.

---

### Phase 6 — Connection agent and assignment system

Build these after the base pipeline is proven on real data, because:
1. The connection agent needs a meaningful volume of analysis artifacts to find anything
2. The assignment system is most useful once you understand the gaps the base pipeline actually produces

**Connection agent**

DeepAgent — see `AGENT_DESIGN_PATTERNS.md`. Runs on a schedule (e.g., every 4 hours) rather than event-triggered — it reads the full analysis layer, not individual artifacts.

**Tools**: `semantic_cluster`, `entity_cross_reference`, `write_connection_memo`, `create_assignment`. Durable state under `/memories/` tracks cross-beat threads already surfaced to avoid repetition.

Semantic clustering: embed the query "what themes appear across beats in the last N days?" and find artifact clusters. Entity cross-reference: find entities appearing in >1 beat.

**Assignment system**

The assignment system is an orchestrator, not an agent. It can be implemented as a set of functions called by the editorial API and by agents:

```python
def create_assignment(query_text, type, triggered_by, triggered_by_id) -> Assignment:
    # Extract query_params via LLM
    # Query store for existing artifacts
    # Run gap analysis
    # Dispatch to appropriate agents
    # Return assignment with status

def gap_analysis(assignment: Assignment) -> list[Gap]:
    # Compare existing artifacts against expected chain
    # Return list of gaps with type (missing raw, missing processed, etc.)

def dispatch(assignment: Assignment, gaps: list[Gap]) -> None:
    # For each gap, send targeted request to appropriate agent/service
```

**Discovery and research search agents**

These are the last pieces because they depend on:
- The source registry (discovery agent proposes to it)
- The assignment system (research search is triggered by assignments)

Both use **DeepAgents** — they are open-ended search tasks where the number of steps (search, fetch, validate, follow links) is unknown at design time. Discovery search uses a `CompositeBackend` so `/memories/` (explored domains, prior proposals) persists across runs. Research search is stateless.

---

## Build sequence summary

```
Phase 1: DB schema + artifact store service + pub/sub          ✓ complete
Phase 2: Source registry + ingestion agents                    ✓ complete
Phase 3: Processing agents                                     ✓ complete
Phase 4: Beat agents (DeepAgents)                              ✓ complete
Phase 5: Editor agents + editorial API                         ~ in progress (API layer done; editor agent pending)
Phase 6: Connection agent + assignment system                  not started
```

After Phase 3 you can run ingestion → processing on real sources. After Phase 4 (now complete) you have analysis artifacts. After Phase 5 you have a complete pipeline from source to human review.

---

## Key decisions to make before writing code

1. **Embedding model**: OpenAI `text-embedding-3-small` (1536-dim) is the pragmatic default. Dimension is baked into the schema (`vector(1536)`) and the ivfflat index — changing it later requires rebuilding the column. Decide before running the first migration.

2. **Notification fan-out**: A single `artifact_written` channel works for small agent counts. If you end up with many beat agents, consider per-beat channels (`artifact_written:government:city-council:us:il:springfield:springfield`) to avoid agents waking up for irrelevant events. Easy to change early, harder to change once agents are deployed.

**Decided** (see `AGENT_DESIGN_PATTERNS.md` for rationale):
- Agent framework: DeepAgents for all agent roles (including enrichment processors); Scrapy for ingestion; plain functions for normalization only (PDF text extraction, STT).
- All LLM calls use `llm.with_structured_output(PydanticModel)` — no free-form string parsing.

## Post-doc implementation follow-ups

These are implementation tickets implied by the reconciled design docs:

1. Enforce controlled `content_type` validation in `ArtifactStore.write()` (parallel to existing beat/geo validation).
2. Define and implement row-level projection strategy for `entity-extract` structured fields (especially financial figures and motions/votes).
3. Set embedding policy for extraction/index artifacts (including whether and how `entity-extract` bodies are embedded).
4. Specify and implement connection-agent execution mode in production (schedule cadence, threshold buffering, replay behavior).
5. Formalize artifact-chain templates in assignment orchestrator code so gap analysis is deterministic.

---

## Decision log

Record significant design changes here. Keep the doc body current; use this log to explain why it changed.

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-18 | Split agent framework: LangGraph for Beat/Research/Connection; DeepAgents for Editor/Discovery/Research search; plain functions for Processing | Match framework to control-flow ownership — fixed topology → LangGraph; open-ended planning → DeepAgents; stateless transform → no framework |
| 2026-03-26 | Removed `sidekick examine` and source examination agent from the plan | Spiders are hand-authored; code-gen path was removed |
| 2026-03-23 | Standardized on DeepAgents for all agent roles; removed LangGraph Graph API | Beat/research/connection agents make real decisions (`write_brief`, `flag_item`, entity lookups) — these are tool calls made when warranted, not predetermined graph nodes. DeepAgents covers all agent needs uniformly; stateless transforms remain plain functions |
| 2026-03-18 | All LLM calls require `with_structured_output(PydanticModel)` | Type safety and explicit contracts; free-form string parsing is fragile at scale |
| 2026-03-18 | Replaced fetch strategy vocabulary with playbook model; split ingestion into Source Examination Agent + Ingestion Worker | Fixed strategy types can't express real-world source complexity without growing into a DSL |
| 2026-03-18 | Added `agent_configs` table and `AgentConfigRegistry` to Phase 1 | Model and prompt configuration must exist before any agent runs; belongs in the data layer alongside the other registries |
| 2026-03-19 | Replaced agentic ingestion worker (DeepAgents + playbook) with Scrapy spiders | Eliminates LLM cost and non-determinism at every crawl. Examination agent now generates a committed spider file instead of a DB playbook. Ingestion becomes deterministic code: cheaper, faster, easier to debug, and testable without mocking LLM calls |
| 2026-03-20 | Removed `playbook` column from `sources` table (schema and doc references) | Column was never populated after the Scrapy migration — the spider file is the authoritative fetch description. Keeping a null column in the schema was misleading |
| 2026-03-20 | Phase 3: `services/processing/`, acquisition via `complete_acquisition`, processors only on `raw`+`active`; add `document-text` | Aligns processing with two-phase raw stubs; separates byte capture from STT/PDF text extraction; Step-Functions-friendly dispatch |
| 2026-03-20 | Phase 3 now includes `summary` + `entity-extract` enrichment as required deliverables before Phase 4 | Beat agents' primary input must be enriched artifacts, not raw text. Enrichment is stateless per-document work (belongs in processing); beat agents' job is longitudinal synthesis. A single enrichment pass also serves multiple downstream agents independently. Phase 4 cannot start until Phase 3 enrichment is complete. |
| 2026-03-21 | Phase 3 complete: `structured-data` extractor deferred | `summary` + `entity-extract` are the hard prerequisites for Phase 4 beat agents. `structured-data` is conditional on content_type (budget/agenda) and adds scope; deferred until the enrichment pattern is proven and beat agents are consuming the required artifacts. |
| 2026-03-21 | Added Terraform `newsroom` module (ECS task defs, RDS Postgres, Step Functions skeleton) | Establishes production execution/orchestration primitives without recreating VPC or ECS cluster; production env wires module + documents subnet tfvars. |
| 2026-03-22 | Aligned memory and artifact semantics with reconciled design docs; added implementation follow-up list | Removes checkpoint-as-primary-memory ambiguity and turns taxonomy/assignment decisions into concrete build tasks |
| 2026-03-22 | Split STT into **`services/transcription`** (`sidekick-transcribe`, dedicated GPU Dockerfile) separate from **`services/processing`** | Independent deps and images; optional `stt` extra on processing was the wrong boundary |
| 2026-03-23 | Reclassified enrichment processors (summary, entity-extract) as DeepAgents with skills | Skills provide domain knowledge (news-values, entity-and-actor-tracking, etc.) that plain functions cannot access. Processors are ephemeral — no durable state. Plain functions remain correct for normalization-only steps (PDF text, STT). |
| 2026-03-24 | Ingestion `list-due` in production: shared logic in `sidekick.core.due_sources`; Lambda package `packages/lambda-handlers`; Terraform `null_resource` + `data.archive_file` zip + Step Functions `lambda:invoke` | Avoid Fargate for a trivial DB query; keep Scrapy out of the Lambda artifact; DB remains source of truth for due sources. |
| 2026-03-28 | Beat agent orchestration via Step Functions + EventBridge instead of a `beat_agent_manager` process | Event-driven scope workflow (debounce → claim → RunBeatAgent on Fargate → record → check → quiet period → release) is more resilient and observable than a long-running listener process. `AnalysisScope` table provides coordination state; no durable agent memory needed. |
| 2026-03-28 | Beat agent is stateless per run — no durable `/memories/` state | The scope coordination layer (`AnalysisScope`) captures all orchestration state. Agent memory across runs was not needed to produce useful `beat-brief` and `flag` artifacts in practice; added complexity for unproven benefit. Can be revisited once the base pipeline is running on real data. |
| 2026-03-28 | Phase 5 split: API layer (auth + CRUD + Terraform) built first, editor agent deferred | The API foundation (Cognito, api_clients, all resource routes) is a prerequisite for the editorial workflow and useful independently for tooling. Editor agent and draft review routes are the remaining Phase 5 deliverable. |
| 2026-03-29 | Added `packages/api-client/` — generated Python client for the API | Typed client used by agents, CLI tools, and tests to call the API without raw HTTP; generated from OpenAPI schema so it stays in sync automatically. |
