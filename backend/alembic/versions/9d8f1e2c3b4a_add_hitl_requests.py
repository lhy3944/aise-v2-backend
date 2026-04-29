"""add hitl_requests

Revision ID: 9d8f1e2c3b4a
Revises: c3d4e5f6a7b8
Create Date: 2026-04-29

Phase 3 HITL persistence:
- pending interrupt context survives process restart
- completed requests are retained for audit
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "9d8f1e2c3b4a"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "hitl_requests" in inspector.get_table_names():
        _upgrade_existing_table()
        return

    op.create_table(
        "hitl_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False, server_default=""),
        sa.Column("selected_agent", sa.String(length=100), nullable=False),
        sa.Column("interrupt_id", sa.String(length=100), nullable=False),
        sa.Column("interrupt_kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("routing", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "accumulated_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", name="uq_hitl_requests_thread_id"),
        sa.CheckConstraint(
            "status IN ('pending','resumed','expired','cancelled')",
            name="ck_hitl_requests_status",
        ),
        sa.CheckConstraint(
            "interrupt_kind IN ('clarify','confirm','decision')",
            name="ck_hitl_requests_kind",
        ),
    )
    op.create_index(
        "ix_hitl_requests_thread_status",
        "hitl_requests",
        ["thread_id", "status"],
    )
    op.create_index(
        "ix_hitl_requests_session_status",
        "hitl_requests",
        ["session_id", "status"],
    )
    op.create_index(
        "ix_hitl_requests_expires_at",
        "hitl_requests",
        ["expires_at"],
    )


def _upgrade_existing_table() -> None:
    """Bring the early Phase 3 prototype table up to the persisted schema.

    Some dev/test DBs already contain a prototype `hitl_requests` table
    (`kind`, `request_payload`, `response_payload`, `responded_at`). Preserve
    data and add the columns used by the current model instead of dropping it.
    """

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("hitl_requests")}

    def add(name: str, column: sa.Column) -> None:
        if name not in columns:
            op.add_column("hitl_requests", column)
            columns.add(name)

    add("thread_id", sa.Column("thread_id", sa.String(length=100), nullable=True))
    add("user_input", sa.Column("user_input", sa.Text(), nullable=True))
    add("selected_agent", sa.Column("selected_agent", sa.String(length=100), nullable=True))
    add("interrupt_kind", sa.Column("interrupt_kind", sa.String(length=20), nullable=True))
    add("payload", sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    add("history", sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    add("routing", sa.Column("routing", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    add(
        "accumulated_state",
        sa.Column("accumulated_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    add("response", sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    add("expires_at", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    add("completed_at", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE hitl_requests SET thread_id = interrupt_id WHERE thread_id IS NULL")
    op.execute("UPDATE hitl_requests SET user_input = '' WHERE user_input IS NULL")
    op.execute("UPDATE hitl_requests SET selected_agent = 'unknown' WHERE selected_agent IS NULL")
    if "kind" in columns:
        op.execute("UPDATE hitl_requests SET interrupt_kind = kind WHERE interrupt_kind IS NULL")
    op.execute("UPDATE hitl_requests SET interrupt_kind = 'confirm' WHERE interrupt_kind IS NULL")
    if "request_payload" in columns:
        op.execute("UPDATE hitl_requests SET payload = request_payload WHERE payload IS NULL")
    op.execute("UPDATE hitl_requests SET payload = '{}'::jsonb WHERE payload IS NULL")
    op.execute("UPDATE hitl_requests SET history = '[]'::jsonb WHERE history IS NULL")
    op.execute(
        "UPDATE hitl_requests SET accumulated_state = '{}'::jsonb "
        "WHERE accumulated_state IS NULL"
    )
    if "response_payload" in columns:
        op.execute("UPDATE hitl_requests SET response = response_payload WHERE response IS NULL")
    op.execute(
        "UPDATE hitl_requests SET expires_at = created_at + interval '24 hours' "
        "WHERE expires_at IS NULL"
    )
    if "responded_at" in columns:
        op.execute(
            "UPDATE hitl_requests SET completed_at = responded_at "
            "WHERE completed_at IS NULL"
        )

    # Prototype-only columns are left in place for backward compatibility, but
    # the current ORM no longer writes them.
    if "kind" in columns:
        op.alter_column(
            "hitl_requests",
            "kind",
            existing_type=sa.String(length=20),
            nullable=True,
        )
    if "request_payload" in columns:
        op.alter_column(
            "hitl_requests",
            "request_payload",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    if "response_payload" in columns:
        op.alter_column(
            "hitl_requests",
            "response_payload",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    if "updated_at" in columns:
        op.alter_column(
            "hitl_requests",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )

    for name in [
        "thread_id",
        "user_input",
        "selected_agent",
        "interrupt_kind",
        "payload",
        "history",
        "accumulated_state",
        "expires_at",
    ]:
        op.alter_column("hitl_requests", name, nullable=False)

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_hitl_requests_thread_id "
        "ON hitl_requests(thread_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hitl_requests_thread_status "
        "ON hitl_requests(thread_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hitl_requests_session_status "
        "ON hitl_requests(session_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hitl_requests_expires_at "
        "ON hitl_requests(expires_at)"
    )


def downgrade() -> None:
    op.drop_index("ix_hitl_requests_expires_at", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_session_status", table_name="hitl_requests")
    op.drop_index("ix_hitl_requests_thread_status", table_name="hitl_requests")
    op.drop_table("hitl_requests")
