"""Claim analysis scope ownership for the current Step Functions execution."""

from __future__ import annotations

from typing import Any

from sidekick_lambda.analysis_scope import claim_scope
from sidekick_lambda.runtime import session


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    with session() as db:
        return claim_scope(
            db,
            scope_key=event["scope_key"],
            execution_arn=event["execution_arn"],
        )
