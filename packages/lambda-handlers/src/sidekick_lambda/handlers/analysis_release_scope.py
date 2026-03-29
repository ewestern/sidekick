"""Release analysis scope ownership."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.analysis_scope import release_scope
from sidekick_lambda.runtime import session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    with session() as db:
        return release_scope(
            db,
            scope_key=event["scope_key"],
            execution_arn=event["execution_arn"],
            keep_dirty=bool(event.get("keep_dirty", False)),
            error=event.get("error"),
        )
