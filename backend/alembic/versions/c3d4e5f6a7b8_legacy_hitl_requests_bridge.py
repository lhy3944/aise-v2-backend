"""legacy hitl_requests bridge

Revision ID: c3d4e5f6a7b8
Revises: 535a79769c7e
Create Date: 2026-04-29

Some development databases were stamped with an early Phase 3 prototype
revision that created a preliminary `hitl_requests` table. The revision file
was not kept in the branch. Keep this no-op bridge so those databases can move
forward; the next migration upgrades the existing prototype table if present.
"""
from __future__ import annotations


revision = "c3d4e5f6a7b8"
down_revision = "535a79769c7e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
