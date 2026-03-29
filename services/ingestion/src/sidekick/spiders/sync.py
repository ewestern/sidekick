"""Sync spider metadata to the Sidekick API."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from http import HTTPStatus

from rich.console import Console

from sidekick_client.api.sources import (
    create_source_sources_post as _api_create_source,
    get_source_sources_source_id_get as _api_get_source,
    patch_source_sources_source_id_patch as _api_patch_source,
)
from sidekick_client.client import AuthenticatedClient
from sidekick_client.models.source_create import SourceCreate
from sidekick_client.models.source_create_schedule_type_0 import SourceCreateScheduleType0
from sidekick_client.models.source_patch import SourcePatch
from sidekick_client.models.source_patch_schedule_type_0 import SourcePatchScheduleType0

from sidekick.spiders._discovery import discover_spiders

console = Console()


def sync_spiders() -> tuple[int, int]:
    """Upsert Source rows via the Sidekick API from discovered spider classes.

    Reads SIDEKICK_API_URL and SIDEKICK_API_KEY from the environment.
    Health fields are preserved on update.

    Returns:
        (created, updated) counts.

    Raises:
        RuntimeError: if required env vars are missing or the API returns an unexpected status.
    """
    api_url = os.environ.get("SIDEKICK_API_URL")
    api_key = os.environ.get("SIDEKICK_API_KEY")
    if not api_url or not api_key:
        raise RuntimeError(
            "SIDEKICK_API_URL and SIDEKICK_API_KEY must be set.")

    spiders = discover_spiders()
    if not spiders:
        return 0, 0

    client = AuthenticatedClient(
        base_url=api_url,
        token=api_key,
        auth_header_name="X-API-Key",
        prefix="",
    )

    created = updated = 0
    for source_id, cls in spiders.items():
        meta = cls.get_meta()

        resp = _api_get_source.sync_detailed(source_id, client=client)

        if resp.status_code == HTTPStatus.NOT_FOUND:
            schedule_obj = (
                SourceCreateScheduleType0.from_dict(
                    {"type": "cron", "expr": meta.schedule})
                if meta.schedule
                else None
            )
            body = SourceCreate(
                id=source_id,
                name=meta.name,
                endpoint=meta.endpoint,
                beat=meta.beat.beat_id if meta.beat is not None else None,
                geo=meta.geo.geo_id,
                schedule=schedule_obj,
                registered_at=datetime.now(UTC),
                source_tier=meta.source_tier.value,
                outlet=meta.outlet,
            )
            _api_create_source.sync(client=client, body=body)
            created += 1
            console.print(f"  Created [green]{source_id}[/green]")

        elif resp.status_code == HTTPStatus.OK:
            schedule_obj = (
                SourcePatchScheduleType0.from_dict(
                    {"type": "cron", "expr": meta.schedule})
                if meta.schedule
                else None
            )
            body = SourcePatch(
                name=meta.name,
                endpoint=meta.endpoint,
                beat=meta.beat.beat_id if meta.beat is not None else None,
                geo=meta.geo.geo_id,
                schedule=schedule_obj,
                source_tier=meta.source_tier.value,
                outlet=meta.outlet,
            )
            _api_patch_source.sync(source_id, client=client, body=body)
            updated += 1
            console.print(f"  Updated [cyan]{source_id}[/cyan]")

        else:
            raise RuntimeError(
                f"Unexpected {resp.status_code} for {source_id}")

    return created, updated
