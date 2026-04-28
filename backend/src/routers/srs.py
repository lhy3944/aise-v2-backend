"""SRS 생성/조회 API 라우터.

Phase C 변경:
- `PUT /{srs_id}/sections/{section_id}` 제거 — 사용자 수동 편집은 통합
  Artifact 라우터(PATCH /artifacts/{id})와 staging-store/PR 워크플로우로 통일.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.srs import (
    SrsDocumentResponse,
    SrsListResponse,
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
    """승인된 레코드 기반 SRS 생성 (새 ArtifactVersion 추가)."""
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
    """srs_id = ArtifactVersion.id (Phase C 통합 후)."""
    return await srs_svc.get_srs(db, project_id, srs_id)


@router.post("/{srs_id}/regenerate", response_model=SrsDocumentResponse, status_code=201)
async def regenerate_srs(
    project_id: uuid.UUID,
    srs_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """SRS 재생성 (새 ArtifactVersion 추가). srs_id 는 base 로만 사용."""
    return await srs_svc.generate_srs(db, project_id)
