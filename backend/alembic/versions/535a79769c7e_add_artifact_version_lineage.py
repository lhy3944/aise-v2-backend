"""add artifact_version lineage column

Revision ID: 535a79769c7e
Revises: d7f4e5a80102
Create Date: 2026-04-27

Phase E (PLAN_ARTIFACT_LINEAGE.md §E.1):
artifact_versions.source_artifact_versions JSONB nullable.

Schema:
{
  "record": [{"artifact_id": "uuid", "version_number": 3}, ...],
  "srs":    [{"artifact_id": "uuid", "version_number": 1, "section_id": "..."}],
  "design": [{"artifact_id": "uuid", "version_number": 2}, ...]
}

각 entry 는 "이 ArtifactVersion 을 만들 때 입력으로 사용한 다른 artifact 의
version" 을 명시한다 — record 가 v3→v4 가 되면 이 SRS version 은
referenced(v3) < current(v4) 이므로 stale 판정 가능.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "535a79769c7e"
down_revision = "d7f4e5a80102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifact_versions",
        sa.Column(
            "source_artifact_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_artifact_versions_source_lineage",
        "artifact_versions",
        ["source_artifact_versions"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_versions_source_lineage", table_name="artifact_versions")
    op.drop_column("artifact_versions", "source_artifact_versions")
