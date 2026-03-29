"""Machine API key lifecycle routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from sidekick.api.auth import issue_api_key, require_roles
from sidekick.api.db import get_session
from sidekick.api.schemas import ApiClientCreate, ApiClientRotate, ApiKeyIssuedResponse
from sidekick.core.models import ApiClient

router = APIRouter(prefix="/api-clients", tags=["api-clients"])


@router.get("", response_model=list[ApiClient], dependencies=[Depends(require_roles("admin"))])
def list_api_clients(session: Annotated[Session, Depends(get_session)]) -> list[ApiClient]:
    return list(session.exec(select(ApiClient)).all())


@router.post(
    "",
    response_model=ApiKeyIssuedResponse,
    dependencies=[Depends(require_roles("admin"))],
)
def create_api_client(
    payload: ApiClientCreate,
    session: Annotated[Session, Depends(get_session)],
) -> ApiKeyIssuedResponse:
    issued = issue_api_key(
        session,
        name=payload.name,
        roles=payload.roles,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        created_by="api-admin",
    )
    return ApiKeyIssuedResponse(
        id=issued.client.id,
        name=issued.client.name,
        key_prefix=issued.client.key_prefix,
        plaintext_key=issued.plaintext_key,
        roles=issued.client.roles,
        scopes=issued.client.scopes,
        status=issued.client.status,
        created_at=issued.client.created_at,
        expires_at=issued.client.expires_at,
    )


@router.post(
    "/{client_id}/rotate",
    response_model=ApiKeyIssuedResponse,
    dependencies=[Depends(require_roles("admin"))],
)
def rotate_api_client_key(
    client_id: str,
    payload: ApiClientRotate,
    session: Annotated[Session, Depends(get_session)],
) -> ApiKeyIssuedResponse:
    row = session.get(ApiClient, client_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API client not found")
    row.status = "revoked"
    session.add(row)
    session.commit()
    issued = issue_api_key(
        session,
        name=payload.name or row.name,
        roles=payload.roles or row.roles,
        scopes=payload.scopes or row.scopes,
        expires_at=payload.expires_at if payload.expires_at is not None else row.expires_at,
        rotated_from=row.id,
        created_by="api-admin",
    )
    return ApiKeyIssuedResponse(
        id=issued.client.id,
        name=issued.client.name,
        key_prefix=issued.client.key_prefix,
        plaintext_key=issued.plaintext_key,
        roles=issued.client.roles,
        scopes=issued.client.scopes,
        status=issued.client.status,
        created_at=issued.client.created_at,
        expires_at=issued.client.expires_at,
    )


@router.post(
    "/{client_id}/revoke",
    response_model=ApiClient,
    dependencies=[Depends(require_roles("admin"))],
)
def revoke_api_client(client_id: str, session: Annotated[Session, Depends(get_session)]) -> ApiClient:
    row = session.get(ApiClient, client_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API client not found")
    row.status = "revoked"
    row.last_used_at = row.last_used_at or datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
