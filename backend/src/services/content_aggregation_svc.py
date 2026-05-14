"""Content aggregation service — artifact content JSONB 필드별 on-demand 집계.

ProjectStatusAgent가 사용자 질문에 맞춰 동적으로 DB를 조회할 수 있도록,
artifact content JSONB의 임의 필드에 대해 GROUP BY + COUNT 쿼리를 제공한다.

새 artifact type이나 content 필드가 추가되어도 코드 변경 없이 자동 대응.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.artifact import Artifact

_MISSING_LABEL = "(없음)"


def _jsonb_column(field_path: str):
    """field_path 문자열을 SQLAlchemy JSONB 접근 표현식으로 변환.

    "priority"           → Artifact.content["priority"].astext
    "metadata.status"    → Artifact.content["metadata"]["status"].astext
    """
    col = Artifact.content
    for part in field_path.split("."):
        col = col[part]
    return col.astext


async def aggregate_field(
    db: AsyncSession,
    project_id: uuid.UUID,
    artifact_type: str,
    field_path: str,
) -> dict[str, int]:
    """지정 artifact_type의 content JSONB에서 field_path 값별 개수 반환.

    예: aggregate_field(db, pid, "testcase", "priority")
        → {"high": 3, "medium": 5, "low": 2}
    """
    expr = _jsonb_column(field_path)
    rows = (
        await db.execute(
            select(expr, func.count())
            .where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == artifact_type,
                Artifact.lifecycle_status == "active",
            )
            .group_by(expr)
            .order_by(func.count().desc())
        )
    ).all()

    result: dict[str, int] = {}
    for value, cnt in rows:
        key = value if value else _MISSING_LABEL
        result[key] = cnt
    return result


async def query_content_by_field(
    db: AsyncSession,
    project_id: uuid.UUID,
    artifact_type: str,
    field_path: str,
    field_value: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """특정 필드값과 일치하는 artifact의 content + display_id 반환.

    예: query_content_by_field(db, pid, "testcase", "priority", "high")
        → [{"display_id": "TC-001", "title": "...", "priority": "high", ...}, ...]
    """
    expr = _jsonb_column(field_path)
    rows = (
        await db.execute(
            select(Artifact.display_id, Artifact.content)
            .where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == artifact_type,
                Artifact.lifecycle_status == "active",
                expr == field_value,
            )
            .limit(limit)
        )
    ).all()

    result: list[dict[str, Any]] = []
    for display_id, content in rows:
        item = content if isinstance(content, dict) else {}
        item["display_id"] = display_id
        result.append(item)
    return result


__all__ = [
    "aggregate_field",
    "query_content_by_field",
]
