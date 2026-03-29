"""Minimal runtime wiring for Lambda (env only — no ECS / Scrapy)."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlmodel import Session

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.embeddings import build_embed_fn
from sidekick.core.object_store import ObjectStore, create_object_store
from sidekick.registry.registry import SourceRegistry


def _database_url() -> str:
    return os.environ["DATABASE_URL"]


def source_registry() -> SourceRegistry:
    """Return a `SourceRegistry` backed by ``DATABASE_URL``."""
    return SourceRegistry(db_url=_database_url())


def engine() -> Engine:
    """Return a SQLAlchemy engine backed by ``DATABASE_URL``."""
    return create_engine(_database_url())


def session() -> Session:
    """Return a new SQLModel session backed by ``DATABASE_URL``."""
    return Session(engine())


def object_store() -> ObjectStore:
    """Return the configured object store for Lambda handlers."""
    return create_object_store()


def artifact_store() -> ArtifactStore:
    """Return an ArtifactStore wired to the Lambda environment."""
    return ArtifactStore(
        db_url=_database_url(),
        object_store=object_store(),
        embed_fn=build_embed_fn(),
    )
