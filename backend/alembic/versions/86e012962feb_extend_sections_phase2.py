"""extend_sections_phase2

Revision ID: 86e012962feb
Revises: 8f8875d1d811
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '86e012962feb'
down_revision: Union[str, Sequence[str], None] = '8f8875d1d811'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('requirement_sections', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('requirement_sections', sa.Column('output_format_hint', sa.Text(), nullable=True))
    op.add_column('requirement_sections', sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('requirement_sections', sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('requirement_sections', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('requirement_sections', 'is_active')
    op.drop_column('requirement_sections', 'is_default')
    op.drop_column('requirement_sections', 'is_required')
    op.drop_column('requirement_sections', 'output_format_hint')
    op.drop_column('requirement_sections', 'description')
