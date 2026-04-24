"""Artifact 통합 모델 — Record/SRS/Design/TestCase 공통 Git-like 버전 관리

Git 개념 매핑:
- Artifact.working_status:
    clean   = HEAD 버전과 일치, 변경 없음
    dirty   = working copy에 pending edit 존재 (PR 미생성)
    staged  = open PR이 워킹 카피를 lock 중
- ArtifactVersion = 불변 커밋 스냅샷 (append-only)
- PullRequest = staging → review → merge 라이프사이클
- ChangeEvent = 범용 감사 로그
- ArtifactDependency = 영향도 전파 그래프 (upstream → downstream)
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


ARTIFACT_TYPES = ("record", "srs", "design", "testcase")
WORKING_STATUSES = ("clean", "dirty", "staged")
LIFECYCLE_STATUSES = ("active", "archived", "deleted")
PR_STATUSES = ("open", "approved", "rejected", "merged", "superseded")
DEPENDENCY_TYPES = ("derives_from", "references", "covers")
CHANGE_ACTIONS = (
    "created",
    "edited",
    "staged",
    "pr_opened",
    "pr_approved",
    "pr_merged",
    "pr_rejected",
    "reverted",
)


class Artifact(Base):
    """산출물 working copy — 타입별 payload를 JSONB로 통합."""

    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "artifact_type", "display_id",
            name="uq_artifacts_project_type_display",
        ),
        CheckConstraint(
            "artifact_type IN ('record','srs','design','testcase')",
            name="ck_artifacts_type",
        ),
        CheckConstraint(
            "working_status IN ('clean','dirty','staged')",
            name="ck_artifacts_working_status",
        ),
        CheckConstraint(
            "lifecycle_status IN ('active','archived','deleted')",
            name="ck_artifacts_lifecycle_status",
        ),
        CheckConstraint(
            "working_status <> 'staged' OR open_pr_id IS NOT NULL",
            name="ck_artifacts_staged_requires_pr",
        ),
        CheckConstraint(
            "working_status <> 'clean' OR current_version_id IS NOT NULL",
            name="ck_artifacts_clean_requires_version",
        ),
        Index("ix_artifacts_project_type", "project_id", "artifact_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_id: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 타입별 payload (record: {text, source_location, confidence_score, ...},
    # srs: {sections: [...]}, testcase: {steps: [...], expected: ...})
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    working_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="dirty"
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )

    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "artifact_versions.id",
            use_alter=True,
            name="fk_artifacts_current_version",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    open_pr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "pull_requests.id",
            use_alter=True,
            name="fk_artifacts_open_pr",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ArtifactVersion(Base):
    """불변 커밋 스냅샷. 한 번 작성되면 수정하지 않는다."""

    __tablename__ = "artifact_versions"
    __table_args__ = (
        UniqueConstraint(
            "artifact_id", "version_number",
            name="uq_artifact_versions_artifact_vn",
        ),
        Index(
            "ix_artifact_versions_artifact",
            "artifact_id", "version_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author_id: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    merged_from_pr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "pull_requests.id",
            use_alter=True,
            name="fk_artifact_versions_pr",
            ondelete="SET NULL",
        ),
        nullable=True,
    )


class PullRequest(Base):
    """Artifact 단위 PR. artifact당 open 상태는 최대 1개 (부분 유니크 인덱스)."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','approved','rejected','merged','superseded')",
            name="ck_pull_requests_status",
        ),
        Index("ix_pull_requests_artifact_status", "artifact_id", "status"),
        Index(
            "uq_pr_one_open_per_artifact",
            "artifact_id",
            unique=True,
            postgresql_where=sa.text("status = 'open'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    head_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    author_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ChangeEvent(Base):
    """범용 감사 로그 — 모든 Artifact 변경 이력."""

    __tablename__ = "change_events"
    __table_args__ = (
        Index("ix_change_events_project", "project_id", "occurred_at"),
        Index("ix_change_events_artifact", "artifact_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    pr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    diff_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    impact_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ArtifactDependency(Base):
    """Artifact 간 계보 — upstream 변경 시 downstream 영향도 전파."""

    __tablename__ = "artifact_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "upstream_artifact_id", "downstream_artifact_id",
            name="uq_artifact_dependencies_pair",
        ),
        CheckConstraint(
            "dependency_type IN ('derives_from','references','covers')",
            name="ck_artifact_dependencies_type",
        ),
        CheckConstraint(
            "upstream_artifact_id <> downstream_artifact_id",
            name="ck_artifact_dependencies_no_self",
        ),
        Index("ix_artifact_dependencies_upstream", "upstream_artifact_id"),
        Index("ix_artifact_dependencies_downstream", "downstream_artifact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upstream_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    downstream_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="derives_from"
    )
    upstream_version_pinned_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
