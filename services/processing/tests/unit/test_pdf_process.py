"""PDF → document-text (object storage)."""

from unittest.mock import MagicMock, patch

from sidekick.core.models import Artifact

from sidekick.processing.processors.pdf import process_pdf_to_document_text


def test_process_pdf_writes_document_text_to_object_store():
    row = Artifact(
        id="art_raw",
        content_type="document-raw",
        stage="raw",
        status="active",
        media_type="application/pdf",
        beat="government:city_council",
        geo="us:il:springfield:springfield",
        source_id="src_x",
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"%PDF-1.4 fake"
    with patch(
        "sidekick.processing.processors.pdf.extract_text_from_pdf_bytes",
        return_value="Agenda line one.",
    ):
        process_pdf_to_document_text("art_raw", store)

    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out = args[0]
    body = args[1]
    assert body == "Agenda line one.".encode("utf-8")
    assert kwargs.get("object_content_type") == "text/plain"
    assert out.content_type == "document-text"
    assert out.stage == "processed"
    assert out.derived_from == ["art_raw"]
    proc_entities = [e for e in (out.entities or []) if e.get("type") == "pdf-extraction"]
    assert len(proc_entities) == 1
    assert proc_entities[0].get("ocr") == "not_applied"
