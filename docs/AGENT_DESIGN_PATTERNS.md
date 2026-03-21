# Agent Design Patterns

> **Status**: stable
> **Scope**: Framework selection, state design, memory architecture, modularity, error handling, and LLM conventions — authoritative for how agents in this pipeline are implemented
> **Last updated**: 2026-03-19

---

## Agent architecture selection

Two top-level implementation patterns matter for this pipeline:

| Pattern | When to use | Tradeoff |
|---|---|---|
| **LangGraph Graph API** | Workflow topology is known: explicit stages, bounded branching, fan-out/fan-in, resumability, typed state | More structure up front, but orchestration is explicit and testable |
| **DeepAgents** | Workflow is genuinely open-ended: unknown number of steps, unknown tool ordering, model must plan its own path | Highest flexibility, but also highest context and orchestration overhead |

### Selection rules

- Use LangGraph when the workflow can be expressed as a small DAG without inventing fake branches.
- Use DeepAgents only when encoding the control flow would be more complex than letting the model plan.
- Prefer moving deterministic routing, deduplication, storage, retries, and health updates into code even when some stages still use an LLM.
- If one part of a workflow is open-ended but the surrounding orchestration is not, keep the outer workflow explicit and isolate only that stage behind an agent node.

### Node types inside a graph

Graphs may contain multiple kinds of nodes. Be explicit about which kind you are using.

| Node type | Use when | Important property |
|---|---|---|
| **Agent node** | The node may need tool use, reflection, or recursive problem solving | Can recurse and re-plan within the node |
| **Plain LLM call node** | The task is a single bounded generation or extraction step with no need for tool selection or reflection | Cheaper and simpler, but no recursion or internal planning |
| **Deterministic code node** | Routing, normalization, deduplication, validation, persistence, counters, health updates | Should own non-LLM control flow and policy |

### Preference order inside graphs

- Prefer deterministic code nodes for work that does not require model judgment.
- Prefer agent nodes over plain LLM call nodes when the stage may need to inspect, retry, or reflect before producing a result.
- Prefer plain LLM call nodes over agent nodes when the stage is truly a single bounded inference with a clear schema and no need for tool use.
- Do not treat plain Python functions as an \"agent framework\" choice on their own. They are supporting node implementations inside a larger architecture, not usually a top-level agent pattern.

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

**Rule**: agent factory functions and constructors accept `config_registry: AgentConfigRegistry` as a dependency. Call `resolve()` at the start of each run — never hardcode model names or prompt text in agent code.

```python
# DeepAgents agent (factory pattern)
class IngestionWorker:
    AGENT_ID = "ingestion-worker"

    def __init__(self, ..., config_registry: AgentConfigRegistry) -> None:
        self._config_registry = config_registry

    def run_source(self, source_id: str) -> int:
        config = self._config_registry.resolve(self.AGENT_ID)
        llm = ChatAnthropic(model=config.model)
        # pass config.prompts["system"] to the DeepAgents invocation
        ...

# LangGraph agent (state pattern)
class BeatAgent:
    AGENT_ID = "beat-agent"

    def handle_artifact_written(self, event: dict) -> None:
        agent_id = f"{self.AGENT_ID}:{self._beat}:{self._geo}"
        config = self._config_registry.resolve(agent_id)
        self._graph.invoke({"event": event, "agent_config": config.model_dump()}, ...)
```

For LangGraph agents, pass the resolved config into graph state as `agent_config: dict` (JSON-serializable for checkpointing). Nodes reconstruct it via `ResolvedAgentConfig.model_validate(state["agent_config"])` when needed.

---

## State schema design

Store raw data in state, not formatted text. Format inside nodes on-demand.

```python
# Good — raw structured data; different nodes format it differently
class BeatAgentState(TypedDict):
    beat: str
    geo: str
    narrative: str                    # prose summary updated by analyze node
    known_entities: list[dict]        # {name, type, role, first_seen}
    developing_stories: list[dict]    # {id, title, artifact_ids, status, last_updated}
    pending_flags: list[str]          # artifact IDs — formatted into prompts inside nodes

# Bad — pre-formatted prompt text; you've discarded the raw data
class BadState(TypedDict):
    context_prompt: str
```

State fields should be the **minimum needed to reconstruct context**. Heavy content (transcripts, full documents) lives in the artifact store; state holds IDs and metadata only.

---

## Context isolation

Context growth is an architectural concern, not just a prompt-tuning problem.

### Rules

- Do not let large intermediate payloads accumulate across unrelated steps in the same conversation or graph state.
- Keep heavy page/document bodies local to the stage that needs them; return structured results, not raw source material.
- When a workflow fans out over many similar items, isolate each item's heavy processing so item A does not carry item B's context.
- Use typed contracts between stages. Good boundaries return fields like `urls`, `title`, `entities`, `requires_followup`; bad boundaries return full HTML, whole documents, or free-form summaries that must be reparsed.
- If a stage only needs a reduced representation of a source, build a helper that returns that reduced representation instead of relying on the model to ignore irrelevant content.

### Heuristic

If you find yourself saying "this stage only needs one page / one record / one artifact, not the whole run history," that stage probably needs explicit context isolation.

---

## Orchestration boundaries

Use the workflow layer to own sequencing. Do not hide important control flow inside prompts when the sequence is already known.

### Prefer explicit graphs when:

- the next stage is known from structured metadata
- there is fan-out or fan-in across repeated tasks
- some stages are deterministic and others are LLM-backed
- retries, short-circuits, or health updates must happen predictably
- you need to prove that one stage cannot see another stage's heavy inputs

### Prefer agent planning when:

- the order of operations is genuinely unknown
- the agent must discover which tools matter while working
- the number of steps is not meaningfully bounded ahead of time

### Rule of thumb

If the workflow can be drawn as a small DAG without inventing fake branches, it should usually be implemented as a graph and not as a single general-purpose agent loop.

---

## Memory architecture

Two distinct concerns requiring different solutions:

### Within-run memory (LangGraph checkpoint state)

`PostgresSaver` handles this automatically on stateful agents. Use `thread_id = f"{beat}-{geo}"` for beat and research agents so each domain pair has its own checkpoint.

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
graph = graph.compile(checkpointer=checkpointer)

# Each beat/geo pair resumes from its own checkpoint
config = {"configurable": {"thread_id": "government:city_council:us:il:springfield:springfield"}}
graph.invoke(event, config=config)
```

### Cross-thread / long-term memory

For information that must survive restarts or be shared across invocations:

- **LangGraph Store** (Beat, Research, Connection agents): structured key-value store queryable by namespace. Good for entity registries and historical baselines.
- **DeepAgents `CompositeBackend`** (Discovery, Editor agents): routes `/memories/` paths to `StoreBackend` for persistence; everything else to ephemeral `StateBackend`.

```python
# DeepAgents long-term memory
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={"/memories/": StoreBackend(runtime)},
    )

agent = create_deep_agent(backend=make_backend, store=PostgresStore(DATABASE_URL))
```

Use `InMemoryStore` locally; `PostgresStore` in production.

### Checkpointer configuration by context

| Context | Setting | Reason |
|---|---|---|
| Stateful agents (Beat, Research, Connection) | `PostgresSaver` | Thread-level persistence across restarts |
| Subgraphs within a stateful graph | `None` (default, per-invocation) | Independent calls; most multi-agent applications |
| Processing agents | No checkpointer | Plain functions; LangGraph not used |
| Editor / search agents (DeepAgents) | Managed by DeepAgents | Per-run ephemeral; no cross-run state |

---

## Modularity

### LangGraph subgraphs

Use when a cluster of nodes is shared across multiple graphs, or when a team owns a sub-workflow independently.

Two wiring patterns depending on state overlap:

```python
# Different state schemas — wrap in a node function to transform at the boundary
def run_analysis_subgraph(state: BeatAgentState) -> dict:
    subgraph_input = {"artifact_id": state["current_artifact_id"], ...}
    result = analysis_subgraph.invoke(subgraph_input)
    return {"brief": result["brief"]}

parent_graph.add_node("analyze", run_analysis_subgraph)

# Shared state keys — add compiled subgraph directly as a node
parent_graph.add_node("analyze", analysis_subgraph)
```

The `write_brief + flag_item` cluster from beat agents is a candidate subgraph — both beat and research agents produce analysis artifacts via the same logic.

### DeepAgents subagents

Use for context isolation and delegation. The main agent spawns an ephemeral subagent, gets a concise result, and discards the intermediate work.

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
| **Transient** | Network timeout fetching a source | Retry policy on the node |
| **LLM-recoverable** | Structured output validation fails | Store error in state; let the next analyze pass self-correct |
| **User-fixable** | Editor approval required before publishing | `interrupt()` — pause indefinitely, resume after human input |
| **Unexpected** | Database connection lost mid-write | Bubble up — do not mask |

### `interrupt()` for human-in-the-loop

```python
from langgraph.types import interrupt

def draft_node(state: EditorState) -> dict:
    draft = structured_llm.invoke(prompt)
    if state.get("requires_editorial_approval"):
        interrupt({"draft": draft.model_dump(), "reason": state["flag_reason"]})
    return {"draft": draft}
```

State is preserved indefinitely across the pause. Resumption picks up at the exact node where `interrupt()` fired.

### `interrupt_on` for DeepAgents

Use `interrupt_on` to gate destructive or high-stakes tool calls:

```python
agent = create_deep_agent(
    tools=[...],
    interrupt_on=["publish_story", "activate_source"],
)
```

---

## Human-in-the-loop placement

Use `interrupt()` or `interrupt_on` at these specific points:

| Point | Mechanism | Condition |
|---|---|---|
| Editor agent draft | `interrupt()` in `draft` node | Beat agent set `flag.requires_editor_approval` |
| Discovery agent source proposal | `interrupt_on` | Always — no agent-proposed source auto-activates |
| Connection agent assignment creation | `interrupt()` | Creating a story-type assignment (per ASSIGNMENTS.md human gate rule) |
| Research search agent | `interrupt_on` | Writing artifacts from an untrusted source |

---

## Agent interface contract

Each agent module exposes a single entry point. No agent imports from another agent module — the interface is: receive an event, read from the artifact store, write to the artifact store.

```python
# LangGraph agents
class BeatAgent:
    def handle_artifact_written(self, event: ArtifactEvent) -> None:
        """Entry point from event bus. Reads artifact, runs graph, writes outputs."""
        config = {"configurable": {"thread_id": f"{self.beat}-{self.geo}"}}
        self.graph.invoke({"event": event}, config=config)

# DeepAgents agents
def create_editor_agent(artifact_store: ArtifactStore, event_bus: EventBus) -> Agent:
    """Factory. Inject dependencies; return a configured DeepAgent."""
    ...
    return create_deep_agent(tools=[...], system_prompt=...)
```

Dependencies (`ArtifactStore`, `EventBus`, `ObjectStore`) are always injected — never instantiated inside agent code. This keeps agents testable and environment-agnostic.

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

| Pattern | Framework | Memory | Checkpointer |
|---|---|---|---|
| Stateless transform | Plain functions | None | — |
| Fixed workflow with typed stages | LangGraph Graph API | Optional, depending on statefulness | Usually yes for persistent workflows |
| Open-ended tool-using planner | DeepAgents | Usually ephemeral unless explicitly persisted | Managed by framework choice |

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
