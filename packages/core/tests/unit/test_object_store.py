"""Unit tests for ObjectStore — uses moto to fake S3 without real AWS credentials."""

import os

import boto3
import pytest
from moto import mock_aws

from sidekick.core.object_store import S3ObjectStore


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Ensure boto3 doesn't accidentally hit real AWS."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)


@mock_aws
def test_put_returns_s3_uri():
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    store = S3ObjectStore("test-bucket")
    uri = store.put("my/key.txt", b"hello world", "text/plain")
    assert uri == "s3://test-bucket/my/key.txt"


@mock_aws
def test_get_returns_content():
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    store = S3ObjectStore("test-bucket")
    store.put("my/key.txt", b"hello world")
    assert store.get("my/key.txt") == b"hello world"


@mock_aws
def test_get_missing_key_raises():
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    store = S3ObjectStore("test-bucket")
    with pytest.raises(KeyError):
        store.get("does/not/exist.txt")


def test_artifact_key_convention():
    key = S3ObjectStore.artifact_key("processed", "government:city_council", "us:il:springfield:springfield", "art_123")
    assert key == "artifacts/processed/government-city_council/us-il-springfield-springfield/art_123"


def test_artifact_key_unknown_beat_geo():
    key = S3ObjectStore.artifact_key("raw", None, None, "art_456")
    assert key == "artifacts/raw/_/_/art_456"
