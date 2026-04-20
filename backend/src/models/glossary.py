import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class GlossaryItem(Base):
    __tablename__ = "glossary_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    term: Mapped[str] = mapped_column(String(200), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    product_group: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Phase 2.2 확장 필드
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    synonyms: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    abbreviations: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    section_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    is_auto_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship(back_populates="glossary_items")
    source_document: Mapped["KnowledgeDocument | None"] = relationship()
