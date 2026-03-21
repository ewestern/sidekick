"""SQLModel table definitions — the single source of truth for database schema.

Never write raw CREATE TABLE SQL. Define tables here and let Alembic generate migrations.
"""

from datetime import UTC, date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class AgentConfig(SQLModel, table=True):
    """Runtime configuration for a named agent — model and prompt definitions.

    A row must exist before an agent can be invoked. There are no code-level
    defaults; agents raise KeyError if no row is found.

    agent_id examples:
        "ingestion-worker"
        "source-examination"
        "beat-agent:city-council:springfield-il"
        "editor-agent"

    prompts keys are agent-specific slot names, e.g.:
        {"system": "...", "analyze_template": "..."}
    """

    __tablename__ = "agent_configs"
    __table_args__ = (UniqueConstraint("agent_id"),)

    id: str = Field(primary_key=True)
    agent_id: str
    model: str  # e.g. "claude-sonnet-4-6"
    prompts: dict[str, str] = Field(sa_column=Column(JSON))  # slot_name -> prompt text
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by: str | None = None  # user ID from editorial API


class Source(SQLModel, table=True):
    """A recurring information channel (e.g. a council agenda page, an RSS feed)."""

    __tablename__ = "sources"

    id: str = Field(primary_key=True)
    name: str
    endpoint: str | None = None
    schedule: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    expected_content: list[dict] | None = Field(
        default=None, sa_column=Column(JSON)
    )  # [{media_type, content_type}] declared at registration; guides examination
    beat: str | None = None
    geo: str | None = None
    related_sources: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(Text))
    )
    discovered_by: str | None = None  # human | agent | derived
    registered_at: datetime | None = None
    examination_status: str = Field(default="pending")  # pending | active | failed | paused
    health: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class Artifact(SQLModel, table=True):
    """A unit of content at any pipeline stage — raw, processed, analysis, connections, or draft."""

    __tablename__ = "artifacts"

    id: str = Field(primary_key=True)
    content_type: str  # controlled vocabulary — see ARTIFACT_STORE.md
    stage: str  # raw | processed | analysis | connections | draft
    media_type: str | None = None

    # Lineage — mandatory on all non-raw artifacts, enforced by ArtifactStore.write()
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

    # Discovery
    entities: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    topics: list[str] | None = Field(default=None, sa_column=Column(ARRAY(Text)))
    # 1536-dim vector for text-embedding-3-small. Dimension is baked in — changing requires
    # rebuilding the column and the ivfflat index.
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(1536))
    )

    # Content — bodies live in object storage (see ARTIFACT_STORE.md)
    content_uri: str | None = None  # s3://bucket/artifacts/{stage}/{beat}/{geo}/{id}
    # Set on pending_acquisition stubs — the source URL the acquisition worker must fetch.
    # Cleared (set to None) once acquisition completes and content_uri is populated.
    acquisition_url: str | None = None

    # Provenance
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Status
    status: str = Field(default="active")  # active | pending_acquisition | superseded | retracted
    superseded_by: str | None = Field(default=None, foreign_key="artifacts.id")


class Assignment(SQLModel, table=True):
    """A targeted investigation request — research, story, or monitor type."""

    __tablename__ = "assignments"

    id: str = Field(primary_key=True)
    type: str  # research | story | monitor
    status: str = Field(default="open")  # open | in-progress | complete | cancelled

    # Intent — query_text preserved exactly; query_params extracted by LLM at creation time
    query_text: str
    query_params: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Provenance
    triggered_by: str | None = None  # human | connection-agent | beat-agent | schedule
    triggered_by_id: str | None = None
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parent_assignment: str | None = Field(default=None, foreign_key="assignments.id")

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
    monitor: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
