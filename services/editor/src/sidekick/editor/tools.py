"""Tool factories for the editor agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import ulid
from langchain_core.tools import BaseTool, tool
from sqlmodel import Session, create_engine

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact, Source
from sidekick.core.vocabulary import ContentType, Stage


def _read_json_body(artifact_store: ArtifactStore, artifact: Artifact) -> dict:
    return json.loads(artifact_store.get_text_utf8(artifact))


def _format_source_context(db_url: str, rows: list[Artifact]) -> dict[str, str]:
    source_ids = {row.source_id for row in rows if row.source_id}
    if not source_ids:
        return {}
    engine = create_engine(db_url)
    source_context: dict[str, str] = {}
    with Session(engine) as session:
        for source_id in source_ids:
            source = session.get(Source, source_id)
            if source is None:
                continue
            detail = f"source_tier={source.source_tier}"
            if source.outlet:
                detail += f"; outlet={source.outlet}"
            source_context[source_id] = detail
    return source_context


def _format_artifact_context(
    artifact_store: ArtifactStore,
    rows: list[Artifact],
    source_context: dict[str, str],
) -> str:
    sections: list[str] = []
    for row in rows:
        try:
            body = artifact_store.get_text_utf8(row)
        except Exception:
            body = "(content unavailable)"
        source_line = ""
        if row.source_id and row.source_id in source_context:
            source_line = f"\nsource={row.source_id} {source_context[row.source_id]}"
        sections.append(
            f"=== {row.content_type} | {row.id} ==="
            f"\nstage={row.stage} beat={row.beat} geo={row.geo} story_key={row.story_key}{source_line}\n{body}"
        )
    return "\n\n".join(sections)


def make_load_story_candidate_context(
    artifact_store: ArtifactStore,
    db_url: str,
    loaded_candidate_ids: list[str],
) -> BaseTool:
    """Return a tool that loads a story candidate and its supporting lineage."""

    @tool
    def load_story_candidate_context(
        candidate_id: Annotated[str, "Story-candidate artifact ID to draft from."],
    ) -> str:
        """Load a story-candidate plus supporting analysis and lineage context."""
        candidate = artifact_store.read(candidate_id)
        if candidate.content_type != ContentType.STORY_CANDIDATE:
            raise ValueError(f"Artifact {candidate_id!r} is not a story-candidate")

        loaded_candidate_ids.append(candidate_id)
        candidate_payload = _read_json_body(artifact_store, candidate)

        supporting_rows: list[Artifact] = []
        for parent_id in candidate.derived_from or []:
            supporting_rows.append(artifact_store.read(parent_id))
            supporting_rows.extend(artifact_store.lineage(parent_id, direction="up"))

        deduped_rows: list[Artifact] = []
        seen: set[str] = {candidate.id}
        for row in supporting_rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            deduped_rows.append(row)

        source_context = _format_source_context(db_url, deduped_rows)
        context = _format_artifact_context(artifact_store, deduped_rows, source_context)

        return (
            "=== story-candidate ===\n"
            f"{json.dumps(candidate_payload, ensure_ascii=False, indent=2)}\n\n"
            f"{context}"
        )

    return load_story_candidate_context


def make_write_story_draft(
    artifact_store: ArtifactStore,
    written_ids: list[str],
    created_by: str,
) -> BaseTool:
    """Return a tool that writes a story-draft artifact."""

    @tool
    def write_story_draft(
        candidate_id: Annotated[str, "Story-candidate artifact ID this draft is based on."],
        headline: Annotated[str, "Final draft headline."],
        dek: Annotated[str, "One-sentence summary deck."],
        narrative: Annotated[str, "Draft body text grounded in the candidate evidence."],
        sourcing_notes: Annotated[str, "Short note describing sourcing confidence and attribution constraints."],
        supersede_draft_id: Annotated[str | None, "Optional prior draft artifact ID to supersede."] = None,
        topics: Annotated[list[str] | None, "Optional lowercase topic slugs to carry onto the draft."] = None,
    ) -> str:
        """Write a story-draft artifact derived from a story-candidate."""
        candidate = artifact_store.read(candidate_id)
        if candidate.content_type != ContentType.STORY_CANDIDATE:
            raise ValueError(f"Artifact {candidate_id!r} is not a story-candidate")
        if candidate.story_key is None:
            raise ValueError(f"Story candidate {candidate_id!r} is missing story_key")

        candidate_payload = _read_json_body(artifact_store, candidate)
        body = json.dumps(
            {
                "headline": headline,
                "dek": dek,
                "narrative": narrative,
                "sourcing_notes": sourcing_notes,
                "candidate_id": candidate_id,
                "candidate_recommended_action": candidate_payload.get("recommended_action"),
            },
            ensure_ascii=False,
        ).encode("utf-8")

        artifact = Artifact(
            id=f"art_{ulid.new()}",
            title=headline,
            content_type=ContentType.STORY_DRAFT,
            stage=Stage.DRAFT,
            media_type="application/json",
            derived_from=[candidate_id],
            beat=candidate.beat,
            geo=candidate.geo,
            event_group=candidate.event_group,
            period_start=candidate.period_start,
            period_end=candidate.period_end,
            assignment_id=candidate.assignment_id,
            story_key=candidate.story_key,
            topics=topics or candidate.topics,
            created_by=created_by,
        )
        new_id = artifact_store.write_with_bytes(
            artifact,
            body,
            object_content_type="application/json",
        )
        if supersede_draft_id:
            artifact_store.patch(supersede_draft_id, superseded_by=new_id)
        written_ids.append(new_id)
        return new_id

    return write_story_draft
