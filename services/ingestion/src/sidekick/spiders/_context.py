"""Module-level run-context registry for passing live objects to Scrapy components.

Scrapy deepcopies its settings dict during ``CrawlerRunner.__init__``, so
database connections and boto3 clients cannot be stored there directly.  The
standard pattern is to store only a string token in settings and look up the
real objects here by that token.

Usage::

    # In the runner, before starting the CrawlerProcess:
    token = register(artifact_store=store, object_store=obj_store, event_bus=bus)
    settings["SIDEKICK_RUN_TOKEN"] = token
    ...
    # After the crawl:
    deregister(token)

    # In a pipeline or middleware from_crawler classmethod:
    from sidekick.spiders._context import get
    ctx = get(crawler.settings["SIDEKICK_RUN_TOKEN"])
    return cls(ctx.artifact_store, ctx.object_store, ctx.event_bus)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.event_bus import EventBus
from sidekick.core.object_store import ObjectStore

_registry: dict[str, "RunContext"] = {}


@dataclass(frozen=True)
class RunContext:
    artifact_store: ArtifactStore
    object_store: ObjectStore
    event_bus: EventBus


def register(
    artifact_store: ArtifactStore, object_store: ObjectStore, event_bus: EventBus
) -> str:
    """Store a run context and return its token."""
    token = str(uuid.uuid4())
    _registry[token] = RunContext(
        artifact_store=artifact_store, object_store=object_store, event_bus=event_bus
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
