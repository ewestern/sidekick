"""Initial schema — sources, artifacts, assignments tables.

Revision ID: 001
Revises:
Create Date: 2026-03-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # -- sources --------------------------------------------------------
    op.create_table(
        "sources",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column("expected_content", sa.JSON(), nullable=True),
        sa.Column("beat", sa.Text(), nullable=True),
        sa.Column("geo", sa.Text(), nullable=True),
        sa.Column("related_sources", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("discovered_by", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("examination_status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("health", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # -- artifacts ------------------------------------------------------
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=True),
        sa.Column("derived_from", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("source_id", sa.Text(), nullable=True),
        sa.Column("event_group", sa.Text(), nullable=True),
        sa.Column("beat", sa.Text(), nullable=True),
        sa.Column("geo", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("assignment_id", sa.Text(), nullable=True),
        sa.Column("entities", sa.JSON(), nullable=True),
        sa.Column("topics", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("content_uri", sa.Text(), nullable=True),
        sa.Column("acquisition_url", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("superseded_by", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["superseded_by"], ["artifacts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_artifacts_stage_beat_geo",
        "artifacts",
        ["stage", "beat", "geo"],
    )
    op.create_index("ix_artifacts_event_group", "artifacts", ["event_group"])
    op.create_index("ix_artifacts_assignment_id", "artifacts", ["assignment_id"])
    # ivfflat index for approximate nearest-neighbour cosine search
    op.execute(
        "CREATE INDEX ix_artifacts_embedding ON artifacts "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # -- assignments ----------------------------------------------------
    op.create_table(
        "assignments",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_params", sa.JSON(), nullable=True),
        sa.Column("triggered_by", sa.Text(), nullable=True),
        sa.Column("triggered_by_id", sa.Text(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("parent_assignment", sa.Text(), nullable=True),
        sa.Column("artifacts_in", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("artifacts_out", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("sub_assignments", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("monitor", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["parent_assignment"], ["assignments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("assignments")
    op.drop_index("ix_artifacts_embedding", table_name="artifacts")
    op.drop_index("ix_artifacts_assignment_id", table_name="artifacts")
    op.drop_index("ix_artifacts_event_group", table_name="artifacts")
    op.drop_index("ix_artifacts_stage_beat_geo", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_table("sources")
    op.execute("DROP EXTENSION IF EXISTS vector")
