"""Requirement Section CRUD + AI 추출 API 라우터"""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.requirement import (
    SectionCreate,
    SectionUpdate,
    SectionReorderRequest,
    SectionResponse,
    SectionListResponse,
)
from src.services import section_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/requirement-sections",
    tags=["requirement-sections"],
)


class ToggleRequest(BaseModel):
    is_active: bool


@router.get("", response_model=SectionListResponse)
async def list_sections(
    project_id: uuid.UUID,
    type: str | None = Query(default=None, description="섹션 유형 필터"),
    db: AsyncSession = Depends(get_db),
):
    sections = await section_svc.get_sections(db, project_id, type_filter=type)
    return SectionListResponse(sections=sections)


@router.post("", response_model=SectionResponse, status_code=201)
async def create_section(
    project_id: uuid.UUID,
    body: SectionCreate,
    db: AsyncSession = Depends(get_db),
):
    return await section_svc.create_section(db, project_id, body)


@router.put("/reorder", response_model=dict)
async def reorder_sections(
    project_id: uuid.UUID,
    body: SectionReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    updated_count = await section_svc.reorder_sections(db, project_id, body)
    return {"updated_count": updated_count}


@router.put("/{section_id}", response_model=SectionResponse)
async def update_section(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    body: SectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await section_svc.update_section(db, project_id, section_id, body)


@router.patch("/{section_id}/toggle", response_model=SectionResponse)
async def toggle_section(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    body: ToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    """섹션 활성화/비활성화 토글"""
    return await section_svc.toggle_section(db, project_id, section_id, body.is_active)


@router.delete("/{section_id}", status_code=204)
async def delete_section(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """섹션 삭제 (기본 섹션은 삭제 불가)"""
    await section_svc.delete_section(db, project_id, section_id)


@router.post("/extract", response_model=SectionListResponse)
async def extract_sections(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """지식 문서 기반 섹션 후보 AI 추출"""
    candidates = await section_svc.extract_sections(db, project_id)
    return SectionListResponse(sections=candidates)
