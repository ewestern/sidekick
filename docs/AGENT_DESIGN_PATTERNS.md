# Agent Design Patterns

> **Status**: stable
> **Scope**: Framework selection, state design, memory architecture, modularity, error handling, and LLM conventions — authoritative for how agents in this pipeline are implemented
> **Last updated**: 2026-03-23 (enrichment processors reclassified as DeepAgents)

---

## Agent architecture selection

Two implementation patterns are used in this pipeline:

| Pattern | When to use |
|---|---|
| **DeepAgents** | Any agent that makes decisions, uses tools, or manages multi-step workflows |
| **Plain functions** | Stateless, deterministic transforms with no decision-making |

All agent roles use DeepAgents. The distinction between "known topology" and "open-ended" is not the right split — beat agents deciding whether to write a brief, flag an item, or query prior entity history are making real decisions, not executing predetermined steps. `write_brief` and `flag_item` are tools the agent calls when warranted, alongside artifact retrieval, entity lookup, and others. DeepAgents provides built-in tools, context summarization, `interrupt_on` for human-in-the-loop gating, `CompositeBackend` for separating per-run scratch from durable cross-run state, and subagent delegation for context isolation.

Plain functions are appropriate only for **normalization processors** — genuinely stateless transforms (PDF → text, audio → transcript) with no decision-making or tool use. **Enrichment processors** (summary, entity-extract) **are DeepAgents** — they use the skills system for domain-informed extraction and produce structured output via `response_format=ToolStrategy(PydanticModel)`.

---

## LLM calls: structured output required

**All LLM calls in this pipeline must use LangChain's structured output interface.** No free-form string parsing.

```python
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

class BriefOutput(BaseModel):
    summary: str
    key_developments: list[str]
    entities_mentioned: list[str]
    flag_for_editor: bool
    flag_reason: str | None = None

llm = ChatAnthropic(model="claude-sonnet-4-6")
structured_llm = llm.with_structured_output(BriefOutput)

result: BriefOutput = structured_llm.invoke(prompt)
```

This applies everywhere: beat briefs, entity extraction, query param extraction in assignments, source proposals from discovery agents, editorial decisions. Define a Pydantic model for every LLM output. Never parse LLM output with string splitting or regex.

**Why**: structured output gives you type-safe results, Pydantic validation, and consistent error surfaces. It also makes every LLM call's contract explicit and testable.

---

## Agent configuration

Every agent that makes LLM calls requires a config row in `agent_configs` before it can be invoked. See `docs/AGENT_CONFIG.md` for full details.

**Rule**: agent factory functions accept `config_registry: AgentConfigRegistry` as a dependency. Call `resolve()` at the start of each run — never hardcode model names or prompt text in agent code.

```python
def create_beat_agent(
    beat: str,
    geo: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
) -> Agent:
    agent_id = f"beat-agent:{beat}:{geo}"
    config = config_registry.resolve(agent_id)
    return create_deep_agent(
        tools=[write_brief_tool, flag_item_tool, query_artifacts_tool, ...],
        system_prompt=config.prompts["system"],
        model=config.model,
        backend=make_backend(agent_id),
    )
```

---

## Durable state design

Store raw structured data in durable state, not formatted text. Format inside tool calls on-demand.

```python
# Good — raw structured data persisted under /memories/
{
    "open_threads": [
        {"id": "t1", "title": "...", "artifact_ids": [...], "last_seen": "2026-03-20"}
    ],
    "known_entity_aliases": {"Jane Smith": ["J. Smith", "Councilwoman Smith"]},
    "seen_artifact_ids": ["art_a1b2c3", "art_x9y8z7"],
}

# Bad — pre-formatted prompt text; you've discarded the raw data
{
    "context_prompt": "As of last week, Jane Smith proposed a zoning ordinance..."
}
```

Durable state fields should be the **minimum needed to reconstruct context** across runs. Heavy content (transcripts, full documents) lives in the artifact store; durable state holds IDs and metadata only.

---

## Context isolation

Context growth is an architectural concern, not just a prompt-tuning problem.

### Rules

- Do not let large intermediate payloads accumulate across unrelated steps in the same conversation or agent run.
- Keep heavy page/document bodies local to the stage that needs them; return structured results, not raw source material.
- When a workflow fans out over many similar items, isolate each item's heavy processing so item A does not carry item B's context.
- Use typed contracts between stages. Good boundaries return fields like `urls`, `title`, `entities`, `requires_followup`; bad boundaries return full HTML, whole documents, or free-form summaries that must be reparsed.
- If a stage only needs a reduced representation of a source, build a helper that returns that reduced representation instead of relying on the model to ignore irrelevant content.

### Heuristic

If you find yourself saying "this stage only needs one page / one record / one artifact, not the whole run history," that stage probably needs explicit context isolation — use a subagent.

---

## Code vs tool calls

Keep deterministic work in code, not agent tool calls.

- **Plain code** owns: routing, deduplication, storage writes, retries, health updates, schema validation.
- **Tool calls** are for: decisions requiring model judgment, actions where the right choice isn't known in advance, multi-step sub-tasks worth delegating.

If a step would produce the same result regardless of artifact content, it belongs in deterministic code. Tool calls are for when the agent must evaluate content and decide.

---

## Memory architecture

Use a three-layer model. This is the canonical rule set for all services.

### Layer 1: artifact knowledge (system source of truth)

The artifact store is the durable knowledge substrate. Anything that should be searchable, auditable, shared between agents, or reused across threads belongs in artifacts.

- Examples: summaries, extracted entities, policy diffs, drafts, and the lineage graph linking them.
- Implication: beat/research/context knowledge should be reconstructed from artifact reads plus targeted retrieval, not copied into large long-term agent state.

### Layer 2: per-run working state (ephemeral)

Each agent invocation has ephemeral scratch state via the DeepAgents `StateBackend`. This holds in-progress reasoning context for that run and is discarded afterward. It is not a persistence mechanism.

### Layer 3: durable agent state (minimal cross-run memory)

Use durable memory stores only for compact state that improves control flow and reduces repeated work but is not itself the newsroom knowledge base.

- Good durable state: open investigation threads, alias maps, suppression/de-dup markers, reminders, cursor/bookmark positions.
- Bad durable state: large narrative history, full entity registries, or raw content copies that should be artifacts.

Use a `CompositeBackend` that keeps scratch ephemeral and durable memory explicitly namespaced:

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

def make_backend(agent_id: str, runtime) -> CompositeBackend:
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={"/memories/": StoreBackend(runtime, namespace=agent_id)},
    )
```

Use `InMemoryStore` locally; `PostgresStore` in production.

### Backend matrix by agent role

| Agent role | Per-run scratch | Durable state backend | Primary retrieval backend | Primary writes |
|---|---|---|---|---|
| Normalization (PDF text, STT) | N/A (plain functions) | None | ArtifactStore read by ID | `processed` artifacts (`document-text`) |
| Enrichment (summary, entity-extract) | N/A (ephemeral DeepAgent — `StoreBackend` + `InMemoryStore` for skills) | None | ArtifactStore read by ID | `processed` artifacts (`summary`, `entity-extract`) |
| Beat / Research | DeepAgents `StateBackend` (ephemeral) | `StoreBackend` under `/memories/` (minimal state) | ArtifactStore structured + semantic + lineage queries | `analysis` artifacts |
| Connection | DeepAgents `StateBackend` (ephemeral) | `StoreBackend` under `/memories/` (minimal cross-run state) | ArtifactStore semantic + entity cross-reference queries | `connections` artifacts |
| Editor | DeepAgents `StateBackend` (ephemeral) | Optional `StoreBackend` under `/memories/` for lightweight editorial memory | ArtifactStore + lineage traversal | `draft` artifacts |
| Discovery search | DeepAgents `StateBackend` (ephemeral) | `StoreBackend` under `/memories/` for explored-domain memory | Source registry + external web + ArtifactStore signals | Source proposals |
| Research search | DeepAgents `StateBackend` (ephemeral) | None (stateless by default) | External web + assignment/request context | `raw` artifacts |

### Decision boundary: artifact vs durable state

When deciding where data lives:

1. If another agent may need it, it must be queryable, or humans must audit it later → write an artifact.
2. If it only improves one agent's control flow across runs → keep it in minimal durable state.
3. If it is only needed for the current invocation → per-run scratch (discarded after run).

---

## Modularity: subagents

Use subagents for context isolation and delegation. The main agent spawns an ephemeral subagent, gets a concise result, and discards the intermediate work.

**Critical rule**: subagent responses must be concise — return summaries, not raw data. Keep responses under ~400 words.

```python
subagents = [
    {
        "name": "document_fetcher",
        "description": "Fetches and extracts clean text from a specific URL or document.",
        "system_prompt": (
            "Retrieve the document at the given URL. Return a plain-text summary "
            "under 400 words covering the key facts. Do not include raw HTML."
        ),
        "tools": [fetch_tool, extract_tool],
        # model omitted: inherits from parent
    }
]
agent = create_deep_agent(tools=[...], subagents=subagents)
```

Keep subagent tool lists minimal. A subagent that does one thing is better than one that does many. Write specific `description` fields — the parent agent uses them to decide when to delegate.

---

## Error handling

Four categories requiring different handling:

| Error type | Example in this pipeline | How to handle |
|---|---|---|
| **Transient** | Network timeout fetching a source | Retry policy in the tool implementation |
| **LLM-recoverable** | Structured output validation fails | Surface error in tool result; agent self-corrects on next step |
| **User-fixable** | Editor approval required before publishing | `interrupt_on` — gate the tool call pending human input |
| **Unexpected** | Database connection lost mid-write | Bubble up — do not mask |

### `interrupt_on` for human-in-the-loop

Use `interrupt_on` to gate high-stakes tool calls. The agent pauses before executing the named tool and resumes when the human approves or modifies the call.

```python
agent = create_deep_agent(
    tools=[...],
    interrupt_on=["publish_story", "activate_source", "create_story_assignment"],
)
```

---

## Human-in-the-loop placement

Use `interrupt_on` at these specific points:

| Point | Gated tool | Condition |
|---|---|---|
| Editor agent draft publication | `publish_story` | Always — human approves before publish |
| Discovery agent source proposal | `activate_source` | Always — no agent-proposed source auto-activates |
| Connection agent story assignment creation | `create_story_assignment` | Always — per ASSIGNMENTS.md human gate rule |
| Research search agent artifact write | `write_artifact` | When source trust level is below threshold |

---

## Agent interface contract

Each agent module exposes a factory function. No agent imports from another agent module — the interface is: receive an event, read from the artifact store, write to the artifact store.

```python
def create_beat_agent(
    beat: str,
    geo: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
) -> Agent:
    """Factory. Inject dependencies; return a configured DeepAgent."""
    agent_id = f"beat-agent:{beat}:{geo}"
    config = config_registry.resolve(agent_id)
    return create_deep_agent(
        tools=[write_brief_tool, flag_item_tool, query_artifacts_tool, ...],
        system_prompt=config.prompts["system"],
        model=config.model,
        backend=make_backend(agent_id),
        interrupt_on=[],
    )
```

Dependencies (`ArtifactStore`, `ObjectStore`) are always injected — never instantiated inside agent code. This keeps agents testable and environment-agnostic.

---

## Shared agent tools

HTTP and other **agent-agnostic** helpers live in `services/ingestion/src/sidekick/agents/tools/` (for example shared fetch helpers and structured response types). **Not** in `packages/core` — core stays the data layer. If another deployable service needs the same helpers later, extract a small shared package.

### A helper is a good candidate for sharing when:

- its behavior is defined by data shape, transport, or format handling rather than one agent's workflow
- another future agent could use it without knowing the current caller's orchestration
- it returns a stable typed contract
- it does not encode agent-specific sequencing or policy decisions

### A helper is not a good candidate for sharing when:

- it only exists to support one prompt or one graph edge
- it bakes in current-agent assumptions like "this is the listing stage" or "this is the final write step"
- its output is only meaningful inside one agent's orchestration contract

Per-agent READMEs should document how a specific agent composes shared helpers, but this document should stay at the pattern level.

---

## Summary: pattern → implementation

| Pattern | Framework | Durable state |
|---|---|---|
| Normalization (PDF → text, audio → transcript) | Plain functions | None |
| Enrichment (summary, entity-extract) | DeepAgents (ephemeral — `StoreBackend` + `InMemoryStore` for skills) | None |
| All other agent roles (decisions, tool use, multi-step) | DeepAgents | `StoreBackend` under `/memories/` where cross-run state is needed |

---

## Decision log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-18 | Initial document | Synthesized from LangGraph and DeepAgents docs to establish patterns before Phase 2 implementation begins |
| 2026-03-18 | Structured output required for all LLM calls | Type safety, Pydantic validation, and explicit contracts; free-form string parsing is fragile |
| 2026-03-18 | Framework selection aligned to control-flow ownership | Open-ended planning belongs in agent loops; known topology belongs in explicit graphs; pure transforms stay plain functions |
| 2026-03-18 | AgentConfig system added — DB-only, no code-level defaults | Explicit configuration makes the active model and prompts unambiguous. Code defaults create silent fallback risk and discourage proper seeding. Raises KeyError if row not found |
| 2026-03-19 | Added context-isolation and orchestration-boundary guidance | Large intermediate payloads should stay local to the stage that needs them; explicit DAGs are preferable when the workflow shape is already known |
| 2026-03-19 | Clarified criteria for shared agent tools | Shared helpers should be reusable without knowledge of a particular agent's current orchestration |
| 2026-03-19 | Distinguished graph agent nodes from plain LLM call nodes | Agent nodes can recurse and reflect; plain LLM nodes are only appropriate for bounded single-step inference |
| 2026-03-22 | Reframed memory as artifact-first with explicit three-layer model + backend matrix | Removes checkpoint-vs-memory ambiguity and sets a buildable contract for what belongs in artifacts, checkpoints, and durable agent state |
| 2026-03-23 | Standardized on DeepAgents for all agent roles; removed LangGraph Graph API as a pattern | Beat/research/connection agents make real decisions (`write_brief`, `flag_item`, entity lookups) — these are tool calls made when warranted, not predetermined graph nodes. DeepAgents provides built-in tools, context management, `interrupt_on`, and `CompositeBackend` covering all agent needs without artificial topology constraints |
| 2026-03-23 | Reclassified enrichment processors (summary, entity-extract) as DeepAgents with skills | Enrichment is domain-informed extraction that benefits from journalistic skill files (news-values, entity-and-actor-tracking, etc.). Plain functions cannot use the skills system. Processors are ephemeral — `StoreBackend` + `InMemoryStore` provides skills access without any durable state |
