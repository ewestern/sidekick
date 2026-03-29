"""CLI for the editor agent — ``sidekick-editor``."""

from __future__ import annotations

import json
import logging
import sys

import typer
from rich.console import Console

from sidekick.editor.agent import DEFAULT_AGENT_ID, run_editor_agent
from sidekick.editor.runtime import build_editor_runtime, database_url
from sidekick.editor.seed_configs import seed as seed_editor_configs

app = typer.Typer(no_args_is_help=True, help="Editor agent — draft tier (Phase 5)")
console = Console()
logger = logging.getLogger(__name__)


@app.command("draft")
def cmd_draft(
    candidate_id: str = typer.Option(..., "--candidate-id", help="Story-candidate artifact ID"),
    agent_id: str = typer.Option(DEFAULT_AGENT_ID, help="Agent config ID to use"),
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Run the editor agent for a story-candidate and write a story-draft."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    artifact_store, _, config_registry = build_editor_runtime()
    try:
        written_ids = run_editor_agent(
            candidate_id=candidate_id,
            artifact_store=artifact_store,
            config_registry=config_registry,
            db_url=database_url(),
            agent_id=agent_id,
        )
    except KeyError as exc:
        print(
            f"Missing agent config — run seed-configs first: {exc}", file=sys.stderr
        )
        raise typer.Exit(code=1)
    except Exception as exc:
        logger.exception("Editor agent run failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)

    if output_json:
        print(json.dumps({"written_artifact_ids": written_ids}))
    else:
        if written_ids:
            console.print(
                f"[green]Wrote {len(written_ids)} artifact(s): {', '.join(written_ids)}[/green]"
            )
        else:
            console.print("[yellow]Agent completed but wrote no artifacts.[/yellow]")


@app.command("seed-configs")
def cmd_seed_configs() -> None:
    """Upsert agent_configs rows for editor agents."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        seed_editor_configs()
        console.print("[green]Seeded editor-agent config.[/green]")
    except Exception as exc:
        logger.exception("Seed failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
