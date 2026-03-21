"""Audio/video → transcript-clean processor tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.models import Artifact

from sidekick.processing.processors.transcript import (
    _segments_to_text,
    process_audio_to_transcript,
)


# --- _segments_to_text ---


def test_segments_to_text_no_diarization():
    segments = [{"text": "Hello world."}, {"text": " How are you?"}]
    assert _segments_to_text(segments) == "Hello world. How are you?"


def test_segments_to_text_with_diarization_groups_speakers():
    segments = [
        {"text": "Good morning.", "speaker": "SPEAKER_00"},
        {"text": "Thank you.", "speaker": "SPEAKER_00"},
        {"text": "Any objections?", "speaker": "SPEAKER_01"},
        {"text": "None.", "speaker": "SPEAKER_00"},
    ]
    result = _segments_to_text(segments)
    lines = result.splitlines()
    assert lines[0] == "[SPEAKER_00] Good morning. Thank you."
    assert lines[1] == "[SPEAKER_01] Any objections?"
    assert lines[2] == "[SPEAKER_00] None."


def test_segments_to_text_skips_empty_text():
    segments = [
        {"text": "Hello.", "speaker": "SPEAKER_00"},
        {"text": "", "speaker": "SPEAKER_00"},
        {"text": "  ", "speaker": "SPEAKER_01"},
        {"text": "Goodbye.", "speaker": "SPEAKER_01"},
    ]
    result = _segments_to_text(segments)
    assert "[SPEAKER_00] Hello." in result
    assert "[SPEAKER_01] Goodbye." in result


# --- process_audio_to_transcript ---


def _make_raw_artifact(**kwargs) -> Artifact:
    defaults = dict(
        id="art_raw",
        content_type="audio-raw",
        stage="raw",
        status="active",
        media_type="audio/mpeg",
        beat="government:city_council",
        geo="us:il:springfield:springfield",
        source_id="src_x",
    )
    defaults.update(kwargs)
    return Artifact(**defaults)


def test_process_audio_writes_transcript_clean():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"

    with patch(
        "sidekick.processing.processors.transcript.transcribe_audio_file",
        return_value="Council member Smith moved to approve.",
    ):
        process_audio_to_transcript("art_raw", store)

    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out: Artifact = args[0]
    body: bytes = args[1]

    assert body == b"Council member Smith moved to approve."
    assert kwargs.get("object_content_type") == "text/plain"
    assert out.content_type == "transcript-clean"
    assert out.stage == "processed"
    assert out.derived_from == ["art_raw"]


def test_process_audio_records_whisperx_entity_without_diarization():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"

    with patch(
        "sidekick.processing.processors.transcript.transcribe_audio_file",
        return_value="Some text.",
    ):
        process_audio_to_transcript("art_raw", store, model_size="base")

    out = store.write_with_bytes.call_args[0][0]
    stt_entities = [e for e in (out.entities or []) if e.get("type") == "speech-to-text"]
    assert len(stt_entities) == 1
    assert stt_entities[0]["engine"] == "whisperx"
    assert stt_entities[0]["model"] == "base"
    assert stt_entities[0]["diarization"] is False


def test_process_audio_records_diarization_true_when_hf_token_provided():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"

    with patch(
        "sidekick.processing.processors.transcript.transcribe_audio_file",
        return_value="[SPEAKER_00] Motion approved.",
    ):
        process_audio_to_transcript("art_raw", store, hf_token="hf_fake_token")

    out = store.write_with_bytes.call_args[0][0]
    stt_entities = [e for e in (out.entities or []) if e.get("type") == "speech-to-text"]
    assert stt_entities[0]["diarization"] is True


def test_process_audio_raises_on_empty_transcript():
    row = _make_raw_artifact()
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"fake-audio"

    with patch(
        "sidekick.processing.processors.transcript.transcribe_audio_file",
        return_value="",
    ):
        with pytest.raises(ValueError, match="no text"):
            process_audio_to_transcript("art_raw", store)

    store.write_with_bytes.assert_not_called()
