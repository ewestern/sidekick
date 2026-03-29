"""Eligibility helpers for acquisition, normalization, and enrichment — not a workflow engine."""

from __future__ import annotations

from typing import Literal

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ArtifactStatus, ProcessingProfile, Stage

ProcessKind = Literal["pdf_text", "transcript"]
class UnsupportedProcessingError(ValueError):
    """Raised when no acquisition or processor applies to an artifact."""


def _is_hls_url(url: str) -> bool:
    base = url.split("?")[0].strip().lower()
    return base.endswith(".m3u8") or base.endswith(".m3u")


def can_acquire_hls_stub(artifact: Artifact) -> bool:
    """Return True if this row is an HLS stub awaiting ffmpeg capture."""
    return (
        artifact.stage == Stage.RAW
        and artifact.status == ArtifactStatus.PENDING_ACQUISITION
        and artifact.acquisition_url is not None
        and _is_hls_url(artifact.acquisition_url)
    )


def resolve_active_raw_processor(artifact: Artifact) -> ProcessKind:
    """Return the processor kind for a **complete** raw artifact.

    ``processing_profile=evidence`` skips PDF text extraction and STT normalization
    (archive-only raw).

    Args:
        artifact: Must be ``stage="raw"`` and ``status="active"`` with bytes available.

    Raises:
        UnsupportedProcessingError: If the artifact is not processable.
    """
    if artifact.stage != Stage.RAW:
        raise UnsupportedProcessingError(
            f"Processing expects stage=raw; got {artifact.stage!r}"
        )
    if artifact.status != ArtifactStatus.ACTIVE:
        raise UnsupportedProcessingError(
            f"Processing expects status=active (complete raw); got {artifact.status!r}. "
            "Run `sidekick-process acquire` for pending_acquisition stubs first."
        )
    if artifact.processing_profile == ProcessingProfile.EVIDENCE:
        raise UnsupportedProcessingError(
            "processing_profile=evidence skips normalization (archive-only raw)."
        )
    mt = artifact.media_type or ""
    if mt == "application/pdf":
        return "pdf_text"
    if mt.startswith("audio/") or mt.startswith("video/"):
        return "transcript"
    raise UnsupportedProcessingError(
        f"No processor for media_type={mt!r} content_type={artifact.content_type!r}"
    )
