"""Artifact resource routes (no create endpoint in v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, select

from sidekick.api.auth import require_roles
from sidekick.api.db import get_session
from sidekick.api.schemas import ArtifactPatch
from sidekick.core.models import Artifact
from sidekick.core.vocabulary import ArtifactStatus

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("", response_model=list[Artifact], dependencies=[Depends(require_roles("reader", "editor", "admin", "machine"))])
def list_artifacts(
    session: Annotated[Session, Depends(get_session)],
    content_type: str | None = Query(default=None, description="Filter by content_type"),
    content_types: list[str] | None = Query(
        default=None,
        description="Filter by any of these content_type values",
    ),
    stage: str | None = Query(default=None, description="Filter by stage"),
    story_key: str | None = Query(default=None, description="Filter by story_key"),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by artifact status (e.g. active)",
    ),
) -> list[Artifact]:
    stmt = select(Artifact)
    if content_type is not None:
        stmt = stmt.where(col(Artifact.content_type) == content_type)
    if content_types:
        stmt = stmt.where(col(Artifact.content_type).in_(content_types))
    if stage is not None:
        stmt = stmt.where(col(Artifact.stage) == stage)
    if story_key is not None:
        stmt = stmt.where(col(Artifact.story_key) == story_key)
    if status_filter is not None:
        stmt = stmt.where(col(Artifact.status) == status_filter)
    return list(session.exec(stmt).all())


@router.get("/{artifact_id}", response_model=Artifact, dependencies=[Depends(require_roles("reader", "editor", "admin", "machine"))])
def get_artifact(artifact_id: str, session: Annotated[Session, Depends(get_session)]) -> Artifact:
    row = session.get(Artifact, artifact_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return row


@router.patch("/{artifact_id}", response_model=Artifact, dependencies=[Depends(require_roles("editor", "admin"))])
def patch_artifact(
    artifact_id: str,
    payload: ArtifactPatch,
    session: Annotated[Session, Depends(get_session)],
) -> Artifact:
    row = session.get(Artifact, artifact_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
def retract_artifact(artifact_id: str, session: Annotated[Session, Depends(get_session)]) -> None:
    row = session.get(Artifact, artifact_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    row.status = ArtifactStatus.RETRACTED
    session.add(row)
    session.commit()
