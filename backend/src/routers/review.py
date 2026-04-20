"""요구사항 Review 라우터 -- 충돌(conflict) + 중복(duplicate) 검출 API."""

# --- v2 예정: 수정 제안 수락/거절 ---

import uuid

from fastapi import APIRouter, Depends, Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import AppException
from src.schemas.api.review import (
    # AcceptSuggestionResponse,  # v2 예정
    LatestReviewResponse,
    # RejectSuggestionResponse,  # v2 예정
    ReviewRequest,
    ReviewResponse,
)
from src.services import review_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/review",
    tags=["review"],
)


@router.post("/requirements", response_model=ReviewResponse)
async def review_requirements_endpoint(
    project_id: uuid.UUID,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """요구사항을 분석하여 충돌(conflict) + 중복(duplicate)을 검출한다."""
    logger.info(f"POST /review/requirements | project_id={project_id}")
    return await review_svc.review_requirements(
        requirement_ids=request.requirement_ids,
        project_id=project_id,
        db=db,
    )


# --- v2 예정: 수정 제안 수락/거절 ---
# @router.post("/suggestions/{issue_id}/accept", response_model=AcceptSuggestionResponse)
# async def accept_review_suggestion(
#     project_id: uuid.UUID,
#     issue_id: str = Path(min_length=1, max_length=12, pattern=r"^[a-f0-9]+$"),
#     db: AsyncSession = Depends(get_db),
# ):
#     """리뷰 수정 제안 수락 -- 즉시 DB 반영."""
#     logger.info(f"POST /review/suggestions/{issue_id}/accept | project_id={project_id}")
#     return await review_svc.accept_suggestion(project_id, issue_id, db)
#
#
# @router.post("/suggestions/{issue_id}/reject", response_model=RejectSuggestionResponse)
# async def reject_review_suggestion(
#     project_id: uuid.UUID,
#     issue_id: str = Path(min_length=1, max_length=12, pattern=r"^[a-f0-9]+$"),
#     db: AsyncSession = Depends(get_db),
# ):
#     """리뷰 수정 제안 거절."""
#     logger.info(f"POST /review/suggestions/{issue_id}/reject | project_id={project_id}")
#     return await review_svc.reject_suggestion(project_id, issue_id, db)


@router.get("/results/latest", response_model=LatestReviewResponse)
async def get_latest_review_result(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """마지막 리뷰 결과 조회."""
    logger.info(f"GET /review/results/latest | project_id={project_id}")
    result = await review_svc.get_latest_review(project_id, db)
    if result is None:
        raise AppException(status_code=404, detail="리뷰 이력이 없습니다.")
    return result
