"""ObjectStore protocol and implementations.

Agent code must depend only on the ObjectStore protocol — never import S3ObjectStore directly.
The runtime wires the correct implementation based on environment (AWS_ENDPOINT_URL presence).
"""

import os
from typing import Protocol, runtime_checkable

import boto3
from botocore.config import Config


def normalize_for_uri(identifier: str | None) -> str:
    """Normalize an identifier for use in URI/path segments.

    Replaces colons with hyphens to make identifiers URI-safe while preserving
    the hierarchical structure. Used for object store keys and other path-like IDs.

    Args:
        identifier: Canonical identifier string (colon-delimited) or None.

    Returns:
        URI-safe identifier with colons replaced by hyphens, or '_' if None.
    """
    if identifier is None:
        return "_"
    return identifier.replace(":", "-")


@runtime_checkable
class ObjectStore(Protocol):
    """Store and retrieve binary content by key."""

    def put(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Write content under key and return the full URI (s3://bucket/key)."""
        ...

    def get(self, key: str) -> bytes:
        """Read content by key. Raises KeyError if not found."""
        ...


class S3ObjectStore:
    """boto3-backed store that works against both MinIO (local) and AWS S3 (production).

    Set AWS_ENDPOINT_URL=http://localhost:9000 to point at MinIO; unset it in production.
    """

    def __init__(self, bucket: str) -> None:
        self._bucket = bucket
        endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def artifact_key(stage: str, beat: str | None, geo: str | None, artifact_id: str) -> str:
        """Return the canonical S3 key for an artifact.

        Convention: artifacts/{stage}/{beat}/{geo}/{artifact_id}
        Beat and geo identifiers are normalized for URI safety (colons -> hyphens).
        Unknown beat/geo segments are replaced with '_'.
        """
        beat_segment = normalize_for_uri(beat)
        geo_segment = normalize_for_uri(geo)
        return f"artifacts/{stage}/{beat_segment}/{geo_segment}/{artifact_id}"

    def put(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return f"s3://{self._bucket}/{key}"

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey:
            raise KeyError(f"Object not found: s3://{self._bucket}/{key}")


def create_object_store(bucket: str | None = None) -> S3ObjectStore:
    """Factory that creates an S3ObjectStore from environment variables.

    Reads S3_BUCKET env var when bucket is not supplied explicitly.
    """
    resolved_bucket = bucket or os.environ["S3_BUCKET"]
    return S3ObjectStore(resolved_bucket)
