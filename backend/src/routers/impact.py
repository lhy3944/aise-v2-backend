"""Impact / Stale API 라우터."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session, get_db
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """선택된(또는 전체) stale artifact 를 백그라운드에서 일괄 자동 재생성.

    - `body.artifact_ids` 가 비어 있으면 프로젝트의 모든 stale 을 대상으로 한다.
    - srs / design / testcase 자동 재생성 지원. record 는 skipped.
    - 즉시 빈 응답을 반환하고 실제 재생성은 백그라운드에서 실행됩니다.
    """
    artifact_ids = body.artifact_ids or None

    # 백그라운드에서 재생성 실행 — 새로고침해도 진행 유지
    background_tasks.add_task(
        _run_regeneration_background,
        str(project_id),
        artifact_ids,
    )

    return ImpactApplyResponse()


async def _run_regeneration_background(
    project_id_str: str,
    artifact_ids: list[str] | None,
) -> None:
    """BackgroundTasks에서 실행되는 재생성 로직.

    세션 팩토리를 전달하여 각 재생성 작업이 독립적인 단명 세션을
    사용하도록 한다. 긴 LLM 호출 후 커넥션이 닫히는 문제를 방지.
    """
    from loguru import logger

    project_id = uuid.UUID(project_id_str)
    try:
        await impact_svc.apply_regeneration(
            async_session, project_id, artifact_ids=artifact_ids,
        )
    except Exception:
        logger.exception(f"Background regeneration failed: project={project_id_str}")
