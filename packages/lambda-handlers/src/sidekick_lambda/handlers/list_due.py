"""List source IDs due for scheduled ingestion — same contract as ``sidekick spiders list-due``."""

from __future__ import annotations

from typing import Any

from sidekick.core.due_sources import list_due_spiders_payload
from sidekick.core.due_sources import ListDueSpidersPayload
from sidekick_lambda.runtime import source_registry


def handler(event: dict[str, Any], context: Any) -> ListDueSpidersPayload:
    """AWS Lambda handler; returns ``ListDueSpidersPayload``."""
    registry = source_registry()
    return list_due_spiders_payload(registry)
