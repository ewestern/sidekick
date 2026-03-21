"""Entity extraction enrichment processor tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.models import Artifact
from sidekick.processing.processors.entity_extract import process_to_entity_extract
from sidekick.processing.processors.schemas import Entity, EntityExtractionOutput
from sidekick.processing.router import UnsupportedProcessingError


def _make_transcript_artifact(**overrides) -> Artifact:
    defaults = dict(
        id="art_transcript",
        content_type="transcript-clean",
        stage="processed",
        status="active",
        media_type="text/plain",
        beat="government:city_council",
        geo="us:ca:tulare:visalia",
        source_id="src_y",
        event_group="eg_2",
        entities=[],
    )
    defaults.update(overrides)
    return Artifact(**defaults)


def _make_entity_output() -> EntityExtractionOutput:
    return EntityExtractionOutput(
        entities=[
            Entity(name="Jane Smith", type="person", role="council-member"),
            Entity(name="Springfield City Hall", type="place"),
        ],
        financial_figures=[{"description": "FY2027 budget", "amount": "$4.2M", "context": "proposed"}],
        motions_or_votes=[{"description": "Approve Ordinance 2026-14", "result": "passed", "vote_tally": "5-2"}],
    )


def test_process_to_entity_extract_writes_entity_extract_artifact():
    row = _make_transcript_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "Council meeting transcript..."
    store.write_with_bytes.return_value = "art_entity_1"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "Extract entities."})

    entity_result = _make_entity_output()

    with patch("sidekick.processing.processors.entity_extract.ChatAnthropic") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value.invoke.return_value = entity_result

        result_id = process_to_entity_extract("art_transcript", store, registry)

    assert result_id == "art_entity_1"
    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out_artifact = args[0]
    body_bytes = args[1]

    assert out_artifact.content_type == "entity-extract"
    assert out_artifact.stage == "processed"
    assert out_artifact.media_type == "application/json"
    assert out_artifact.derived_from == ["art_transcript"]
    assert kwargs.get("object_content_type") == "application/json"

    body = json.loads(body_bytes.decode("utf-8"))
    assert len(body["entities"]) == 2
    assert body["entities"][0]["name"] == "Jane Smith"
    assert body["motions_or_votes"][0]["result"] == "passed"


def test_process_to_entity_extract_populates_entities_on_artifact():
    row = _make_transcript_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "sys"})

    with patch("sidekick.processing.processors.entity_extract.ChatAnthropic") as mock_llm_cls:
        mock_llm_cls.return_value.with_structured_output.return_value.invoke.return_value = _make_entity_output()
        process_to_entity_extract("art_transcript", store, registry)

    out = store.write_with_bytes.call_args[0][0]
    # Entities from LLM output are serialized into the artifact entities list
    entity_names = [e.get("name") for e in (out.entities or []) if "name" in e]
    assert "Jane Smith" in entity_names
    assert "Springfield City Hall" in entity_names


def test_process_to_entity_extract_records_llm_enrichment_entity():
    row = _make_transcript_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "sys"})

    with patch("sidekick.processing.processors.entity_extract.ChatAnthropic") as mock_llm_cls:
        mock_llm_cls.return_value.with_structured_output.return_value.invoke.return_value = _make_entity_output()
        process_to_entity_extract("art_transcript", store, registry)

    out = store.write_with_bytes.call_args[0][0]
    enrichment_entities = [e for e in (out.entities or []) if e.get("type") == "llm-enrichment"]
    assert len(enrichment_entities) == 1
    assert enrichment_entities[0]["processor"] == "entity-extract"


def test_process_to_entity_extract_rejects_non_text_processed():
    row = Artifact(
        id="art_summary",
        content_type="summary",
        stage="processed",
        status="active",
        media_type="application/json",
    )
    store = MagicMock()
    store.read_row.return_value = row
    registry = MagicMock()

    with pytest.raises(UnsupportedProcessingError, match="content_type"):
        process_to_entity_extract("art_summary", store, registry)


def test_process_to_entity_extract_copies_context_fields():
    row = _make_transcript_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_e"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "sys"})

    with patch("sidekick.processing.processors.entity_extract.ChatAnthropic") as mock_llm_cls:
        mock_llm_cls.return_value.with_structured_output.return_value.invoke.return_value = _make_entity_output()
        process_to_entity_extract("art_transcript", store, registry)

    out = store.write_with_bytes.call_args[0][0]
    assert out.beat == "government:city_council"
    assert out.geo == "us:ca:tulare:visalia"
    assert out.source_id == "src_y"
    assert out.event_group == "eg_2"
