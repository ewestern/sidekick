"""Add api_clients table for machine API key auth.

Revision ID: 003
Revises: 002
Create Date: 2026-03-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_clients",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("roles", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.Text(), nullable=False,
                  server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["rotated_from"], ["api_clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_clients_key_prefix", "api_clients", ["key_prefix"])


def downgrade() -> None:
    op.drop_index("ix_api_clients_key_prefix", table_name="api_clients")
    op.drop_table("api_clients")
