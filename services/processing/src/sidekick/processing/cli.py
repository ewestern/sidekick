"""CLI for acquisition and processing — ``sidekick-process``."""

from __future__ import annotations

import json
import logging
import sys
import typer
from rich.console import Console

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.processing.acquisition.hls import acquire_hls_stub
from sidekick.processing.processors.entity_extract import process_to_entity_extract
from sidekick.processing.processors.pdf import process_pdf_to_document_text, warm_marker_cache
from sidekick.processing.processors.summary import process_to_summary
from sidekick.processing.router import (
    UnsupportedProcessingError,
    can_acquire_hls_stub,
)
from sidekick.processing.runtime import build_processing_runtime
from sidekick.processing.seed_configs import seed as seed_processing_configs

app = typer.Typer(no_args_is_help=True,
                  help="Acquisition and processing (Phase 3)")
console = Console()
logger = logging.getLogger(__name__)


@app.command("acquire")
def cmd_acquire(
    artifact_id: str,
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Complete a pending HLS raw stub (ffmpeg → S3 → complete_acquisition)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, object_store, _registry = build_processing_runtime()
    row = store.read_row(artifact_id)
    if not can_acquire_hls_stub(row):
        print("Not an HLS pending_acquisition stub (need .m3u8 acquisition_url).", file=sys.stderr)
        raise typer.Exit(code=1)
    try:
        acquire_hls_stub(artifact_id, store, object_store)
    except UnsupportedProcessingError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as exc:  # pragma: no cover
        logger.exception("Acquisition failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)
    if output_json:
        completed = store.read_row(artifact_id)
        print(json.dumps({
            "artifact_id": artifact_id,
            "stage": completed.stage,
            "content_type": completed.content_type,
            "media_type": completed.media_type,
            "status": completed.status,
            "processing_profile": completed.processing_profile,
        }))
    else:
        console.print(f"[green]Acquisition complete for {artifact_id}[/green]")


@app.command("extract-pdf")
def cmd_extract_pdf(
    artifact_id: str,
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Run PDF text extraction on an **active** raw PDF artifact."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, _, _registry = build_processing_runtime()
    row = store.read_row(artifact_id)
    if row.media_type != "application/pdf":
        logger.info(f"Artifact {artifact_id!r} is not a PDF.")
        return
    try:
        new_id = process_pdf_to_document_text(artifact_id, store)
    except Exception as exc:  # pragma: no cover
        logger.exception("PDF text extraction failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)
    if output_json:
        new_row = store.read_row(new_id)
        print(json.dumps({
            "artifact_id": new_id,
            "stage": new_row.stage,
            "content_type": new_row.content_type,
            "media_type": new_row.media_type,
            "status": new_row.status,
            "processing_profile": new_row.processing_profile,
        }))
    else:
        console.print(f"[green]Wrote processed artifact {new_id}[/green]")


@app.command("warm-marker-cache")
def cmd_warm_marker_cache() -> None:
    """Download and initialize Marker model artifacts into the configured local cache."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        warm_marker_cache()
    except Exception as exc:  # pragma: no cover
        logger.exception("Marker cache warmup failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)
    console.print("[green]Marker model cache is ready.[/green]")


def _processing_runtime() -> tuple[ArtifactStore, AgentConfigRegistry]:
    """Return store + registry for a single enrichment step."""
    store, _, registry = build_processing_runtime()
    return store, registry


@app.command("summary")
def cmd_summary(
    artifact_id: str,
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Run LLM summary enrichment on a processed text artifact."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, registry = _processing_runtime()
    try:
        summary_id = process_to_summary(artifact_id, store, registry)
    except KeyError as exc:
        print(
            f"Missing agent config — run seed-configs first: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as exc:  # pragma: no cover
        logger.exception("Summary enrichment failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)
    if output_json:
        new_row = store.read_row(summary_id)
        print(json.dumps({
            "artifact_id": summary_id,
            "stage": new_row.stage,
            "content_type": new_row.content_type,
            "media_type": new_row.media_type,
            "status": new_row.status,
            "processing_profile": new_row.processing_profile,
        }))
    else:
        console.print(f"[green]Wrote summary artifact {summary_id}[/green]")


@app.command("entity-extract")
def cmd_entity_extract(
    artifact_id: str,
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Run LLM entity-extract enrichment on a processed text artifact."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, registry = _processing_runtime()
    entity_id = process_to_entity_extract(artifact_id, store, registry)
    if output_json:
        new_row = store.read_row(entity_id)
        print(json.dumps({
            "artifact_id": entity_id,
            "stage": new_row.stage,
            "content_type": new_row.content_type,
            "media_type": new_row.media_type,
            "status": new_row.status,
            "processing_profile": new_row.processing_profile,
        }))
    else:
        console.print(
            f"[green]Wrote entity-extract artifact {entity_id}[/green]")


@app.command("seed-configs")
def cmd_seed_configs() -> None:
    """Upsert agent_configs rows for enrichment processors."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _, _, registry = build_processing_runtime()
    try:
        seed_processing_configs()
        console.print(
            "[green]Seeded processor:summary, processor:entity-extract, processor:structured-data.[/green]"
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Seed failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
