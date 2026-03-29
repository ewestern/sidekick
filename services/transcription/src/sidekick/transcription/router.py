"""Route raw artifacts to the transcription processor (mirrors processing router rules)."""

from __future__ import annotations

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ArtifactStatus, ProcessingProfile, Stage


class UnsupportedTranscriptionError(ValueError):
    """Raised when a raw artifact is not eligible for speech-to-text."""


def assert_transcribable_raw(artifact: Artifact) -> None:
    """Validate ``artifact`` is raw, active, and audio/video.

    Args:
        artifact: Row from the artifact store.

    Raises:
        UnsupportedTranscriptionError: If transcription does not apply.
    """
    if artifact.stage != Stage.RAW:
        raise UnsupportedTranscriptionError(
            f"Transcription expects stage=raw; got {artifact.stage!r}"
        )
    if artifact.status != ArtifactStatus.ACTIVE:
        raise UnsupportedTranscriptionError(
            f"Transcription expects status=active (complete raw); got {artifact.status!r}. "
            "Complete acquisition first if this artifact is pending_acquisition."
        )
    if artifact.processing_profile == ProcessingProfile.EVIDENCE:
        raise UnsupportedTranscriptionError(
            "processing_profile=evidence skips transcription (archive-only raw)."
        )
    mt = artifact.media_type or ""
    if not (mt.startswith("audio/") or mt.startswith("video/")):
        raise UnsupportedTranscriptionError(
            f"Artifact is not audio/video suitable for transcription "
            f"(media_type={mt!r}, content_type={artifact.content_type!r})."
        )
