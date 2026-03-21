"""Unit tests for ArtifactStore logic.

All database and S3 calls are mocked — these tests run without any external services.
They cover: validation rules, event bus notification, object storage, embedding generation.
"""

from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.artifact_store import ArtifactStore
from sidekick.core.models import Artifact
from sidekick.core.event_bus import EventBus
from sidekick.core.object_store import ObjectStore


def _store(embed_fn=None) -> ArtifactStore:
    """Build an ArtifactStore with all external dependencies mocked."""
    store = ArtifactStore(
        db_url="postgresql://unused",
        object_store=MagicMock(spec=ObjectStore),
        event_bus=MagicMock(spec=EventBus),
        embed_fn=embed_fn,
    )
    return store


def _patch_session(store: ArtifactStore, stored: dict | None = None):
    """Context manager that patches Session to avoid real DB calls.

    stored: optional dict of artifact_id -> Artifact for .get() lookups.
    """
    stored = stored or {}
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.get = lambda model, pk: stored.get(pk)
    mock_session.exec = MagicMock(return_value=iter([]))
    return patch("sidekick.core.artifact_store.Session", return_value=mock_session)


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

def test_raw_artifact_without_derived_from_passes_validation():
    store = _store()
    artifact = Artifact(
        id="art_1",
        content_type="document-raw",
        stage="raw",
        content_uri="s3://bucket/artifacts/raw/_/_/art_1",
    )
    with _patch_session(store):
        store.write(artifact)  # Should not raise


def test_non_raw_without_derived_from_raises():
    store = _store()
    artifact = Artifact(id="art_2", content_type="summary", stage="processed")
    with pytest.raises(ValueError, match="derived_from is required"):
        store.write(artifact)


def test_analysis_without_derived_from_raises():
    store = _store()
    artifact = Artifact(id="art_3", content_type="beat-brief", stage="analysis")
    with pytest.raises(ValueError, match="derived_from is required"):
        store.write(artifact)


def test_non_raw_with_derived_from_passes_validation():
    store = _store()
    artifact = Artifact(
        id="art_4",
        content_type="summary",
        stage="processed",
        derived_from=["art_raw_parent"],
        content_uri="s3://bucket/artifacts/processed/_/_/art_4",
    )
    with _patch_session(store):
        store.write(artifact)  # Should not raise


def test_missing_id_raises():
    store = _store()
    artifact = Artifact(id="", content_type="document-raw", stage="raw")
    with pytest.raises(ValueError, match="id is required"):
        store.write(artifact)


def test_missing_content_type_raises():
    store = _store()
    artifact = Artifact(id="art_x", content_type="", stage="raw")
    with pytest.raises(ValueError, match="content_type is required"):
        store.write(artifact)


def test_missing_stage_raises():
    store = _store()
    artifact = Artifact(id="art_y", content_type="document-raw", stage="")
    with pytest.raises(ValueError, match="stage is required"):
        store.write(artifact)


# ------------------------------------------------------------------
# Event bus notification
# ------------------------------------------------------------------

def test_write_publishes_artifact_written_event():
    store = _store()
    artifact = Artifact(
        id="art_notify",
        content_type="document-raw",
        stage="raw",
        beat="government:city_council",
        geo="us:il:springfield:springfield",
        content_uri="s3://bucket/artifacts/raw/government-city_council/us-il-springfield-springfield/art_notify",
    )
    with _patch_session(store):
        store.write(artifact)

    store._event_bus.publish.assert_called_once()
    event_type, payload = store._event_bus.publish.call_args[0]
    assert event_type == "artifact_written"
    assert payload == {
        "id": "art_notify",
        "stage": "raw",
        "content_type": "document-raw",
        "beat": "government:city_council",
        "geo": "us:il:springfield:springfield",
        "status": "active",
    }


def test_write_succeeds_even_if_event_bus_raises():
    """A failing event bus must not roll back the DB write."""
    store = _store()
    store._event_bus.publish.side_effect = RuntimeError("bus down")
    artifact = Artifact(
        id="art_bus_fail",
        content_type="document-raw",
        stage="raw",
        content_uri="s3://bucket/artifacts/raw/_/_/art_bus_fail",
    )
    with _patch_session(store):
        result = store.write(artifact)  # Should not raise
    assert result == "art_bus_fail"


# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------

def test_read_returns_artifact():
    store = _store()
    expected = Artifact(
        id="art_r",
        content_type="document-raw",
        stage="raw",
        content_uri="s3://bucket/artifacts/raw/_/_/art_r",
    )
    with _patch_session(store, stored={"art_r": expected}):
        fetched = store.read("art_r")
    assert fetched.id == "art_r"


def test_read_missing_raises():
    store = _store()
    with _patch_session(store, stored={}):
        with pytest.raises(KeyError):
            store.read("does_not_exist")


def test_read_row_does_not_fetch_object_store():
    store = _store()
    row = Artifact(
        id="art_row",
        content_type="document-raw",
        stage="raw",
        content_uri="s3://bucket/artifacts/raw/_/_/art_row",
    )
    with _patch_session(store, stored={"art_row": row}):
        out = store.read_row("art_row")
    assert out.id == "art_row"
    store._object_store.get.assert_not_called()


def test_get_content_bytes_uses_object_store():
    store = _store()
    store._object_store.get.return_value = b"%PDF-1.4"
    art = Artifact(
        id="art_bin",
        content_type="document-raw",
        stage="raw",
        content_uri="s3://mybucket/artifacts/raw/government-city_council/us-il-springfield-springfield/art_bin",
    )
    assert store.get_content_bytes(art) == b"%PDF-1.4"
    store._object_store.get.assert_called_once_with(
        "artifacts/raw/government-city_council/us-il-springfield-springfield/art_bin"
    )


def test_write_without_content_uri_raises():
    store = _store()
    artifact = Artifact(id="art_no_uri", content_type="document-raw", stage="raw")
    with _patch_session(store):
        with pytest.raises(ValueError, match="content_uri"):
            store.write(artifact)


def test_pending_acquisition_stub_writes_without_content_uri():
    store = _store()
    stub = Artifact(
        id="art_stub_w",
        content_type="audio-raw",
        stage="raw",
        status="pending_acquisition",
        acquisition_url="https://cdn.example.com/x.m3u8",
    )
    with _patch_session(store):
        store.write(stub)


def test_write_with_bytes_sets_uri_and_writes():
    store = _store()
    store._object_store.put.return_value = "s3://bucket/artifacts/processed/_/_/art_new"
    art = Artifact(
        id="art_new",
        content_type="document-text",
        stage="processed",
        media_type="text/plain",
        derived_from=["art_raw"],
    )
    with _patch_session(store):
        store.write_with_bytes(art, b"hello world", object_content_type="text/plain")
    store._object_store.put.assert_called_once()
    assert art.content_uri == "s3://bucket/artifacts/processed/_/_/art_new"


def test_complete_acquisition_updates_row_and_notifies():
    stub = Artifact(
        id="art_stub",
        content_type="audio-raw",
        stage="raw",
        status="pending_acquisition",
        acquisition_url="https://cdn.example.com/meeting.m3u8",
        beat="government:city_council",
        geo="us:il:springfield:springfield",
    )
    store = _store()
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.get = lambda model, pk: stub if pk == "art_stub" else None
    with patch("sidekick.core.artifact_store.Session", return_value=mock_session):
        store.complete_acquisition(
            "art_stub", "s3://bucket/artifacts/raw/_/_/art_stub", media_type="audio/mpeg"
        )

    assert stub.status == "active"
    assert stub.content_uri == "s3://bucket/artifacts/raw/_/_/art_stub"
    assert stub.acquisition_url is None
    assert stub.media_type == "audio/mpeg"
    store._event_bus.publish.assert_called_once()
    event_type, payload = store._event_bus.publish.call_args[0]
    assert event_type == "artifact_written"
    assert payload["id"] == "art_stub"
    assert payload["status"] == "active"


def test_complete_acquisition_wrong_status_raises():
    ready = Artifact(
        id="art_ready",
        content_type="document-raw",
        stage="raw",
        status="active",
        content_uri="s3://bucket/artifacts/raw/_/_/art_ready",
    )
    store = _store()
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.get = lambda model, pk: ready if pk == "art_ready" else None
    with patch("sidekick.core.artifact_store.Session", return_value=mock_session):
        with pytest.raises(ValueError, match="pending_acquisition"):
            store.complete_acquisition("art_ready", "s3://b/k")


# ------------------------------------------------------------------
# Query filters
# ------------------------------------------------------------------

def test_query_unsupported_filter_raises():
    store = _store()
    with pytest.raises(ValueError, match="Unsupported filter key"):
        store.query(filters={"nonexistent_column": "value"})


# ------------------------------------------------------------------
# Lineage
# ------------------------------------------------------------------

def test_lineage_invalid_direction_raises():
    store = _store()
    with pytest.raises(ValueError, match="direction must be"):
        store.lineage("art_x", direction="sideways")


# ------------------------------------------------------------------
# Embedding generation
# ------------------------------------------------------------------

def test_embedding_generated_when_embed_fn_provided():
    fake_embedding = [0.1] * 1536
    store = _store(embed_fn=lambda text: fake_embedding)
    store._object_store.get.return_value = b"Council voted yes on Ordinance 2026-14."

    artifact = Artifact(
        id="art_emb",
        content_type="document-raw",
        stage="raw",
        media_type="text/plain",
        content_uri="s3://bucket/artifacts/raw/_/_/art_emb",
    )
    with _patch_session(store):
        store.write(artifact)

    assert artifact.embedding == fake_embedding


def test_embedding_not_overwritten_when_already_set():
    called = []
    store = _store(embed_fn=lambda text: called.append(text) or [0.0] * 1536)

    artifact = Artifact(
        id="art_emb2",
        content_type="document-raw",
        stage="raw",
        embedding=[0.5] * 1536,
        content_uri="s3://bucket/artifacts/raw/_/_/art_emb2",
    )
    with _patch_session(store):
        store.write(artifact)

    assert called == []  # embed_fn should not have been called


def test_embedding_skipped_when_no_embed_fn():
    store = _store(embed_fn=None)
    artifact = Artifact(
        id="art_no_emb",
        content_type="document-raw",
        stage="raw",
        content_uri="s3://bucket/artifacts/raw/_/_/art_no_emb",
    )
    with _patch_session(store):
        store.write(artifact)
    assert artifact.embedding is None


# ------------------------------------------------------------------
# S3 key convention (tested on S3ObjectStore directly)
# ------------------------------------------------------------------

def test_artifact_key_convention():
    from sidekick.core.object_store import S3ObjectStore

    key = S3ObjectStore.artifact_key("processed", "government:city_council", "us:il:springfield:springfield", "art_123")
    assert key == "artifacts/processed/government-city_council/us-il-springfield-springfield/art_123"


def test_artifact_key_unknown_beat_geo():
    from sidekick.core.object_store import S3ObjectStore

    key = S3ObjectStore.artifact_key("raw", None, None, "art_456")
    assert key == "artifacts/raw/_/_/art_456"
