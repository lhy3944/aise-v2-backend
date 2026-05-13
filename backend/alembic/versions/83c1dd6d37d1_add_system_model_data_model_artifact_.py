"""add_system_model_data_model_artifact_types

Revision ID: 83c1dd6d37d1
Revises: 9d8f1e2c3b4a
Create Date: 2026-05-12 19:03:14.918534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83c1dd6d37d1'
down_revision: Union[str, Sequence[str], None] = '9d8f1e2c3b4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_CONSTRAINT = "ck_artifacts_type"
NEW_TYPES = "'record','srs','system_model','data_model','design','testcase'"
OLD_TYPES = "'record','srs','design','testcase'"


def upgrade() -> None:
    op.drop_constraint(OLD_CONSTRAINT, "artifacts", type_="check")
    op.execute(
        f"ALTER TABLE artifacts ADD CONSTRAINT {OLD_CONSTRAINT} "
        f"CHECK (artifact_type IN ({NEW_TYPES}))"
    )


def downgrade() -> None:
    op.drop_constraint(OLD_CONSTRAINT, "artifacts", type_="check")
    op.execute(
        f"ALTER TABLE artifacts ADD CONSTRAINT {OLD_CONSTRAINT} "
        f"CHECK (artifact_type IN ({OLD_TYPES}))"
    )
