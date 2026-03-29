"""Unit tests for editor agent tools."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from sidekick.core.models import Artifact, Source
from sidekick.core.vocabulary import ContentType, SourceTier, Stage

from sidekick.editor.tools import (
    make_load_story_candidate_context,
    make_write_story_draft,
)


def _candidate() -> Artifact:
    return Artifact(
        id="art_candidate",
        title="Budget cut candidate",
        content_type=ContentType.STORY_CANDIDATE,
        stage=Stage.ANALYSIS,
        media_type="application/json",
        derived_from=["art_brief"],
        beat="government:city-council",
        geo="us:ca:shasta:redding",
        story_key="budget-cut:2026-03",
        content_uri="s3://bucket/artifacts/analysis/x/art_candidate",
        created_by="beat-agent",
    )


def test_load_story_candidate_context_includes_payload_and_lineage() -> None:
    store = MagicMock()
    candidate = _candidate()
    brief = Artifact(
        id="art_brief",
        title="Budget brief",
        content_type=ContentType.BEAT_BRIEF,
        stage=Stage.ANALYSIS,
        source_id="src_1",
        content_uri="s3://bucket/artifacts/analysis/x/art_brief",
    )
    summary = Artifact(
        id="art_summary",
        title="Budget summary",
        content_type=ContentType.SUMMARY,
        stage=Stage.PROCESSED,
        source_id="src_1",
        content_uri="s3://bucket/artifacts/processed/x/art_summary",
    )
    store.read.side_effect = [candidate, brief]
    store.get_text_utf8.side_effect = [
        json.dumps({"headline": "Budget cut", "recommended_action": "priority_draft"}),
        "Brief narrative",
        "Summary narrative",
    ]
    store.lineage.return_value = [summary]

    session = MagicMock()
    session.get.return_value = Source(
        id="src_1",
        name="City Council",
        source_tier=SourceTier.PRIMARY,
    )
    session.__enter__.return_value = session
    session.__exit__.return_value = False

    with patch("sidekick.editor.tools.Session", return_value=session), patch(
        "sidekick.editor.tools.create_engine", return_value=MagicMock()
    ):
        tool = make_load_story_candidate_context(store, "postgresql://unused", [])
        result = tool.invoke({"candidate_id": "art_candidate"})

    assert "story-candidate" in result
    assert "recommended_action" in result
    assert "source_tier=primary" in result
    assert "Brief narrative" in result
    assert "Summary narrative" in result


def test_write_story_draft_copies_story_key_and_candidate_linkage() -> None:
    store = MagicMock()
    store.write_with_bytes.return_value = "art_draft"
    candidate = _candidate()
    store.read.return_value = candidate
    store.get_text_utf8.return_value = json.dumps({"recommended_action": "auto_draft"})

    written_ids: list[str] = []
    tool = make_write_story_draft(store, written_ids, "editor-agent")
    result = tool.invoke(
        {
            "candidate_id": "art_candidate",
            "headline": "Council weighs sharp cuts",
            "dek": "A proposed 20% reduction would reshape city services.",
            "narrative": "The council reviewed a budget framework on Tuesday.",
            "sourcing_notes": "Grounded in the meeting packet and official summary.",
        }
    )

    assert result == "art_draft"
    assert written_ids == ["art_draft"]
    artifact: Artifact = store.write_with_bytes.call_args[0][0]
    assert artifact.content_type == ContentType.STORY_DRAFT
    assert artifact.stage == Stage.DRAFT
    assert artifact.story_key == "budget-cut:2026-03"
    assert artifact.derived_from == ["art_candidate"]
    body = json.loads(store.write_with_bytes.call_args[0][1])
    assert body["candidate_id"] == "art_candidate"
