"""Design 생성/조회 API 라우터.

SRS 와 동일한 구조 — 사용자 수동 편집은 통합 Artifact 라우터(PATCH /artifacts/{id})
와 staging-store/PR 워크플로우로 통일하므로 별도 PUT 엔드포인트를 두지 않는다.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.design import (
    DesignDocumentResponse,
    DesignListResponse,
)
from src.services import design_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/design",
    tags=["design"],
)


@router.post("/generate", response_model=DesignDocumentResponse, status_code=201)
async def generate_design(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """SRS clean version 기반 설계 산출물 생성 (새 ArtifactVersion 추가)."""
    return await design_svc.generate_design(db, project_id)


@router.get("", response_model=DesignListResponse)
async def list_design(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await design_svc.list_design(db, project_id)


@router.get("/{design_id}", response_model=DesignDocumentResponse)
async def get_design(
    project_id: uuid.UUID,
    design_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """design_id = ArtifactVersion.id."""
    return await design_svc.get_design(db, project_id, design_id)


@router.post(
    "/{design_id}/regenerate", response_model=DesignDocumentResponse, status_code=201
)
async def regenerate_design(
    project_id: uuid.UUID,
    design_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Design 재생성 (새 ArtifactVersion 추가). design_id 는 base 로만 사용."""
    return await design_svc.generate_design(db, project_id)
