"""Project API 라우터"""

import uuid

from loguru import logger
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.project import (
    ProjectCreate,
    ProjectDeletePreview,
    ProjectDeleteRequest,
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
async def list_projects(
    db: AsyncSession = Depends(get_db),
    include_deleted: bool = False,
):
    """프로젝트 목록 조회. `include_deleted=true` 면 휴지통(soft-deleted) 도 포함."""
    return await project_svc.list_projects(db, include_deleted=include_deleted)


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
    body: ProjectDeleteRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 soft delete (status='deleted' 마킹).

    - 30일 retention 후 cron 으로 hard delete 또는 사용자가 즉시 영구 삭제 가능.
    - body.confirm_name 이 있으면 프로젝트 이름과 일치해야 진행 (운영 안전망).
    """
    await project_svc.delete_project(
        db, project_id, confirm_name=body.confirm_name if body else None,
    )


@router.get("/{project_id}/delete-preview", response_model=ProjectDeletePreview)
async def get_delete_preview(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 삭제 시 영향받을 데이터 카운트 미리보기."""
    return await project_svc.get_delete_preview(db, project_id)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """soft-deleted 프로젝트 복원 (status='active')."""
    return await project_svc.restore_project(db, project_id)


@router.delete("/{project_id}/hard", status_code=204)
async def hard_delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 영구 삭제 (DB CASCADE + MinIO prefix 정리). 복원 불가."""
    await project_svc.hard_delete_project(db, project_id)


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
