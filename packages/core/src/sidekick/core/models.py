"""SQLModel table definitions — the single source of truth for database schema.

Never write raw CREATE TABLE SQL. Define tables here and let Alembic generate migrations.
"""

from datetime import UTC, date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from sidekick.core.vocabulary import (
    ArtifactStatus,
    ContentType,
    ProcessingProfile,
    SourceStatus,
    SourceTier,
    Stage,
)


class AgentConfig(SQLModel, table=True):
    """Runtime configuration for a named agent — model and prompt definitions.

    A row must exist before an agent can be invoked. There are no code-level
    defaults; agents raise KeyError if no row is found.

    agent_id examples:
        "ingestion-worker"
        "processor:summary"
        "beat-agent:city-council:springfield-il"
        "editor-agent"

    prompts keys are agent-specific slot names, e.g.:
        {"system": "...", "analyze_template": "..."}
    """

    __tablename__ = "agent_configs"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("agent_id"),)

    id: str = Field(primary_key=True)
    agent_id: str
    model: str  # e.g. "claude-sonnet-4-6"
    prompts: dict[str, str] = Field(
        sa_column=Column(JSON))  # slot_name -> prompt text
    # skill IDs from skills/
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by: str | None = None  # user ID from editorial API


class Source(SQLModel, table=True):
    """A recurring information channel (e.g. a council agenda page, an RSS feed)."""

    __tablename__ = "sources"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True)
    name: str
    endpoint: str | None = None
    schedule: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON))
    beat: str | None = None
    geo: str | None = None
    related_sources: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text))
    )
    registered_at: datetime | None = None
    health: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    # primary (default) | secondary — see SOURCE_STRATEGIES.md
    source_tier: SourceTier = Field(default=SourceTier.PRIMARY)
    # Name of the publishing outlet; required when source_tier=secondary (e.g. "Associated Press")
    outlet: str | None = None
    # active (default) | inactive — inactive sources are excluded from scheduled list-due
    status: SourceStatus = Field(default=SourceStatus.ACTIVE)


class Artifact(SQLModel, table=True):
    """A unit of content at any pipeline stage — raw, processed, analysis, connections, or draft."""

    __tablename__ = "artifacts"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True)
    title: str
    content_type: ContentType
    stage: Stage
    media_type: str | None = None
    # Ingest-time routing intent; inherited on derived artifacts. None = legacy rows (treat as full).
    processing_profile: ProcessingProfile | None = None

    # Lineage — required for derived artifacts. Direct-ingested canonical text may omit it.
    derived_from: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text))
    )

    # Context
    source_id: str | None = Field(default=None, foreign_key="sources.id")
    event_group: str | None = None
    beat: str | None = None
    geo: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    assignment_id: str | None = None
    story_key: str | None = None

    # Discovery
    entities: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column(JSON))
    topics: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text)))
    # 1536-dim vector for text-embedding-3-small. Dimension is baked in — changing requires
    # rebuilding the column and the ivfflat index.
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(1536))
    )

    # Content — bodies live in object storage (see ARTIFACT_STORE.md)
    # s3://bucket/artifacts/{stage}/{beat}/{geo}/{id}
    content_uri: str | None = None
    # Set on pending_acquisition stubs — the source URL the acquisition worker must fetch.
    # Cleared (set to None) once acquisition completes and content_uri is populated.
    acquisition_url: str | None = None

    # Provenance
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Status
    status: ArtifactStatus = Field(default=ArtifactStatus.ACTIVE)
    superseded_by: str | None = Field(default=None, foreign_key="artifacts.id")

    def model_post_init(self, __context: Any) -> None:
        if self.content_type == "transcript-clean":
            self.content_type = ContentType.DOCUMENT_TEXT
        elif self.content_type == "transcript-raw":
            self.content_type = ContentType.DOCUMENT_RAW


class Assignment(SQLModel, table=True):
    """A targeted investigation request — research, story, or monitor type."""

    __tablename__ = "assignments"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True)
    type: str  # research | story | monitor
    # open | in-progress | complete | cancelled
    status: str = Field(default="open")

    # Intent — query_text preserved exactly; query_params extracted by LLM at creation time
    query_text: str
    query_params: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON))

    # Provenance
    triggered_by: str | None = None  # human | connection-agent | beat-agent | schedule
    triggered_by_id: str | None = None
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parent_assignment: str | None = Field(
        default=None, foreign_key="assignments.id")

    # Execution
    artifacts_in: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text))
    )
    artifacts_out: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text))
    )
    sub_assignments: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text))
    )

    # Monitor-type only
    monitor: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON))


class AnalysisScope(SQLModel, table=True):
    """Durable coordination state for one analysis scope (currently one event group)."""

    __tablename__ = "analysis_scopes"  # pyright: ignore[reportAssignmentType]

    scope_key: str = Field(primary_key=True)
    event_group: str
    beat: str
    geo: str
    status: str = Field(default="idle")
    dirty: bool = Field(default=False)
    revision: int = Field(default=0)
    active_execution_arn: str | None = None
    last_input_at: datetime | None = None
    last_run_started_at: datetime | None = None
    last_run_completed_at: datetime | None = None
    last_revision_started: int | None = None
    last_revision_completed: int | None = None
    last_brief_artifact_id: str | None = Field(
        default=None, foreign_key="artifacts.id")
    last_error: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApiClient(SQLModel, table=True):
    """Machine API client credentials and authorization metadata."""

    __tablename__ = "api_clients"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True)
    name: str
    key_prefix: str = Field(index=True)
    key_hash: str
    roles: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    scopes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = Field(default="active")  # active | revoked
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    rotated_from: str | None = Field(
        default=None, foreign_key="api_clients.id")
