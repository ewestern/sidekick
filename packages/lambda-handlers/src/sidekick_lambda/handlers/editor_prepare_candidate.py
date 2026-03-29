"""Prepare and gate a story-candidate for editorial orchestration."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.editorial import prepare_candidate
from sidekick_lambda.runtime import artifact_store, session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    detail = event.get("detail", event)
    artifact_id = detail["id"]
    with session() as db:
        return prepare_candidate(db, artifact_store(), artifact_id=artifact_id)
