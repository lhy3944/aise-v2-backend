"""remove_is_required_from_sections

Revision ID: b6c0e46306ed
Revises: f1df240269cf
Create Date: 2026-04-06 02:48:41.376671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b6c0e46306ed'
down_revision: Union[str, Sequence[str], None] = 'f1df240269cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('requirement_sections', 'is_required')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('requirement_sections', sa.Column('is_required', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
