"""Add analysis scope coordinator table.

Revision ID: 005
Revises: 004
Create Date: 2026-03-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_scopes",
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("event_group", sa.Text(), nullable=False),
        sa.Column("beat", sa.Text(), nullable=False),
        sa.Column("geo", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="idle", nullable=False),
        sa.Column("dirty", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active_execution_arn", sa.Text(), nullable=True),
        sa.Column("last_input_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_revision_started", sa.Integer(), nullable=True),
        sa.Column("last_revision_completed", sa.Integer(), nullable=True),
        sa.Column("last_brief_artifact_id", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["last_brief_artifact_id"], ["artifacts.id"]),
        sa.PrimaryKeyConstraint("scope_key"),
    )
    op.create_index("ix_analysis_scopes_event_group", "analysis_scopes", ["event_group"])
    op.create_index(
        "ix_analysis_scopes_active_execution_arn",
        "analysis_scopes",
        ["active_execution_arn"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_scopes_active_execution_arn", table_name="analysis_scopes")
    op.drop_index("ix_analysis_scopes_event_group", table_name="analysis_scopes")
    op.drop_table("analysis_scopes")
