"""SRS Document 모델"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class SrsDocument(Base):
    __tablename__ = "srs_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), default="generating")  # generating, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    based_on_records: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"record_ids": [...]}
    based_on_documents: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"document_ids": [...], "names": [...]}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sections: Mapped[list["SrsSection"]] = relationship(back_populates="srs_document", cascade="all, delete-orphan")


class SrsSection(Base):
    __tablename__ = "srs_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    srs_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("srs_documents.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("requirement_sections.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    srs_document: Mapped["SrsDocument"] = relationship(back_populates="sections")
