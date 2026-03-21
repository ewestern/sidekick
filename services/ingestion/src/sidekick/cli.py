"""sidekick CLI — seed configs, examine sources, run spiders."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.table import Table

from sidekick.agents.examination.examination import examine_source
from sidekick.core.models import Source
from sidekick.core.object_store import create_object_store
from sidekick.core.vocabulary import validate_beat, validate_geo
from sidekick.runtime import build_runtime
from sidekick.seed_configs import seed as seed_agent_configs
from sidekick.spiders._discovery import discover_spiders
from sidekick.spiders._runner import run_spider, run_spiders

app = typer.Typer(no_args_is_help=True, help="Local news ingestion CLI")
console = Console()


@app.command("seed-configs")
def cmd_seed_configs() -> None:
    """Upsert agent_configs for the source-examination (code-gen) agent."""
    seed_agent_configs()
    console.print("[green]Seeded agent_configs.[/green]")


@app.command("examine")
def cmd_examine(
    goal: str = typer.Argument(help="What are we trying to retrieve from the source?"),
    url: str = typer.Argument(help="Source endpoint URL"),
    beat: str = typer.Argument(help="Coverage beat in canonical format (e.g. government:city_council)"),
    geo: str = typer.Argument(help="Geography identifier in canonical format (e.g. us:il:springfield:springfield)"),
    name: str | None = typer.Argument(None, help="Provisional source name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Log each tool call and result"),
) -> None:
    """Browse a source and generate a Scrapy spider file.

    The agent browses the source, understands the page structure, and writes a spider
    to sidekick/spiders/.  Review and commit the generated file, then run
    ``sidekick spiders sync`` to register it in the database.
    """
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        validate_beat(beat)
        validate_geo(geo)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"Examining [cyan]{url}[/cyan]...")
    path = asyncio.run(
        examine_source(
            goal=goal,
            url=url,
            beat=beat,
            geo=geo,
            name=name,
        )
    )
    if path:
        console.print(f"[green]Spider written to:[/green] {path}")
        console.print("Review the file, then run [bold]sidekick spiders sync[/bold].")
    else:
        console.print("[red]Examination agent did not produce a spider file.[/red]")
        raise typer.Exit(code=1)


# ── spiders sub-app ────────────────────────────────────────────────────────────

spiders_app = typer.Typer(help="Spider management commands")
app.add_typer(spiders_app, name="spiders")


@spiders_app.command("list")
def cmd_spiders_list() -> None:
    """List all discovered spider classes with DB health."""
    registry, _, _, _ = build_runtime()
    spiders = discover_spiders()
    if not spiders:
        console.print("No spiders found.")
        return

    table = Table("source_id", "name", "beat", "geo", "schedule", "last_checked", "status")
    for source_id, cls in sorted(spiders.items()):
        meta = cls.get_meta()
        try:
            source = registry.get(source_id)
            health = source.health or {}
            last_checked = health.get("last_checked", "-")
            status = health.get("status", source.examination_status)
        except KeyError:
            last_checked = "(not synced)"
            status = "-"
        table.add_row(
            source_id,
            meta.name,
            meta.beat,
            meta.geo,
            meta.schedule or "-",
            last_checked,
            status,
        )
    console.print(table)


@spiders_app.command("sync")
def cmd_spiders_sync() -> None:
    """Upsert Source rows in DB from discovered spider classes.

    Health fields (last_checked, last_new_item, status) are preserved on update.
    ``examination_status`` is set to ``active`` for all discovered spiders.
    """
    registry, _, _, _ = build_runtime()
    spiders = discover_spiders()
    if not spiders:
        console.print("No spiders found — nothing to sync.")
        return

    created = updated = 0
    for source_id, cls in spiders.items():
        meta = cls.get_meta()
        schedule_dict = (
            {"type": "cron", "expr": meta.schedule} if meta.schedule else None
        )
        try:
            registry.get(source_id)
            # Exists — update metadata fields but preserve health
            registry.update(
                source_id,
                {
                    "name": meta.name,
                    "endpoint": meta.endpoint,
                    "beat": meta.beat,
                    "geo": meta.geo,
                    "schedule": schedule_dict,
                    "expected_content": meta.expected_content,
                    "examination_status": "active",
                },
            )
            updated += 1
            console.print(f"  Updated [cyan]{source_id}[/cyan]")
        except KeyError:
            source = Source(
                id=source_id,
                name=meta.name,
                endpoint=meta.endpoint,
                beat=meta.beat,
                geo=meta.geo,
                schedule=schedule_dict,
                expected_content=meta.expected_content,
                examination_status="active",
                discovered_by="spider",
                registered_at=datetime.now(UTC),
            )
            registry.create(source)
            created += 1
            console.print(f"  Created [green]{source_id}[/green]")

    console.print(f"Sync complete: {created} created, {updated} updated.")


@spiders_app.command("run")
def cmd_spiders_run(
    spider_name: str = typer.Argument(help="Spider source_id or Scrapy name"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run a specific spider by source_id."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    spiders = discover_spiders()
    cls = spiders.get(spider_name)
    if cls is None:
        # Try matching by scrapy name
        cls = next(
            (c for c in spiders.values() if c.name == spider_name), None
        )
    if cls is None:
        console.print(f"[red]Spider not found:[/red] {spider_name}")
        raise typer.Exit(code=1)

    registry, _, artifact_store, event_bus = build_runtime()
    object_store = create_object_store()
    n = run_spider(cls, artifact_store, object_store, registry, event_bus, verbose=verbose)
    console.print(f"Ingested [green]{n}[/green] new item(s).")


@spiders_app.command("due")
def cmd_spiders_due(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run all spiders whose cron schedule is due."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    registry, _, artifact_store, event_bus = build_runtime()
    object_store = create_object_store()

    # get_due_sources() checks examination_status="active" + cron schedule
    due_sources = registry.get_due_sources()
    if not due_sources:
        console.print("No sources due.")
        return

    due_ids = {s.id for s in due_sources}
    spiders = discover_spiders()
    due_spiders = [cls for sid, cls in spiders.items() if sid in due_ids]

    if not due_spiders:
        console.print("No spider classes found for due sources.")
        return

    console.print(f"Running {len(due_spiders)} spider(s)...")
    results = run_spiders(due_spiders, artifact_store, object_store, registry, event_bus, verbose=verbose)
    for source_id, count in results.items():
        console.print(f"  {source_id}: [green]{count}[/green] new")


@spiders_app.command("test")
def cmd_spiders_test(
    spider_name: str = typer.Argument(help="Spider source_id or Scrapy name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip artifact writes"),
) -> None:
    """Run a spider with verbose logging but without writing artifacts (dry run).

    Useful for validating a newly generated spider before committing.
    """
    spiders = discover_spiders()
    cls = spiders.get(spider_name) or next(
        (c for c in spiders.values() if c.name == spider_name), None
    )
    if cls is None:
        console.print(f"[red]Spider not found:[/red] {spider_name}")
        raise typer.Exit(code=1)

    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    if dry_run:
        console.print("[yellow]Dry run — no artifacts will be written.[/yellow]")
        # Import here so Scrapy settings don't need real infra for a dry run
        from unittest.mock import MagicMock

        artifact_store = MagicMock()
        artifact_store.query.return_value = []
        object_store = MagicMock()
        object_store.put.return_value = "s3://dry-run/fake"
        registry = MagicMock()
        registry.update_health.return_value = None
        event_bus = MagicMock()
    else:
        registry, _, artifact_store, event_bus = build_runtime()
        object_store = create_object_store()

    n = run_spider(cls, artifact_store, object_store, registry, event_bus, verbose=True)
    console.print(f"[green]{n}[/green] item(s) would be written.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
