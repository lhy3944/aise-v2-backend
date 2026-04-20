"""SRS 생성/조회/편집 API 라우터"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.srs import (
    SrsDocumentResponse,
    SrsListResponse,
    SrsSectionUpdate,
)
from src.services import srs_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/srs",
    tags=["srs"],
)


@router.post("/generate", response_model=SrsDocumentResponse, status_code=201)
async def generate_srs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """승인된 레코드 기반 SRS 생성"""
    return await srs_svc.generate_srs(db, project_id)


@router.get("", response_model=SrsListResponse)
async def list_srs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await srs_svc.list_srs(db, project_id)


@router.get("/{srs_id}", response_model=SrsDocumentResponse)
async def get_srs(
    project_id: uuid.UUID,
    srs_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await srs_svc.get_srs(db, project_id, srs_id)


@router.put("/{srs_id}/sections/{section_id}", response_model=SrsDocumentResponse)
async def update_srs_section(
    project_id: uuid.UUID,
    srs_id: uuid.UUID,
    section_id: uuid.UUID,
    body: SrsSectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """SRS 섹션 인라인 편집"""
    return await srs_svc.update_srs_section(db, project_id, srs_id, section_id, body)


@router.post("/{srs_id}/regenerate", response_model=SrsDocumentResponse, status_code=201)
async def regenerate_srs(
    project_id: uuid.UUID,
    srs_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """SRS 재생성 (새 버전)"""
    return await srs_svc.generate_srs(db, project_id)
