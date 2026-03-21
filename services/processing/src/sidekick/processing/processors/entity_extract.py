"""``document-text`` / ``transcript-clean`` → ``entity-extract`` enrichment processor."""

from __future__ import annotations

import ulid
from langchain_anthropic import ChatAnthropic

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact

from sidekick.processing.processors.schemas import EntityExtractionOutput
from sidekick.processing.router import UnsupportedProcessingError, resolve_enrichment_input

# Truncate input text to keep within model context limits (~25K tokens).
_MAX_INPUT_CHARS = 100_000

AGENT_ID = "processor:entity-extract"


def process_to_entity_extract(
    artifact_id: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
    *,
    created_by: str = "processor:entity-extract",
) -> str:
    """Create an ``entity-extract`` artifact from a ``document-text`` or ``transcript-clean`` artifact.

    Args:
        artifact_id: ID of the processed text artifact to extract entities from.
        artifact_store: Store used to read input and write output.
        config_registry: Registry used to resolve model and prompt configuration.
        created_by: Provenance tag written to the output artifact.

    Returns:
        ID of the newly written ``entity-extract`` artifact.

    Raises:
        UnsupportedProcessingError: If the input artifact is not enrichable.
        KeyError: If no agent config row exists for ``processor:entity-extract``.
    """
    row = artifact_store.read_row(artifact_id)
    resolve_enrichment_input(row)  # raises UnsupportedProcessingError if not enrichable

    text = artifact_store.get_text_utf8(row)
    if len(text) > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]

    config = config_registry.resolve(AGENT_ID)
    llm = ChatAnthropic(model=config.model)  # type: ignore[call-arg]
    structured_llm = llm.with_structured_output(EntityExtractionOutput)

    system_prompt = config.prompts["system"]
    prompt = f"{system_prompt}\n\n---\n\n{text}"
    result: EntityExtractionOutput = structured_llm.invoke(prompt)  # type: ignore[assignment]

    # Serialize extracted entities into the artifact's entities list.
    extracted = [e.model_dump(exclude_none=True) for e in result.entities]
    artifact_entities = list(row.entities or [])
    artifact_entities.extend(extracted)
    artifact_entities.append(
        {
            "type": "llm-enrichment",
            "processor": "entity-extract",
            "model": config.model,
        }
    )

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        id=new_id,
        content_type="entity-extract",
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
        entities=artifact_entities,
        created_by=created_by,
    )
    return artifact_store.write_with_bytes(
        out,
        result.model_dump_json().encode("utf-8"),
        object_content_type="application/json",
    )
