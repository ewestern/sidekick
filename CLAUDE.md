# Sidekick Pipeline

An agentic newsroom pipeline that ingests public data, analyzes it with specialized agents, and surfaces story drafts for human editorial review.

## Current status

- STATUS.md — current phase, what's been built, and deviations from design docs

## Design documentation

Design docs live in `docs/`. They are the source of truth for architecture decisions — read the relevant one before touching code. Each doc has a **Status**, **Scope**, and **Decision log**.

- docs/AGENTS.md — agent roles, capabilities, topology, and memory patterns
- docs/ARTIFACT_STORE.md — artifact schema, stage/content-type vocabulary, lineage, querying
- docs/SOURCE_STRATEGIES.md — source registry schema, fetch strategies, trust model
- docs/ASSIGNMENTS.md — assignment types, execution flow, sub-assignment rules
- docs/IMPLEMENTATION_PLAN.md — stack decisions and build phases
- docs/AGENT_DESIGN_PATTERNS.md — framework selection, state design, memory architecture, structured output, error handling
- docs/AGENT_CONFIG.md — agent configuration (model + prompt management), AgentConfigRegistry, seeding
- docs/SIDEKICK_CMS.md — editorial CMS + public reader app (`sidekick-cms/`)

## Repo structure

uv workspace. Each service is independently deployable with its own `pyproject.toml` and `Dockerfile`. All Python code lives under the `sidekick` namespace package.

```
sidekick/
├── migrations/
├── packages/
│   └── core/                   # shared infrastructure — touch carefully
│       └── src/sidekick/
│           ├── core/           # models, artifact_store, object_store, agent_config
│           └── registry/       # SourceRegistry (used by ingestion + api)
├── services/
│   ├── ingestion/              # Scrapy spiders + ingestion CLI
│   ├── processing/             # acquisition, PDF text, LLM enrichment (Phase 3)
│   ├── transcription/          # WhisperX STT → document-text (Phase 3)
│   ├── analysis/               # beat, research, connection agents (Phase 4)
│   ├── api/                    # FastAPI editorial interface (Phase 5)
│   └── ui/                     # frontend (future)
├── sidekick-cms/               # Next.js CMS + public reader (Drizzle, better-auth)
└── pyproject.toml              # workspace root: [tool.uv.workspace] only
```

**Key rules:**
- `packages/core/` is imported by everything. Add to it sparingly; changes here have wide blast radius.
- Agents communicate through the artifact store only — never import one agent module from another.
- `models.py` is the single schema definition. Never write raw `CREATE TABLE` SQL; define tables in SQLModel and let Alembic generate migrations.
- Each service declares `sidekick-core` as a workspace dependency. See `services/ingestion/pyproject.toml` as the reference.
- Always inject `ArtifactStore` and `ObjectStore` as dependencies instead of instantiating them inside agent code.

## Code conventions

- Python 3.12+; type hints required on all public functions and methods
- Google-style docstrings on public interfaces; skip for internal helpers
- `black` formatting, `isort` import order
- Prefer `Protocol` over `ABC` for interfaces (`core/object_store.py` is the reference)
- No raw SQL except in `artifact_store.py`; use SQLModel/SQLAlchemy elsewhere
- All LLM calls must use `llm.with_structured_output(PydanticModel)` — never parse free-form strings; see `docs/AGENT_DESIGN_PATTERNS.md`

## Documentation conventions

- **Keep docs current**: whenever you change how something works — agent behavior, ingestion model, CLI commands, data flow — update the relevant design doc in the same pass. Never leave a doc describing the old approach.
- **New design doc**: place in `docs/`, add Status/Scope/Last-updated metadata block and a Decision log table, add entry here.
- **Design change**: update the doc body, add a Decision log row, update Last-updated.
- **New agent**: add entry to `AGENTS.md`; add `README.md` in the agent subdirectory using `docs/templates/AGENT_README_TEMPLATE.md`.
- **Schema change**: update `core/models.py`, run `alembic revision --autogenerate`, review before committing.
- **New content type or fetch strategy**: update the controlled vocabulary in `ARTIFACT_STORE.md` or `SOURCE_STRATEGIES.md` — these are deliberate additions, not casual ones.
