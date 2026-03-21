# Agent Configuration

> **Status**: stable
> **Scope**: Model and prompt configuration for agents — authoritative for how agent configs are stored, retrieved, and swapped at runtime
> **Last updated**: 2026-03-18

---

## Overview

Each agent requires a configuration row in the `agent_configs` table before it can be invoked. The config specifies:

- **model** — the LLM model identifier (e.g. `"claude-sonnet-4-6"`)
- **prompts** — a dict of named prompt slots (e.g. `{"system": "...", "analyze_template": "..."}`)

There are no code-level defaults. `AgentConfigRegistry.resolve()` raises `KeyError` if no row exists. This is intentional: forcing explicit configuration makes it clear which model and prompts are active and avoids silent fallback to stale defaults.

Config rows must be seeded before the pipeline runs. Use `sidekick seed-configs` (ingestion service) or `AgentConfigRegistry.set()` from code.

---

## Agent IDs

Each agent type defines a string constant for its `agent_id`. Examples:

| Agent | agent_id |
|---|---|
| Ingestion worker | `"ingestion-worker"` |
| Source examination | `"source-examination"` |
| Beat agent (city council, Springfield) | `"beat-agent:government:city_council:us:il:springfield:springfield"` |
| Editor agent | `"editor-agent"` |

Beat and research agents may use colon-delimited IDs to allow per-beat or per-geo configs. Each is an independent row — there is no cascading lookup.

---

## Prompt Slots

Prompt slot names are defined by each agent. They are not enforced by the schema — the `prompts` dict is freeform JSON. Each agent documents its expected slots in its `README.md`.

Common slot names:

| Slot | Purpose |
|---|---|
| `system` | System prompt passed to the LLM |
| `analyze_template` | Template filled with artifact content before the analyze call |
| `write_brief_template` | Template for the brief-writing step |

Slot values may contain `{placeholder}` variables substituted by the agent at invocation time using `str.format_map()`. The agent fills these immediately before calling the LLM — the stored prompt text is the template.

---

## Usage in Agent Code

Agents receive `AgentConfigRegistry` as an injected dependency. Call `resolve()` at the start of each run:

```python
# LangGraph agent — call at the top of the entry-point node
config = self._config_registry.resolve(self.AGENT_ID)
llm = ChatAnthropic(model=config.model)
prompt = config.prompts["analyze_template"].format_map({"content": artifact_content})

# DeepAgents — call inside the factory or at the start of run_source()
config = self._config_registry.resolve(self.AGENT_ID)
```

Never instantiate a model name or prompt text inline in agent code. Always read from `ResolvedAgentConfig`.

---

## Cache Behaviour

`resolve()` caches results for 60 seconds per `agent_id`. Calls to `set()` or `delete()` immediately invalidate the local cache entry, so the next `resolve()` re-fetches from the database.

In a multi-process deployment (e.g. multiple Fargate tasks running beat agents), a config change propagates within one cache TTL (60 seconds) across all processes. If faster propagation is needed, a short TTL or no cache can be configured; cache TTL is a constant in `core/agent_config.py`.

---

## Editorial API Endpoints (Phase 5)

The following endpoints will be added to the FastAPI editorial interface:

| Method | Path | Action |
|---|---|---|
| `GET` | `/agent-configs` | List all config rows with current model and prompt slot names |
| `PUT` | `/agent-configs/{agent_id}` | Create or update config (model + prompts) |
| `DELETE` | `/agent-configs/{agent_id}` | Delete config row |

---

## Schema

```python
class AgentConfig(SQLModel, table=True):
    id: str                   # primary key (ulid-prefixed)
    agent_id: str             # unique — logical agent name
    model: str                # LLM model identifier
    prompts: dict[str, str]   # slot_name -> prompt text
    updated_at: datetime
    updated_by: str | None    # user ID for audit trail
```

---

## Decision log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-18 | Initial document — no code-level defaults, DB row required | Explicit configuration makes the active model and prompts unambiguous. Code defaults create silent fallback risk and discourage proper seeding |

