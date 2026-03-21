"""Router rules for acquisition and processing."""

import pytest

from sidekick.core.models import Artifact
from sidekick.processing.router import (
    UnsupportedProcessingError,
    can_acquire_hls_stub,
    resolve_active_raw_processor,
    resolve_enrichment_input,
)


def test_can_acquire_hls_stub_true():
    art = Artifact(
        id="art_1",
        content_type="audio-raw",
        stage="raw",
        status="pending_acquisition",
        acquisition_url="https://cdn.example.com/x.m3u8?tok=1",
    )
    assert can_acquire_hls_stub(art) is True


def test_can_acquire_hls_stub_false_wrong_status():
    art = Artifact(
        id="art_1",
        content_type="audio-raw",
        stage="raw",
        status="active",
        acquisition_url="https://cdn.example.com/x.m3u8",
    )
    assert can_acquire_hls_stub(art) is False


def test_resolve_pdf_processor():
    art = Artifact(
        id="art_pdf",
        content_type="document-raw",
        stage="raw",
        status="active",
        media_type="application/pdf",
    )
    assert resolve_active_raw_processor(art) == "pdf_text"


def test_resolve_transcript_processor():
    art = Artifact(
        id="art_a",
        content_type="audio-raw",
        stage="raw",
        status="active",
        media_type="audio/mpeg",
    )
    assert resolve_active_raw_processor(art) == "transcript"


def test_resolve_rejects_pending():
    art = Artifact(
        id="art_p",
        content_type="audio-raw",
        stage="raw",
        status="pending_acquisition",
        acquisition_url="https://x.m3u8",
    )
    with pytest.raises(UnsupportedProcessingError, match="active"):
        resolve_active_raw_processor(art)


# ── Enrichment routing ────────────────────────────────────────────────────────


def test_resolve_enrichment_input_document_text():
    art = Artifact(
        id="art_dt",
        content_type="document-text",
        stage="processed",
        status="active",
        media_type="text/plain",
    )
    kinds = resolve_enrichment_input(art)
    assert "summary" in kinds
    assert "entity_extract" in kinds


def test_resolve_enrichment_input_transcript_clean():
    art = Artifact(
        id="art_tc",
        content_type="transcript-clean",
        stage="processed",
        status="active",
        media_type="text/plain",
    )
    kinds = resolve_enrichment_input(art)
    assert "summary" in kinds
    assert "entity_extract" in kinds


def test_resolve_enrichment_rejects_raw_stage():
    art = Artifact(
        id="art_r",
        content_type="document-raw",
        stage="raw",
        status="active",
        media_type="application/pdf",
    )
    with pytest.raises(UnsupportedProcessingError, match="stage=processed"):
        resolve_enrichment_input(art)


def test_resolve_enrichment_rejects_summary_content_type():
    """Prevents infinite enrichment loop — summary artifacts cannot be re-enriched."""
    art = Artifact(
        id="art_s",
        content_type="summary",
        stage="processed",
        status="active",
        media_type="application/json",
    )
    with pytest.raises(UnsupportedProcessingError, match="content_type"):
        resolve_enrichment_input(art)
