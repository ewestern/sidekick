"""HLS (m3u8) capture — ffmpeg → object store → complete_acquisition."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.object_store import ObjectStore, S3ObjectStore

from sidekick.processing.router import UnsupportedProcessingError, can_acquire_hls_stub

logger = logging.getLogger(__name__)


def _ffmpeg_hls_to_mp3(m3u8_url: str, out_path: Path) -> None:
    """Run ffmpeg to extract audio as MP3. Requires ``ffmpeg`` on PATH."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        m3u8_url,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "4",
        str(out_path),
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        # ffmpeg writes diagnostics to stderr; include both streams in the error.
        err_parts = []
        if exc.stderr and exc.stderr.strip():
            err_parts.append(exc.stderr.strip())
        if exc.stdout and exc.stdout.strip():
            err_parts.append(exc.stdout.strip())
        detail = "\n".join(err_parts) if err_parts else f"exit code {exc.returncode}"
        raise RuntimeError(f"ffmpeg failed: {detail}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg not found on PATH; install ffmpeg and retry."
        ) from exc


def acquire_hls_stub(
    artifact_id: str,
    artifact_store: ArtifactStore,
    object_store: ObjectStore,
) -> str:
    """Download HLS stream audio for a pending stub; complete the raw artifact.

    Returns:
        The artifact ID (same row updated to ``active``).
    """
    row = artifact_store.read_row(artifact_id)
    if not can_acquire_hls_stub(row):
        raise UnsupportedProcessingError(
            f"Artifact {artifact_id!r} is not an HLS pending_acquisition stub."
        )
    assert row.acquisition_url is not None
    url = row.acquisition_url

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        logger.info("Capturing HLS for %s from %s", artifact_id, url)
        _ffmpeg_hls_to_mp3(url, out_path)
        mp3_bytes = out_path.read_bytes()
        key = S3ObjectStore.artifact_key("raw", row.beat, row.geo, row.id)
        uri = object_store.put(key, mp3_bytes, content_type="audio/mpeg")
        artifact_store.complete_acquisition(
            artifact_id,
            uri,
            media_type="audio/mpeg",
        )
    finally:
        out_path.unlink(missing_ok=True)

    return artifact_id
