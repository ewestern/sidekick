"""Add artifacts.story_key for story candidate and draft dedupe.

Revision ID: 006
Revises: 005
Create Date: 2026-03-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "artifacts",
        sa.Column("story_key", sa.Text(), nullable=True),
    )
    op.create_index("ix_artifacts_story_key", "artifacts", ["story_key"])


def downgrade() -> None:
    op.drop_index("ix_artifacts_story_key", table_name="artifacts")
    op.drop_column("artifacts", "story_key")
