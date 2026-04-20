"""DB 조회 공통 유틸리티"""

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException

T = TypeVar("T")


async def get_or_404(
    db: AsyncSession,
    model: type[T],
    *filters,
    error_msg: str = "리소스를 찾을 수 없습니다.",
) -> T:
    """주어진 모델과 필터 조건으로 단일 레코드를 조회한다.

    레코드가 없으면 AppException(404)을 발생시킨다.

    Usage::

        project = await get_or_404(db, Project, Project.id == project_id,
                                   error_msg="프로젝트를 찾을 수 없습니다.")
    """
    result = await db.execute(select(model).where(*filters))
    item = result.scalar_one_or_none()
    if item is None:
        raise AppException(404, error_msg)
    return item
