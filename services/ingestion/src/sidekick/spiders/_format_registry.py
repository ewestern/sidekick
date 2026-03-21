"""Format detection and media handling registry.

Maps detected formats to acquisition methods and stored MIME types. Detection runs in
priority order: URL extension → Content-Type header → magic bytes.

Two-phase acquisition contract for async formats (HLS, yt-dlp):
  1. Spider discovers the source URL and calls detect_format().
  2. Pipeline writes a stub artifact with:
       status="pending_acquisition"
       acquisition_url=<source_url>  (URL the acquisition worker must fetch)
       content_uri=None  (not yet populated)
  3. Pipeline publishes an "acquisition_needed" event.
  4. Acquisition worker runs ffmpeg/yt-dlp against acquisition_url, writes the result to S3,
     then ArtifactStore.complete_acquisition(): status="active", content_uri=<s3_key>,
     acquisition_url=None.
"""

from __future__ import annotations

import pathlib
import urllib.parse
from enum import StrEnum

from pydantic import BaseModel, computed_field


class AcquisitionMethod(StrEnum):
    HTTP_DOWNLOAD = "HTTP_DOWNLOAD"   # GET URL, store bytes
    HLS_CAPTURE = "HLS_CAPTURE"       # ffmpeg: m3u8 endpoint → audio  (async)
    YTDLP_AUDIO = "YTDLP_AUDIO"       # yt-dlp: YouTube → audio         (async)
    INLINE_TEXT = "INLINE_TEXT"        # fetch and decode body, store inline


_ASYNC_METHODS = frozenset({AcquisitionMethod.HLS_CAPTURE, AcquisitionMethod.YTDLP_AUDIO})


class FormatSpec(BaseModel, frozen=True):
    """Describes how a format should be acquired and stored."""

    format_id: str
    acquisition: AcquisitionMethod
    stored_mime_type: str   # MIME type stored in the artifact (may differ from source MIME)
    content_type: str       # controlled artifact content_type vocabulary

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_async(self) -> bool:
        """True when acquisition cannot run inline in Scrapy's synchronous pipeline."""
        return self.acquisition in _ASYNC_METHODS


# ---------------------------------------------------------------------------
# Format registry
# ---------------------------------------------------------------------------

FORMAT_REGISTRY: dict[str, FormatSpec] = {
    "pdf": FormatSpec(
        format_id="pdf",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="application/pdf",
        content_type="document-raw",
    ),
    "html": FormatSpec(
        format_id="html",
        acquisition=AcquisitionMethod.INLINE_TEXT,
        stored_mime_type="text/html",
        content_type="document-raw",
    ),
    "xlsx": FormatSpec(
        format_id="xlsx",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content_type="document-raw",
    ),
    "csv": FormatSpec(
        format_id="csv",
        acquisition=AcquisitionMethod.INLINE_TEXT,
        stored_mime_type="text/csv",
        content_type="document-raw",
    ),
    "docx": FormatSpec(
        format_id="docx",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content_type="document-raw",
    ),
    "mp3": FormatSpec(
        format_id="mp3",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="audio/mpeg",
        content_type="audio-raw",
    ),
    "wav": FormatSpec(
        format_id="wav",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="audio/wav",
        content_type="audio-raw",
    ),
    "ogg": FormatSpec(
        format_id="ogg",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="audio/ogg",
        content_type="audio-raw",
    ),
    "aac": FormatSpec(
        format_id="aac",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="audio/aac",
        content_type="audio-raw",
    ),
    "mp4": FormatSpec(
        format_id="mp4",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="video/mp4",
        content_type="video-raw",
    ),
    "webm": FormatSpec(
        format_id="webm",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="video/webm",
        content_type="video-raw",
    ),
    "mov": FormatSpec(
        format_id="mov",
        acquisition=AcquisitionMethod.HTTP_DOWNLOAD,
        stored_mime_type="video/quicktime",
        content_type="video-raw",
    ),
    "hls": FormatSpec(
        format_id="hls",
        acquisition=AcquisitionMethod.HLS_CAPTURE,
        stored_mime_type="audio/mpeg",
        content_type="audio-raw",
    ),
    "mpeg-ts": FormatSpec(
        format_id="mpeg-ts",
        acquisition=AcquisitionMethod.HLS_CAPTURE,
        stored_mime_type="audio/mpeg",
        content_type="audio-raw",
    ),
}

# ---------------------------------------------------------------------------
# MIME → format_id (many-to-one; keys are normalized lowercase base MIME)
# ---------------------------------------------------------------------------

MIME_TO_FORMAT: dict[str, str] = {
    "application/pdf": "pdf",
    "text/html": "html",
    "text/plain": "html",
    "application/x-mpegurl": "hls",
    "application/vnd.apple.mpegurl": "hls",
    "video/mp2t": "mpeg-ts",
    "video/ts": "mpeg-ts",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/aac": "aac",
    "video/mp4": "mp4",
    "video/mpeg": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
    "application/vnd.ms-excel": "xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/csv": "csv",
}

# ---------------------------------------------------------------------------
# URL extension → format_id (lowercase extension including leading dot)
# ---------------------------------------------------------------------------

EXT_TO_FORMAT: dict[str, str] = {
    ".pdf": "pdf",
    ".html": "html",
    ".htm": "html",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "csv",
    ".docx": "docx",
    ".doc": "docx",
    ".mp3": "mp3",
    ".wav": "wav",
    ".ogg": "ogg",
    ".aac": "aac",
    ".mp4": "mp4",
    ".webm": "webm",
    ".mov": "mov",
    ".m3u8": "hls",
    ".ts": "mpeg-ts",
}

# ---------------------------------------------------------------------------
# Magic bytes → format_id (None means ambiguous — fall through to MIME)
# ---------------------------------------------------------------------------

MAGIC_BYTES: list[tuple[bytes, str | None]] = [
    (b"%PDF", "pdf"),
    (b"#EXTM3U", "hls"),
    (b"PK\x03\x04", None),           # zip-based — ambiguous (xlsx, docx, jar, …)
    (b"\x1a\x45\xdf\xa3", "webm"),
    (b"ID3", "mp3"),
    (b"RIFF", None),                  # WAV or AVI — resolve with MIME or fail
]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


class UnknownFormatError(ValueError):
    """Raised when no format can be determined for a URL / Content-Type / body."""


def detect_format(
    url: str,
    content_type_header: str | None,
    body_head: bytes | None,
) -> FormatSpec:
    """Detect the format of a resource using multi-signal heuristics.

    Priority order:
      1. URL file extension (most reliable for well-formed URLs)
      2. Content-Type response header (handles API URLs with no extension)
      3. Magic bytes from the response body head (last resort)

    Args:
        url: The resource URL (query strings and fragments are ignored).
        content_type_header: The raw Content-Type header value, if available.
        body_head: The first N bytes of the response body, if available.

    Returns:
        The matching FormatSpec from FORMAT_REGISTRY.

    Raises:
        UnknownFormatError: If no format can be determined.
    """
    # 1. URL extension
    parsed = urllib.parse.urlparse(url)
    suffix = pathlib.PurePosixPath(parsed.path).suffix.lower()
    if suffix and suffix in EXT_TO_FORMAT:
        return FORMAT_REGISTRY[EXT_TO_FORMAT[suffix]]

    # 2. Content-Type header
    if content_type_header:
        base_mime = content_type_header.split(";")[0].strip().lower()
        if base_mime in MIME_TO_FORMAT:
            return FORMAT_REGISTRY[MIME_TO_FORMAT[base_mime]]

    # 3. Magic bytes
    if body_head:
        for magic, format_id in MAGIC_BYTES:
            if body_head.startswith(magic) and format_id is not None:
                return FORMAT_REGISTRY[format_id]

    raise UnknownFormatError(
        f"Cannot determine format for URL={url!r}, "
        f"Content-Type={content_type_header!r}"
    )
