"""AI Assist 라우터 — 요구사항 정제(refine), 보완 제안(suggest), 대화 모드(chat)."""

import uuid

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.assist import (
    ChatRequest,
    ChatResponse,
    RefineRequest,
    RefineResponse,
    SuggestRequest,
    SuggestResponse,
)
from src.services.assist_svc import chat_assist, refine_requirement, suggest_requirements

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/assist",
    tags=["assist"],
)


@router.post("/refine", response_model=RefineResponse)
async def refine(
    project_id: uuid.UUID,
    request: RefineRequest,
):
    """자연어 텍스트를 정제된 요구사항으로 변환한다."""
    logger.info(f"POST /assist/refine | project_id={project_id}")
    return await refine_requirement(request)


@router.post("/suggest", response_model=SuggestResponse)
async def suggest(
    project_id: uuid.UUID,
    request: SuggestRequest,
    db: AsyncSession = Depends(get_db),
):
    """기존 요구사항을 분석하여 누락된 요구사항을 제안한다."""
    logger.info(f"POST /assist/suggest | project_id={project_id}")
    return await suggest_requirements(
        requirement_ids=request.requirement_ids,
        project_id=project_id,
        db=db,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    project_id: uuid.UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """대화 모드 — 자유 대화를 통해 요구사항을 탐색적으로 정의한다."""
    logger.info(f"POST /assist/chat | project_id={project_id}")
    return await chat_assist(
        message=request.message,
        history=[msg.model_dump() for msg in request.history],
        project_id=project_id,
        db=db,
    )
