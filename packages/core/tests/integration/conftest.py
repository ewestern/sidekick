"""Shared fixtures for integration tests.

Requires: docker compose up (Postgres + MinIO running locally).
"""

import os

import boto3
import pytest
from dotenv import load_dotenv
from sqlmodel import SQLModel

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.event_bus import LocalEventBus
from sidekick.core.object_store import S3ObjectStore

load_dotenv()

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql://sidekick:sidekick@localhost:5432/sidekick"
)
BUCKET = os.environ.get("S3_BUCKET", "artifacts")


@pytest.fixture(scope="session")
def object_store() -> S3ObjectStore:
    store = S3ObjectStore(BUCKET)
    return store


@pytest.fixture(scope="session")
def event_bus() -> LocalEventBus:
    return LocalEventBus(dsn=DB_URL)


@pytest.fixture()
def artifact_store(object_store, event_bus) -> ArtifactStore:
    from sqlalchemy import create_engine

    engine = create_engine(DB_URL)
    # Create tables fresh for each test (drop and recreate)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    return ArtifactStore(
        db_url=DB_URL,
        object_store=object_store,
        event_bus=event_bus,
    )
