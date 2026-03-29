"""Router rules for acquisition and processing."""

import pytest

from sidekick.core.vocabulary import (
    ArtifactStatus,
    ContentType,
    ProcessingProfile,
    Stage,
)
from sidekick.core.models import Artifact
from sidekick.processing.router import (
    UnsupportedProcessingError,
    can_acquire_hls_stub,
    resolve_active_raw_processor,
)


def test_can_acquire_hls_stub_true():
    art = Artifact(
        id="art_1",
        title="March Agenda",
        content_type=ContentType.AUDIO_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.PENDING_ACQUISITION,
        acquisition_url="https://cdn.example.com/x.m3u8?tok=1",
    )
    assert can_acquire_hls_stub(art) is True


def test_can_acquire_hls_stub_false_wrong_status():
    art = Artifact(
        id="art_1",
        title="March Agenda",
        content_type=ContentType.AUDIO_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.ACTIVE,
        acquisition_url="https://cdn.example.com/x.m3u8",
    )
    assert can_acquire_hls_stub(art) is False


def test_resolve_pdf_processor():
    art = Artifact(
        id="art_pdf",
        title="March Agenda",
        content_type=ContentType.DOCUMENT_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.ACTIVE,
        media_type="application/pdf",
    )
    assert resolve_active_raw_processor(art) == "pdf_text"


def test_resolve_transcript_processor():
    art = Artifact(
        id="art_a",
        title="March Agenda",
        content_type=ContentType.AUDIO_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.ACTIVE,
        media_type="audio/mpeg",
    )
    assert resolve_active_raw_processor(art) == "transcript"


def test_resolve_rejects_evidence_profile():
    art = Artifact(
        id="art_e",
        title="March Agenda",
        content_type=ContentType.DOCUMENT_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.ACTIVE,
        media_type="application/pdf",
        processing_profile=ProcessingProfile.EVIDENCE,
    )
    with pytest.raises(UnsupportedProcessingError, match="evidence"):
        resolve_active_raw_processor(art)


def test_resolve_rejects_pending():
    art = Artifact(
        id="art_p",
        title="March Agenda",
        content_type=ContentType.AUDIO_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.PENDING_ACQUISITION,
        acquisition_url="https://x.m3u8",
    )
    with pytest.raises(UnsupportedProcessingError, match="active"):
        resolve_active_raw_processor(art)
