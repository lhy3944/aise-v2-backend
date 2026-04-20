"""add_srs_tables

Revision ID: f1df240269cf
Revises: 13788b005ba9
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f1df240269cf'
down_revision: Union[str, Sequence[str], None] = '13788b005ba9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('srs_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='generating'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('based_on_records', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('based_on_documents', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('srs_sections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('srs_document_id', sa.UUID(), nullable=False),
        sa.Column('section_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['section_id'], ['requirement_sections.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['srs_document_id'], ['srs_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('srs_sections')
    op.drop_table('srs_documents')
