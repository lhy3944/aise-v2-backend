"""change_is_selected_default_to_true

Revision ID: b9ecf95eea63
Revises: bcdc56812745
Create Date: 2026-03-31 11:04:32.381168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9ecf95eea63'
down_revision: Union[str, Sequence[str], None] = 'bcdc56812745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'requirements',
        'is_selected',
        server_default=sa.true(),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'requirements',
        'is_selected',
        server_default=None,
    )
