"""Integration tests for ArtifactStore against real Postgres + MinIO.

Run with: pytest tests/integration/ (requires docker compose up)
"""

import pytest

from sidekick.core.models import Artifact
from sidekick.core.object_store import S3ObjectStore


def test_write_and_read_raw(artifact_store, object_store: S3ObjectStore):
    artifact = Artifact(
        id="int_art_1",
        content_type="document-raw",
        stage="raw",
        beat="government:city_council",
        geo="us:ca:san_bernardino:san_bernardino",
    )
    body = b"Council meeting agenda for March 11 2026."
    key = S3ObjectStore.artifact_key("raw", "government:city_council", "us:ca:san_bernardino:san_bernardino", "int_art_1")
    uri = object_store.put(key, body, content_type="text/plain")
    artifact.content_uri = uri
    artifact_store.write(artifact)
    fetched = artifact_store.read("int_art_1")

    assert fetched.id == "int_art_1"
    assert fetched.stage == "raw"
    assert artifact_store.get_text_utf8(fetched) == body.decode("utf-8")


def test_write_processed_requires_derived_from(artifact_store):
    artifact = Artifact(
        id="int_art_no_lineage",
        content_type="summary",
        stage="processed",
    )
    with pytest.raises(ValueError, match="derived_from is required"):
        artifact_store.write(artifact)


def test_lineage_up(artifact_store, object_store: S3ObjectStore):
    raw = Artifact(id="lineage_raw", content_type="document-raw", stage="raw")
    raw.content_uri = object_store.put(
        S3ObjectStore.artifact_key("raw", None, None, "lineage_raw"),
        b"x",
        content_type="application/octet-stream",
    )
    processed = Artifact(
        id="lineage_proc",
        content_type="summary",
        stage="processed",
        derived_from=["lineage_raw"],
    )
    processed.content_uri = object_store.put(
        S3ObjectStore.artifact_key("processed", None, None, "lineage_proc"),
        b"summary text",
        content_type="text/plain",
    )
    analysis = Artifact(
        id="lineage_anal",
        content_type="beat-brief",
        stage="analysis",
        derived_from=["lineage_proc"],
    )
    analysis.content_uri = object_store.put(
        S3ObjectStore.artifact_key("analysis", None, None, "lineage_anal"),
        b"brief",
        content_type="text/plain",
    )
    artifact_store.write(raw)
    artifact_store.write(processed)
    artifact_store.write(analysis)

    ancestors = artifact_store.lineage("lineage_anal", direction="up")
    ancestor_ids = {a.id for a in ancestors}
    assert "lineage_proc" in ancestor_ids
    assert "lineage_raw" in ancestor_ids


def test_lineage_down(artifact_store, object_store: S3ObjectStore):
    raw = Artifact(id="down_raw", content_type="document-raw", stage="raw")
    raw.content_uri = object_store.put(
        S3ObjectStore.artifact_key("raw", None, None, "down_raw"),
        b"x",
        content_type="application/octet-stream",
    )
    proc = Artifact(
        id="down_proc",
        content_type="summary",
        stage="processed",
        derived_from=["down_raw"],
    )
    proc.content_uri = object_store.put(
        S3ObjectStore.artifact_key("processed", None, None, "down_proc"),
        b"y",
        content_type="text/plain",
    )
    artifact_store.write(raw)
    artifact_store.write(proc)

    descendants = artifact_store.lineage("down_raw", direction="down")
    assert any(a.id == "down_proc" for a in descendants)


def test_query_by_beat_and_stage(artifact_store, object_store: S3ObjectStore):
    a1 = Artifact(
        id="q_art_1",
        content_type="document-raw",
        stage="raw",
        beat="government:city_council",
        geo="us:ca:san_bernardino:san_bernardino",
    )
    a1.content_uri = object_store.put(
        S3ObjectStore.artifact_key("raw", "government:city_council", "us:ca:san_bernardino:san_bernardino", "q_art_1"),
        b"a",
        content_type="text/plain",
    )
    a2 = Artifact(
        id="q_art_2",
        content_type="document-raw",
        stage="raw",
        beat="education:school_board",
        geo="us:ca:san_bernardino:san_bernardino",
    )
    a2.content_uri = object_store.put(
        S3ObjectStore.artifact_key("raw", "education:school_board", "us:ca:san_bernardino:san_bernardino", "q_art_2"),
        b"b",
        content_type="text/plain",
    )
    artifact_store.write(a1)
    artifact_store.write(a2)

    results = artifact_store.query(filters={"beat": "government:city_council", "stage": "raw"})
    ids = {r.id for r in results}
    assert "q_art_1" in ids
    assert "q_art_2" not in ids


def test_write_with_bytes_round_trip(artifact_store, object_store: S3ObjectStore):
    artifact = Artifact(
        id="wb_art",
        content_type="document-text",
        stage="processed",
        media_type="text/plain",
        derived_from=["parent"],
    )
    large_content = "x" * 5_000
    artifact_store.write_with_bytes(
        artifact,
        large_content.encode("utf-8"),
        object_content_type="text/plain",
    )

    fetched = artifact_store.read("wb_art")
    assert artifact_store.get_text_utf8(fetched) == large_content


def test_read_missing_raises(artifact_store):
    with pytest.raises(KeyError):
        artifact_store.read("does_not_exist")
