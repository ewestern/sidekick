"""Wire ArtifactStore + ObjectStore + embeddings from the environment."""

from __future__ import annotations

import os

import boto3
from botocore.client import BaseClient
from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.embeddings import build_embed_fn
from sidekick.core.object_store import ObjectStore, create_object_store

load_dotenv()


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def build_transcription_runtime() -> tuple[
    ArtifactStore,
    ObjectStore,
    AgentConfigRegistry,
    BaseClient,
]:
    """Construct dependencies for transcription CLI and workers.

    Returns:
        ``artifact_store``, ``object_store``, ``config_registry``,
        and a Step Functions boto3 client (``send_task_success`` / ``failure`` / ``heartbeat``).
    """
    db = database_url()
    object_store = create_object_store()
    artifact_store = ArtifactStore(
        db_url=db,
        object_store=object_store,
        embed_fn=build_embed_fn(),
    )
    config_registry = AgentConfigRegistry(db_url=db)
    sfn = boto3.client("stepfunctions")
    return artifact_store, object_store, config_registry, sfn
