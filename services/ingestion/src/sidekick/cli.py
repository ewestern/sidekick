"""sidekick CLI — seed configs, fetch-url, spider scaffold/sync/run."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import UTC, date, datetime

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from sidekick.agents.tools.http import fetch_url as http_fetch
from sidekick.core.due_sources import list_due_spiders_payload
from sidekick.core.object_store import create_object_store
from sidekick.core.vocabulary import validate_beat, validate_geo
from sidekick.runtime import build_runtime
from sidekick.seed_configs import seed as seed_agent_configs
from sidekick.spiders._discovery import discover_spiders
from sidekick.spiders._runner import RunResult, run_spider, run_spiders
from sidekick.spiders._scaffold import scaffold_spider
from sidekick.spiders.sync import sync_spiders

app = typer.Typer(no_args_is_help=True, help="Local news ingestion CLI")
console = Console()


@app.command("seed-configs")
def cmd_seed_configs() -> None:
    """Upsert agent_configs (ingestion seed hook; may be empty)."""
    seed_agent_configs()
    console.print("[green]Seeded agent_configs.[/green]")


@app.command("fetch-url")
def cmd_fetch_url(
    url: str = typer.Argument(help="URL to fetch"),
    raw: bool = typer.Option(
        False, "--raw", help="Print raw JSON result instead of rendered HTML"),
) -> None:
    """Fetch a URL through the headless browser and print what the agent sees.

    Useful for inspecting JS-rendered pages before editing a spider.
    """

    result = http_fetch(url)
    if raw:
        console.print_json(json.dumps(result.to_dict()))
    else:
        if result.error:
            console.print(
                f"[red]Error:[/red] {result.error} (status {result.status_code})")
            raise typer.Exit(code=1)
        console.print(
            f"[dim]status={result.status_code} url={result.final_url} content_type={result.content_type}[/dim]")
        if result.body:
            console.print(Syntax(result.body, "html", word_wrap=True))
        else:
            console.print("[yellow](empty body — binary or redirect)[/yellow]")


# ── spiders sub-app ────────────────────────────────────────────────────────────

spiders_app = typer.Typer(help="Spider management commands")
app.add_typer(spiders_app, name="spiders")


@spiders_app.command("scaffold")
def cmd_spiders_scaffold(
    geo: str = typer.Argument(
        help="Geo identifier (e.g. us:ca:shasta:redding)"),
    endpoint: str = typer.Argument(help="Starting URL for the spider"),
    source: str = typer.Argument(
        help='Short source descriptor (e.g. "agendas", "videos", "packets")'),
    beat: str | None = typer.Option(
        None, "--beat", help="Optional default beat identifier for this spider"),
    schedule: str | None = typer.Option(
        None,
        "--schedule",
        "-s",
        help='Cron expression (default: daily at local time when you run this command)',
    ),
) -> None:
    """Generate a stub spider file ready for manual implementation.

    File and identifiers are derived from geo + source:
      agendas.py
      src_us_ca_shasta_redding_agendas
      redding-agendas  (Scrapy name)

    Validates geo and optional beat, then writes a stub to services/ingestion/src/sidekick/spiders/.
    Open the file and implement parse() — see services/ingestion/SPIDERS.md for guidance.
    """
    try:
        if beat is not None:
            validate_beat(beat)
        validate_geo(geo)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    try:
        path = scaffold_spider(
            beat=beat, geo=geo, source=source, endpoint=endpoint, schedule=schedule)
    except (ValueError, FileExistsError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[green]Spider stub written to:[/green] {path}")
    console.print(
        "Implement [bold]parse()[/bold], then run [bold]sidekick spiders sync[/bold].")
    console.print(
        f"Inspect the page first: [bold]sidekick fetch-url {endpoint}[/bold]")


@spiders_app.command("list-due")
def cmd_spiders_list_due() -> None:
    """Emit JSON list of source IDs whose cron schedule is due. No side effects.

    Uses the source registry only (DB as source of truth); does not scan spider modules.
    """
    registry, _, _ = build_runtime()
    output = list_due_spiders_payload(registry)
    print(json.dumps(output))


@spiders_app.command("list")
def cmd_spiders_list() -> None:
    """List all discovered spider classes with DB health."""
    registry, _, _ = build_runtime()
    spiders = discover_spiders()
    if not spiders:
        console.print("No spiders found.")
        return

    table = Table("source_id", "name", "beat", "geo",
                  "schedule", "last_checked", "status")
    for source_id, cls in sorted(spiders.items()):
        meta = cls.get_meta()
        try:
            source = registry.get(source_id)
            health = source.health or {}
            last_checked = health.get("last_checked", "-")
            status = health.get("status", "-")
        except KeyError:
            last_checked = "(not synced)"
            status = "-"
        table.add_row(
            source_id,
            meta.name,
            meta.beat.beat_id if meta.beat is not None else "-",
            meta.geo.geo_id,
            meta.schedule or "-",
            last_checked,
            status,
        )
    console.print(table)


@spiders_app.command("sync")
def cmd_spiders_sync() -> None:
    """Upsert Source rows via the Sidekick API from discovered spider classes.

    Reads SIDEKICK_API_URL and SIDEKICK_API_KEY from the environment.
    Health fields (last_checked, last_new_item, status) are preserved on update.
    """
    try:
        created, updated = sync_spiders()
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    if created == 0 and updated == 0:
        console.print("No spiders found — nothing to sync.")
        return

    console.print(f"Sync complete: {created} created, {updated} updated.")


@spiders_app.command("run")
def cmd_spiders_run(
    spider_name: str = typer.Argument(help="Spider source_id or Scrapy name"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    output_json: bool = typer.Option(
        False, "--output-json", help="Emit JSON artifact list and send SFN task success"),
    max_items: int | None = typer.Option(
        None,
        "--max-items",
        min=1,
        help="Approximate cap on new RawItems emitted this run (natural crawl drain; omit for no cap)",
    ),
    min_date: str | None = typer.Option(
        None,
        "--min-date",
        help="Drop items older than this date (YYYY-MM-DD). Requests with a known date are skipped before download.",
    ),
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

    parsed_min_date: date | None = (
        date.fromisoformat(min_date) if min_date else None
    )
    registry, _, artifact_store = build_runtime()
    object_store = create_object_store()
    result: RunResult = run_spider(
        cls,
        artifact_store,
        object_store,
        registry,
        verbose=verbose,
        max_items=max_items,
        min_date=parsed_min_date,
    )
    if output_json:
        payload = {
            "source_id": result.source_id,
            "artifacts": [asdict(a) for a in result.artifacts],
        }
        print(json.dumps(payload))
    else:
        console.print(f"Ingested [green]{result.count}[/green] new item(s).")


@spiders_app.command("due")
def cmd_spiders_due(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run all spiders whose cron schedule is due."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    registry, _, artifact_store = build_runtime()
    object_store = create_object_store()

    # get_due_sources() returns active sources whose cron schedule is due
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
    results = run_spiders(due_spiders, artifact_store,
                          object_store, registry, verbose=verbose)
    for source_id, result in results.items():
        console.print(f"  {source_id}: [green]{result.count}[/green] new")


@spiders_app.command("test")
def cmd_spiders_test(
    spider_name: str = typer.Argument(help="Spider source_id or Scrapy name"),
    max_items: int | None = typer.Option(
        None,
        "--max-items",
        min=1,
        help="Approximate cap on new RawItems emitted this run (natural crawl drain; omit for no cap)",
    ),
    min_date: str | None = typer.Option(
        None,
        "--min-date",
        help="Drop items older than this date (YYYY-MM-DD). Requests with a known date are skipped before download.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Skip artifact writes"),
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
        console.print(
            "[yellow]Dry run — no artifacts will be written.[/yellow]")
        # Import here so Scrapy settings don't need real infra for a dry run
        from unittest.mock import MagicMock

        artifact_store = MagicMock()
        artifact_store.query.return_value = []
        object_store = MagicMock()
        object_store.put.return_value = "s3://dry-run/fake"
        registry = MagicMock()
        registry.update_health.return_value = None
    else:
        registry, _, artifact_store = build_runtime()
        object_store = create_object_store()
    parsed_min_date: date | None = (
        date.fromisoformat(min_date) if min_date else None
    )

    result = run_spider(cls, artifact_store, object_store,
                        registry, verbose=True, max_items=max_items, min_date=parsed_min_date)
    console.print(f"[green]{result.count}[/green] item(s) would be written.")
    console.print(f"Artifacts: {json.dumps([asdict(a) for a in result.artifacts], indent=2)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
