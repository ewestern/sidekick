# Pipeline Status

**Current phase**: Phase 5 in progress — API layer complete; editor agent and draft review routes pending
**Last updated**: 2026-03-29

---

## What exists

- Design docs (`AGENTS.md`, `ARTIFACT_STORE.md`, `SOURCE_STRATEGIES.md`, `ASSIGNMENTS.md`, `IMPLEMENTATION_PLAN.md`)
- **Phase 1 implementation** — data layer
- **Phase 2 implementation** — source registry, Scrapy spider harness, `sidekick` CLI
- **Phase 3 implementation** — full processing chain: HLS acquisition, PDF text extraction, STT (`services/transcription`), LLM-based summarization and entity extraction (`services/processing`)
- **Phase 4 implementation** — beat agents (`services/beat/`), analysis scope coordination (Lambda handlers in `packages/lambda-handlers/`), `analysis_scopes` migration, Step Functions analysis workflow
- **Phase 5 partial** — FastAPI service (`services/api/`), Cognito + API key authentication, all resource CRUD routes, Terraform modules for API + Cognito, generated Python client (`packages/api-client/`)

### Phase 1 files

```
docker-compose.yml                          # Postgres 16 + pgvector, MinIO
pyproject.toml                              # uv workspace root
alembic.ini
migrations/
    env.py
    versions/001_initial_schema.py
    versions/002_agent_configs.py
packages/core/
    pyproject.toml                          # sidekick-core
    src/sidekick/core/   — models, artifact_store, object_store, agent_config
    src/sidekick/registry/registry.py
    tests/unit/
```

### Phase 2 files

```
services/ingestion/
    pyproject.toml          # deepagents, scrapy, typer; script: sidekick
    src/sidekick/
        agents/tools/http.py      — shared fetch_url / FetchResult (used by fetch-url CLI)
        agents/utils.py           — RunStats, UsageLoggingCallback
        spiders/__init__.py       — package (harness = _prefixed, spiders = non-prefixed)
        spiders/_base.py          — SidekickSpider, RawItem, SpiderMeta
        spiders/_pipeline.py      — ArtifactWriterPipeline
        spiders/_middleware.py    — DeduplicationMiddleware
        spiders/_runner.py        — run_spider() / run_spiders()
        spiders/_discovery.py     — discover_spiders()
        seed_configs.py           — agent_configs seed hook (placeholder)
        runtime.py                — DB + ArtifactStore wiring from env
        cli.py                    — seed-configs, fetch-url, spiders scaffold/list/list-due/sync/run/due/test
    tests/unit/test_ingestion.py, test_fetch_url.py
scripts/seed_agent_configs.py   — delegates to ingestion seed module
```

### Phase 3 files

```
services/processing/
    pyproject.toml              # sidekick-processing; script: sidekick-process; langchain-anthropic dep
    Dockerfile
    README.md
    src/sidekick/processing/
        runtime.py              # DB + ArtifactStore + ObjectStore + AgentConfigRegistry
        router.py               # raw→pdf_text/transcript; processed→summary/entity_extract routing
        cli.py                  # acquire, process (PDF only), summary, entity-extract, seed-configs
        seed_configs.py         # processor:summary + processor:entity-extract agent config rows
        acquisition/hls.py      # ffmpeg → complete_acquisition
        processors/schemas.py   # SummaryOutput, EntityExtractionOutput Pydantic models
        processors/pdf.py       # document-text
        processors/summary.py   # summary (LLM via ChatAnthropic)
        processors/entity_extract.py  # entity-extract (LLM via ChatAnthropic)
    tests/unit/
services/transcription/
    pyproject.toml              # sidekick-transcription; script: sidekick-transcribe; whisperx/torch
    Dockerfile                  # GPU / CUDA image for Batch
    src/sidekick/transcription/ # processor, router, runtime, cli
    tests/unit/
```

### Phase 4 files

```
services/beat/
    pyproject.toml              # sidekick-beat; script: sidekick-beat
    Dockerfile
    src/sidekick/beat/
        agent.py                # run_beat_agent() — DeepAgents entry point
        cli.py                  # sidekick-beat brief (--event-group or --since/--until), seed-configs
        tools.py                # query_artifacts, write_beat_brief, flag_item, create_research_assignment
        scope.py                # BeatScope, EventGroupScope, DateWindowScope
        seed_configs.py         # beat-agent:government config row
        runtime.py              # DB + ArtifactStore + AgentConfigRegistry + AssignmentStore
        utils.py                # build_skill_store helper
    tests/unit/
packages/lambda-handlers/
    src/sidekick_lambda/
        analysis_scope.py       # scope coordination logic (upsert/claim/record/check/release)
        handlers/               # one Lambda handler per scope operation
migrations/src/migrations/versions/
    005_analysis_scopes.py      # analysis_scopes table
infrastructure/modules/newsroom/
    step_functions.tf           # analysis SFN: EventBridge→debounce→claim→RunBeatAgent→record→check→release
    lambda.tf                   # analysis scope Lambdas (5 handlers)
```

### Phase 5 files (partial)

```
services/api/
    pyproject.toml              # sidekick-api; script: uvicorn; fastapi, python-jose, PyJWT
    Dockerfile
    src/sidekick/api/
        main.py                 # FastAPI app, CORS, lifespan (runs migrations on startup)
        auth.py                 # Cognito JWT + X-API-Key auth; CallerType, AuthContext, require_roles()
        db.py                   # SQLModel session dependency
        settings.py             # settings (database_url, jwks_url, cognito_audience, cors, etc.)
        schemas.py              # request/response schemas (SourceCreate/Patch, ArtifactPatch, etc.)
        routers/
            sources.py          # CRUD for sources
            artifacts.py        # list/get/patch/retract artifacts
            assignments.py      # CRUD for assignments
            agent_configs.py    # CRUD for agent configs
            api_clients.py      # create/list/rotate/revoke API keys
        cli.py                  # sidekick-api CLI (start server)
    tests/unit/
packages/api-client/
    src/sidekick_client/        # generated typed Python client (from OpenAPI schema)
        api/                    # per-resource endpoint modules
        models/                 # Pydantic response models
migrations/src/migrations/versions/
    003_api_clients.py          # api_clients table
    004_artifact_processing_profile.py
infrastructure/modules/
    api/                        # ECS Fargate service + ALB for the API
    cognito/                    # Cognito user pool + app client
```

**Unit tests:** run from each package: `uv run pytest tests/unit/`. (Counts vary as tests are added.)

**Ingestion orchestration (AWS):** `sidekick spiders list-due` uses `sidekick.core.due_sources` (registry DB only). The ingestion Step Functions `ListDueSpiders` state invokes a **Lambda** built from `packages/lambda-handlers` as a **container image** (`just push lambda-list-due` → ECR; Terraform uses `aws_ecr_image` + `image_uri` digest; see `packages/lambda-handlers/Dockerfile`).

---

## Ingestion model

**Spider authoring** (one-time per source): `sidekick spiders scaffold …`, then implement `parse()` / callbacks; commit the spider file.
→ `sidekick spiders sync` upserts the Source row in DB (sets `examination_status=active`).

**Ingestion** (scheduled): `sidekick spiders due` or `sidekick spiders run SOURCE_ID`
→ Runs deterministic Scrapy spider — no LLM at crawl time.
→ `DeduplicationMiddleware` drops already-ingested URLs.
→ `ArtifactWriterPipeline` writes raw artifacts.
→ Health fields updated in source registry after each run.

---

## Phase checklist

- [x] **Phase 1** — Data layer
- [x] **Phase 2** — Registry + Scrapy ingestion (local CLI)
- [x] **Phase 3** — Processing agents (HLS acquisition + PDF text + STT + summary + entity-extract)
- [x] **Phase 4** — Beat agents (DeepAgents + Step Functions analysis workflow)
- [ ] **Phase 5** — Editor agent + draft review routes (API layer done; editor agent pending)
- [ ] **Phase 6** — Connection + assignments

---

## Deviations from design docs

- **Single `S3ObjectStore` class** — same as before (`AWS_ENDPOINT_URL` for MinIO).

---

## Open decisions
