"""add_artifact_dependencies

Artifact 간 계보 그래프 — upstream 변경 시 downstream 영향도 전파.

Revision ID: b5d2c3e4f506
Revises: a4c1b2d3e4f5
Create Date: 2026-04-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5d2c3e4f506"
down_revision: Union[str, Sequence[str], None] = "a4c1b2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artifact_dependencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("upstream_artifact_id", sa.UUID(), nullable=False),
        sa.Column("downstream_artifact_id", sa.UUID(), nullable=False),
        sa.Column(
            "dependency_type",
            sa.String(length=20),
            nullable=False,
            server_default="derives_from",
        ),
        sa.Column("upstream_version_pinned_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["upstream_artifact_id"], ["artifacts.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["downstream_artifact_id"], ["artifacts.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["upstream_version_pinned_id"],
            ["artifact_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "upstream_artifact_id", "downstream_artifact_id",
            name="uq_artifact_dependencies_pair",
        ),
        sa.CheckConstraint(
            "dependency_type IN ('derives_from','references','covers')",
            name="ck_artifact_dependencies_type",
        ),
        sa.CheckConstraint(
            "upstream_artifact_id <> downstream_artifact_id",
            name="ck_artifact_dependencies_no_self",
        ),
    )
    op.create_index(
        "ix_artifact_dependencies_upstream",
        "artifact_dependencies",
        ["upstream_artifact_id"],
    )
    op.create_index(
        "ix_artifact_dependencies_downstream",
        "artifact_dependencies",
        ["downstream_artifact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_artifact_dependencies_downstream",
        table_name="artifact_dependencies",
    )
    op.drop_index(
        "ix_artifact_dependencies_upstream",
        table_name="artifact_dependencies",
    )
    op.drop_table("artifact_dependencies")
