"""Helpers for editorial Step Functions orchestration."""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, col, desc, select

from sidekick.core.models import Artifact, Assignment
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.vocabulary import ArtifactStatus, ContentType


def _read_candidate_payload(artifact_store: ArtifactStore, candidate: Artifact) -> dict[str, Any]:
    return json.loads(artifact_store.get_text_utf8(candidate))


def _newer_active_candidate_exists(session: Session, candidate: Artifact) -> bool:
    if not candidate.story_key:
        return False
    stmt = (
        select(Artifact)
        .where(Artifact.story_key == candidate.story_key)
        .where(Artifact.content_type == ContentType.STORY_CANDIDATE)
        .where(Artifact.status == ArtifactStatus.ACTIVE)
        .where(Artifact.id != candidate.id)
        .where(col(Artifact.superseded_by).is_(None))
        .order_by(desc(Artifact.created_at))
    )
    for row in session.exec(stmt).all():
        if row.created_at > candidate.created_at:
            return True
    return False


def _active_draft_exists(session: Session, candidate: Artifact) -> bool:
    if not candidate.story_key:
        return False
    stmt = (
        select(Artifact)
        .where(Artifact.story_key == candidate.story_key)
        .where(Artifact.content_type == ContentType.STORY_DRAFT)
        .where(Artifact.status == ArtifactStatus.ACTIVE)
        .where(col(Artifact.superseded_by).is_(None))
    )
    return session.exec(stmt).first() is not None


def prepare_candidate(
    session: Session,
    artifact_store: ArtifactStore,
    *,
    artifact_id: str,
) -> dict[str, Any]:
    candidate = session.get(Artifact, artifact_id)
    if candidate is None:
        return {"should_run": False, "skip_reason": "artifact_not_found", "candidate_id": artifact_id}
    if candidate.status != ArtifactStatus.ACTIVE:
        return {"should_run": False, "skip_reason": "candidate_inactive", "candidate_id": candidate.id}
    if candidate.content_type != ContentType.STORY_CANDIDATE:
        return {"should_run": False, "skip_reason": "not_story_candidate", "candidate_id": candidate.id}
    if candidate.story_key is None:
        return {"should_run": False, "skip_reason": "missing_story_key", "candidate_id": candidate.id}
    if candidate.superseded_by is not None:
        return {"should_run": False, "skip_reason": "candidate_superseded", "candidate_id": candidate.id}

    payload = _read_candidate_payload(artifact_store, candidate)
    recommended_action = payload.get("recommended_action")
    if not payload.get("evidence_ready"):
        return {
            "should_run": False,
            "skip_reason": "candidate_not_evidence_ready",
            "candidate_id": candidate.id,
            "story_key": candidate.story_key,
            "recommended_action": recommended_action,
        }
    if recommended_action not in {"auto_draft", "priority_draft"}:
        return {
            "should_run": False,
            "skip_reason": "candidate_not_auto_runnable",
            "candidate_id": candidate.id,
            "story_key": candidate.story_key,
            "recommended_action": recommended_action,
        }
    if _newer_active_candidate_exists(session, candidate):
        return {
            "should_run": False,
            "skip_reason": "newer_candidate_exists",
            "candidate_id": candidate.id,
            "story_key": candidate.story_key,
            "recommended_action": recommended_action,
        }
    if _active_draft_exists(session, candidate):
        return {
            "should_run": False,
            "skip_reason": "active_draft_exists",
            "candidate_id": candidate.id,
            "story_key": candidate.story_key,
            "recommended_action": recommended_action,
        }

    return {
        "should_run": True,
        "candidate_id": candidate.id,
        "story_key": candidate.story_key,
        "recommended_action": recommended_action,
        "urgency": payload.get("urgency"),
        "assignment_id": candidate.assignment_id,
    }


def record_editor_run(
    session: Session,
    *,
    candidate_id: str,
    story_key: str | None,
    assignment_id: str | None,
    written_artifact_ids: list[str],
) -> dict[str, Any]:
    if assignment_id:
        assignment = session.get(Assignment, assignment_id)
        if assignment is not None:
            artifacts_out = list(assignment.artifacts_out or [])
            for artifact_id in written_artifact_ids:
                if artifact_id not in artifacts_out:
                    artifacts_out.append(artifact_id)
            assignment.artifacts_out = artifacts_out
            session.add(assignment)
            session.commit()
    return {
        "candidate_id": candidate_id,
        "story_key": story_key,
        "assignment_id": assignment_id,
        "written_artifact_ids": written_artifact_ids,
    }
