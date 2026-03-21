"""``document-text`` / ``transcript-clean`` → ``summary`` enrichment processor."""

from __future__ import annotations

import ulid
from langchain_anthropic import ChatAnthropic

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact

from sidekick.processing.processors.schemas import SummaryOutput
from sidekick.processing.router import UnsupportedProcessingError, resolve_enrichment_input

# Truncate input text to keep within model context limits (~25K tokens).
_MAX_INPUT_CHARS = 100_000

AGENT_ID = "processor:summary"


def process_to_summary(
    artifact_id: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
    *,
    created_by: str = "processor:summary",
) -> str:
    """Create a ``summary`` artifact from a ``document-text`` or ``transcript-clean`` artifact.

    Args:
        artifact_id: ID of the processed text artifact to summarize.
        artifact_store: Store used to read input and write output.
        config_registry: Registry used to resolve model and prompt configuration.
        created_by: Provenance tag written to the output artifact.

    Returns:
        ID of the newly written ``summary`` artifact.

    Raises:
        UnsupportedProcessingError: If the input artifact is not enrichable.
        KeyError: If no agent config row exists for ``processor:summary``.
    """
    row = artifact_store.read_row(artifact_id)
    resolve_enrichment_input(row)  # raises UnsupportedProcessingError if not enrichable

    text = artifact_store.get_text_utf8(row)
    if len(text) > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]

    config = config_registry.resolve(AGENT_ID)
    llm = ChatAnthropic(model=config.model)  # type: ignore[call-arg]
    structured_llm = llm.with_structured_output(SummaryOutput)

    system_prompt = config.prompts["system"]
    prompt = f"{system_prompt}\n\n---\n\n{text}"
    result: SummaryOutput = structured_llm.invoke(prompt)  # type: ignore[assignment]

    entities = list(row.entities or [])
    entities.append(
        {
            "type": "llm-enrichment",
            "processor": "summary",
            "model": config.model,
        }
    )

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        id=new_id,
        content_type="summary",
        stage="processed",
        media_type="application/json",
        derived_from=[artifact_id],
        source_id=row.source_id,
        event_group=row.event_group,
        beat=row.beat,
        geo=row.geo,
        period_start=row.period_start,
        period_end=row.period_end,
        assignment_id=row.assignment_id,
        topics=result.topics or None,
        entities=entities,
        created_by=created_by,
    )
    return artifact_store.write_with_bytes(
        out,
        result.model_dump_json().encode("utf-8"),
        object_content_type="application/json",
    )
