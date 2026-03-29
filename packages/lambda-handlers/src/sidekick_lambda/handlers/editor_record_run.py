"""Record editorial run outputs for downstream bookkeeping."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.editorial import record_editor_run
from sidekick_lambda.runtime import session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    with session() as db:
        return record_editor_run(
            db,
            candidate_id=event["candidate_id"],
            story_key=event.get("story_key"),
            assignment_id=event.get("assignment_id"),
            written_artifact_ids=list(event.get("written_artifact_ids", [])),
        )
