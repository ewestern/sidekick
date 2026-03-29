"""Assignment resource routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from sidekick.api.auth import require_roles
from sidekick.api.db import get_session
from sidekick.api.schemas import AssignmentCreate, AssignmentPatch
from sidekick.core.models import Assignment

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("", response_model=Assignment, dependencies=[Depends(require_roles("editor", "admin"))])
def create_assignment(
    payload: AssignmentCreate, session: Annotated[Session, Depends(get_session)]
) -> Assignment:
    if session.get(Assignment, payload.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Assignment exists")
    row = Assignment(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("", response_model=list[Assignment], dependencies=[Depends(require_roles("reader", "editor", "admin", "machine"))])
def list_assignments(session: Annotated[Session, Depends(get_session)]) -> list[Assignment]:
    return list(session.exec(select(Assignment)).all())


@router.get("/{assignment_id}", response_model=Assignment, dependencies=[Depends(require_roles("reader", "editor", "admin", "machine"))])
def get_assignment(assignment_id: str, session: Annotated[Session, Depends(get_session)]) -> Assignment:
    row = session.get(Assignment, assignment_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return row


@router.patch("/{assignment_id}", response_model=Assignment, dependencies=[Depends(require_roles("editor", "admin"))])
def patch_assignment(
    assignment_id: str,
    payload: AssignmentPatch,
    session: Annotated[Session, Depends(get_session)],
) -> Assignment:
    row = session.get(Assignment, assignment_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("editor", "admin"))],
)
def delete_assignment(assignment_id: str, session: Annotated[Session, Depends(get_session)]) -> None:
    row = session.get(Assignment, assignment_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    session.delete(row)
    session.commit()
