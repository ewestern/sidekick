"""PDF → document-text (object storage)."""

from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ArtifactStatus, ContentType, ProcessingProfile, Stage

from sidekick.processing.cli import app
from sidekick.processing.processors.pdf import process_pdf_to_document_text


def test_process_pdf_writes_document_text_to_object_store():
    row = Artifact(
        id="art_raw",
        title="March Agenda",
        content_type=ContentType.DOCUMENT_RAW,
        stage=Stage.RAW,
        status=ArtifactStatus.ACTIVE,
        media_type="application/pdf",
        processing_profile=ProcessingProfile.INDEX,
        beat="government:city-council",
        geo="us:il:springfield:springfield",
        source_id="src_x",
    )
    store = MagicMock()
    store.read_row.return_value = row
    store.get_content_bytes.return_value = b"%PDF-1.4 fake"
    with patch(
        "sidekick.processing.processors.pdf.extract_markdown_from_pdf_bytes",
        return_value="## Agenda\n\nItem one.",
    ):
        process_pdf_to_document_text("art_raw", store)

    store.write_with_bytes.assert_called_once()
    args, kwargs = store.write_with_bytes.call_args
    out = args[0]
    body = args[1]
    assert body == "## Agenda\n\nItem one.".encode("utf-8")
    assert kwargs.get("object_content_type") == "text/markdown"
    assert out.content_type == ContentType.DOCUMENT_TEXT
    assert out.stage == Stage.PROCESSED
    assert out.media_type == "text/markdown"
    assert out.derived_from == ["art_raw"]
    assert out.created_by == "processor:marker"
    assert out.processing_profile == ProcessingProfile.INDEX


def test_warm_marker_cache_command_initializes_models():
    runner = CliRunner()

    with patch("sidekick.processing.cli.warm_marker_cache") as warm:
        result = runner.invoke(app, ["warm-marker-cache"])

    assert result.exit_code == 0
    warm.assert_called_once_with()
    assert "Marker model cache is ready." in result.stdout
