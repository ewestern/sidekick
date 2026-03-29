"""PDF → ``document-text`` processed artifact (Markdown in object storage)."""

from __future__ import annotations

from functools import lru_cache
import tempfile

import ulid
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ContentType, Stage

from sidekick.processing.router import UnsupportedProcessingError, resolve_active_raw_processor


@lru_cache(maxsize=1)
def build_pdf_converter() -> PdfConverter:
    """Create the shared Marker converter, triggering model initialization once per process."""
    return PdfConverter(artifact_dict=create_model_dict())


def warm_marker_cache() -> None:
    """Ensure Marker model artifacts are present in the configured local cache."""
    build_pdf_converter()


def extract_markdown_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract Markdown from PDF bytes using Marker (handles scanned + native PDFs)."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as f:
        f.write(pdf_bytes)
        f.flush()
        converter = build_pdf_converter()
        rendered = converter(f.name)
    markdown, _, _ = text_from_rendered(rendered)
    return markdown.strip()


def process_pdf_to_document_text(
    artifact_id: str,
    artifact_store: ArtifactStore,
    *,
    created_by: str = "processor:marker",
) -> str:
    """Create a ``document-text`` artifact with Markdown stored in the object store.

    Uses Marker (Surya OCR + layout detection) so both native and scanned PDFs are
    supported. Output is ``text/markdown`` rather than ``text/plain``.

    Raises:
        ValueError: If no content can be extracted from the PDF.
    """
    row = artifact_store.read_row(artifact_id)
    kind = resolve_active_raw_processor(row)
    if kind != "pdf_text":
        raise UnsupportedProcessingError(
            f"Artifact {artifact_id!r} is not an active PDF raw row (got {kind!r})."
        )

    pdf_bytes = artifact_store.get_content_bytes(row)
    markdown = extract_markdown_from_pdf_bytes(pdf_bytes)
    if not markdown:
        raise ValueError(
            f"No content extracted from PDF artifact {artifact_id!r}. "
            "The document may be empty or corrupt."
        )

    new_id = f"art_{ulid.new()}"
    out = Artifact(
        id=new_id,
        title=row.title,
        content_type=ContentType.DOCUMENT_TEXT,
        stage=Stage.PROCESSED,
        media_type="text/markdown",
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
    return artifact_store.write_with_bytes(
        out,
        markdown.encode("utf-8"),
        object_content_type="text/markdown",
    )
