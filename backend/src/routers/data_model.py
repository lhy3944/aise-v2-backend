"""Data Model 생성/조회 API 라우터."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.data_model import (
    DataModelDocumentResponse,
    DataModelListResponse,
)
from src.services import data_model_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/data-model",
    tags=["data_model"],
)


@router.post("/generate", response_model=DataModelDocumentResponse, status_code=201)
async def generate_data_model(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """SRS + 시스템 모델 기반 데이터 모델 생성 (새 ArtifactVersion 추가)."""
    return await data_model_svc.generate_data_model(db, project_id)


@router.get("", response_model=DataModelListResponse)
async def list_data_model(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await data_model_svc.list_data_model(db, project_id)


@router.get("/{data_model_id}", response_model=DataModelDocumentResponse)
async def get_data_model(
    project_id: uuid.UUID,
    data_model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """data_model_id = ArtifactVersion.id."""
    return await data_model_svc.get_data_model(db, project_id, data_model_id)


@router.post(
    "/{data_model_id}/regenerate",
    response_model=DataModelDocumentResponse,
    status_code=201,
)
async def regenerate_data_model(
    project_id: uuid.UUID,
    data_model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Data Model 재생성 (새 ArtifactVersion 추가)."""
    return await data_model_svc.generate_data_model(db, project_id)
