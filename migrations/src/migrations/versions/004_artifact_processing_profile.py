"""Add artifacts.processing_profile and artifacts.title.

Revision ID: 004
Revises: 003
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "artifacts",
        sa.Column("processing_profile", sa.Text(), nullable=True),
    )
    op.add_column(
        "artifacts",
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
    )
    op.drop_column("sources", "expected_content")
    op.alter_column("artifacts", "title", server_default=None)
    op.add_column(
        "sources",
        sa.Column("source_tier", sa.Text(), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("outlet", sa.Text(), nullable=True),
    )
    # Backfill existing rows to "primary" then make non-nullable
    op.execute("UPDATE sources SET source_tier = 'primary' WHERE source_tier IS NULL")
    op.alter_column("sources", "source_tier", nullable=False)
    op.drop_column("sources", "discovered_by")
    op.drop_column("sources", "examination_status")
    op.add_column(
        "sources",
        sa.Column("status", sa.Text(), nullable=True),
    )
    op.execute("UPDATE sources SET status = 'active' WHERE status IS NULL")
    op.alter_column("sources", "status", nullable=False)


def downgrade() -> None:

    op.drop_column("artifacts", "processing_profile")
    op.drop_column("artifacts", "title")
    op.add_column(
        "sources",
        sa.Column("expected_content", sa.JSON(), nullable=True),
    )
    op.drop_column("sources", "source_tier")
    op.drop_column("sources", "outlet")
    op.add_column(
        "sources",
        sa.Column("discovered_by", sa.Text(), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("examination_status", sa.Text(),
                  nullable=False, server_default="pending"),
    )
    op.drop_column("sources", "status")
