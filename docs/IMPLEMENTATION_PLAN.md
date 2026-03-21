# Implementation Plan

> **Status**: stable
> **Scope**: Stack decisions and build phases — authoritative for technology choices, local/production environment split, and build order
> **Last updated**: 2026-03-20 (Phase 3 enrichment required before Phase 4)

---

> See `AGENT_DESIGN_PATTERNS.md` for framework selection rationale, state design, memory architecture, structured output conventions, and error handling patterns. This doc covers stack and build order; that doc covers implementation patterns.

## Stack

| Concern | Local | Production (AWS) |
|---|---|---|
| Stateful agent orchestration (Beat, Research, Connection) | LangGraph Graph API | LangGraph Graph API |
| Open-ended agents (Editor, Discovery, Research search, Source examination) | DeepAgents (built on LangGraph) | DeepAgents (built on LangGraph) |
| Scheduled ingestion | Scrapy (`CrawlerProcess`) | Scrapy (`CrawlerProcess`) |
| Artifact metadata + vector index | Postgres + pgvector | Postgres + pgvector (RDS) |
| Document / media storage | MinIO (S3-compatible) | S3 |
| Inter-agent messaging | Postgres LISTEN/NOTIFY | EventBridge / SQS |
| Assignment store | Postgres (separate table) | Postgres (RDS) |
| Beat agent persistent state | LangGraph checkpoints via `PostgresSaver` | LangGraph checkpoints via `PostgresSaver` |
| Schema management | SQLModel + Alembic | SQLModel + Alembic |
| STT | WhisperX on CPU (small model) | WhisperX on AWS Batch (g4dn.xlarge spot) |
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
    expected_content JSONB,       -- declared at registration; guides examination
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
NOTIFY artifact_written, '{"id": "art_a1b2c3", "stage": "processed", "beat": "government:city_council", "geo": "us:il:springfield:springfield", "content_type": "summary"}';
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

The event bus and object store differ between local and AWS. Define interfaces up front so agent code never imports environment-specific libraries directly:

```python
class EventBus(Protocol):
    def publish(self, event_type: str, payload: dict) -> None: ...
    def subscribe(self, event_type: str, handler: Callable) -> None: ...

class ObjectStore(Protocol):
    def put(self, key: str, content: bytes) -> str: ...   # returns URI
    def get(self, key: str) -> bytes: ...
```

Two implementations:
- `LocalEventBus`: wraps Postgres LISTEN/NOTIFY
- `AWSEventBus`: wraps EventBridge/SQS; `subscribe()` is a no-op at runtime — routing is configured in infrastructure (CDK/Terraform)

- `MinIOObjectStore` / `S3ObjectStore`: identical boto3 code, different `endpoint_url`. Set `AWS_ENDPOINT_URL=http://localhost:9000` locally; unset in production.

Agent code only ever sees the `EventBus` and `ObjectStore` protocols. Swap implementations via dependency injection at startup.

For event handlers, use a decorator that works in both environments:

```python
@event_handler("artifact_written", stage="processed", beat="government:city_council")
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

**Deliverable**: artifact store service with write/read/query/lineage, pub/sub listener, `AgentConfigRegistry` with TTL cache, Alembic migrations, environment abstraction layer, Docker Compose local dev setup, and basic tests against a local Postgres + MinIO instance.

---

### Phase 2 — Ingestion pipeline ✓ (complete)

**Source registry service**

CRUD operations on the `sources` table. Thin layer — no complex logic.

**Source examination agent**

DeepAgents (LangChain `create_react_agent`) — examining a source involves open-ended browsing where the number of steps is unknown at design time.

The agent browses the source endpoint and writes a `SidekickSpider` subclass to `services/ingestion/src/sidekick/spiders/`. It does not create a DB row — that happens via `spiders sync` after developer review. Model configured inline; no `agent_configs` DB row required.

```
sidekick examine --url URL --beat BEAT --geo GEO [--name NAME]
```

**Spider harness**

Scrapy-based deterministic ingestion. No LLM at crawl time. Components:
- `SidekickSpider` base class — required class attributes validated via `SpiderMeta` (Pydantic)
- `ArtifactWriterPipeline` — converts `RawItem` → `Artifact`; binary to object store, text inline
- `DeduplicationMiddleware` — loads seen URLs from artifact store on `spider_opened`; drops duplicates
- `run_spider()` / `run_spiders()` — wires `CrawlerProcess`; updates source health afterward

**CLI commands** (all under `sidekick spiders`):
- `spiders list` — show all discovered spiders with health from DB
- `spiders sync` — upsert `Source` rows from spider class attributes
- `spiders run SOURCE_ID` — run a specific spider
- `spiders due` — run all spiders whose cron schedule is due
- `spiders test SPIDER_NAME` — dry-run (no artifact writes)

**Deliverable** ✓: `sidekick examine` generates a spider file; `spiders sync` registers the source; `spiders run` fetches from it; `raw` artifacts appear in the store and fire `artifact_written` notifications.

---

### Phase 3 — Processing agents

Phase 3 lives in **`services/processing/`**: acquisition (complete async raw stubs) plus **text normalization and enrichment**. Orchestration in production can be Step Functions / Batch; locally, use the **`sidekick-process`** CLI.

Phase 3 must complete the full processing chain through `summary` and `entity-extract` before beat agents (Phase 4) are built. Beat agents' primary input is these enriched artifacts — not raw text or full transcripts. This keeps beat agents focused on longitudinal synthesis rather than per-document extraction, and means a single enrichment pass serves multiple downstream agents independently.

**Event triggers**

- **`acquisition_needed`** (from ingestion for HLS / yt-dlp stubs): dispatch acquisition — ffmpeg / yt-dlp, then `ArtifactStore.complete_acquisition()`.
- **`artifact_written`** with `stage="raw"` and `status="active"`: triggers text extraction processors (`document-text`, `transcript-clean`). Ignore `pending_acquisition` stubs (no bytes yet).
- **`artifact_written`** with `stage="processed"` and `content_type in ("document-text", "transcript-clean")`: triggers enrichment processors (`summary`, `entity-extract`).

**Processors**

Processing runs in two passes. The first pass normalizes bytes to text; the second enriches text into structured analysis artifacts.

| Step / processor | Triggers on | Produces |
|---|---|---|
| Acquisition (HLS, etc.) | `acquisition_needed` + raw stub | Completes same raw row (`active`, `content_uri` set) |
| PDF text extraction | `raw` + `active` + `media_type = application/pdf` | `document-text` |
| Transcript (STT) | `raw` + `active` + `audio/*` or `video/*` | `transcript-clean` |
| Summarization | `processed` + `document-text` or `transcript-clean` | `summary` |
| Entity extraction | `processed` + `document-text` or `transcript-clean` | `entity-extract` |
| Structured data extractor | `processed` + `document-text` where `content_type = budget` or `agenda` | `structured-data` |

Each processor is a simple function, not a LangGraph graph — stateless transformation with no memory needed. **`document-text`** is the required intermediate for LLM-friendly plain text before summarization and NER. Enrichment processors (`summary`, `entity-extract`) use `llm.with_structured_output(PydanticModel)` — see `AGENT_DESIGN_PATTERNS.md`.

**Transcript processor (STT)**

Use **WhisperX** in production — Faster-Whisper (CTranslate2 backend) with pyannote.audio for speaker diarization. Local development may use **faster-whisper** (CPU) in the processing service until WhisperX is wired.

Context prompts are constructed per-source from source registry metadata:
```
"Springfield City Council meeting. Members: Jane Smith, Bob Jones, Alice Chen.
Topics may include: Zoning Ordinance 2026-14, FY2027 budget, Maple Street Elementary."
```
The source registry entry knows the beat and geo; the beat agent's `known_entities` provides the entity list. Processing agents request this context when invoking WhisperX.

*Locally*: run a small model on CPU. Keep a short test clip (5-10 min) for iteration.

*On AWS*: AWS Batch job on a **g4dn.xlarge spot instance** (~$0.16/hr spot). Flow: **`raw` + `active`** audio/video artifact → job → WhisperX large-v3 → **`transcript-clean`** artifact written. A typical 2-hour council meeting costs ~$0.32 in GPU time.

Use `large-v3` in production. The T4 GPU on g4dn.xlarge handles it at roughly real-time speed.

**Deliverable**: Async raw stubs are acquired; `active` raw artifacts produce `document-text` and `transcript-clean`; those in turn produce `summary` and `entity-extract`. Each step fires another `artifact_written` notification. Processing runnable locally and deployable as container/Batch jobs. Beat agents (Phase 4) can start only after enrichment artifacts exist.

---

### Phase 4 — Beat agents

This is the first LangGraph graph in the system and the reference implementation for all stateful agents. All LLM calls use `llm.with_structured_output(PydanticModel)` — see `AGENT_DESIGN_PATTERNS.md`.

**Primary input**: `summary` and `entity-extract` artifacts from Phase 3 enrichment. Beat agents read full `document-text` or `transcript-clean` artifacts only as an exception — when a summary is too lossy for a specific analytical question. Raw artifacts are accessible via lineage traversal but should never be the default read path. This separation ensures beat agents focus on longitudinal synthesis (tracking patterns, entities, and developments across time) rather than per-document extraction, which is already handled by Phase 3.

**Graph structure**

```
[LISTEN for artifact_written] → receive_artifact → analyze → write_brief → update_state
                                                          ↓
                                                     flag_item (if warranted)
```

Beat agents wake on `artifact_written` filtered to `stage="processed"` and `content_type in ("summary", "entity-extract")` for their beat/geo.

**State schema**

```python
class BeatAgentState(TypedDict):
    beat: str
    geo: str
    narrative: str          # running summary of what's happening on this beat
    known_entities: list[dict]
    developing_stories: list[dict]  # {title, first_seen, artifact_ids, status}
    pending_flags: list[str]        # artifact IDs flagged, not yet surfaced
```

State is checkpointed to Postgres via `PostgresSaver` after every run. The beat agent's persistent memory is its LangGraph checkpoint — no separate memory system needed.

**Instantiation**

One graph instance per beat (× geo). A `beat_agent_manager` process:
- Reads the set of active beats/geos from the source registry
- Starts a listener for each
- Resumes from checkpoint if one exists

**Reference implementation**: `government:city_council` beat agent in `us:il:springfield:springfield`. Build this one fully before generalizing.

**Deliverable**: processed artifacts on a beat produce `beat-brief` and `flag` analysis artifacts; beat agent state persists across runs.

---

### Phase 5 — Editor agents and human editorial interface

**Editor agent**

DeepAgents (not LangGraph) — drafting and revision involve an open-ended multi-step loop whose length isn't known at design time. DeepAgents' built-in context summarization handles the long multi-turn feedback cycle cleanly. Each draft is an independent run (ephemeral `StateBackend`; no persistent state).

```
receive_flag → [DeepAgents: gather context, draft, iterate on feedback] → write_draft_artifact
```

`gather_context` reads the flagged analysis artifact, then uses lineage traversal to pull in the supporting processed and raw artifacts (for quotes and sourcing).

Triggered when a `flag` artifact is written, or when a story assignment completes dispatch.

**Human editorial interface**

An API (FastAPI) exposing:
- `GET /queue` — drafts awaiting review, grouped by assignment if applicable
- `POST /draft/{id}/approve` — publishes or moves to publication layer
- `POST /draft/{id}/reject` — archives with reason
- `POST /draft/{id}/send-back` — returns to editor agent with feedback note
- `POST /assignments` — creates a new assignment
- `GET /assignments/{id}` — assignment status and associated artifacts
- `POST /sources` — register a new source; triggers source examination agent automatically
- `GET /sources/{id}` — source entry with health and examination status
- `POST /sources/{id}/examine` — manually trigger re-examination (e.g., after a site redesign)

The send-back flow: the feedback note is appended to the editor agent's context, and it re-runs from `draft`.

**Deliverable**: flags become draft artifacts; a human can approve, reject, or send back. End-to-end pipeline is now testable on real data.

---

### Phase 6 — Connection agent and assignment system

Build these after the base pipeline is proven on real data, because:
1. The connection agent needs a meaningful volume of analysis artifacts to find anything
2. The assignment system is most useful once you understand the gaps the base pipeline actually produces

**Connection agent**

LangGraph graph with persistent state. Runs on a schedule (e.g., every 4 hours) rather than event-triggered — it reads the full analysis layer, not individual artifacts.

State tracks cross-beat threads it has already surfaced, to avoid repetition.

```
scan_new_analysis → semantic_cluster → entity_cross_reference → write_connection_memo
```

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
Phase 1: DB schema + artifact store service + pub/sub
Phase 2: Source registry + ingestion agents
Phase 3: Processing agents
Phase 4: Beat agents (LangGraph, checkpointed)
Phase 5: Editor agents + editorial API
Phase 6: Connection agent + assignment system
```

Each phase produces a testable vertical slice. After Phase 3 you can run ingestion → processing on real sources. After Phase 4 you have analysis. After Phase 5 you have a complete pipeline from source to human review.

---

## Key decisions to make before writing code

1. **Embedding model**: OpenAI `text-embedding-3-small` (1536-dim) is the pragmatic default. Dimension is baked into the schema (`vector(1536)`) and the ivfflat index — changing it later requires rebuilding the column. Decide before running the first migration.

2. **LangGraph deployment**: LangGraph Cloud vs. self-hosted `langgraph-cli`. Cloud is easier to start; self-hosted avoids ongoing vendor dependency for a long-running production system.

3. **Notification fan-out**: A single `artifact_written` channel works for small agent counts. If you end up with many beat agents, consider per-beat channels (`artifact_written:government:city_council:us:il:springfield:springfield`) to avoid agents waking up for irrelevant events. Easy to change early, harder to change once agents are deployed.

**Decided** (see `AGENT_DESIGN_PATTERNS.md` for rationale):
- Agent framework split: LangGraph Graph API for Beat/Research/Connection; DeepAgents for Editor/Discovery/Research search/Source examination; Scrapy for ingestion; plain functions for Processing.
- All LLM calls use `llm.with_structured_output(PydanticModel)` — no free-form string parsing.

---

## Decision log

Record significant design changes here. Keep the doc body current; use this log to explain why it changed.

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-18 | Split agent framework: LangGraph for Beat/Research/Connection; DeepAgents for Editor/Discovery/Research search/Source examination; plain functions for Processing | Match framework to control-flow ownership — fixed topology → LangGraph; open-ended planning → DeepAgents; stateless transform → no framework |
| 2026-03-18 | All LLM calls require `with_structured_output(PydanticModel)` | Type safety and explicit contracts; free-form string parsing is fragile at scale |
| 2026-03-18 | Replaced fetch strategy vocabulary with playbook model; split ingestion into Source Examination Agent + Ingestion Worker | Fixed strategy types can't express real-world source complexity without growing into a DSL |
| 2026-03-18 | Added `agent_configs` table and `AgentConfigRegistry` to Phase 1 | Model and prompt configuration must exist before any agent runs; belongs in the data layer alongside the other registries |
| 2026-03-19 | Replaced agentic ingestion worker (DeepAgents + playbook) with Scrapy spiders | Eliminates LLM cost and non-determinism at every crawl. Examination agent now generates a committed spider file instead of a DB playbook. Ingestion becomes deterministic code: cheaper, faster, easier to debug, and testable without mocking LLM calls |
| 2026-03-20 | Removed `playbook` column from `sources` table (schema and doc references) | Column was never populated after the Scrapy migration — the spider file is the authoritative fetch description. Keeping a null column in the schema was misleading |
| 2026-03-20 | Phase 3: `services/processing/`, acquisition via `complete_acquisition`, processors only on `raw`+`active`; add `document-text` | Aligns processing with two-phase raw stubs; separates byte capture from STT/PDF text extraction; Step-Functions-friendly dispatch |
| 2026-03-20 | Phase 3 now includes `summary` + `entity-extract` enrichment as required deliverables before Phase 4 | Beat agents' primary input must be enriched artifacts, not raw text. Enrichment is stateless per-document work (belongs in processing); beat agents' job is longitudinal synthesis. A single enrichment pass also serves multiple downstream agents independently. Phase 4 cannot start until Phase 3 enrichment is complete. |
| 2026-03-21 | Phase 3 complete: `structured-data` extractor deferred | `summary` + `entity-extract` are the hard prerequisites for Phase 4 beat agents. `structured-data` is conditional on content_type (budget/agenda) and adds scope; deferred until the enrichment pattern is proven and beat agents are consuming the required artifacts. |
