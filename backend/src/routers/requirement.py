"""Requirement CRUD API 라우터"""

import uuid

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.common import RequirementType
from src.schemas.api.requirement import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    RequirementListResponse,
    RequirementSelectionUpdate,
    RequirementReorderRequest,
    RequirementSaveResponse,
)
from src.services import requirement_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/requirements",
    tags=["requirements"],
)


@router.get("", response_model=RequirementListResponse)
async def list_requirements(
    project_id: uuid.UUID,
    type: RequirementType | None = Query(default=None, description="요구사항 유형 필터 (fr, qa, constraints, other)"),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트의 요구사항 목록 조회"""
    requirements = await requirement_svc.get_requirements(db, project_id, type_filter=type)
    return RequirementListResponse(requirements=requirements)


@router.post("", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    project_id: uuid.UUID,
    body: RequirementCreate,
    db: AsyncSession = Depends(get_db),
):
    """요구사항 생성"""
    return await requirement_svc.create_requirement(db, project_id, body)


@router.put("/selection", response_model=dict)
async def update_selection(
    project_id: uuid.UUID,
    body: RequirementSelectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """요구사항 일괄 선택/해제"""
    updated_count = await requirement_svc.update_selection(db, project_id, body)
    return {"updated_count": updated_count}


@router.put("/reorder", response_model=dict)
async def reorder_requirements(
    project_id: uuid.UUID,
    body: RequirementReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    """요구사항 순서 변경 (드래그 앤 드롭)"""
    updated_count = await requirement_svc.reorder_requirements(db, project_id, body)
    return {"updated_count": updated_count}


@router.put("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    body: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
):
    """요구사항 수정"""
    return await requirement_svc.update_requirement(db, project_id, requirement_id, body)


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """요구사항 삭제"""
    await requirement_svc.delete_requirement(db, project_id, requirement_id)


@router.post("/save", response_model=RequirementSaveResponse)
async def save_requirements(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """현재 요구사항 상태를 버전으로 저장"""
    result = await requirement_svc.save_version(db, project_id)
    return RequirementSaveResponse(**result)
