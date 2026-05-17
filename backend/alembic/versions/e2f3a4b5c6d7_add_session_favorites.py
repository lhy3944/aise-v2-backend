"""add_session_favorites

Revision ID: e2f3a4b5c6d7
Revises: 83c1dd6d37d1
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "83c1dd6d37d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(
        "ix_sessions_project_favorite",
        "sessions",
        ["project_id", "is_favorite"],
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_project_favorite", table_name="sessions")
    op.drop_column("sessions", "is_favorite")
