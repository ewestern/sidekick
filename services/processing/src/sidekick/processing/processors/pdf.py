"""PDF → ``document-text`` processed artifact (text in object storage only)."""

from __future__ import annotations

import io

import ulid
from pypdf import PdfReader

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact

from sidekick.processing.router import UnsupportedProcessingError, resolve_active_raw_processor


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes (text layer only; no OCR)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n".join(parts).strip()


def process_pdf_to_document_text(
    artifact_id: str,
    artifact_store: ArtifactStore,
    *,
    created_by: str = "processor:pdf",
) -> str:
    """Create a ``document-text`` artifact with UTF-8 text stored in the object store.

    Raises:
        ValueError: If no text can be extracted (e.g. scanned PDF) — OCR is not implemented,
            so no row is written until extractable text exists in storage.
    """
    row = artifact_store.read_row(artifact_id)
    kind = resolve_active_raw_processor(row)
    if kind != "pdf_text":
        raise UnsupportedProcessingError(
            f"Artifact {artifact_id!r} is not an active PDF raw row (got {kind!r})."
        )

    pdf_bytes = artifact_store.get_content_bytes(row)
    text = extract_text_from_pdf_bytes(pdf_bytes)
    if not text:
        raise ValueError(
            "No extractable text from PDF; OCR is not implemented. "
            "A document-text artifact is only written once UTF-8 text exists in object storage."
        )

    entities = list(row.entities or [])
    entities.append(
        {
            "type": "pdf-extraction",
            "method": "pypdf-text-layer",
            "ocr": "not_applied",
        }
    )

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        id=new_id,
        content_type="document-text",
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
