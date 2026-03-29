"""AssignmentStore — structured persistence for assignment creation and lookup."""

from __future__ import annotations

from typing import Any

import ulid
from sqlmodel import Session, create_engine, select

from sidekick.core.models import Assignment


class AssignmentStore:
    """CRUD helper for assignments used by agents and orchestration code."""

    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(db_url)

    def create(
        self,
        *,
        assignment_type: str,
        query_text: str,
        query_params: dict[str, Any] | None = None,
        triggered_by: str | None = None,
        triggered_by_id: str | None = None,
        parent_assignment: str | None = None,
        artifacts_in: list[str] | None = None,
        sub_assignments: list[str] | None = None,
        status: str = "open",
        assignment_id: str | None = None,
    ) -> Assignment:
        with Session(self._engine) as session:
            row = Assignment(
                id=assignment_id or f"asg_{ulid.new()}",
                type=assignment_type,
                status=status,
                query_text=query_text,
                query_params=query_params,
                triggered_by=triggered_by,
                triggered_by_id=triggered_by_id,
                parent_assignment=parent_assignment,
                artifacts_in=artifacts_in,
                sub_assignments=sub_assignments,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def list_open(
        self,
        *,
        parent_assignment: str | None = None,
        triggered_by: str | None = None,
        triggered_by_id: str | None = None,
    ) -> list[Assignment]:
        with Session(self._engine) as session:
            stmt = select(Assignment).where(Assignment.status.in_(["open", "in-progress"]))  # type: ignore[arg-type]
            if parent_assignment is not None:
                stmt = stmt.where(Assignment.parent_assignment == parent_assignment)
            if triggered_by is not None:
                stmt = stmt.where(Assignment.triggered_by == triggered_by)
            if triggered_by_id is not None:
                stmt = stmt.where(Assignment.triggered_by_id == triggered_by_id)
            return list(session.exec(stmt).all())

    def patch(self, assignment_id: str, **updates: Any) -> Assignment:
        with Session(self._engine) as session:
            row = session.get(Assignment, assignment_id)
            if row is None:
                raise KeyError(f"Assignment not found: {assignment_id}")
            for key, value in updates.items():
                if not hasattr(row, key):
                    raise ValueError(f"Unsupported assignment field: {key!r}")
                setattr(row, key, value)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
