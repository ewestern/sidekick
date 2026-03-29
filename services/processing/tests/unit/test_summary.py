"""Summary enrichment processor tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ContentType, ArtifactStatus, Stage
from sidekick.processing.processors.schemas import SummaryOutput, SummarySourceReference
from sidekick.processing.processors.summary import process_to_summary


def _make_doc_text_artifact(**overrides) -> Artifact:
    defaults = dict(
        id="art_doctext",
        content_type=ContentType.DOCUMENT_TEXT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="text/plain",
        beat="government:city-council",
        geo="us:ca:tulare:visalia",
        source_id="src_x",
        event_group="eg_1",
        period_start=None,
        period_end=None,
        assignment_id=None,
        entities=[{"type": "pdf-extraction", "method": "pypdf-text-layer"}],
    )
    defaults.update(overrides)
    return Artifact(**defaults)  # type: ignore[arg-type]


def _make_summary_output() -> SummaryOutput:
    return SummaryOutput(
        headline="City council approves zoning ordinance",
        summary="The Springfield city council approved...",
        key_developments=["Ordinance 2026-14 passed 5-2"],
        topics=["zoning", "city-council"],
        date_references=["2026-03-11"],
        source_references=[SummarySourceReference(label="meeting transcript")],
    )


def _make_registry(skills: list[str] | None = None) -> MagicMock:
    registry = MagicMock()
    registry.resolve.return_value = MagicMock(
        model="claude-sonnet-4-6",
        prompts={"system": "You are..."},
        skills=skills or [],
    )
    return registry


def test_process_to_summary_writes_summary_artifact():
    row = _make_doc_text_artifact()
    sibling = Artifact(
        id="art_entity_1",
        title="March Agenda entities",
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="application/json",
        derived_from=["art_doctext"],
        entities=[{"name": "Jane Smith", "type": "person"}],
        topics=["housing", "land-use"],
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.side_effect = [
        "Agenda text...",
        json.dumps({"entities": [{"name": "Jane Smith"}], "topics": ["housing", "land-use"]}),
    ]
    store.write_with_bytes.return_value = "art_summary_1"
    store.query.return_value = [sibling]
    store._engine = None

    registry = _make_registry()
    summary_result = _make_summary_output()

    with patch("sidekick.processing.processors.summary.create_deep_agent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.invoke.return_value = {
            "structured_response": summary_result}

        result_id = process_to_summary("art_doctext", store, registry)

    assert result_id == "art_summary_1"
    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out_artifact = args[0]
    body_bytes = args[1]

    assert out_artifact.content_type == "summary"
    assert out_artifact.stage == "processed"
    assert out_artifact.media_type == "text/markdown"
    assert out_artifact.derived_from == ["art_doctext", "art_entity_1"]
    assert out_artifact.topics == ["housing", "land-use"]
    assert kwargs.get("object_content_type") == "text/markdown"

    body = body_bytes.decode("utf-8")
    assert "# City council approves zoning ordinance" in body
    assert "## Key Developments" in body
    assert "## Sources" in body
    assert "art_doctext" in body
    assert "art_entity_1" in body


def test_process_to_summary_passes_skills_to_agent():
    row = _make_doc_text_artifact()
    sibling = Artifact(
        id="art_entity_1",
        title="March Agenda entities",
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="application/json",
        derived_from=["art_doctext"],
        entities=[{"name": "Jane Smith", "type": "person"}],
        topics=["housing", "land-use"],
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.side_effect = ["text", json.dumps({"entities": [], "topics": []})]
    store.write_with_bytes.return_value = "art_s"
    store.query.return_value = [sibling]
    store._engine = None

    registry = _make_registry(skills=["news-values", "document-assessment"])

    with (
        patch("sidekick.processing.processors.summary.build_skill_store") as mock_build,
        patch("sidekick.processing.processors.summary.create_deep_agent") as mock_agent_cls,
    ):
        mock_build.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.invoke.return_value = {
            "structured_response": _make_summary_output()}

        process_to_summary("art_doctext", store, registry,
                           skills_dir=Path("/fake/skills"))

    mock_build.assert_called_once_with(
        ["news-values", "document-assessment"], Path("/fake/skills"))
    _, kwargs = mock_agent_cls.call_args
    assert kwargs["skills"] == ["/skills/"]


def test_process_to_summary_copies_context_fields():
    row = _make_doc_text_artifact()
    sibling = Artifact(
        id="art_entity_1",
        title="March Agenda entities",
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="application/json",
        derived_from=["art_doctext"],
        entities=[{"name": "Jane Smith", "type": "person"}],
        topics=["housing", "land-use"],
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.side_effect = ["text", json.dumps({"entities": [], "topics": []})]
    store.write_with_bytes.return_value = "art_s"
    store.query.return_value = [sibling]
    store._engine = None

    with patch("sidekick.processing.processors.summary.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_summary_output()}
        process_to_summary("art_doctext", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    assert out.beat == "government:city-council"
    assert out.geo == "us:ca:tulare:visalia"
    assert out.source_id == "src_x"
    assert out.event_group == "eg_1"


def test_process_to_summary_sets_topics_from_sibling_entity_extract():
    row = _make_doc_text_artifact()
    sibling = Artifact(
        id="art_entity_1",
        title="March Agenda entities",
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="application/json",
        derived_from=["art_doctext"],
        entities=[{"name": "Jane Smith", "type": "person"}],
        topics=["housing", "land-use"],
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.side_effect = ["text", json.dumps({"entities": [], "topics": []})]
    store.write_with_bytes.return_value = "art_s"
    store.query.return_value = [sibling]
    store._engine = None

    with patch("sidekick.processing.processors.summary.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_summary_output()}
        process_to_summary("art_doctext", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    assert out.topics == ["housing", "land-use"]


def test_process_to_summary_records_provenance_via_created_by():
    row = _make_doc_text_artifact()
    sibling = Artifact(
        id="art_entity_1",
        title="March Agenda entities",
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="application/json",
        derived_from=["art_doctext"],
        entities=[{"name": "Jane Smith", "type": "person"}],
        topics=["housing", "land-use"],
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.side_effect = ["text", json.dumps({"entities": [], "topics": []})]
    store.write_with_bytes.return_value = "art_s"
    store.query.return_value = [sibling]
    store._engine = None

    with patch("sidekick.processing.processors.summary.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_summary_output()}
        process_to_summary("art_doctext", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    assert out.created_by == "processor:summary"
    enrichment_entities = [e for e in (
        out.entities or []) if e.get("type") == "llm-enrichment"]
    assert len(enrichment_entities) == 0


def test_process_to_summary_requires_sibling_entity_extract():
    row = _make_doc_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.query.return_value = []
    store._engine = None

    with pytest.raises(ValueError, match="requires sibling entity-extract"):
        process_to_summary("art_doctext", store, _make_registry())


def test_process_to_summary_reads_sibling_entity_extract_for_entities():
    row = _make_doc_text_artifact()
    sibling = Artifact(
        id="art_entity_1",
        title="March Agenda entities",
        content_type=ContentType.ENTITY_EXTRACT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="application/json",
        derived_from=["art_doctext"],
        entities=[{"name": "Jane Smith", "type": "person"}],
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.side_effect = ["text", json.dumps({"entities": [{"name": "Jane Smith"}]})]
    store.write_with_bytes.return_value = "art_s"
    store.query.return_value = [sibling]
    store._engine = None

    with patch("sidekick.processing.processors.summary.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_summary_output()}
        process_to_summary("art_doctext", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    assert out.entities == [{"name": "Jane Smith", "type": "person"}]
