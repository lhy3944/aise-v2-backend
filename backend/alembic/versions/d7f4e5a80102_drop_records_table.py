"""drop_records_table

레거시 `records` 테이블 제거. 데이터는 c6e3d4f50607 backfill 마이그레이션을
통해 이미 `artifacts(artifact_type='record')` 에 이관됐으며, 애플리케이션
쓰기 경로도 artifact 어댑터로 전환됐다.

Revision ID: d7f4e5a80102
Revises: c6e3d4f50607
Create Date: 2026-04-24
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "d7f4e5a80102"
down_revision: Union[str, Sequence[str], None] = "c6e3d4f50607"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS records CASCADE")


def downgrade() -> None:
    # 데이터 보존 원칙 — 다운그레이드로 records 테이블을 되살리지 않는다.
    # artifacts 가 primary store 이므로 Records 로의 완전한 복원은 불가능.
    pass
