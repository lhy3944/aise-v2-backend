"""extend_glossary_items_phase2

Revision ID: 8f8875d1d811
Revises: b726d9c9f754
Create Date: 2026-04-05 01:03:18.546722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f8875d1d811'
down_revision: Union[str, Sequence[str], None] = 'b726d9c9f754'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('glossary_items', sa.Column('source_document_id', sa.UUID(), nullable=True))
    op.add_column('glossary_items', sa.Column('synonyms', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('glossary_items', sa.Column('abbreviations', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('glossary_items', sa.Column('section_tags', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('glossary_items', sa.Column('is_auto_extracted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('glossary_items', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('glossary_items', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')))
    op.add_column('glossary_items', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')))
    op.create_foreign_key('fk_glossary_source_document', 'glossary_items', 'knowledge_documents', ['source_document_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_glossary_source_document', 'glossary_items', type_='foreignkey')
    op.drop_column('glossary_items', 'updated_at')
    op.drop_column('glossary_items', 'created_at')
    op.drop_column('glossary_items', 'is_approved')
    op.drop_column('glossary_items', 'is_auto_extracted')
    op.drop_column('glossary_items', 'section_tags')
    op.drop_column('glossary_items', 'abbreviations')
    op.drop_column('glossary_items', 'synonyms')
    op.drop_column('glossary_items', 'source_document_id')
