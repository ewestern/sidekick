"""Audio/video raw → ``document-text`` via WhisperX (STT + alignment + diarization)."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import torch
import ulid
import whisperx
from whisperx.diarize import DiarizationPipeline

from dotenv import load_dotenv

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ContentType, Stage

from sidekick.transcription.router import assert_transcribable_raw

load_dotenv()
logger = logging.getLogger(__name__)

_MEDIA_SUFFIX = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/aac": ".aac",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def get_backend() -> str:
    """Return ``cuda`` if available, else ``cpu``."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _suffix_for_media_type(media_type: str | None) -> str:
    if not media_type:
        return ".bin"
    base = media_type.split(";")[0].strip().lower()
    return _MEDIA_SUFFIX.get(base, ".bin")


def _hf_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError(
            "HF_TOKEN is required for WhisperX diarization (pyannote). "
            "Set the environment variable or pass hf_token= to transcribe_audio_file."
        )
    return token


def load_transcription_model(model_size: str, device: str | None = None) -> Any:
    """Load the Whisper ASR model once for reuse across multiple ``transcribe_audio_file`` calls.

    Args:
        model_size: Whisper model name (e.g. ``"base"``, ``"large-v3"``).
        device: ``"cpu"`` or ``"cuda"``. Defaults to ``get_backend()``.

    Returns:
        WhisperX ASR model object from ``whisperx.load_model``.
    """
    dev = device if device is not None else get_backend()
    return whisperx.load_model(model_size, device=dev)


def transcribe_audio_file(path: Path, model: Any) -> list[tuple[str, str]]:
    """Transcribe media at ``path`` using WhisperX (STT, alignment, diarization).

    Args:
        path: Path to the audio/video file.
        model: Pre-loaded Whisper ASR model from ``load_transcription_model``.

    Returns:
        List of ``(speaker, text)`` tuples per segment.
    """
    token = _hf_token()
    device = get_backend()

    audio = whisperx.load_audio(str(path))
    result = model.transcribe(audio, batch_size=16)

    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, device=device
    )

    diarize_model = DiarizationPipeline(token=token, device=device)
    diarize_segments = diarize_model(audio)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    return [(segment["speaker"], segment["text"]) for segment in result["segments"]]


def process_audio_to_transcript(
    artifact_id: str,
    artifact_store: ArtifactStore,
    *,
    model: Any,
    created_by: str = "processor:transcript",
) -> str:
    """Create a ``document-text`` artifact with transcript payload in object storage.

    Body is UTF-8 plain dialog text assembled from WhisperX speaker segments.

    Args:
        artifact_id: ID of the source ``raw`` + ``active`` audio/video artifact.
        artifact_store: Artifact store instance.
        model: Pre-loaded Whisper ASR model from ``load_transcription_model``.

    Raises:
        UnsupportedTranscriptionError: If the artifact is not audio/video raw+active.
        ValueError: If transcription produces no segments.
    """
    row = artifact_store.read_row(artifact_id)
    assert_transcribable_raw(row)

    data = artifact_store.get_content_bytes(row)
    suffix = _suffix_for_media_type(row.media_type)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        media_path = Path(tmp.name)
    try:
        segments = transcribe_audio_file(media_path, model)
    finally:
        media_path.unlink(missing_ok=True)

    if not segments:
        raise ValueError(
            "Transcription produced no segments; document-text is only written once "
            "payload exists in object storage."
        )

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        title=row.title,
        id=new_id,
        content_type=ContentType.DOCUMENT_TEXT,
        stage=Stage.PROCESSED,
        media_type="text/plain",
        processing_profile=row.processing_profile,
        derived_from=[artifact_id],
        source_id=row.source_id,
        event_group=row.event_group,
        beat=row.beat,
        geo=row.geo,
        period_start=row.period_start,
        period_end=row.period_end,
        assignment_id=row.assignment_id,
        entities=list(row.entities or []),
        created_by=created_by,
    )
    # instead of json, just use plain dialog formatting:
    payload = "\n".join([f"{speaker}: {text}" for speaker, text in segments])
    return artifact_store.write_with_bytes(
        out,
        payload.encode("utf-8"),
        object_content_type="text/plain",
    )
