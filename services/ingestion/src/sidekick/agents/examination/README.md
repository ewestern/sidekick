# Source Examination Agent

**Role**: Browse a source endpoint, understand its structure, and write a Scrapy spider that will fetch from it on every scheduled run.

**Agent ID**: `source-examination` (developer-only tool — not in `agent_configs`; model and prompt configured inline in `examination.py`)

## Framework

LangChain `create_agent` (ReAct loop). Examination is open-ended: the number of pages the agent must browse before it understands the source is unknown at design time.

## Tools

| Tool | Purpose |
|------|---------|
| `fetch_url` | GET a URL. Returns JSON: `status_code`, `final_url`, `content_type`, `body_encoding`, `body` (HTML stripped of scripts/styles/comments), `truncated`, `error`, `candidate_asset_urls`. Binary responses return an empty body with the content_type. |
| `write_spider` | Write a generated `SidekickSpider` subclass to `services/ingestion/src/sidekick/spiders/`. Validates syntax (AST parse), checks `SidekickSpider` inheritance, confirms required class attributes (`name`, `source_id`, `endpoint`, `beat`, `geo`), and enforces that detail-page spiders have `parse_*` callbacks. Returns `{"ok": bool, "path": ...}` or `{"ok": bool, "error": ...}`. |

## Entrypoint

```
sidekick examine --url URL --beat BEAT --geo GEO [--name NAME]
```

Developer-triggered only. Runs once per source; not scheduled.

## Non-obvious behavior

- Writes a `.py` file to the spiders package — does **not** write to the database. DB registration happens separately via `sidekick spiders sync` after developer review.
- `write_spider` enforces that the filename is a simple `.py` basename not starting with `_`.
- `write_spider` requires at least one `parse_*` callback if the spider follows detail pages — enforced to ensure `format_id` can be set correctly per content type.
- If the source requires auth or JS rendering that can't be automated, the agent writes a minimal spider whose `parse` yields nothing and includes a docstring explaining why.
- The system prompt (`CODEGEN_SYSTEM` in `examination.py`) embeds the `FORMAT_REGISTRY` table so the agent can set `format_id` correctly on every `RawItem`.
