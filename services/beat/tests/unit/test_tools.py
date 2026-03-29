# type: ignore
"""Unit tests for beat agent tools.

All artifact store calls are mocked — no external services required.
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ArtifactStatus, ContentType, Stage, BeatIdentifier, GeoIdentifier

from sidekick.beat.scope import DateWindowScope, EventGroupScope
from sidekick.beat.tools import (
    make_create_research_assignment,
    make_query_artifacts,
    make_write_beat_brief,
    make_write_story_candidate,
)

BEAT = "government:city-council"
GEO = "us:ca:shasta:redding"
EVENT_GROUP = "shasta-bos:2026-03-25"
DATE_SCOPE = DateWindowScope(since=date(2026, 3, 1), until=date(2026, 3, 31))
EVENT_SCOPE = EventGroupScope(event_group=EVENT_GROUP)


def _make_artifact(
    artifact_id: str,
    content_type: ContentType,
    period_start: date | None = date(2026, 3, 11),
    event_group: str | None = None,
) -> Artifact:
    return Artifact(
        id=artifact_id,
        title="March Agenda",
        content_type=content_type,
        stage=Stage.PROCESSED,
        media_type="application/json",
        beat=BEAT,
        geo=GEO,
        period_start=period_start,
        event_group=event_group,
        created_by="test",
    )


class TestQueryArtifactsDateWindow:
    def test_returns_formatted_text_and_records_ids(self):
        store = MagicMock()
        summary_row = _make_artifact("art_s1", ContentType.SUMMARY)
        entity_row = _make_artifact("art_e1", ContentType.ENTITY_EXTRACT)
        store.query.return_value = [summary_row, entity_row]
        store.get_text_utf8.side_effect = [
            "# Summary\n\nSummary text",
            json.dumps({
                "entities": [{"name": "Jane Smith", "type": "person"}],
                "topics": ["budget"],
                "financial_figures": [{"description": "FY2027 budget", "amount": "$4.2M"}],
                "motions_or_votes": [{"description": "Approve Ordinance 2026-14", "result": "passed"}],
            }),
        ]

        derived_ids: list[str] = []
        tool = make_query_artifacts(store, BEAT, GEO, DATE_SCOPE, derived_ids)
        result = tool.invoke({}) # type: ignore

        assert "art_s1" in result and "Summary text" in result
        assert "art_e1" in result and "Jane Smith (person)" in result
        assert "FY2027 budget: $4.2M" in result
        assert derived_ids == ["art_s1", "art_e1"]
        filters = store.query.call_args.kwargs["filters"]
        assert filters["beat"] == BEAT
        assert filters["geo"] == GEO
        assert filters["period_start_gte"] == DATE_SCOPE.since
        assert filters["period_start_lte"] == DATE_SCOPE.until

    def test_broader_history_drops_current_scope_date_filters(self):
        store = MagicMock()
        in_range = _make_artifact("art_in", ContentType.SUMMARY, period_start=date(2026, 3, 15))
        older = _make_artifact("art_old", ContentType.SUMMARY, period_start=date(2026, 2, 1))
        store.query.return_value = [in_range, older]
        store.get_text_utf8.return_value = "text"

        derived_ids: list[str] = []
        tool = make_query_artifacts(store, BEAT, GEO, DATE_SCOPE, derived_ids)
        result = tool.invoke({"current_scope_only": False})

        assert "art_in" in result
        assert "art_old" in result
        filters = store.query.call_args.kwargs["filters"]
        assert "period_start_gte" not in filters
        assert "period_start_lte" not in filters

    def test_returns_message_when_no_results(self):
        store = MagicMock()
        store.query.return_value = []

        derived_ids: list[str] = []
        tool = make_query_artifacts(store, BEAT, GEO, DATE_SCOPE, derived_ids)
        result = tool.invoke({})

        assert "No processed artifacts found" in result
        assert derived_ids == []


class TestQueryArtifactsEventGroup:
    def test_queries_by_event_group_not_beat_geo(self):
        store = MagicMock()
        row = _make_artifact("art_s1", ContentType.SUMMARY,
                             event_group=EVENT_GROUP)
        store.query.return_value = [row]
        store.get_text_utf8.return_value = "content"

        derived_ids: list[str] = []
        tool = make_query_artifacts(store, BEAT, GEO, EVENT_SCOPE, derived_ids)
        tool.invoke({})

        # Confirm the query used event_group, not beat/geo
        first_call_filters = store.query.call_args_list[0][1]["filters"]
        assert first_call_filters["event_group"] == EVENT_GROUP
        assert first_call_filters["beat"] == BEAT
        assert first_call_filters["geo"] == GEO

    def test_lineage_rows_are_included_and_recorded(self):
        store = MagicMock()
        row = _make_artifact("art_s1", ContentType.SUMMARY, event_group=EVENT_GROUP)
        parent = _make_artifact("art_parent", ContentType.DOCUMENT_TEXT, event_group=EVENT_GROUP)
        store.query.return_value = [row]
        store.lineage.return_value = [parent]
        store.get_text_utf8.side_effect = ["summary", "parent text"]

        derived_ids: list[str] = []
        tool = make_query_artifacts(store, BEAT, GEO, EVENT_SCOPE, derived_ids)
        result = tool.invoke({"include_lineage_from": ["art_s1"]})

        assert "art_s1" in derived_ids
        assert "art_parent" in derived_ids
        assert "match=lineage:up" in result

    def test_uses_semantic_query_when_requested(self):
        store = MagicMock()
        row = _make_artifact("art_sem", ContentType.SUMMARY)
        store.semantic_query_text.return_value = [row]
        store.get_text_utf8.return_value = "semantic match"

        derived_ids: list[str] = []
        tool = make_query_artifacts(store, BEAT, GEO, DATE_SCOPE, derived_ids)
        result = tool.invoke({"mode": "semantic", "query_text": "jail medical contract"})

        assert "match=semantic" in result
        store.semantic_query_text.assert_called_once()
        assert derived_ids == ["art_sem"]


class TestWriteBeatBrief:
    def test_date_window_scope_sets_period_not_event_group(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_new"

        tool = make_write_beat_brief(store, BEAT, GEO, DATE_SCOPE, [
                                     "art_s1"], [], "beat-agent")
        tool.invoke({
            "headline": "Council approves budget",
            "narrative": "The council voted 5-2.",
            "key_developments": ["Budget passed"],
            "topics": ["budget"],
        })

        artifact: Artifact = store.write_with_bytes.call_args[0][0]
        assert artifact.period_start == DATE_SCOPE.since
        assert artifact.period_end == DATE_SCOPE.until
        assert artifact.event_group is None

    def test_event_group_scope_sets_event_group_not_period(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_new"

        tool = make_write_beat_brief(store, BEAT, GEO, EVENT_SCOPE, [
                                     "art_s1"], [], "beat-agent")
        tool.invoke({
            "headline": "Council meeting brief",
            "narrative": "The March 25 meeting...",
            "key_developments": ["Zoning approved"],
            "topics": ["zoning"],
        })

        artifact: Artifact = store.write_with_bytes.call_args[0][0]
        assert artifact.event_group == EVENT_GROUP
        assert artifact.period_start is None
        assert artifact.period_end is None

    def test_metadata_is_correct(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_new"
        written_ids: list[str] = []

        tool = make_write_beat_brief(store, BEAT, GEO, DATE_SCOPE, [
                                     "art_s1", "art_e1"], written_ids, "beat-agent")
        result = tool.invoke({
            "headline": "Headline",
            "narrative": "Narrative.",
            "key_developments": ["Item"],
            "topics": ["zoning"],
        })

        assert result == "art_new"
        assert "art_new" in written_ids
        artifact: Artifact = store.write_with_bytes.call_args[0][0]
        assert artifact.content_type == ContentType.BEAT_BRIEF
        assert artifact.stage == Stage.ANALYSIS
        assert artifact.beat == BEAT
        assert artifact.geo == GEO
        assert artifact.derived_from == ["art_s1", "art_e1"]
        assert artifact.created_by == "beat-agent"

    def test_body_is_valid_json(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_x"

        tool = make_write_beat_brief(store, BEAT, GEO, DATE_SCOPE, [
                                     "art_s1"], [], "beat-agent")
        tool.invoke({
            "headline": "Headline",
            "narrative": "Narrative.",
            "key_developments": ["Item 1"],
            "topics": ["zoning"],
        })

        body = json.loads(store.write_with_bytes.call_args[0][1])
        assert body["headline"] == "Headline"
        assert body["key_developments"] == ["Item 1"]

    def test_supersedes_prior_brief_when_requested(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_new"

        tool = make_write_beat_brief(store, BEAT, GEO, DATE_SCOPE, ["art_s1"], [], "beat-agent")
        tool.invoke({
            "headline": "Headline",
            "narrative": "Narrative.",
            "key_developments": ["Item 1"],
            "topics": ["zoning"],
            "supersede_brief_id": "art_old",
        })

        store.patch.assert_called_once_with("art_old", superseded_by="art_new")


class TestWriteStoryCandidate:
    def test_date_window_scope_sets_period(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_candidate"
        store.query.return_value = []

        tool = make_write_story_candidate(store, BEAT, GEO, DATE_SCOPE, [
                                          "art_s1"], [], "beat-agent")
        tool.invoke({
            "story_key": "budget-cut:2026-03",
            "headline": "Council proposes major budget cut",
            "why_now": "The proposal reduces department spending by 20%.",
            "development_type": "impact",
            "time_sensitivity": "timely",
            "urgency": "same_day",
            "evidence_ready": True,
            "primary_support_present": True,
            "novelty_score": 4,
            "impact_score": 5,
            "confidence_score": 4,
        })

        artifact: Artifact = store.write_with_bytes.call_args[0][0]
        assert artifact.period_start == DATE_SCOPE.since
        assert artifact.event_group is None

    def test_event_group_scope_sets_event_group(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_candidate"
        store.query.return_value = []

        tool = make_write_story_candidate(store, BEAT, GEO, EVENT_SCOPE, [
                                          "art_s1"], [], "beat-agent")
        tool.invoke({
            "story_key": "major-vote",
            "headline": "Council approves disputed zoning vote",
            "why_now": "The commission approved the project after public opposition.",
            "development_type": "decision",
            "time_sensitivity": "breaking",
            "urgency": "immediate",
            "evidence_ready": True,
            "primary_support_present": True,
            "novelty_score": 5,
            "impact_score": 4,
            "confidence_score": 4,
        })

        artifact: Artifact = store.write_with_bytes.call_args[0][0]
        assert artifact.event_group == EVENT_GROUP
        assert artifact.period_start is None

    def test_metadata_and_body(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_candidate"
        store.query.return_value = []
        written_ids: list[str] = []

        tool = make_write_story_candidate(store, BEAT, GEO, DATE_SCOPE, [
                                          "art_s1"], written_ids, "beat-agent")
        result = tool.invoke({
            "story_key": "budget-cut:2026-03",
            "headline": "Unexpected 20% cut",
            "why_now": "The city manager proposed an unexpected 20% cut.",
            "development_type": "impact",
            "time_sensitivity": "timely",
            "urgency": "same_day",
            "evidence_ready": True,
            "primary_support_present": True,
            "novelty_score": 4,
            "impact_score": 5,
            "confidence_score": 4,
            "recommended_action": "priority_draft",
            "reason": "Large public-service impact.",
            "topics": ["budget"],
        })

        assert result == "art_candidate"
        assert "art_candidate" in written_ids
        artifact: Artifact = store.write_with_bytes.call_args[0][0]
        assert artifact.content_type == ContentType.STORY_CANDIDATE
        assert artifact.stage == Stage.ANALYSIS
        assert artifact.story_key == "budget-cut:2026-03"
        body = json.loads(store.write_with_bytes.call_args[0][1])
        assert body["headline"] == "Unexpected 20% cut"
        assert body["recommended_action"] == "priority_draft"
        assert body["supporting_artifact_count"] == 1

    def test_existing_active_draft_downgrades_auto_draft_to_queue(self):
        store = MagicMock()
        store.write_with_bytes.return_value = "art_candidate"
        store.query.side_effect = [
            [Artifact(id="art_draft", title="Draft", content_type=ContentType.STORY_DRAFT, stage=Stage.DRAFT, story_key="budget-cut:2026-03", content_uri="s3://bucket/x")],
            [],
        ]

        tool = make_write_story_candidate(store, BEAT, GEO, DATE_SCOPE, [
                                          "art_s1"], [], "beat-agent")
        tool.invoke({
            "story_key": "budget-cut:2026-03",
            "headline": "Unexpected 20% cut",
            "why_now": "The city manager proposed an unexpected 20% cut.",
            "development_type": "impact",
            "time_sensitivity": "timely",
            "urgency": "same_day",
            "evidence_ready": True,
            "primary_support_present": True,
            "novelty_score": 4,
            "impact_score": 5,
            "confidence_score": 4,
            "recommended_action": "auto_draft",
        })

        body = json.loads(store.write_with_bytes.call_args[0][1])
        assert body["recommended_action"] == "queue"


class TestCreateResearchAssignment:
    def test_creates_assignment_with_context_payload(self):
        assignment_store = MagicMock()
        assignment_store.list_open.return_value = []
        assignment_store.create.return_value.id = "asg_123"
        derived_ids = ["art_s1", "art_e1"]

        tool = make_create_research_assignment(
            assignment_store,
            BEAT,
            GEO,
            EVENT_SCOPE,
            derived_ids,
            "beat-agent",
        )
        result = tool.invoke({
            "query_text": "Find prior jail medical contract values and vendor history.",
            "topic": "jail-medical-contract",
            "reason": "baseline",
            "entity_names": ["Wellpath"],
            "target_document_types": ["contracts", "agendas"],
        })

        assert result == "asg_123"
        kwargs = assignment_store.create.call_args.kwargs
        assert kwargs["assignment_type"] == "research"
        assert kwargs["artifacts_in"] == derived_ids
        assert kwargs["query_params"]["event_group"] == EVENT_GROUP
        assert kwargs["query_params"]["reason"] == "baseline"

    def test_reuses_existing_matching_assignment(self):
        assignment_store = MagicMock()
        assignment_store.list_open.return_value = [
            MagicMock(
                id="asg_existing",
                query_params={
                    "reason": "baseline",
                    "topic": "jail-medical-contract",
                    "entity_names": ["Wellpath"],
                    "target_document_types": ["contracts"],
                },
            )
        ]
        tool = make_create_research_assignment(
            assignment_store,
            BEAT,
            GEO,
            EVENT_SCOPE,
            ["art_s1"],
            "beat-agent",
        )
        result = tool.invoke({
            "query_text": "Find prior jail medical contract values.",
            "topic": "jail-medical-contract",
            "reason": "baseline",
            "entity_names": ["Wellpath"],
            "target_document_types": ["contracts"],
        })

        assert result == "asg_existing"
        assignment_store.create.assert_not_called()
