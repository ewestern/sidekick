"""Check whether an analysis scope needs another run."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.analysis_scope import check_scope
from sidekick_lambda.runtime import session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    with session() as db:
        return check_scope(db, scope_key=event["scope_key"])
