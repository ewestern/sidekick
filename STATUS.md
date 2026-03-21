# Pipeline Status

**Current phase**: Phase 3 complete — full processing chain through summary + entity-extract
**Last updated**: 2026-03-21

---

## What exists

- Design docs (`AGENTS.md`, `ARTIFACT_STORE.md`, `SOURCE_STRATEGIES.MD`, `ASSIGNMENTS.md`, `IMPLEMENTATION_PLAN.md`)
- **Phase 1 implementation** — data layer
- **Phase 2 implementation** — source registry, examination agent, Scrapy spider harness, `sidekick` CLI
- **Phase 3 implementation** — full processing chain: HLS acquisition, PDF text extraction, STT transcription, LLM-based summarization and entity extraction

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
    src/sidekick/core/   — models, artifact_store, event_bus, object_store, agent_config
    src/sidekick/registry/registry.py
    tests/unit/
```

### Phase 2 files

```
services/ingestion/
    pyproject.toml          # deepagents, scrapy, typer; script: sidekick
    src/sidekick/
        agents/tools/http.py      — shared fetch_url / FetchResult (used by examination agent)
        agents/utils.py           — RunStats, UsageLoggingCallback
        agents/examination/examination.py  — code-gen agent (writes Scrapy spider files)
        spiders/__init__.py       — package (harness = _prefixed, spiders = non-prefixed)
        spiders/_base.py          — SidekickSpider, RawItem, SpiderMeta
        spiders/_pipeline.py      — ArtifactWriterPipeline
        spiders/_middleware.py    — DeduplicationMiddleware
        spiders/_runner.py        — run_spider() / run_spiders()
        spiders/_discovery.py     — discover_spiders()
        seed_configs.py           — CODEGEN_SYSTEM prompt + example spiders for examination agent
        runtime.py                — DB + ArtifactStore + EventBus wiring from env
        cli.py                    — seed-configs, examine, spiders list/sync/run/due/test
    tests/unit/test_ingestion.py, test_fetch_url.py
scripts/seed_agent_configs.py   — delegates to ingestion seed module
```

### Phase 3 files

```
services/processing/
    pyproject.toml              # sidekick-processing; script: sidekick-process; langchain-anthropic dep
    README.md
    src/sidekick/processing/
        runtime.py              # DB + ArtifactStore + ObjectStore + EventBus + AgentConfigRegistry
        router.py               # raw→pdf_text/transcript; processed→summary/entity_extract routing
        cli.py                  # acquire, process, enrich, seed-configs
        seed_configs.py         # processor:summary + processor:entity-extract agent config rows
        acquisition/hls.py      # ffmpeg → complete_acquisition
        processors/schemas.py   # SummaryOutput, EntityExtractionOutput Pydantic models
        processors/pdf.py       # document-text
        processors/transcript.py  # transcript-clean (faster-whisper)
        processors/summary.py   # summary (LLM via ChatAnthropic)
        processors/entity_extract.py  # entity-extract (LLM via ChatAnthropic)
    tests/unit/                 # 28 unit tests
```

**Unit tests:** run from each package: `uv run pytest tests/unit/`. (Counts vary as tests are added.)

---

## Ingestion model

**Examination** (one-time, per source): `sidekick examine --url URL --beat BEAT --geo GEO`
→ code-gen agent browses the source and writes a Scrapy spider to `spiders/`.
→ Developer reviews and commits the spider file.
→ `sidekick spiders sync` upserts the Source row in DB (sets `examination_status=active`).

**Ingestion** (scheduled): `sidekick spiders due` or `sidekick spiders run SOURCE_ID`
→ Runs deterministic Scrapy spider — no LLM at crawl time.
→ `DeduplicationMiddleware` drops already-ingested URLs.
→ `ArtifactWriterPipeline` writes raw artifacts; fires `artifact_written` NOTIFY.
→ Health fields updated in source registry after each run.

---

## Phase checklist

- [x] **Phase 1** — Data layer
- [x] **Phase 2** — Registry + examination (code-gen) + Scrapy ingestion (local CLI)
- [x] **Phase 3** — Processing agents (HLS acquisition + PDF text + STT + summary + entity-extract)
- [ ] **Phase 4** — Beat agents
- [ ] **Phase 5** — Editor + FastAPI
- [ ] **Phase 6** — Connection + assignments

---

## Deviations from design docs

- **Single `S3ObjectStore` class** — same as before (`AWS_ENDPOINT_URL` for MinIO).

---

## Open decisions

- Per-beat NOTIFY vs single `artifact_written` channel.
