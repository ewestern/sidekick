"""CLI for acquisition and processing — ``sidekick-process``."""

from __future__ import annotations

import logging
from typing import Optional

import typer
from rich.console import Console

from sidekick.processing.acquisition.hls import acquire_hls_stub
from sidekick.processing.processors.entity_extract import process_to_entity_extract
from sidekick.processing.processors.pdf import process_pdf_to_document_text
from sidekick.processing.processors.summary import process_to_summary
from sidekick.processing.processors.transcript import process_audio_to_transcript
from sidekick.processing.router import (
    UnsupportedProcessingError,
    can_acquire_hls_stub,
    resolve_active_raw_processor,
    resolve_enrichment_input,
)
from sidekick.processing.runtime import build_processing_runtime
from sidekick.processing.seed_configs import seed as seed_processing_configs

app = typer.Typer(no_args_is_help=True, help="Acquisition and processing (Phase 3)")
console = Console()
logger = logging.getLogger(__name__)


@app.command("acquire")
def cmd_acquire(artifact_id: str) -> None:
    """Complete a pending HLS raw stub (ffmpeg → S3 → complete_acquisition)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, object_store, _, _registry = build_processing_runtime()
    row = store.read_row(artifact_id)
    if not can_acquire_hls_stub(row):
        console.print(
            "[red]Not an HLS pending_acquisition stub (need .m3u8 acquisition_url).[/red]"
        )
        raise typer.Exit(code=1)
    try:
        acquire_hls_stub(artifact_id, store, object_store)
    except UnsupportedProcessingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:  # pragma: no cover
        logger.exception("Acquisition failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Acquisition complete for {artifact_id}[/green]")


@app.command("process")
def cmd_process(
    artifact_id: str,
    whisper_model: str = typer.Option(
        "base",
        "--whisper-model",
        help="faster-whisper model size (transcript path only)",
    ),
) -> None:
    """Run PDF text extraction or transcription on an **active** raw artifact."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, _, _, _registry = build_processing_runtime()
    row = store.read_row(artifact_id)
    try:
        kind = resolve_active_raw_processor(row)
    except UnsupportedProcessingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    try:
        if kind == "pdf_text":
            new_id = process_pdf_to_document_text(artifact_id, store)
        else:
            new_id = process_audio_to_transcript(
                artifact_id, store, model_size=whisper_model
            )
    except Exception as exc:  # pragma: no cover
        logger.exception("Processing failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Wrote processed artifact {new_id}[/green]")


@app.command("enrich")
def cmd_enrich(
    artifact_id: str,
    only: Optional[str] = typer.Option(
        None,
        "--only",
        help="Run only one enrichment: 'summary' or 'entity-extract'",
    ),
) -> None:
    """Run LLM enrichment (summary and/or entity-extract) on a processed text artifact."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store, _, _, registry = build_processing_runtime()
    row = store.read_row(artifact_id)

    try:
        resolve_enrichment_input(row)
    except UnsupportedProcessingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if only is not None and only not in ("summary", "entity-extract"):
        console.print("[red]--only must be 'summary' or 'entity-extract'[/red]")
        raise typer.Exit(code=1)

    try:
        if only in (None, "summary"):
            summary_id = process_to_summary(artifact_id, store, registry)
            console.print(f"[green]Wrote summary artifact {summary_id}[/green]")

        if only in (None, "entity-extract"):
            entity_id = process_to_entity_extract(artifact_id, store, registry)
            console.print(f"[green]Wrote entity-extract artifact {entity_id}[/green]")

    except KeyError as exc:
        console.print(f"[red]Missing agent config — run seed-configs first: {exc}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:  # pragma: no cover
        logger.exception("Enrichment failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


@app.command("seed-configs")
def cmd_seed_configs() -> None:
    """Upsert agent_configs rows for enrichment processors (processor:summary, processor:entity-extract)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _, _, _, registry = build_processing_runtime()
    try:
        seed_processing_configs()
        console.print("[green]Seeded processor:summary and processor:entity-extract configs.[/green]")
    except Exception as exc:  # pragma: no cover
        logger.exception("Seed failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
