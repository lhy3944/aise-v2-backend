import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import String, Text, Boolean, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class RequirementSection(Base):
    """섹션 — SRS 문서 구조를 정의하는 단위"""
    __tablename__ = "requirement_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # fr, qa, constraints, overview, interfaces, other
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_format_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship(back_populates="requirement_sections")
    requirements: Mapped[list["Requirement"]] = relationship(back_populates="section")


# 프로젝트 생성 시 자동 생성되는 기본 섹션 정의
DEFAULT_SECTIONS = [
    {"type": "overview", "name": "Overview", "description": "시스템 개요 및 범위", "is_default": True, "order_index": 0},
    {"type": "fr", "name": "Functional Requirements", "description": "기능 요구사항", "is_default": True, "order_index": 1},
    {"type": "qa", "name": "Quality Attributes", "description": "품질 속성 (성능, 보안 등)", "is_default": True, "order_index": 2},
    {"type": "constraints", "name": "Constraints", "description": "제약 조건", "is_default": True, "order_index": 3},
    {"type": "interfaces", "name": "Interfaces", "description": "외부 인터페이스 정의", "is_default": True, "order_index": 4},
]


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint("project_id", "display_id", name="uq_requirements_project_display_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("requirement_sections.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # fr, qa, constraints, other
    display_id: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    refined_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=True, server_default=sa.true())
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship(back_populates="requirements")
    section: Mapped["RequirementSection | None"] = relationship(back_populates="requirements")


class RequirementVersion(Base):
    """요구사항 저장 시점의 스냅샷"""
    __tablename__ = "requirement_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized requirements
    saved_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
