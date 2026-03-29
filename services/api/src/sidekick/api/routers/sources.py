"""Source resource routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from sidekick.api.auth import require_roles
from sidekick.api.db import get_session
from sidekick.api.schemas import SourceCreate, SourcePatch
from sidekick.core.models import Source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=Source, dependencies=[Depends(require_roles("editor", "admin"))])
def create_source(payload: SourceCreate, session: Annotated[Session, Depends(get_session)]) -> Source:
    if session.get(Source, payload.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Source exists")
    row = Source(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("", response_model=list[Source], dependencies=[Depends(require_roles("reader", "editor", "admin", "machine"))])
def list_sources(session: Annotated[Session, Depends(get_session)]) -> list[Source]:
    return list(session.exec(select(Source)).all())


@router.get("/{source_id}", response_model=Source, dependencies=[Depends(require_roles("reader", "editor", "admin", "machine"))])
def get_source(source_id: str, session: Annotated[Session, Depends(get_session)]) -> Source:
    row = session.get(Source, source_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return row


@router.patch("/{source_id}", response_model=Source, dependencies=[Depends(require_roles("editor", "admin"))])
def patch_source(
    source_id: str,
    payload: SourcePatch,
    session: Annotated[Session, Depends(get_session)],
) -> Source:
    row = session.get(Source, source_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("editor", "admin"))],
)
def delete_source(source_id: str, session: Annotated[Session, Depends(get_session)]) -> None:
    row = session.get(Source, source_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    session.delete(row)
    session.commit()
