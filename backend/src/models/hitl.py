import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


HITL_STATUSES = ("pending", "resumed", "expired", "cancelled")
HITL_KINDS = ("clarify", "confirm", "decision")


class HitlRequest(Base):
    """Persisted HITL interrupt context for resume and audit."""

    __tablename__ = "hitl_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','resumed','expired','cancelled')",
            name="ck_hitl_requests_status",
        ),
        CheckConstraint(
            "interrupt_kind IN ('clarify','confirm','decision')",
            name="ck_hitl_requests_kind",
        ),
        Index("ix_hitl_requests_thread_status", "thread_id", "status"),
        Index("ix_hitl_requests_session_status", "session_id", "status"),
        Index("ix_hitl_requests_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_input: Mapped[str] = mapped_column(Text, nullable=False, default="")
    selected_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    interrupt_id: Mapped[str] = mapped_column(String(100), nullable=False)
    interrupt_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    routing: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    accumulated_state: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
