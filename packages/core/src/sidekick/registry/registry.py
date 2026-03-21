"""Source registry service — CRUD operations on the sources table."""

import logging
from datetime import UTC, datetime
from typing import Any

from croniter import croniter
from sqlmodel import Session, create_engine, select

from sidekick.core.models import Source
from sidekick.core.vocabulary import validate_beat, validate_geo

logger = logging.getLogger(__name__)


class SourceRegistry:
    """CRUD interface for the source registry.

    The registry answers: what recurring sources exist, how to fetch them, and when they are due.
    All schedule evaluation and health tracking happens here.
    """

    def __init__(self, db_url: str) -> None:
        """
        Args:
            db_url: SQLAlchemy-compatible Postgres connection string.
        """
        self._engine = create_engine(db_url)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, source_id: str) -> Source:
        """Fetch a source by ID.

        Raises:
            KeyError: If the source does not exist.
        """
        with Session(self._engine) as session:
            source = session.get(Source, source_id)
        if source is None:
            raise KeyError(f"Source not found: {source_id}")
        return source

    def list(self, filters: dict[str, Any] | None = None) -> list[Source]:
        """List sources, optionally filtered by top-level column equality.

        Args:
            filters: Column equality filters. Supported keys:
                     beat, geo, examination_status, discovered_by.

        Returns:
            All matching sources ordered by name.
        """
        filters = filters or {}
        allowed = {"beat", "geo", "examination_status", "discovered_by"}
        for key in filters:
            if key not in allowed:
                raise ValueError(f"Unsupported filter key: {key!r}")

        with Session(self._engine) as session:
            stmt = select(Source)
            for key, value in filters.items():
                stmt = stmt.where(getattr(Source, key) == value)
            stmt = stmt.order_by(Source.name)
            return list(session.exec(stmt).all())

    def get_due_sources(self) -> list[Source]:
        """Return sources whose cron schedule is due for a fetch run.

        A source is due when:
        - Its examination_status is "active" (examination has succeeded)
        - Its schedule type is "cron"
        - The next scheduled run after last_checked is at or before now

        Sources with no health record (never checked) are always due if they have a cron schedule.
        """
        now = datetime.now(UTC)
        candidates = self.list(filters={"examination_status": "active"})
        due = []

        for source in candidates:
            if not source.schedule or source.schedule.get("type") != "cron":
                continue

            cron_expr = source.schedule.get("expr")
            if not cron_expr:
                continue

            health = source.health or {}
            last_checked_raw = health.get("last_checked")
            if last_checked_raw is None:
                due.append(source)
                continue

            if isinstance(last_checked_raw, str):
                last_checked = datetime.fromisoformat(last_checked_raw)
                if last_checked.tzinfo is None:
                    last_checked = last_checked.replace(tzinfo=UTC)
            else:
                last_checked = last_checked_raw

            try:
                next_run = croniter(cron_expr, last_checked).get_next(datetime)
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=UTC)
                if next_run <= now:
                    due.append(source)
            except Exception:
                logger.exception("Failed to evaluate cron for source %s", source.id)

        return due

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create(self, source: Source) -> Source:
        """Persist a new source.

        Raises:
            ValueError: If a source with this ID already exists, or if beat/geo are invalid.
        """
        if source.beat is not None:
            validate_beat(source.beat)
        if source.geo is not None:
            validate_geo(source.geo)
        with Session(self._engine) as session:
            existing = session.get(Source, source.id)
            if existing is not None:
                raise ValueError(f"Source already exists: {source.id}")
            session.add(source)
            session.commit()
            session.refresh(source)
        logger.debug("Created source %s (%s)", source.id, source.name)
        return source

    def update(self, source_id: str, updates: dict[str, Any]) -> Source:
        """Apply field updates to an existing source.

        Args:
            source_id: ID of the source to update.
            updates: Dict of field names to new values.

        Raises:
            KeyError: If the source does not exist.
        """
        if "beat" in updates and updates["beat"] is not None:
            validate_beat(updates["beat"])
        if "geo" in updates and updates["geo"] is not None:
            validate_geo(updates["geo"])
        with Session(self._engine) as session:
            source = session.get(Source, source_id)
            if source is None:
                raise KeyError(f"Source not found: {source_id}")
            for key, value in updates.items():
                setattr(source, key, value)
            session.add(source)
            session.commit()
            session.refresh(source)
        return source

    def update_health(self, source_id: str, health_update: dict[str, Any]) -> None:
        """Merge health fields for a source.

        Merges health_update into the existing health dict rather than replacing it,
        so callers only need to supply the fields they want to change.

        Raises:
            KeyError: If the source does not exist.
        """
        with Session(self._engine) as session:
            source = session.get(Source, source_id)
            if source is None:
                raise KeyError(f"Source not found: {source_id}")
            existing = dict(source.health or {})
            existing.update(health_update)
            source.health = existing
            session.add(source)
            session.commit()

    def delete(self, source_id: str) -> None:
        """Delete a source by ID.

        Raises:
            KeyError: If the source does not exist.
        """
        with Session(self._engine) as session:
            source = session.get(Source, source_id)
            if source is None:
                raise KeyError(f"Source not found: {source_id}")
            session.delete(source)
            session.commit()
        logger.debug("Deleted source %s", source_id)
