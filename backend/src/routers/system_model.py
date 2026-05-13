"""System Model 생성/조회 API 라우터."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.system_model import (
    SystemModelDocumentResponse,
    SystemModelListResponse,
)
from src.services import system_model_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/system-model",
    tags=["system_model"],
)


@router.post("/generate", response_model=SystemModelDocumentResponse, status_code=201)
async def generate_system_model(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """SRS clean version 기반 시스템 모델 생성 (새 ArtifactVersion 추가)."""
    return await system_model_svc.generate_system_model(db, project_id)


@router.get("", response_model=SystemModelListResponse)
async def list_system_model(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await system_model_svc.list_system_model(db, project_id)


@router.get("/{system_model_id}", response_model=SystemModelDocumentResponse)
async def get_system_model(
    project_id: uuid.UUID,
    system_model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """system_model_id = ArtifactVersion.id."""
    return await system_model_svc.get_system_model(db, project_id, system_model_id)


@router.post(
    "/{system_model_id}/regenerate",
    response_model=SystemModelDocumentResponse,
    status_code=201,
)
async def regenerate_system_model(
    project_id: uuid.UUID,
    system_model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """System Model 재생성 (새 ArtifactVersion 추가)."""
    return await system_model_svc.generate_system_model(db, project_id)
