"""add_artifacts_core

Git-like Artifact Governance — 통합 산출물 모델 신설.
- artifacts (working copy)
- artifact_versions (불변 스냅샷)
- pull_requests (staging → review → merge)
- change_events (범용 감사 로그)

Revision ID: a4c1b2d3e4f5
Revises: a2b3c4d5e6f7
Create Date: 2026-04-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c1b2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) artifacts — working copy
    #    Circular FK 회피: current_version_id / open_pr_id는 테이블 생성 시
    #    FK 없이 UUID 컬럼만 추가하고, 뒤에서 use_alter ADD CONSTRAINT로 붙인다.
    op.create_table(
        "artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("artifact_type", sa.String(length=20), nullable=False),
        sa.Column("display_id", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "content",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "working_status",
            sa.String(length=20),
            nullable=False,
            server_default="dirty",
        ),
        sa.Column(
            "lifecycle_status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("open_pr_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "artifact_type", "display_id",
            name="uq_artifacts_project_type_display",
        ),
        sa.CheckConstraint(
            "artifact_type IN ('record','srs','design','testcase')",
            name="ck_artifacts_type",
        ),
        sa.CheckConstraint(
            "working_status IN ('clean','dirty','staged')",
            name="ck_artifacts_working_status",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('active','archived','deleted')",
            name="ck_artifacts_lifecycle_status",
        ),
        sa.CheckConstraint(
            "working_status <> 'staged' OR open_pr_id IS NOT NULL",
            name="ck_artifacts_staged_requires_pr",
        ),
        sa.CheckConstraint(
            "working_status <> 'clean' OR current_version_id IS NOT NULL",
            name="ck_artifacts_clean_requires_version",
        ),
    )
    op.create_index(
        "ix_artifacts_project_type",
        "artifacts",
        ["project_id", "artifact_type"],
    )

    # 2) artifact_versions — 불변 커밋 스냅샷
    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.UUID(), nullable=True),
        sa.Column("snapshot", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "commit_message",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "author_id",
            sa.String(length=100),
            nullable=False,
            server_default="system",
        ),
        sa.Column(
            "committed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("merged_from_pr_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["artifacts.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"], ["artifact_versions.id"], ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "artifact_id", "version_number",
            name="uq_artifact_versions_artifact_vn",
        ),
    )
    op.create_index(
        "ix_artifact_versions_artifact",
        "artifact_versions",
        ["artifact_id", "version_number"],
    )

    # 3) pull_requests — artifacts/artifact_versions 존재 후 생성
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("base_version_id", sa.UUID(), nullable=True),
        sa.Column("head_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="open",
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author_id", sa.String(length=100), nullable=False),
        sa.Column("reviewer_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["artifacts.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["base_version_id"], ["artifact_versions.id"], ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["head_version_id"], ["artifact_versions.id"], ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('open','approved','rejected','merged','superseded')",
            name="ck_pull_requests_status",
        ),
    )
    op.create_index(
        "ix_pull_requests_artifact_status",
        "pull_requests",
        ["artifact_id", "status"],
    )
    # 부분 유니크: open 상태 PR은 artifact당 1개
    op.create_index(
        "uq_pr_one_open_per_artifact",
        "pull_requests",
        ["artifact_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    # 4) Circular FK를 use_alter로 뒤늦게 추가
    op.create_foreign_key(
        "fk_artifacts_current_version",
        "artifacts", "artifact_versions",
        ["current_version_id"], ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_artifacts_open_pr",
        "artifacts", "pull_requests",
        ["open_pr_id"], ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_artifact_versions_pr",
        "artifact_versions", "pull_requests",
        ["merged_from_pr_id"], ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )

    # 5) change_events — 감사 로그
    op.create_table(
        "change_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("artifact_id", sa.UUID(), nullable=True),
        sa.Column("pr_id", sa.UUID(), nullable=True),
        sa.Column("version_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column(
            "actor",
            sa.String(length=100),
            nullable=False,
            server_default="system",
        ),
        sa.Column("diff_summary", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("impact_summary", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["artifacts.id"], ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["pr_id"], ["pull_requests.id"], ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"], ["artifact_versions.id"], ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_change_events_project",
        "change_events",
        ["project_id", "occurred_at"],
    )
    op.create_index(
        "ix_change_events_artifact",
        "change_events",
        ["artifact_id", "occurred_at"],
    )


def downgrade() -> None:
    # Circular FK 먼저 제거
    op.drop_constraint("fk_artifact_versions_pr", "artifact_versions", type_="foreignkey")
    op.drop_constraint("fk_artifacts_open_pr", "artifacts", type_="foreignkey")
    op.drop_constraint("fk_artifacts_current_version", "artifacts", type_="foreignkey")

    op.drop_index("ix_change_events_artifact", table_name="change_events")
    op.drop_index("ix_change_events_project", table_name="change_events")
    op.drop_table("change_events")

    op.drop_index("uq_pr_one_open_per_artifact", table_name="pull_requests")
    op.drop_index("ix_pull_requests_artifact_status", table_name="pull_requests")
    op.drop_table("pull_requests")

    op.drop_index("ix_artifact_versions_artifact", table_name="artifact_versions")
    op.drop_table("artifact_versions")

    op.drop_index("ix_artifacts_project_type", table_name="artifacts")
    op.drop_table("artifacts")
