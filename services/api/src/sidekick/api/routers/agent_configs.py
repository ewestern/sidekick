"""Agent config routes."""

from datetime import UTC, datetime
from typing import Annotated

import ulid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from sidekick.api.auth import require_roles
from sidekick.api.db import get_session
from sidekick.api.schemas import AgentConfigCreate
from sidekick.core.models import AgentConfig

router = APIRouter(prefix="/agent-configs", tags=["agent-configs"])


@router.post("", response_model=AgentConfig, dependencies=[Depends(require_roles("admin"))])
def create_agent_config(
    payload: AgentConfigCreate,
    session: Annotated[Session, Depends(get_session)],
) -> AgentConfig:
    agent_id = payload.agent_id
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="agent_id is required",
        )
    existing = session.exec(select(AgentConfig).where(
        AgentConfig.agent_id == agent_id)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Agent config exists")
    row = AgentConfig(
        id=payload.id or f"cfg_{ulid.new()}",
        agent_id=agent_id,
        model=payload.model,
        prompts=payload.prompts,
        skills=payload.skills,
        updated_at=datetime.now(UTC),
        updated_by=payload.updated_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("", response_model=list[AgentConfig], dependencies=[Depends(require_roles("reader", "editor", "admin"))])
def list_agent_configs(session: Annotated[Session, Depends(get_session)]) -> list[AgentConfig]:
    return list(session.exec(select(AgentConfig)).all())


@router.get(
    "/{agent_id}",
    response_model=AgentConfig,
    dependencies=[Depends(require_roles("reader", "editor", "admin"))],
)
def get_agent_config(agent_id: str, session: Annotated[Session, Depends(get_session)]) -> AgentConfig:
    row = session.exec(select(AgentConfig).where(
        AgentConfig.agent_id == agent_id)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Agent config not found")
    return row


@router.put("/{agent_id}", response_model=AgentConfig, dependencies=[Depends(require_roles("admin"))])
def put_agent_config(
    agent_id: str,
    payload: AgentConfigCreate,
    session: Annotated[Session, Depends(get_session)],
) -> AgentConfig:
    row = session.exec(select(AgentConfig).where(
        AgentConfig.agent_id == agent_id)).first()
    if row is None:
        row = AgentConfig(
            id=payload.id or f"cfg_{ulid.new()}",
            agent_id=agent_id,
            model=payload.model,
            prompts=payload.prompts,
            skills=payload.skills,
            updated_at=datetime.now(UTC),
            updated_by=payload.updated_by,
        )
    else:
        row.model = payload.model
        row.prompts = payload.prompts
        row.skills = payload.skills
        row.updated_at = datetime.now(UTC)
        row.updated_by = payload.updated_by
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
def delete_agent_config(agent_id: str, session: Annotated[Session, Depends(get_session)]) -> None:
    row = session.exec(select(AgentConfig).where(
        AgentConfig.agent_id == agent_id)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Agent config not found")
    session.delete(row)
    session.commit()
