"""Impact / Stale API 라우터."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.impact import (
    ImpactApplyRequest,
    ImpactApplyResponse,
    ImpactResponse,
)
from src.services import impact_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/impact",
    tags=["impact"],
)


@router.get("", response_model=ImpactResponse)
async def get_impact(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트의 모든 stale artifact 목록.

    `source_artifact_versions` lineage 를 바탕으로, 현재 입력 source 의
    version 이 갱신됐는데 이 artifact 는 옛 source 를 참조 중인 케이스를 반환.
    """
    return await impact_svc.get_project_impact(db, project_id)


@router.post("/apply", response_model=ImpactApplyResponse)
async def apply_impact(
    project_id: uuid.UUID,
    body: ImpactApplyRequest,
    db: AsyncSession = Depends(get_db),
):
    """선택된(또는 전체) stale artifact 를 일괄 자동 재생성.

    - `body.artifact_ids` 가 비어 있으면 프로젝트의 모든 stale 을 대상으로 한다.
    - srs / design 만 자동 재생성 지원. record / testcase 는 skipped 로 응답.
    """
    return await impact_svc.apply_regeneration(
        db, project_id, artifact_ids=body.artifact_ids or None,
    )
