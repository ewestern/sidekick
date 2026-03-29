"""Pydantic API DTOs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from sidekick.core.vocabulary import SourceStatus


class SourceCreate(BaseModel):
    id: str
    name: str
    endpoint: str | None = None
    schedule: dict[str, Any] | None = None
    beat: str | None = None
    geo: str | None = None
    related_sources: list[str] | None = None
    registered_at: datetime | None = None
    health: dict[str, Any] | None = None
    source_tier: str | None = None
    outlet: str | None = None
    status: SourceStatus = SourceStatus.ACTIVE


class SourcePatch(BaseModel):
    name: str | None = None
    endpoint: str | None = None
    schedule: dict[str, Any] | None = None
    beat: str | None = None
    geo: str | None = None
    related_sources: list[str] | None = None
    registered_at: datetime | None = None
    health: dict[str, Any] | None = None
    source_tier: str | None = None
    outlet: str | None = None
    status: SourceStatus | None = None


class AssignmentCreate(BaseModel):
    id: str
    type: str
    status: str = "open"
    query_text: str
    query_params: dict[str, Any] | None = None
    triggered_by: str | None = None
    triggered_by_id: str | None = None
    triggered_at: datetime | None = None
    parent_assignment: str | None = None
    artifacts_in: list[str] | None = None
    artifacts_out: list[str] | None = None
    sub_assignments: list[str] | None = None
    monitor: dict[str, Any] | None = None


class AssignmentPatch(BaseModel):
    type: str | None = None
    status: str | None = None
    query_text: str | None = None
    query_params: dict[str, Any] | None = None
    triggered_by: str | None = None
    triggered_by_id: str | None = None
    triggered_at: datetime | None = None
    parent_assignment: str | None = None
    artifacts_in: list[str] | None = None
    artifacts_out: list[str] | None = None
    sub_assignments: list[str] | None = None
    monitor: dict[str, Any] | None = None


class AgentConfigCreate(BaseModel):
    id: str | None = None
    agent_id: str | None = None
    model: str
    prompts: dict[str, str]
    skills: list[str] = Field(default_factory=list)
    updated_by: str | None = None


class ArtifactPatch(BaseModel):
    media_type: str | None = None
    event_group: str | None = None
    beat: str | None = None
    geo: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    assignment_id: str | None = None
    story_key: str | None = None
    entities: list[dict[str, Any]] | None = None
    topics: list[str] | None = None
    status: str | None = None
    superseded_by: str | None = None


class ApiClientCreate(BaseModel):
    name: str
    roles: list[str]
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class ApiClientRotate(BaseModel):
    name: str | None = None
    roles: list[str] | None = None
    scopes: list[str] | None = None
    expires_at: datetime | None = None


class ApiKeyIssuedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    plaintext_key: str
    roles: list[str]
    scopes: list[str]
    status: str
    created_at: datetime
    expires_at: datetime | None = None
