"""Record one completed analysis run."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.analysis_scope import record_run
from sidekick_lambda.runtime import session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    with session() as db:
        return record_run(
            db,
            scope_key=event["scope_key"],
            execution_arn=event["execution_arn"],
            written_artifact_ids=list(event.get("written_artifact_ids", [])),
        )
