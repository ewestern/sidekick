from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from sidekick.core.models import Artifact, Assignment
from sidekick.core.vocabulary import ArtifactStatus, ContentType, Stage
from sidekick_lambda.editorial import prepare_candidate, record_editor_run


def _candidate() -> Artifact:
    return Artifact(
        id="art_candidate",
        title="Budget cut candidate",
        content_type=ContentType.STORY_CANDIDATE,
        stage=Stage.ANALYSIS,
        story_key="budget-cut:2026-03",
        content_uri="s3://bucket/artifacts/analysis/x/art_candidate",
        created_at=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
    )


def test_prepare_candidate_runs_when_auto_draft_and_no_duplicates() -> None:
    session = MagicMock()
    candidate = _candidate()
    session.get.return_value = candidate
    session.exec.side_effect = [MagicMock(all=lambda: []), MagicMock(first=lambda: None)]

    artifact_store = MagicMock()
    artifact_store.get_text_utf8.return_value = json.dumps(
        {"evidence_ready": True, "recommended_action": "auto_draft", "urgency": "same_day"}
    )

    result = prepare_candidate(session, artifact_store, artifact_id="art_candidate")

    assert result["should_run"] is True
    assert result["candidate_id"] == "art_candidate"
    assert result["story_key"] == "budget-cut:2026-03"


def test_prepare_candidate_skips_when_active_draft_exists() -> None:
    session = MagicMock()
    candidate = _candidate()
    session.get.return_value = candidate
    session.exec.side_effect = [
        MagicMock(all=lambda: []),
        MagicMock(first=lambda: Artifact(
            id="art_draft",
            title="Existing draft",
            content_type=ContentType.STORY_DRAFT,
            stage=Stage.DRAFT,
            story_key="budget-cut:2026-03",
            content_uri="s3://bucket/artifacts/draft/x/art_draft",
        )),
    ]

    artifact_store = MagicMock()
    artifact_store.get_text_utf8.return_value = json.dumps(
        {"evidence_ready": True, "recommended_action": "priority_draft"}
    )

    result = prepare_candidate(session, artifact_store, artifact_id="art_candidate")

    assert result["should_run"] is False
    assert result["skip_reason"] == "active_draft_exists"


def test_record_editor_run_appends_assignment_artifacts_out() -> None:
    session = MagicMock()
    assignment = Assignment(id="asg_1", type="story", query_text="Budget cut", artifacts_out=["art_old"])
    session.get.return_value = assignment

    result = record_editor_run(
        session,
        candidate_id="art_candidate",
        story_key="budget-cut:2026-03",
        assignment_id="asg_1",
        written_artifact_ids=["art_new"],
    )

    assert result["written_artifact_ids"] == ["art_new"]
    assert assignment.artifacts_out == ["art_old", "art_new"]
    session.commit.assert_called_once()
