"""Due-source listing for scheduled ingestion — DB is the source of truth.

Used by ingestion CLI and Lambda handlers. Does not import Scrapy or spider modules.
"""

from __future__ import annotations

from typing import TypedDict

from sidekick.registry.registry import SourceRegistry


class ListDueSpidersPayload(TypedDict):
    """JSON shape for ``spiders list-due`` and Step Functions ``SpiderMap`` input."""

    spiders: list[str]


def list_due_source_ids(registry: SourceRegistry) -> list[str]:
    """Return source IDs due for a scheduled fetch (active status + cron per registry rules)."""
    return [s.id for s in registry.get_due_sources()]


def list_due_spiders_payload(registry: SourceRegistry) -> ListDueSpidersPayload:
    """Return ``{\"spiders\": [source_id, ...]}`` for CLI / orchestration."""
    return {"spiders": list_due_source_ids(registry)}
