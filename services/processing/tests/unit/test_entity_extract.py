"""Entity extraction enrichment processor tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import (
    ArtifactStatus,
    ContentType,
    Stage,
)
from sidekick.processing.processors.entity_extract import process_to_entity_extract
from sidekick.processing.processors.schemas import Entity, EntityExtractionOutput


def _make_document_text_artifact(**overrides) -> Artifact:
    defaults = dict(
        id="art_text",
        content_type=ContentType.DOCUMENT_TEXT,
        stage=Stage.PROCESSED,
        status=ArtifactStatus.ACTIVE,
        media_type="text/plain",
        beat="government:city-council",
        geo="us:ca:tulare:visalia",
        source_id="src_y",
        event_group="eg_2",
        entities=[],
    )
    defaults.update(overrides)
    return Artifact(**defaults)  # type: ignore[arg-type]


def _make_entity_output() -> EntityExtractionOutput:
    return EntityExtractionOutput(
        entities=[
            Entity(name="Jane Smith", type="person", role="council-member"),
            Entity(name="Springfield City Hall", type="place"),
        ],
        topics=["zoning", "budget"],
        financial_figures=[{"description": "FY2027 budget",
                            "amount": "$4.2M", "context": "proposed"}],
        motions_or_votes=[{"description": "Approve Ordinance 2026-14",
                           "result": "passed", "vote_tally": "5-2"}],
    )


def _make_registry(skills: list[str] | None = None) -> MagicMock:
    registry = MagicMock()
    registry.resolve.return_value = MagicMock(
        model="claude-sonnet-4-6",
        prompts={"system": "Extract entities."},
        skills=skills or [],
    )
    return registry


def test_process_to_entity_extract_writes_entity_extract_artifact():
    row = _make_document_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "Council meeting transcript..."
    store.write_with_bytes.return_value = "art_entity_1"

    entity_result = _make_entity_output()

    with patch("sidekick.processing.processors.entity_extract.create_deep_agent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.invoke.return_value = {"structured_response": entity_result}

        result_id = process_to_entity_extract(
            "art_text", store, _make_registry())

    assert result_id == "art_entity_1"
    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out_artifact = args[0]
    body_bytes = args[1]

    assert out_artifact.content_type == "entity-extract"
    assert out_artifact.stage == "processed"
    assert out_artifact.media_type == "application/json"
    assert out_artifact.derived_from == ["art_text"]
    assert kwargs.get("object_content_type") == "application/json"

    body = json.loads(body_bytes.decode("utf-8"))
    assert len(body["entities"]) == 2
    assert body["entities"][0]["name"] == "Jane Smith"
    assert body["topics"] == ["zoning", "budget"]
    assert body["motions_or_votes"][0]["result"] == "passed"


def test_process_to_entity_extract_passes_skills_to_agent():
    row = _make_document_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    registry = _make_registry(
        skills=["entity-and-actor-tracking", "document-assessment"])

    with (
        patch("sidekick.processing.processors.entity_extract.build_skill_store") as mock_build,
        patch("sidekick.processing.processors.entity_extract.create_deep_agent") as mock_agent_cls,
    ):
        mock_build.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.invoke.return_value = {
            "structured_response": _make_entity_output()}

        process_to_entity_extract(
            "art_text", store, registry, skills_dir=Path("/fake/skills"))

    mock_build.assert_called_once_with(
        ["entity-and-actor-tracking",
            "document-assessment"], Path("/fake/skills")
    )
    _, kwargs = mock_agent_cls.call_args
    assert kwargs["skills"] == ["/skills/"]


def test_process_to_entity_extract_populates_entities_on_artifact():
    row = _make_document_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    with patch("sidekick.processing.processors.entity_extract.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_entity_output()}
        process_to_entity_extract("art_text", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    entity_names = [e.get("name") for e in (out.entities or []) if "name" in e]
    assert "Jane Smith" in entity_names
    assert "Springfield City Hall" in entity_names
    assert out.topics == ["zoning", "budget"]


def test_process_to_entity_extract_records_provenance_via_created_by():
    row = _make_document_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    with patch("sidekick.processing.processors.entity_extract.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_entity_output()}
        process_to_entity_extract("art_text", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    assert out.created_by == "processor:entity-extract"
    enrichment_entities = [e for e in (
        out.entities or []) if e.get("type") == "llm-enrichment"]
    assert len(enrichment_entities) == 0


def test_process_to_entity_extract_copies_context_fields():
    row = _make_document_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    with patch("sidekick.processing.processors.entity_extract.create_deep_agent") as mock_agent_cls:
        mock_agent_cls.return_value.invoke.return_value = {
            "structured_response": _make_entity_output()}
        process_to_entity_extract("art_text", store, _make_registry())

    out = store.write_with_bytes.call_args[0][0]
    assert out.beat == "government:city-council"
    assert out.geo == "us:ca:tulare:visalia"
    assert out.source_id == "src_y"
    assert out.event_group == "eg_2"
