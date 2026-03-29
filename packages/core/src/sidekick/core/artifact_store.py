"""ArtifactStore — the only path for reading and writing artifacts.

Direct database access from agents is a code smell. All artifact I/O goes through here.

Responsibilities:
- Validate required fields (derived_from mandatory on non-raw artifacts)
- Persist all bodies in object storage (`content_uri`); no inline column
- Insert artifact row to Postgres
- Complete two-phase raw stubs via :meth:`complete_acquisition`
- Support structured + semantic query and lineage traversal
"""

import json
import logging
from typing import Any, Callable

from sqlalchemy import text
from sqlmodel import Session, create_engine, select, desc

from sidekick.core.models import Artifact
from sidekick.core.object_store import ObjectStore, S3ObjectStore
from sidekick.core.vocabulary import ArtifactStatus, ContentType, Stage, validate_beat, validate_geo

logger = logging.getLogger(__name__)


class ArtifactStore:
    """Service for reading and writing pipeline artifacts.

    Inject this into agents rather than giving them database or S3 access directly.
    """

    def __init__(
        self,
        db_url: str,
        object_store: ObjectStore,
        embed_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        """
        Args:
            db_url: SQLAlchemy-compatible Postgres connection string.
            object_store: ObjectStore implementation (S3/MinIO).
            embed_fn: Optional callable that takes a string and returns a list of 1536 floats.
                      When provided, artifacts without an embedding will have one generated.
        """
        self._engine = create_engine(db_url)
        self._object_store = object_store
        self._embed_fn = embed_fn

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write(self, artifact: Artifact) -> str:
        """Persist an artifact and notify subscribers.

        Validates, optionally generates an embedding, inserts the row, and fires NOTIFY.
        Every persisted artifact must reference object storage via ``content_uri``, except
        ``pending_acquisition`` stubs (see :meth:`_validate`).

        Returns:
            The artifact ID.

        Raises:
            ValueError: If required fields are missing (e.g., derived_from on non-raw).
        """
        self._validate(artifact)

        # Generate embedding if caller didn't provide one and we have an embed function
        if artifact.embedding is None and self._embed_fn is not None:
            text_for_embedding = self._text_for_embedding(artifact)
            if text_for_embedding:
                artifact.embedding = self._embed_fn(text_for_embedding)

        with Session(self._engine) as session:
            session.add(artifact)
            session.commit()
            session.refresh(artifact)

        logger.debug(
            "Wrote artifact %s (%s/%s)", artifact.id, artifact.stage, artifact.content_type
        )
        return artifact.id

    def write_with_bytes(
        self,
        artifact: Artifact,
        body: bytes,
        *,
        object_content_type: str = "application/octet-stream",
    ) -> str:
        """Store ``body`` in object storage, set ``artifact.content_uri``, then :meth:`write`.

        Use for processed text (``text/plain``), raw HTML, PDFs, audio, etc.

        Args:
            artifact: Row to persist (``id`` and routing fields must be set).
            body: Bytes written to the object store.
            object_content_type: MIME type passed to the object store.

        Returns:
            The artifact ID.
        """
        key = S3ObjectStore.artifact_key(
            artifact.stage, artifact.beat, artifact.geo, artifact.id
        )
        artifact.content_uri = self._object_store.put(
            key, body, content_type=object_content_type
        )
        return self.write(artifact)

    def complete_acquisition(
        self,
        artifact_id: str,
        content_uri: str,
        media_type: str | None = None,
        entities: list[dict[str, Any]] | None = None,
        topics: list[str] | None = None,
    ) -> str:
        """Finish a two-phase raw artifact: stub → active with object-store content.

        Only artifacts in ``status="pending_acquisition"`` may be completed. This is the
        sanctioned exception to "immutable after write" for raw stubs that have no bytes yet.

        Args:
            artifact_id: The stub artifact ID.
            content_uri: URI returned by ObjectStore.put (e.g. s3://bucket/key).
            media_type: Optional stored MIME type to set (e.g. audio/mpeg after capture).
            entities: If provided, replaces ``entities`` on the row.
            topics: If provided, replaces ``topics`` on the row.

        Returns:
            The artifact ID.

        Raises:
            KeyError: If the artifact does not exist.
            ValueError: If the artifact is not ``pending_acquisition``.
        """
        with Session(self._engine) as session:
            row = session.get(Artifact, artifact_id)
            if row is None:
                raise KeyError(f"Artifact not found: {artifact_id}")
            if row.status != ArtifactStatus.PENDING_ACQUISITION:
                raise ValueError(
                    f"complete_acquisition only applies to pending_acquisition stubs; "
                    f"artifact {artifact_id!r} has status={row.status!r}"
                )
            row.status = ArtifactStatus.ACTIVE
            row.content_uri = content_uri
            row.acquisition_url = None
            if media_type is not None:
                row.media_type = media_type
            if entities is not None:
                row.entities = entities
            if topics is not None:
                row.topics = topics
            session.add(row)
            session.commit()
            session.refresh(row)
            updated = row

        logger.debug("Completed acquisition for artifact %s", artifact_id)
        return artifact_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_row(self, artifact_id: str) -> Artifact:
        """Load an artifact row from Postgres only (no object-store fetch).

        Use for binary media before calling :meth:`get_content_bytes`.

        Raises:
            KeyError: If the artifact does not exist.
        """
        with Session(self._engine) as session:
            artifact = session.get(Artifact, artifact_id)
        if artifact is None:
            raise KeyError(f"Artifact not found: {artifact_id}")
        return artifact

    def read(self, artifact_id: str) -> Artifact:
        """Fetch an artifact row by ID. Body bytes live at ``content_uri`` in object storage.

        Use :meth:`get_content_bytes` or :meth:`get_text_utf8` to load the payload.

        Raises:
            KeyError: If the artifact does not exist.
        """
        return self.read_row(artifact_id)

    def patch(self, artifact_id: str, **updates: Any) -> Artifact:
        """Apply partial updates to an existing artifact row.

        This is intended for metadata-only changes such as supersession pointers.

        Raises:
            KeyError: If the artifact does not exist.
        """
        with Session(self._engine) as session:
            row = session.get(Artifact, artifact_id)
            if row is None:
                raise KeyError(f"Artifact not found: {artifact_id}")
            for key, value in updates.items():
                if not hasattr(row, key):
                    raise ValueError(f"Unsupported artifact field: {key!r}")
                setattr(row, key, value)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def get_content_bytes(self, artifact: Artifact) -> bytes:
        """Return raw bytes for an artifact with ``content_uri`` set.

        Use this for binary media (PDF, audio, video). Avoids :meth:`read`'s UTF-8 decode
        of object-store bodies.

        Args:
            artifact: Artifact row (typically loaded via :meth:`read` without needing inline text).

        Raises:
            ValueError: If ``content_uri`` is not set.
        """
        if artifact.content_uri:
            key = artifact.content_uri.split("/", 3)[-1]
            return self._object_store.get(key)
        raise ValueError(f"Artifact {artifact.id!r} has no content_uri")

    def get_text_utf8(self, artifact: Artifact) -> str:
        """Return stored body decoded as UTF-8 (for text artifacts in object storage)."""
        return self.get_content_bytes(artifact).decode("utf-8")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        filters: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        limit: int = 20,
    ) -> list[Artifact]:
        """Find artifacts by structured filters and/or semantic similarity.

        Args:
            filters: Keyword filters matched against Artifact columns.
                     Supported keys: stage, beat, geo, content_type, event_group,
                                     assignment_id, status, source_id.
            embedding: If provided, results are ordered by cosine similarity to this vector.
            limit: Maximum number of results to return.

        Returns:
            List of matching Artifact objects, ordered by similarity (if embedding given)
            or by created_at descending.
        """
        filters = filters or {}
        with Session(self._engine) as session:
            stmt = select(Artifact)

            allowed_filters = {
                "stage", "beat", "geo", "content_type", "event_group",
                "assignment_id", "status", "source_id", "created_by",
                "id", "topics", "period_start", "period_end", "story_key",
            }
            for key, value in filters.items():
                if key.endswith("_gte") or key.endswith("_lte"):
                    base_key = key[:-4]
                    if base_key not in {"period_start", "period_end", "created_at"}:
                        raise ValueError(f"Unsupported filter key: {key!r}")
                    column = getattr(Artifact, base_key)
                    stmt = stmt.where(column >= value if key.endswith("_gte") else column <= value)
                    continue
                if key == "ids":
                    stmt = stmt.where(Artifact.id.in_(value))  # type: ignore[arg-type]
                    continue
                if key not in allowed_filters:
                    raise ValueError(f"Unsupported filter key: {key!r}")
                column = getattr(Artifact, key)
                if key == "topics":
                    values = value if isinstance(value, (list, tuple, set)) else [value]
                    for topic in values:
                        stmt = stmt.where(text("(:topic) = ANY(topics)").bindparams(topic=topic))
                    continue
                if isinstance(value, (list, tuple, set)):
                    stmt = stmt.where(column.in_(list(value)))  # type: ignore[arg-type]
                else:
                    stmt = stmt.where(column == value)

            if embedding is not None:
                stmt = stmt.order_by(
                    text("embedding <=> CAST(:vec AS vector)")
                ).params(vec=json.dumps(embedding))
            else:
                # type: ignore[attr-defined]
                stmt = stmt.order_by(desc(Artifact.created_at))

            stmt = stmt.limit(limit)
            return list(session.exec(stmt).all())

    def semantic_query_text(
        self,
        query_text: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[Artifact]:
        """Find artifacts similar to the supplied query text."""
        if self._embed_fn is None:
            raise ValueError("Semantic query requires embed_fn to be configured.")
        query_text = query_text.strip()
        if not query_text:
            return []
        return self.query(filters=filters, embedding=self._embed_fn(query_text), limit=limit)

    # ------------------------------------------------------------------
    # Lineage
    # ------------------------------------------------------------------

    def lineage(self, artifact_id: str, direction: str = "up") -> list[Artifact]:
        """Traverse lineage links from a given artifact.

        Args:
            artifact_id: Starting artifact ID.
            direction: "up" walks toward raw sources (follows derived_from);
                       "down" walks toward drafts (finds artifacts deriving from this one).

        Returns:
            All artifacts reachable in the given direction, breadth-first.
            The starting artifact is not included.
        """
        if direction not in ("up", "down"):
            raise ValueError(
                f"direction must be 'up' or 'down', got {direction!r}")

        visited: set[str] = {artifact_id}
        queue: list[str] = [artifact_id]
        results: list[Artifact] = []

        with Session(self._engine) as session:
            while queue:
                current_id = queue.pop(0)

                if direction == "up":
                    current = session.get(Artifact, current_id)
                    if current is None or not current.derived_from:
                        continue
                    next_ids = [
                        aid for aid in current.derived_from if aid not in visited]
                else:
                    rows = session.exec(
                        select(Artifact).where(
                            text("(:id) = ANY(derived_from)").bindparams(
                                id=current_id)
                        )
                    ).all()
                    next_ids = [r.id for r in rows if r.id not in visited]

                for nid in next_ids:
                    visited.add(nid)
                    queue.append(nid)
                    artifact = session.get(Artifact, nid)
                    if artifact:
                        results.append(artifact)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(self, artifact: Artifact) -> None:
        if not artifact.id:
            raise ValueError("Artifact.id is required")
        if not artifact.content_type:
            raise ValueError("Artifact.content_type is required")
        if not artifact.stage:
            raise ValueError("Artifact.stage is required")
        try:
            ContentType(artifact.content_type)
        except ValueError:
            raise ValueError(
                f"Unknown content_type {artifact.content_type!r}. "
                f"Allowed values: {sorted(e.value for e in ContentType)}. "
                "Adding a new content type requires updating ContentType in vocabulary.py and ARTIFACT_STORE.md."
            )
        if (
            artifact.stage != Stage.RAW
            and not artifact.derived_from
            and not (
                artifact.stage == Stage.PROCESSED
                and artifact.content_type == ContentType.DOCUMENT_TEXT
            )
        ):
            raise ValueError(
                f"Artifact.derived_from is required for stage={artifact.stage!r}. "
                "Every non-raw artifact must declare what it was derived from, "
                "except direct-ingested processed document-text artifacts."
            )
        if artifact.beat is not None:
            validate_beat(artifact.beat)
        if artifact.geo is not None:
            validate_geo(artifact.geo)
        self._validate_content_storage(artifact)

    def _validate_content_storage(self, artifact: Artifact) -> None:
        """Require object storage for all rows except pending acquisition stubs."""
        if artifact.status == ArtifactStatus.PENDING_ACQUISITION:
            if not artifact.acquisition_url:
                raise ValueError(
                    "pending_acquisition artifacts must set acquisition_url until completed."
                )
            if artifact.content_uri is not None:
                raise ValueError(
                    "pending_acquisition stub must not set content_uri until acquisition completes."
                )
            return
        if artifact.content_uri is None:
            raise ValueError(
                "Artifact.content_uri is required — store all bodies in object storage."
            )

    def _text_for_embedding(self, artifact: Artifact) -> str | None:
        """Extract text suitable for embedding — load text/* from object store, else metadata."""
        if artifact.content_uri:
            mt = (artifact.media_type or "").split(";")[0].strip().lower()
            if mt.startswith("text/") or artifact.content_type in (
                ContentType.DOCUMENT_TEXT,
                ContentType.SUMMARY,
            ):
                try:
                    raw = self.get_content_bytes(artifact).decode("utf-8")
                    return raw[:8_000]
                except (UnicodeDecodeError, ValueError):
                    pass
        parts = [artifact.content_type, artifact.beat,
                 artifact.geo, artifact.event_group]
        if artifact.topics:
            parts.extend(artifact.topics)
        return " ".join(p for p in parts if p) or None
