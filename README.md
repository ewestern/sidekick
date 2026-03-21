# Sidekick Pipeline

An agentic newsroom pipeline that ingests public government data, analyzes it with specialized agents, and surfaces story drafts for human editorial review.

## Environment setup

```bash
docker compose up -d          # start Postgres + MinIO
uv sync                       # install dependencies
alembic upgrade head          # run migrations
```

After migrations, seed agent configs (required before running examination/ingestion):

```bash
uv run --directory services/ingestion sidekick seed-configs
```

## Required environment variables

See `.env.example`. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `AWS_ENDPOINT_URL` | Set to `http://localhost:9000` locally (MinIO); unset in production |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | MinIO credentials locally |
| `S3_BUCKET` | Artifact storage bucket name |
| `OPENAI_API_KEY` | Embeddings + LLM (default seed model: `openai:gpt-4o`) |

## Common commands

```bash
# Ingestion CLI (needs DATABASE_URL, S3_BUCKET, AWS_*, OPENAI_API_KEY)
uv run --directory services/ingestion sidekick examine --url URL --beat BEAT --geo GEO
uv run --directory services/ingestion sidekick sources list
uv run --directory services/ingestion sidekick ingest run SOURCE_ID
uv run --directory services/ingestion sidekick ingest due

# Tests
pytest packages/core/tests/unit/
pytest services/ingestion/tests/unit/
pytest tests/integration/     # requires docker compose up

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```
