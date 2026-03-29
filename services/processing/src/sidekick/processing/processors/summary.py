"""``document-text`` → ``summary`` enrichment processor."""

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
from sidekick.core.models import Artifact, Source
from sidekick.core.vocabulary import ContentType, Stage
from sqlmodel import Session, select

from sidekick.processing.processors.schemas import SummaryOutput
from sidekick.processing.processors.utils import build_skill_store

# Truncate input text to keep within model context limits (~25K tokens).
_MAX_INPUT_CHARS = 100_000

AGENT_ID = "processor:summary"


def _resolve_skills_dir(skills_dir: Path | None) -> Path:
    if skills_dir is not None:
        return skills_dir
    env_path = os.environ.get("SKILLS_DIR")
    if env_path:
        return Path(env_path)
    # Repo root is six levels up from this file.
    return Path(__file__).parents[6] / "skills"


def _load_source_details(
    artifact_store: ArtifactStore,
    source_id: str | None,
) -> tuple[str | None, str | None]:
    if source_id is None:
        return None, None
    engine = getattr(artifact_store, "_engine", None)
    if engine is None:
        return source_id, source_id
    with Session(engine) as session:
        row = session.exec(select(Source).where(Source.id == source_id)).first()
    if row is None:
        return source_id, source_id
    return row.id, row.name or row.id


def _find_sibling_entity_extract(
    artifact_store: ArtifactStore,
    row: Artifact,
    artifact_id: str,
) -> Artifact | None:
    filters = {
        "stage": Stage.PROCESSED,
        "status": row.status,
        "content_type": ContentType.ENTITY_EXTRACT,
    }
    if row.event_group is not None:
        filters["event_group"] = row.event_group
    elif row.source_id is not None:
        filters["source_id"] = row.source_id
    else:
        filters["beat"] = row.beat
        filters["geo"] = row.geo

    candidates: list[Artifact] = []
    for candidate in artifact_store.query(filters=filters, limit=50):
        if artifact_id in (candidate.derived_from or []):
            candidates.append(candidate)
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: candidate.created_at, reverse=True)
    return candidates[0]


def _render_summary_markdown(
    output: SummaryOutput,
    *,
    summary_artifact_id: str,
    input_artifact_id: str,
    source_artifact_ids: list[str],
    source_id: str | None,
    source_label: str | None,
    sibling_entity_extract_id: str | None,
) -> str:
    lines: list[str] = [f"# {output.headline}", "", output.summary.strip()]

    if output.key_developments:
        lines.extend(["", "## Key Developments", ""])
        lines.extend(f"- {item}" for item in output.key_developments)

    if output.date_references:
        lines.extend(["", "## Dates Mentioned", ""])
        lines.extend(f"- {item}" for item in output.date_references)

    lines.extend(["", "## Sources", ""])
    if source_label is not None:
        source_line = f"- Source: {source_label}"
        if source_id is not None:
            source_line += f" (`source_id: {source_id}`)"
        lines.append(source_line)
    for ref in output.source_references:
        lines.append(f"- Referenced source material: {ref.label}")
    lines.append(f"- Summary artifact ID: `{summary_artifact_id}`")
    lines.append(f"- Input text artifact ID: `{input_artifact_id}`")
    for source_artifact_id in source_artifact_ids:
        lines.append(f"- Upstream artifact ID: `{source_artifact_id}`")
    if sibling_entity_extract_id is not None:
        lines.append(f"- Sibling entity-extract artifact ID: `{sibling_entity_extract_id}`")

    return "\n".join(lines).strip() + "\n"


def process_to_summary(
    artifact_id: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
    *,
    skills_dir: Path | None = None,
    created_by: str = "processor:summary",
) -> str:
    """Create a ``summary`` artifact from a textual artifact.

    Args:
        artifact_id: ID of the processed text artifact to summarize.
        artifact_store: Store used to read input and write output.
        config_registry: Registry used to resolve model and prompt configuration.
        skills_dir: Root directory containing skill subdirectories. Defaults to
            the ``SKILLS_DIR`` environment variable or the repo-level ``skills/``.
        created_by: Provenance tag written to the output artifact.

    Returns:
        ID of the newly written ``summary`` artifact.

    Raises:
        KeyError: If no agent config row exists for ``processor:summary``.
    """
    row = artifact_store.read_row(artifact_id)
    text = artifact_store.get_text_utf8(row)
    if len(text) > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]

    config = config_registry.resolve(AGENT_ID)
    store = build_skill_store(config.skills, _resolve_skills_dir(
        skills_dir)) if config.skills else None
    sibling_entity_extract = _find_sibling_entity_extract(
        artifact_store, row, artifact_id)
    if sibling_entity_extract is None:
        raise ValueError(
            f"Summary requires sibling entity-extract for {artifact_id!r}; orchestration should "
            "run entity-extract first."
        )

    prompt_sections = [
        "Primary document or transcript:",
        text,
    ]
    prompt_sections.extend([
        "",
        "Sibling entity extraction for this same artifact:",
        artifact_store.get_text_utf8(sibling_entity_extract),
    ])
    prompt = "\n".join(prompt_sections)

    agent = create_deep_agent(
        model=config.model,
        tools=[],
        system_prompt=config.prompts["system"],
        skills=["/skills/"] if config.skills else None,
        response_format=ToolStrategy(SummaryOutput),
        backend=StoreBackend,
        store=store,
    )

    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    output: SummaryOutput = result["structured_response"]

    new_id = f"art_{ulid.new()}"
    source_id, source_label = _load_source_details(artifact_store, row.source_id)
    rendered_markdown = _render_summary_markdown(
        output,
        summary_artifact_id=new_id,
        input_artifact_id=artifact_id,
        source_artifact_ids=list(row.derived_from or []),
        source_id=source_id,
        source_label=source_label,
        sibling_entity_extract_id=sibling_entity_extract.id if sibling_entity_extract else None,
    )
    out = Artifact(
        id=new_id,
        title=row.title,
        content_type=ContentType.SUMMARY,
        stage=Stage.PROCESSED,
        media_type="text/markdown",
        processing_profile=row.processing_profile,
        derived_from=[artifact_id, sibling_entity_extract.id],
        source_id=row.source_id,
        event_group=row.event_group,
        beat=row.beat,
        geo=row.geo,
        period_start=row.period_start,
        period_end=row.period_end,
        assignment_id=row.assignment_id,
        topics=list(sibling_entity_extract.topics or []) or None,
        entities=list(sibling_entity_extract.entities or []) or None,
        created_by=created_by,
    )
    return artifact_store.write_with_bytes(
        out,
        rendered_markdown.encode("utf-8"),
        object_content_type="text/markdown",
    )
