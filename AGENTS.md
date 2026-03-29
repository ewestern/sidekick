# Repository Guidelines

## Project Structure & Module Organization
`packages/` holds shared Python code: `core` for models and storage logic, `api-client` for generated client bindings, and `lambda-handlers` for AWS Lambda entrypoints. `services/` contains deployable apps (`api`, `ingestion`, `processing`, `transcription`, `beat`), each with `src/` and `tests/`. Frontend apps live in `admin/`, `landing/`, and `sidekick-cms/` (Next.js editorial + public reader site). Infrastructure code is under `infrastructure/`, migrations under `migrations/`, and architecture notes in `docs/`.

## Build, Test, and Development Commands
Use `uv sync` to install the Python workspace and `docker compose up -d` to start local Postgres and MinIO. Apply schema changes with `alembic upgrade head`. Common service commands:

- `uv run --directory services/ingestion sidekick spiders list`
- `pytest packages/core/tests/unit/`
- `pytest services/ingestion/tests/unit/`
- `pytest tests/integration/`
- `just build api` or `just build ingestion`
- `cd admin && npm run dev`
- `cd admin && npm run build`
- `cd sidekick-cms && npm install && npm run dev`
- `cd sidekick-cms && npm run build` (after `npm run db:migrate`; see `sidekick-cms/README.md`)

Use `just --list` to see deployment and Terraform recipes.

## Coding Style & Naming Conventions
Python uses 4-space indentation, `black` with a 100-character line length, and `isort` with the Black profile. Prefer typed functions, `snake_case` module names, and `test_*.py` filenames. Keep SQLModel definitions in `packages/core/src/sidekick/core/models.py`; do not hand-write schema SQL. Type-check Python with `pyright`.

Frontend code in `admin/` uses TypeScript, React, and ESLint. Prefer `PascalCase` for components and `camelCase` for hooks and helpers.

## Testing Guidelines
`pytest` is configured per package/service with `tests/` as the default test root and `asyncio_mode = "auto"` where needed. Add unit tests next to the package or service you change, and add integration coverage when storage, database, or pipeline boundaries change. Run the narrowest relevant suite before opening a PR, then widen to cross-service tests for shared model changes.

## Commit & Pull Request Guidelines
Recent history uses short subject lines such as `lint` and `prepare batch job`. Keep commit titles brief, imperative, and specific; avoid `wip` for reviewable work. PRs should explain the behavioral change, list validation steps, link the relevant issue or task, and include screenshots for `admin/` or `landing/` UI changes.

## Security & Configuration Tips
Start from `.env.example`; never commit secrets from `.env`. Local object storage uses MinIO via `AWS_ENDPOINT_URL=http://localhost:9000`. Regenerate API clients only against the intended local API schema and review generated diffs carefully.
