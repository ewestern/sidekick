"""Helpers for Step Functions analysis scope coordination."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from sidekick.core.models import AnalysisScope, Artifact
from sidekick.core.vocabulary import ContentType, Stage


def _now() -> datetime:
    return datetime.now(UTC)


def _scope_key(artifact: Artifact) -> str:
    return f"event_group:{artifact.event_group}"


def _read_artifact(session: Session, artifact_id: str) -> Artifact | None:
    return session.get(Artifact, artifact_id)


def _pick_latest_brief_id(session: Session, written_ids: list[str]) -> str | None:
    if not written_ids:
        return None
    stmt = select(Artifact).where(Artifact.id.in_(written_ids))  # type: ignore[arg-type]
    rows = list(session.exec(stmt))
    for row in rows:
        if row.content_type == ContentType.BEAT_BRIEF:
            return row.id
    return written_ids[-1]


def upsert_scope_state(
    session: Session,
    *,
    artifact_id: str,
    execution_arn: str,
) -> dict[str, Any]:
    artifact = _read_artifact(session, artifact_id)
    if artifact is None:
        return {"skip": True, "reason": "artifact_not_found", "artifact_id": artifact_id}
    if (
        artifact.stage != Stage.PROCESSED
        or artifact.content_type not in {ContentType.SUMMARY, ContentType.ENTITY_EXTRACT}
        or artifact.event_group is None
        or artifact.beat is None
        or artifact.geo is None
    ):
        return {"skip": True, "reason": "artifact_not_scopeable", "artifact_id": artifact_id}

    now = _now()
    scope_key = _scope_key(artifact)
    row = session.get(AnalysisScope, scope_key)
    if row is None:
        row = AnalysisScope(
            scope_key=scope_key,
            event_group=artifact.event_group,
            beat=artifact.beat,
            geo=artifact.geo,
        )

    row.event_group = artifact.event_group
    row.beat = artifact.beat
    row.geo = artifact.geo
    row.dirty = True
    row.revision += 1
    row.last_input_at = now
    row.updated_at = now
    owned_by_other = bool(
        row.active_execution_arn and row.active_execution_arn != execution_arn
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "skip": False,
        "artifact_id": artifact.id,
        "scope_key": row.scope_key,
        "event_group": row.event_group,
        "beat": row.beat,
        "geo": row.geo,
        "revision": row.revision,
        "owned_by_other": owned_by_other,
    }


def claim_scope(
    session: Session,
    *,
    scope_key: str,
    execution_arn: str,
) -> dict[str, Any]:
    row = session.get(AnalysisScope, scope_key)
    if row is None:
        return {"claimed": False, "reason": "scope_not_found", "scope_key": scope_key}
    if row.active_execution_arn not in (None, execution_arn):
        return {"claimed": False, "reason": "owned_by_other", "scope_key": scope_key}

    now = _now()
    row.active_execution_arn = execution_arn
    row.status = "running"
    row.dirty = False
    row.last_run_started_at = now
    row.last_revision_started = row.revision
    row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "claimed": True,
        "scope_key": row.scope_key,
        "event_group": row.event_group,
        "beat": row.beat,
        "geo": row.geo,
        "run_revision": row.last_revision_started,
    }


def record_run(
    session: Session,
    *,
    scope_key: str,
    execution_arn: str,
    written_artifact_ids: list[str],
) -> dict[str, Any]:
    row = session.get(AnalysisScope, scope_key)
    if row is None:
        return {"scope_key": scope_key, "recorded": False, "reason": "scope_not_found"}
    if row.active_execution_arn != execution_arn:
        return {"scope_key": scope_key, "recorded": False, "reason": "ownership_lost"}

    now = _now()
    row.last_run_completed_at = now
    row.last_revision_completed = row.last_revision_started
    row.last_error = None
    row.updated_at = now
    latest_brief_id = _pick_latest_brief_id(session, written_artifact_ids)
    if latest_brief_id is not None:
        row.last_brief_artifact_id = latest_brief_id
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "scope_key": row.scope_key,
        "recorded": True,
        "last_revision_completed": row.last_revision_completed,
        "last_brief_artifact_id": row.last_brief_artifact_id,
    }


def check_scope(
    session: Session,
    *,
    scope_key: str,
) -> dict[str, Any]:
    row = session.get(AnalysisScope, scope_key)
    if row is None:
        return {"scope_key": scope_key, "rerun_required": False, "exists": False}
    last_completed = row.last_revision_completed or 0
    return {
        "scope_key": row.scope_key,
        "exists": True,
        "rerun_required": row.revision > last_completed,
        "revision": row.revision,
        "last_revision_completed": last_completed,
    }


def release_scope(
    session: Session,
    *,
    scope_key: str,
    execution_arn: str,
    keep_dirty: bool = False,
    error: str | None = None,
) -> dict[str, Any]:
    row = session.get(AnalysisScope, scope_key)
    if row is None:
        return {"scope_key": scope_key, "released": False, "reason": "scope_not_found"}
    if row.active_execution_arn not in (None, execution_arn):
        return {"scope_key": scope_key, "released": False, "reason": "ownership_lost"}

    row.active_execution_arn = None
    row.status = "idle"
    row.dirty = keep_dirty
    row.last_error = error
    row.updated_at = _now()
    session.add(row)
    session.commit()
    return {"scope_key": scope_key, "released": True, "keep_dirty": keep_dirty}
