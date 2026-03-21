"""Wire ArtifactStore + ObjectStore + EventBus + AgentConfigRegistry from the environment."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.event_bus import LocalEventBus
from sidekick.core.object_store import ObjectStore, create_object_store

load_dotenv()


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def build_processing_runtime() -> tuple[ArtifactStore, ObjectStore, LocalEventBus, AgentConfigRegistry]:
    """Construct dependencies for processing CLI and workers."""
    db = database_url()
    event_bus = LocalEventBus(dsn=db)
    object_store = create_object_store()
    artifact_store = ArtifactStore(
        db_url=db,
        object_store=object_store,
        event_bus=event_bus,
    )
    config_registry = AgentConfigRegistry(db_url=db)
    return artifact_store, object_store, event_bus, config_registry
