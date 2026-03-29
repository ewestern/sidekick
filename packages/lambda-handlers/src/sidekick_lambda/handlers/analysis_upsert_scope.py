"""Upsert analysis scope state from an artifact payload."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.analysis_scope import upsert_scope_state
from sidekick_lambda.runtime import session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    detail = event.get("detail", event)
    artifact_id = detail["id"]
    execution_arn = event["execution_arn"]
    with session() as db:
        return upsert_scope_state(db, artifact_id=artifact_id, execution_arn=execution_arn)
