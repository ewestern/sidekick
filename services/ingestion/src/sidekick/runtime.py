"""Wire core services from environment (CLI and local runs)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.event_bus import LocalEventBus
from sidekick.core.object_store import create_object_store
from sidekick.registry.registry import SourceRegistry

load_dotenv()


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def build_runtime() -> tuple[
    SourceRegistry,
    AgentConfigRegistry,
    ArtifactStore,
    LocalEventBus,
]:
    db = database_url()
    registry = SourceRegistry(db)
    config_registry = AgentConfigRegistry(db)
    event_bus = LocalEventBus(dsn=db)
    object_store = create_object_store()
    artifact_store = ArtifactStore(
        db_url=db,
        object_store=object_store,
        event_bus=event_bus,
    )
    return registry, config_registry, artifact_store, event_bus
