"""Tool factories for the beat agent."""

from __future__ import annotations

import json
from datetime import date
from typing import Annotated, Any

import ulid
from langchain_core.tools import BaseTool, tool

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.assignment_store import AssignmentStore
from sidekick.core.models import Artifact, Assignment
from sidekick.core.vocabulary import ArtifactStatus, ContentType, Stage

from sidekick.beat.scope import BeatScope, DateWindowScope, EventGroupScope


def _format_entity_extract_payload(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text

    lines: list[str] = []
    entities = payload.get("entities") or []
    if entities:
        lines.append("Entities:")
        for entity in entities:
            name = entity.get("name", "unknown")
            entity_type = entity.get("type", "unknown")
            role = entity.get("role")
            context = entity.get("context")
            detail = f"- {name} ({entity_type})"
            if role:
                detail += f"; role={role}"
            if context:
                detail += f"; context={context}"
            lines.append(detail)

    topics = payload.get("topics") or []
    if topics:
        lines.append("Topics:")
        lines.extend(f"- {topic}" for topic in topics)

    financial_figures = payload.get("financial_figures") or []
    if financial_figures:
        lines.append("Financial figures:")
        for item in financial_figures:
            description = item.get("description", "amount")
            amount = item.get("amount", "unknown")
            context = item.get("context")
            detail = f"- {description}: {amount}"
            if context:
                detail += f" ({context})"
            lines.append(detail)

    motions_or_votes = payload.get("motions_or_votes") or []
    if motions_or_votes:
        lines.append("Motions or votes:")
        for item in motions_or_votes:
            description = item.get("description", "motion")
            result = item.get("result", "unknown")
            vote_tally = item.get("vote_tally")
            detail = f"- {description}: {result}"
            if vote_tally:
                detail += f" ({vote_tally})"
            lines.append(detail)

    return "\n".join(lines) if lines else text


def _format_artifact_body(row: Artifact, text: str) -> str:
    if row.content_type == ContentType.ENTITY_EXTRACT:
        return _format_entity_extract_payload(text)
    return text


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _append_unique(target: list[str], values: list[str]) -> None:
    seen = set(target)
    for value in values:
        if value not in seen:
            target.append(value)
            seen.add(value)


def _default_filters(
    beat: str,
    geo: str,
    scope: BeatScope,
    *,
    current_scope_only: bool,
) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "stage": Stage.PROCESSED,
        "status": ArtifactStatus.ACTIVE,
        "beat": beat,
        "geo": geo,
    }
    if isinstance(scope, EventGroupScope):
        if current_scope_only:
            filters["event_group"] = scope.event_group
    else:
        if current_scope_only:
            filters["period_start_gte"] = scope.since
            filters["period_start_lte"] = scope.until
    return filters


def _resolve_content_types(content_types: list[str] | None) -> list[str] | None:
    if not content_types:
        return [ContentType.SUMMARY, ContentType.ENTITY_EXTRACT]
    return [ContentType(item) for item in content_types]


def _format_artifact_sections(rows: list[Artifact], artifact_store: ArtifactStore, match_label: str) -> str:
    sections: list[str] = []
    for row in rows:
        try:
            text = artifact_store.get_text_utf8(row)
        except Exception:
            text = "(content unavailable)"
        text = _format_artifact_body(row, text)
        period = f"{row.period_start}" if row.period_start else "unknown date"
        sections.append(
            f"=== {row.content_type} | {row.id} | {period} | match={match_label} ===\n{text}"
        )
    return "\n\n".join(sections)


def _dedupe_rows(rows: list[Artifact]) -> list[Artifact]:
    deduped: list[Artifact] = []
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        deduped.append(row)
    return deduped


def _active_story_artifacts(
    artifact_store: ArtifactStore,
    *,
    story_key: str,
    content_type: ContentType,
) -> list[Artifact]:
    return artifact_store.query(
        filters={
            "story_key": story_key,
            "content_type": content_type,
            "status": ArtifactStatus.ACTIVE,
        },
        limit=20,
    )


def make_query_artifacts(
    artifact_store: ArtifactStore,
    beat: str,
    geo: str,
    scope: BeatScope,
    derived_ids: list[str],
) -> BaseTool:
    """Return a tool that retrieves processed artifacts for beat analysis."""

    @tool
    def query_artifacts(
        query_text: Annotated[str | None, "Optional semantic query text for broader contextual retrieval."] = None,
        content_types: Annotated[list[str] | None, "Optional content types to fetch. Defaults to ['summary', 'entity-extract']."] = None,
        mode: Annotated[str, "Retrieval mode: 'structured', 'semantic', or 'hybrid'."] = "structured",
        current_scope_only: Annotated[bool, "When true, stay within the current run scope. When false, search broader beat history."] = True,
        event_group: Annotated[str | None, "Optional event-group override."] = None,
        beat_override: Annotated[str | None, "Optional beat override for structured retrieval."] = None,
        geo_override: Annotated[str | None, "Optional geo override for structured retrieval."] = None,
        topics: Annotated[list[str] | None, "Optional topic filters. All supplied topics must match the artifact topics array."] = None,
        created_by: Annotated[list[str] | None, "Optional artifact creators to filter on."] = None,
        since: Annotated[str | None, "Optional ISO date lower bound for period_start."] = None,
        until: Annotated[str | None, "Optional ISO date upper bound for period_start."] = None,
        include_lineage_from: Annotated[list[str] | None, "Optional artifact IDs whose lineage should be included."] = None,
        lineage_direction: Annotated[str, "Lineage direction: 'up' or 'down'."] = "up",
        limit: Annotated[int, "Maximum number of structured or semantic matches to return before lineage expansion."] = 20,
    ) -> str:
        """Retrieve source artifacts and broader beat context."""
        if mode not in {"structured", "semantic", "hybrid"}:
            raise ValueError("mode must be one of: structured, semantic, hybrid")
        if lineage_direction not in {"up", "down"}:
            raise ValueError("lineage_direction must be one of: up, down")

        resolved_content_types = _resolve_content_types(content_types)
        filters = _default_filters(
            beat_override or beat,
            geo_override or geo,
            scope,
            current_scope_only=current_scope_only,
        )
        if event_group is not None:
            filters["event_group"] = event_group
            filters.pop("beat", None)
            filters.pop("geo", None)
            filters.pop("period_start_gte", None)
            filters.pop("period_start_lte", None)
        if resolved_content_types:
            filters["content_type"] = resolved_content_types
        if topics:
            filters["topics"] = topics
        if created_by:
            filters["created_by"] = created_by

        since_date = _parse_iso_date(since)
        until_date = _parse_iso_date(until)
        if since_date is not None:
            filters["period_start_gte"] = since_date
        if until_date is not None:
            filters["period_start_lte"] = until_date

        rows: list[Artifact] = []
        sections: list[str] = []

        if mode in {"structured", "hybrid"}:
            structured_rows = artifact_store.query(filters=filters, limit=limit)
            rows.extend(structured_rows)
            if structured_rows:
                sections.append(_format_artifact_sections(structured_rows, artifact_store, "structured"))

        if mode in {"semantic", "hybrid"} and query_text:
            semantic_rows = artifact_store.semantic_query_text(query_text, filters=filters, limit=limit)
            rows.extend(semantic_rows)
            if semantic_rows:
                sections.append(_format_artifact_sections(semantic_rows, artifact_store, "semantic"))

        if include_lineage_from:
            lineage_rows: list[Artifact] = []
            for artifact_id in include_lineage_from:
                lineage_rows.extend(artifact_store.lineage(artifact_id, direction=lineage_direction))
            lineage_rows = _dedupe_rows(lineage_rows)
            rows.extend(lineage_rows)
            if lineage_rows:
                sections.append(_format_artifact_sections(lineage_rows, artifact_store, f"lineage:{lineage_direction}"))

        rows = _dedupe_rows(rows)
        _append_unique(derived_ids, [row.id for row in rows])

        if not rows:
            scope_desc = (
                f"event_group={event_group or getattr(scope, 'event_group', None)!r}"
                if isinstance(scope, EventGroupScope) and current_scope_only
                else f"beat={beat_override or beat!r}, geo={geo_override or geo!r}"
            )
            return f"No processed artifacts found for {scope_desc}."

        return "\n\n".join(section for section in sections if section)

    return query_artifacts


def make_write_beat_brief(
    artifact_store: ArtifactStore,
    beat: str,
    geo: str,
    scope: BeatScope,
    derived_ids: list[str],
    written_ids: list[str],
    created_by: str,
) -> BaseTool:
    """Return a tool that writes a beat-brief artifact."""

    @tool
    def write_beat_brief(
        headline: Annotated[str, "One-sentence factual headline capturing the most newsworthy element."],
        narrative: Annotated[str, "2-5 paragraph narrative summary of notable developments."],
        key_developments: Annotated[list[str], "Concise bullet-point items covering decisions, actions, or announcements."],
        topics: Annotated[list[str], "Lowercase slug-style topic tags (e.g. ['zoning', 'budget'])."],
        supersede_brief_id: Annotated[str | None, "Optional prior beat-brief artifact ID to supersede with this new version."] = None,
    ) -> str:
        """Write a beat-brief artifact synthesizing the queried source material."""
        event_group = scope.event_group if isinstance(scope, EventGroupScope) else None
        period_start = None if isinstance(scope, EventGroupScope) else scope.since
        period_end = None if isinstance(scope, EventGroupScope) else scope.until
        body = json.dumps(
            {
                "headline": headline,
                "narrative": narrative,
                "key_developments": key_developments,
                "topics": topics,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        artifact = Artifact(
            id=f"art_{ulid.new()}",
            title=headline,
            content_type=ContentType.BEAT_BRIEF,
            stage=Stage.ANALYSIS,
            media_type="application/json",
            derived_from=list(derived_ids),
            beat=beat,
            geo=geo,
            event_group=event_group,
            period_start=period_start,
            period_end=period_end,
            topics=topics or None,
            created_by=created_by,
        )
        new_id = artifact_store.write_with_bytes(
            artifact,
            body,
            object_content_type="application/json",
        )
        if supersede_brief_id:
            artifact_store.patch(supersede_brief_id, superseded_by=new_id)
        written_ids.append(new_id)
        return new_id

    return write_beat_brief


def make_write_story_candidate(
    artifact_store: ArtifactStore,
    beat: str,
    geo: str,
    scope: BeatScope,
    derived_ids: list[str],
    written_ids: list[str],
    created_by: str,
) -> BaseTool:
    """Return a tool that writes a story-candidate artifact."""

    @tool
    def write_story_candidate(
        story_key: Annotated[str, "Stable dedupe key for the story candidate."],
        headline: Annotated[str, "Working headline for the candidate story."],
        why_now: Annotated[str, "Short explanation of the new development or change."],
        development_type: Annotated[str, "One of: decision, disclosure, conflict, impact, trend, cross-beat-pattern."],
        time_sensitivity: Annotated[str, "One of: breaking, timely, routine."],
        urgency: Annotated[str, "One of: immediate, same_day, normal."],
        evidence_ready: Annotated[bool, "Whether the current supporting evidence is sufficient to draft safely."],
        primary_support_present: Annotated[bool, "Whether at least one primary-source-backed lineage branch supports the candidate."],
        novelty_score: Annotated[int, "1-5 novelty score for the development."],
        impact_score: Annotated[int, "1-5 impact score for the development."],
        confidence_score: Annotated[int, "1-5 confidence score in the evidence and framing."],
        missing_gaps: Annotated[list[str] | None, "Short descriptions of missing evidence or unanswered questions."] = None,
        recommended_action: Annotated[str, "One of: auto_draft, priority_draft, queue, research, suppress."] = "queue",
        reason: Annotated[str, "Concise editorial rationale for the routing decision."] = "",
        topics: Annotated[list[str] | None, "Optional lowercase slug-style topic tags to carry onto the candidate."] = None,
        supersede_candidate_id: Annotated[str | None, "Optional prior story-candidate artifact ID to supersede explicitly."] = None,
    ) -> str:
        """Write a structured story-candidate artifact."""
        event_group = scope.event_group if isinstance(scope, EventGroupScope) else None
        period_start = None if isinstance(scope, EventGroupScope) else scope.since
        period_end = None if isinstance(scope, EventGroupScope) else scope.until
        if recommended_action not in {"auto_draft", "priority_draft", "queue", "research", "suppress"}:
            raise ValueError("recommended_action must be one of: auto_draft, priority_draft, queue, research, suppress")
        if urgency not in {"immediate", "same_day", "normal"}:
            raise ValueError("urgency must be one of: immediate, same_day, normal")
        if time_sensitivity not in {"breaking", "timely", "routine"}:
            raise ValueError("time_sensitivity must be one of: breaking, timely, routine")
        if development_type not in {"decision", "disclosure", "conflict", "impact", "trend", "cross-beat-pattern"}:
            raise ValueError("development_type must be a supported story-candidate type")
        for score_name, score_value in (
            ("novelty_score", novelty_score),
            ("impact_score", impact_score),
            ("confidence_score", confidence_score),
        ):
            if score_value < 1 or score_value > 5:
                raise ValueError(f"{score_name} must be between 1 and 5")

        final_action = recommended_action
        existing_drafts = _active_story_artifacts(
            artifact_store,
            story_key=story_key,
            content_type=ContentType.STORY_DRAFT,
        )
        if existing_drafts and final_action in {"auto_draft", "priority_draft"}:
            final_action = "queue"
            reason = (
                f"{reason} Active draft already exists for this story key."
                if reason
                else "Active draft already exists for this story key."
            )

        supporting_artifact_count = len(set(derived_ids))
        body = json.dumps(
            {
                "story_key": story_key,
                "headline": headline,
                "why_now": why_now,
                "development_type": development_type,
                "time_sensitivity": time_sensitivity,
                "urgency": urgency,
                "evidence_ready": evidence_ready,
                "primary_support_present": primary_support_present,
                "supporting_artifact_count": supporting_artifact_count,
                "novelty_score": novelty_score,
                "impact_score": impact_score,
                "confidence_score": confidence_score,
                "missing_gaps": missing_gaps or [],
                "recommended_action": final_action,
                "reason": reason,
                "topics": topics or [],
            },
            ensure_ascii=False,
        ).encode("utf-8")

        artifact = Artifact(
            id=f"art_{ulid.new()}",
            title=headline,
            content_type=ContentType.STORY_CANDIDATE,
            stage=Stage.ANALYSIS,
            media_type="application/json",
            derived_from=list(derived_ids),
            beat=beat,
            geo=geo,
            event_group=event_group,
            period_start=period_start,
            period_end=period_end,
            story_key=story_key,
            topics=topics or None,
            created_by=created_by,
        )
        new_id = artifact_store.write_with_bytes(
            artifact,
            body,
            object_content_type="application/json",
        )
        for existing in _active_story_artifacts(
            artifact_store,
            story_key=story_key,
            content_type=ContentType.STORY_CANDIDATE,
        ):
            if existing.id != new_id:
                artifact_store.patch(existing.id, superseded_by=new_id)
        if supersede_candidate_id:
            artifact_store.patch(supersede_candidate_id, superseded_by=new_id)
        written_ids.append(new_id)
        return new_id

    return write_story_candidate


def _existing_assignment_match(row: Assignment, query_params: dict[str, Any]) -> bool:
    existing = row.query_params or {}
    return (
        existing.get("reason") == query_params.get("reason")
        and existing.get("topic") == query_params.get("topic")
        and existing.get("entity_names") == query_params.get("entity_names")
        and existing.get("target_document_types") == query_params.get("target_document_types")
    )


def make_create_research_assignment(
    assignment_store: AssignmentStore,
    beat: str,
    geo: str,
    scope: BeatScope,
    derived_ids: list[str],
    created_by: str,
) -> BaseTool:
    """Return a tool that creates a de-duplicated research follow-up assignment."""

    @tool
    def create_research_assignment(
        query_text: Annotated[str, "Precise follow-up request for research-search."],
        topic: Annotated[str, "Short slug-like topic or angle for the assignment."],
        reason: Annotated[str, "Why this follow-up is needed: baseline, primary-doc, vendor-history, conflict-check, or prior-history."],
        entity_names: Annotated[list[str] | None, "Optional people, vendors, or institutions relevant to the follow-up."] = None,
        target_document_types: Annotated[list[str] | None, "Optional target document classes such as contracts, invoices, agendas, or audits."] = None,
        since: Annotated[str | None, "Optional ISO date lower bound for the research window."] = None,
        until: Annotated[str | None, "Optional ISO date upper bound for the research window."] = None,
        parent_assignment_id: Annotated[str | None, "Optional parent assignment ID when this beat run is already operating under an assignment."] = None,
    ) -> str:
        """Create a research follow-up assignment for missing context."""
        query_params: dict[str, Any] = {
            "beat": beat,
            "geo": geo,
            "topic": topic,
            "reason": reason,
            "entity_names": entity_names or [],
            "target_document_types": target_document_types or [],
            "event_group": scope.event_group if isinstance(scope, EventGroupScope) else None,
            "since": since or (scope.since.isoformat() if isinstance(scope, DateWindowScope) else None),
            "until": until or (scope.until.isoformat() if isinstance(scope, DateWindowScope) else None),
        }

        existing_rows = assignment_store.list_open(
            parent_assignment=parent_assignment_id,
            triggered_by=created_by,
            triggered_by_id=f"{beat}|{geo}|{scope.event_group if isinstance(scope, EventGroupScope) else f'{scope.since}:{scope.until}'}",
        )
        for row in existing_rows:
            if _existing_assignment_match(row, query_params):
                return row.id

        assignment = assignment_store.create(
            assignment_type="research",
            query_text=query_text,
            query_params=query_params,
            triggered_by=created_by,
            triggered_by_id=f"{beat}|{geo}|{scope.event_group if isinstance(scope, EventGroupScope) else f'{scope.since}:{scope.until}'}",
            parent_assignment=parent_assignment_id,
            artifacts_in=list(derived_ids),
        )
        return assignment.id

    return create_research_assignment
