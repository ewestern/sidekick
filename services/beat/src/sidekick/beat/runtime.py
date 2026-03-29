"""Wire ArtifactStore + ObjectStore + AgentConfigRegistry from the environment."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.assignment_store import AssignmentStore
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.embeddings import build_embed_fn
from sidekick.core.object_store import ObjectStore, create_object_store

load_dotenv()


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def build_beat_runtime() -> tuple[ArtifactStore, ObjectStore, AgentConfigRegistry, AssignmentStore]:
    """Construct dependencies for beat agent CLI and workers."""
    db = database_url()
    object_store = create_object_store()
    artifact_store = ArtifactStore(
        db_url=db,
        object_store=object_store,
        embed_fn=build_embed_fn(),
    )
    config_registry = AgentConfigRegistry(db_url=db)
    assignment_store = AssignmentStore(db_url=db)
    return artifact_store, object_store, config_registry, assignment_store
