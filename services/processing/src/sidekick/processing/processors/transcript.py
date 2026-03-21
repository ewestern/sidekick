"""Audio/video raw → ``transcript-clean`` via WhisperX (STT + forced alignment + diarization)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import ulid
import whisperx

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact

from sidekick.processing.router import UnsupportedProcessingError, resolve_active_raw_processor

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


def _suffix_for_media_type(media_type: str | None) -> str:
    if not media_type:
        return ".bin"
    base = media_type.split(";")[0].strip().lower()
    return _MEDIA_SUFFIX.get(base, ".bin")


def _segments_to_text(segments: list[dict]) -> str:
    """Format whisperx segments into plain text.

    When diarization has been run, segments carry a ``speaker`` field and the
    output uses ``[SPEAKER_XX]`` labels, grouping consecutive segments from the
    same speaker onto one line.  Without diarization the segments are
    concatenated as plain text.
    """
    diarized = any("speaker" in seg for seg in segments)

    if not diarized:
        return " ".join(seg.get("text", "").strip() for seg in segments if seg.get("text", "").strip())

    lines: list[str] = []
    current_speaker: str | None = None
    current_parts: list[str] = []

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        if speaker != current_speaker:
            if current_parts and current_speaker is not None:
                lines.append(f"[{current_speaker}] {' '.join(current_parts)}")
            current_speaker = speaker
            current_parts = [text]
        else:
            current_parts.append(text)

    if current_parts and current_speaker is not None:
        lines.append(f"[{current_speaker}] {' '.join(current_parts)}")

    return "\n".join(lines)


def transcribe_audio_file(
    path: Path,
    *,
    model_size: str = "base",
    device: str = "cpu",
    hf_token: str | None = None,
) -> str:
    """Transcribe an audio file using WhisperX.

    Runs STT via faster-whisper, then forced phoneme alignment for accurate
    word-level timestamps.  When ``hf_token`` is provided, speaker diarization
    is performed via pyannote.audio and ``[SPEAKER_XX]`` labels are included in
    the output.

    Args:
        path: Path to the audio/video file.
        model_size: Whisper model size (e.g. ``"base"``, ``"large-v3"``).
        device: Compute device — ``"cpu"`` or ``"cuda"``.
        hf_token: HuggingFace token for pyannote diarization.  Diarization is
            skipped when absent.

    Returns:
        Plain text transcript.  Speaker labels are included when diarization
        is performed.
    """
    compute_type = "int8" if device == "cpu" else "float16"

    model = whisperx.load_model(model_size, device=device, compute_type=compute_type)
    audio = whisperx.load_audio(str(path))
    result = model.transcribe(audio, batch_size=16)

    # Forced alignment — improves timestamp accuracy before speaker assignment
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(result["segments"], align_model, metadata, audio, device=device)

    if hf_token:
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        diarize_segments = diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    return _segments_to_text(result["segments"])


def process_audio_to_transcript(
    artifact_id: str,
    artifact_store: ArtifactStore,
    *,
    model_size: str = "base",
    device: str = "cpu",
    hf_token: str | None = None,
    created_by: str = "processor:transcript",
) -> str:
    """Create a ``transcript-clean`` artifact with transcript text in object storage.

    Args:
        artifact_id: ID of the source ``raw`` + ``active`` audio/video artifact.
        artifact_store: Artifact store instance.
        model_size: Whisper model size.
        device: Compute device.
        hf_token: HuggingFace token for pyannote diarization.

    Raises:
        UnsupportedProcessingError: If the artifact is not audio/video.
        ValueError: If transcription produces no text.
    """
    row = artifact_store.read_row(artifact_id)
    if resolve_active_raw_processor(row) != "transcript":
        raise UnsupportedProcessingError(
            f"Artifact {artifact_id!r} is not audio/video suitable for transcription."
        )

    data = artifact_store.get_content_bytes(row)
    suffix = _suffix_for_media_type(row.media_type)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        media_path = Path(tmp.name)
    try:
        text = transcribe_audio_file(
            media_path, model_size=model_size, device=device, hf_token=hf_token
        )
    finally:
        media_path.unlink(missing_ok=True)

    if not text:
        raise ValueError(
            "Transcription produced no text; transcript-clean is only written once "
            "UTF-8 text exists in object storage."
        )

    entities = list(row.entities or [])
    entities.append(
        {
            "type": "speech-to-text",
            "engine": "whisperx",
            "model": model_size,
            "diarization": hf_token is not None,
        }
    )

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        id=new_id,
        content_type="transcript-clean",
        stage="processed",
        media_type="text/plain",
        derived_from=[artifact_id],
        source_id=row.source_id,
        event_group=row.event_group,
        beat=row.beat,
        geo=row.geo,
        period_start=row.period_start,
        period_end=row.period_end,
        assignment_id=row.assignment_id,
        entities=entities,
        created_by=created_by,
    )
    return artifact_store.write_with_bytes(
        out,
        text.encode("utf-8"),
        object_content_type="text/plain",
    )
