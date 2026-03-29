"""Module-level run-context registry for passing live objects to Scrapy components.

Scrapy deepcopies its settings dict during ``CrawlerRunner.__init__``, so
database connections and boto3 clients cannot be stored there directly.  The
standard pattern is to store only a string token in settings and look up the
real objects here by that token.

Usage::

    # In the runner, before starting the CrawlerProcess:
    token = register(artifact_store=store, object_store=obj_store, max_items=None)
    settings["SIDEKICK_RUN_TOKEN"] = token
    ...
    # After the crawl:
    deregister(token)

    # In a pipeline or middleware from_crawler classmethod:
    from sidekick.spiders._context import get
    ctx = get(crawler.settings["SIDEKICK_RUN_TOKEN"])
    return cls(ctx.artifact_store, ctx.object_store)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.object_store import ObjectStore

_registry: dict[str, "RunContext"] = {}


@dataclass(frozen=True)
class RunContext:
    artifact_store: ArtifactStore
    object_store: ObjectStore
    artifact_results: dict[str, list[dict]] = field(default_factory=dict)
    max_items: int | None = None
    min_date: date | None = None


def register(
    artifact_store: ArtifactStore,
    object_store: ObjectStore,
    *,
    max_items: int | None = None,
    min_date: date | None = None,
) -> str:
    """Store a run context and return its token."""
    token = str(uuid.uuid4())
    _registry[token] = RunContext(
        artifact_store=artifact_store,
        object_store=object_store,
        max_items=max_items,
        min_date=min_date,
    )
    return token


def get(token: str) -> RunContext:
    """Retrieve a run context by token.

    Raises:
        KeyError: if the token is not registered.
    """
    return _registry[token]


def deregister(token: str) -> None:
    """Remove a run context. Safe to call even if the token is already gone."""
    _registry.pop(token, None)
