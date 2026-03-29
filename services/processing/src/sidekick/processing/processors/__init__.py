"""Content processors — raw (active) → processed."""

from sidekick.processing.processors.pdf import process_pdf_to_document_text

__all__ = [
    "process_pdf_to_document_text",
]
