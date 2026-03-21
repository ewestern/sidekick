"""Phase 3 — acquisition and processing workers.

Completes `pending_acquisition` raw stubs (e.g. HLS via ffmpeg) and produces
`processed` artifacts such as `document-text` and `transcript-clean`.
"""

from sidekick.processing.router import (
    UnsupportedProcessingError,
    can_acquire_hls_stub,
    resolve_active_raw_processor,
)

__all__ = [
    "UnsupportedProcessingError",
    "can_acquire_hls_stub",
    "resolve_active_raw_processor",
]
