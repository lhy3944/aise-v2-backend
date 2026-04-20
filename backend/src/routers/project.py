"""Project API 라우터"""

import uuid

from loguru import logger
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectSettingsResponse,
    ProjectSettingsUpdate,
)
from src.schemas.api.readiness import ReadinessResponse
from src.services import project_svc, readiness_svc, suggestion_svc


router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)):
    """프로젝트 목록 조회"""
    return await project_svc.list_projects(db)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 생성"""
    return await project_svc.create_project(db, data)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 상세 조회"""
    return await project_svc.get_project(db, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 수정"""
    return await project_svc.update_project(db, project_id, data)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 삭제"""
    await project_svc.delete_project(db, project_id)


@router.get("/{project_id}/readiness", response_model=ReadinessResponse)
async def get_readiness(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 준비도 조회"""
    return await readiness_svc.get_readiness(db, project_id)


@router.get("/{project_id}/settings", response_model=ProjectSettingsResponse)
async def get_project_settings(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 설정 조회"""
    return await project_svc.get_project_settings(db, project_id)


@router.put("/{project_id}/settings", response_model=ProjectSettingsResponse)
async def update_project_settings(
    project_id: uuid.UUID,
    data: ProjectSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 설정 수정"""
    return await project_svc.update_project_settings(db, project_id, data)


@router.get("/{project_id}/prompt-suggestions")
async def get_prompt_suggestions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 기반 맞춤형 프롬프트 제안 생성 (메타 fingerprint 기반 캐시)"""
    project = await project_svc.get_project(db, project_id)
    return await suggestion_svc.generate_prompt_suggestions(
        db,
        project_id=project_id,
        project_name=project.name,
        project_description=project.description,
        project_domain=project.domain,
    )


@router.get("/{project_id}/prompt-suggestions/fingerprint")
async def get_prompt_suggestions_fingerprint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 메타데이터 fingerprint 조회 (클라이언트 캐시 유효성 확인용)"""

    fp = await suggestion_svc.get_fingerprint(db, project_id)
    return {"fingerprint": fp}
