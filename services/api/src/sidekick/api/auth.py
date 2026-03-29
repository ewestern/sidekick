"""Authentication and authorization dependencies."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

import jwt
import ulid
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlmodel import Session, select

from sidekick.api.db import get_session
from sidekick.api.settings import get_settings
from sidekick.core.models import ApiClient


class CallerType(StrEnum):
    """Authenticated caller categories."""

    USER = "user"
    MACHINE = "machine"


@dataclass(slots=True)
class AuthContext:
    """Normalized caller identity used by authorization checks."""

    subject: str
    caller_type: CallerType
    roles: set[str]
    scopes: set[str]
    key_id: str | None = None


_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_api_key(raw_key: str, pepper: str) -> str:
    payload = f"{pepper}:{raw_key}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_jwt(token: str) -> dict:
    settings = get_settings()
    if not settings.jwks_url or not settings.cognito_audience:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cognito JWT validation is not configured",
        )
    jwk_client = PyJWKClient(settings.jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.cognito_audience,
        issuer=settings.cognito_issuer or None,
    )


def _validate_api_key(raw_key: str, session: Session) -> ApiClient:
    settings = get_settings()
    key_prefix = raw_key[:12]
    stmt = select(ApiClient).where(ApiClient.key_prefix == key_prefix)
    row = session.exec(stmt).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    expected_hash = _hash_api_key(raw_key, settings.api_key_pepper)
    if not hmac.compare_digest(expected_hash, row.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if row.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is revoked")
    if row.expires_at and row.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    row.last_used_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_auth_context(
    session: Annotated[Session, Depends(get_session)],
    bearer_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(
        _bearer_scheme)] = None,
    api_key: Annotated[str | None, Depends(_api_key_scheme)] = None,
) -> AuthContext:
    """Authenticate request and return normalized identity context."""
    if bearer_credentials:
        claims = _validate_jwt(bearer_credentials.credentials)
        role_values = claims.get("cognito:groups", [])
        if not isinstance(role_values, list):
            role_values = []
        subject = str(claims.get("sub", "")).strip()
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject")
        return AuthContext(
            subject=subject,
            caller_type=CallerType.USER,
            roles={str(role) for role in role_values},
            scopes=set(),
        )

    if api_key:
        row = _validate_api_key(api_key, session)
        return AuthContext(
            subject=row.id,
            caller_type=CallerType.MACHINE,
            roles=set(row.roles or []),
            scopes=set(row.scopes or []),
            key_id=row.id,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing credentials",
    )


def require_roles(*roles: str):
    """Return a dependency that requires at least one role match."""

    allowed = set(roles)

    def _dependency(ctx: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if not (ctx.roles & allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return ctx

    return _dependency


def require_scopes(*scopes: str):
    """Return a dependency that requires all scopes."""

    required = set(scopes)

    def _dependency(ctx: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if not required.issubset(ctx.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return ctx

    return _dependency


@dataclass(slots=True)
class IssuedApiKey:
    """One-time API key issuance response."""

    client: ApiClient
    plaintext_key: str


def issue_api_key(
    session: Session,
    *,
    name: str,
    roles: list[str],
    scopes: list[str],
    created_by: str,
    expires_at: datetime | None = None,
    rotated_from: str | None = None,
) -> IssuedApiKey:
    """Issue and persist a new API key. Plaintext key is returned once."""
    _ = created_by  # placeholder for audit integration in later iterations
    suffix = str(ulid.new())
    plaintext_key = f"sk_{suffix}"
    prefix = plaintext_key[:12]
    key_hash = _hash_api_key(plaintext_key, get_settings().api_key_pepper)
    client = ApiClient(
        id=f"api_{ulid.new()}",
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
        roles=list(roles),
        scopes=list(scopes),
        expires_at=expires_at,
        rotated_from=rotated_from,
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    return IssuedApiKey(client=client, plaintext_key=plaintext_key)
