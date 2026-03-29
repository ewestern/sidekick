"""``document-text`` → ``entity-extract`` enrichment processor."""

from __future__ import annotations

import os
import ulid
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import HumanMessage

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ContentType, Stage

from sidekick.processing.processors.schemas import EntityExtractionOutput
from sidekick.processing.processors.utils import build_skill_store
# Truncate input text to keep within model context limits (~25K tokens).
_MAX_INPUT_CHARS = 100_000

AGENT_ID = "processor:entity-extract"


def _resolve_skills_dir(skills_dir: Path | None) -> Path:
    if skills_dir is not None:
        return skills_dir
    env_path = os.environ.get("SKILLS_DIR")
    if env_path:
        return Path(env_path)
    # Repo root is six levels up from this file.
    return Path(__file__).parents[6] / "skills"


def process_to_entity_extract(
    artifact_id: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
    *,
    skills_dir: Path | None = None,
    created_by: str = "processor:entity-extract",
) -> str:
    """Create an ``entity-extract`` artifact from a ``document-text`` artifact.

    Args:
        artifact_id: ID of the processed text artifact to extract entities from.
        artifact_store: Store used to read input and write output.
        config_registry: Registry used to resolve model and prompt configuration.
        skills_dir: Root directory containing skill subdirectories. Defaults to
            the ``SKILLS_DIR`` environment variable or the repo-level ``skills/``.
        created_by: Provenance tag written to the output artifact.

    Returns:
        ID of the newly written ``entity-extract`` artifact.

    Raises:
        KeyError: If no agent config row exists for ``processor:entity-extract``.
    """
    row = artifact_store.read_row(artifact_id)
    text = artifact_store.get_text_utf8(row)
    if len(text) > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]
    if not text:
        raise ValueError(
            f"Entity extraction requires non-empty text; got {row.id!r} ({len(text)} chars)"
        )

    config = config_registry.resolve(AGENT_ID)
    store = build_skill_store(config.skills, _resolve_skills_dir(
        skills_dir)) if config.skills else None

    agent = create_deep_agent(
        model=config.model,
        tools=[],
        system_prompt=config.prompts["system"],
        skills=["/skills/"] if config.skills else None,
        response_format=ToolStrategy(EntityExtractionOutput),
        backend=StoreBackend,
        store=store,
    )

    result = agent.invoke({"messages": [HumanMessage(content=text)]})
    output: EntityExtractionOutput = result["structured_response"]

    # Project extracted semantic entities into the artifact's entities list (row-level projection).
    # Financial figures and motions/votes stay body-only (in the JSON payload).
    artifact_entities = list(row.entities or [])
    artifact_entities.extend(e.model_dump(exclude_none=True)
                             for e in output.entities)

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        id=new_id,
        title=row.title,
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        media_type="application/json",
        processing_profile=row.processing_profile,
        derived_from=[artifact_id],
        source_id=row.source_id,
        event_group=row.event_group,
        beat=row.beat,
        geo=row.geo,
        period_start=row.period_start,
        period_end=row.period_end,
        assignment_id=row.assignment_id,
        entities=artifact_entities,
        topics=output.topics or None,
        created_by=created_by,
    )
    return artifact_store.write_with_bytes(
        out,
        output.model_dump_json().encode("utf-8"),
        object_content_type="application/json",
    )
