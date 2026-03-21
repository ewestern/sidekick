"""Summary enrichment processor tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.models import Artifact
from sidekick.processing.processors.schemas import SummaryOutput
from sidekick.processing.processors.summary import process_to_summary
from sidekick.processing.router import UnsupportedProcessingError


def _make_doc_text_artifact(**overrides) -> Artifact:
    defaults = dict(
        id="art_doctext",
        content_type="document-text",
        stage="processed",
        status="active",
        media_type="text/plain",
        beat="government:city_council",
        geo="us:ca:tulare:visalia",
        source_id="src_x",
        event_group="eg_1",
        period_start=None,
        period_end=None,
        assignment_id=None,
        entities=[{"type": "pdf-extraction", "method": "pypdf-text-layer"}],
    )
    defaults.update(overrides)
    return Artifact(**defaults)


def _make_summary_output() -> SummaryOutput:
    return SummaryOutput(
        headline="City council approves zoning ordinance",
        summary="The Springfield city council approved...",
        key_developments=["Ordinance 2026-14 passed 5-2"],
        topics=["zoning", "city-council"],
        date_references=["2026-03-11"],
    )


def test_process_to_summary_writes_summary_artifact():
    row = _make_doc_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "Agenda text..."
    store.write_with_bytes.return_value = "art_summary_1"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "You are..."})

    summary_result = _make_summary_output()

    with patch("sidekick.processing.processors.summary.ChatAnthropic") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value.invoke.return_value = summary_result

        result_id = process_to_summary("art_doctext", store, registry)

    assert result_id == "art_summary_1"
    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out_artifact = args[0]
    body_bytes = args[1]

    assert out_artifact.content_type == "summary"
    assert out_artifact.stage == "processed"
    assert out_artifact.media_type == "application/json"
    assert out_artifact.derived_from == ["art_doctext"]
    assert kwargs.get("object_content_type") == "application/json"

    body = json.loads(body_bytes.decode("utf-8"))
    assert body["headline"] == "City council approves zoning ordinance"
    assert body["topics"] == ["zoning", "city-council"]


def test_process_to_summary_copies_context_fields():
    row = _make_doc_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_s"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "sys"})

    with patch("sidekick.processing.processors.summary.ChatAnthropic") as mock_llm_cls:
        mock_llm_cls.return_value.with_structured_output.return_value.invoke.return_value = _make_summary_output()
        process_to_summary("art_doctext", store, registry)

    out = store.write_with_bytes.call_args[0][0]
    assert out.beat == "government:city_council"
    assert out.geo == "us:ca:tulare:visalia"
    assert out.source_id == "src_x"
    assert out.event_group == "eg_1"


def test_process_to_summary_sets_topics_from_llm_output():
    row = _make_doc_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_s"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "sys"})

    with patch("sidekick.processing.processors.summary.ChatAnthropic") as mock_llm_cls:
        mock_llm_cls.return_value.with_structured_output.return_value.invoke.return_value = _make_summary_output()
        process_to_summary("art_doctext", store, registry)

    out = store.write_with_bytes.call_args[0][0]
    assert out.topics == ["zoning", "city-council"]


def test_process_to_summary_records_llm_enrichment_entity():
    row = _make_doc_text_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_text_utf8.return_value = "text"
    store.write_with_bytes.return_value = "art_s"

    registry = MagicMock()
    registry.resolve.return_value = MagicMock(model="claude-sonnet-4-6", prompts={"system": "sys"})

    with patch("sidekick.processing.processors.summary.ChatAnthropic") as mock_llm_cls:
        mock_llm_cls.return_value.with_structured_output.return_value.invoke.return_value = _make_summary_output()
        process_to_summary("art_doctext", store, registry)

    out = store.write_with_bytes.call_args[0][0]
    enrichment_entities = [e for e in (out.entities or []) if e.get("type") == "llm-enrichment"]
    assert len(enrichment_entities) == 1
    assert enrichment_entities[0]["processor"] == "summary"
    assert enrichment_entities[0]["model"] == "claude-sonnet-4-6"


def test_process_to_summary_rejects_raw_artifact():
    row = Artifact(
        id="art_raw",
        content_type="document-raw",
        stage="raw",
        status="active",
        media_type="application/pdf",
    )
    store = MagicMock()
    store.read_row.return_value = row
    registry = MagicMock()

    with pytest.raises(UnsupportedProcessingError, match="stage=processed"):
        process_to_summary("art_raw", store, registry)
