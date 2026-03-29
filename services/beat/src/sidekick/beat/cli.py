"""CLI for the beat agent — ``sidekick-beat``."""

from __future__ import annotations

import json
import logging
import sys
from datetime import date
from typing import Optional

import typer
from rich.console import Console

from sidekick.beat.agent import DEFAULT_AGENT_ID, run_beat_agent
from sidekick.beat.runtime import build_beat_runtime
from sidekick.beat.scope import DateWindowScope, EventGroupScope
from sidekick.beat.seed_configs import seed as seed_beat_configs

app = typer.Typer(no_args_is_help=True,
                  help="Beat agent — analysis tier (Phase 4)")
console = Console()
logger = logging.getLogger(__name__)


@app.command("brief")
def cmd_brief(
    beat: str = typer.Option(...,
                             help="Beat identifier (e.g. government:city-council)"),
    geo: str = typer.Option(...,
                            help="Geo identifier (e.g. us:ca:shasta:redding)"),
    event_group: Optional[str] = typer.Option(
        None, "--event-group", help="Event group ID (e.g. shasta-bos:2026-03-25). Mutually exclusive with --since/--until."),
    since: Optional[str] = typer.Option(
        None, help="Start of date window (YYYY-MM-DD). Requires --until."),
    until: Optional[str] = typer.Option(
        None, help="End of date window (YYYY-MM-DD). Requires --since."),
    agent_id: str = typer.Option(
        DEFAULT_AGENT_ID, help="Agent config ID to use"),
    output_json: bool = typer.Option(False, "--output-json"),
) -> None:
    """Run the beat agent and write analysis artifacts.

    Provide either --event-group (for a single event) or --since + --until
    (for an assignment date window). These options are mutually exclusive.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Validate scope args.
    if event_group and (since or until):
        print("--event-group and --since/--until are mutually exclusive.",
              file=sys.stderr)
        raise typer.Exit(code=1)
    if not event_group and not (since and until):
        print("Provide either --event-group or both --since and --until.",
              file=sys.stderr)
        raise typer.Exit(code=1)
    if (since and not until) or (until and not since):
        print("--since and --until must both be provided together.", file=sys.stderr)
        raise typer.Exit(code=1)

    since_parsed = date.fromisoformat(since) if since else None
    until_parsed = date.fromisoformat(until) if until else None

    scope = (
        EventGroupScope(event_group=event_group)
        if event_group
        else DateWindowScope(since=since_parsed, until=until_parsed) # type: ignore[arg-type]
    )

    artifact_store, _, config_registry, assignment_store = build_beat_runtime()
    try:
        written_ids = run_beat_agent(
            beat=beat,
            geo=geo,
            scope=scope,
            artifact_store=artifact_store,
            config_registry=config_registry,
            assignment_store=assignment_store,
            agent_id=agent_id,
        )
    except KeyError as exc:
        print(
            f"Missing agent config — run seed-configs first: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as exc:
        logger.exception("Beat agent run failed")
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1)

    if output_json:
        print(json.dumps({"written_artifact_ids": written_ids}))
    else:
        if written_ids:
            console.print(
                f"[green]Wrote {len(written_ids)} artifact(s): {', '.join(written_ids)}[/green]")
        else:
            console.print(
                "[yellow]Agent completed but wrote no artifacts.[/yellow]")


@app.command("seed-configs")
def cmd_seed_configs() -> None:
    """Upsert agent_configs rows for beat agents."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        seed_beat_configs()
        console.print(
            "[green]Seeded beat-agent:government:city-council config.[/green]")
    except Exception as exc:
        logger.exception("Seed failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
