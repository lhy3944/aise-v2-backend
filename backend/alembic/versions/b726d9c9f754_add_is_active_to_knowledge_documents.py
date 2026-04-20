"""add_is_active_to_knowledge_documents

Revision ID: b726d9c9f754
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05 00:23:22.682817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b726d9c9f754'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'knowledge_documents',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    # 기존 status 값 마이그레이션: uploading→pending, ready→completed, error→failed
    op.execute("UPDATE knowledge_documents SET status = 'pending' WHERE status = 'uploading'")
    op.execute("UPDATE knowledge_documents SET status = 'completed' WHERE status = 'ready'")
    op.execute("UPDATE knowledge_documents SET status = 'failed' WHERE status = 'error'")


def downgrade() -> None:
    """Downgrade schema."""
    # status 값 복원
    op.execute("UPDATE knowledge_documents SET status = 'uploading' WHERE status = 'pending'")
    op.execute("UPDATE knowledge_documents SET status = 'ready' WHERE status = 'completed'")
    op.execute("UPDATE knowledge_documents SET status = 'error' WHERE status = 'failed'")
    op.drop_column('knowledge_documents', 'is_active')
