"""Audio/video → document-text processor tests."""

from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import (
    ArtifactStatus,
    ContentType,
    ProcessingProfile,
    Stage,
)

from sidekick.transcription.processor import process_audio_to_transcript
from sidekick.transcription.router import (
    UnsupportedTranscriptionError,
    assert_transcribable_raw,
)


def _make_raw_artifact(**kwargs) -> Artifact:
    defaults = dict(
        id="art_raw",
        content_type=ContentType.AUDIO_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.ACTIVE,
        media_type="audio/mpeg",
        beat="government:city-council",
        geo="us:il:springfield:springfield",
        source_id="src_x",
    )
    defaults.update(kwargs)
    return Artifact(**defaults)  # type: ignore[arg-type]


def test_assert_transcribable_raw_accepts_audio():
    assert_transcribable_raw(_make_raw_artifact())


def test_assert_transcribable_raw_rejects_pdf():
    with pytest.raises(UnsupportedTranscriptionError, match="not audio/video"):
        assert_transcribable_raw(
            _make_raw_artifact(
                media_type="application/pdf", content_type="document-raw"
            )
        )


def test_assert_transcribable_raw_rejects_evidence_profile():
    with pytest.raises(UnsupportedTranscriptionError, match="evidence"):
        assert_transcribable_raw(
            _make_raw_artifact(processing_profile=ProcessingProfile.EVIDENCE)
        )


def test_process_audio_writes_document_text():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"
    segments = [("speaker", "Council member Smith moved to approve.")]

    mock_model = MagicMock()
    with patch(
        "sidekick.transcription.processor.transcribe_audio_file",
        return_value=segments,
    ):
        process_audio_to_transcript("art_raw", store, model=mock_model)

    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out: Artifact = args[0]
    body: bytes = args[1]
    assert body.decode(
        "utf-8") == "speaker: Council member Smith moved to approve."
    assert kwargs.get("object_content_type") == "text/plain"
    assert out.content_type == "document-text"
    assert out.stage == "processed"
    assert out.derived_from == ["art_raw"]
    assert out.processing_profile is None


def test_process_audio_created_by_default():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"

    mock_model = MagicMock()
    with patch(
        "sidekick.transcription.processor.transcribe_audio_file",
        return_value=[("speaker", "Some text.")],
    ):
        process_audio_to_transcript("art_raw", store, model=mock_model)

    out = store.write_with_bytes.call_args[0][0]
    assert out.created_by == "processor:transcript"
    stt_entities = [
        e for e in (out.entities or []) if e.get("type") == "speech-to-text"
    ]
    assert len(stt_entities) == 0


def test_process_audio_raises_on_empty_segments():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"

    mock_model = MagicMock()
    with patch(
        "sidekick.transcription.processor.transcribe_audio_file",
        return_value=[],
    ):
        with pytest.raises(ValueError, match="no segments"):
            process_audio_to_transcript("art_raw", store, model=mock_model)

    store.write_with_bytes.assert_not_called()
