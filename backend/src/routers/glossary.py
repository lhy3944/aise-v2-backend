"""Glossary CRUD + AI 자동 생성/추출 라우터"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.glossary import (
    GlossaryApproveRequest,
    GlossaryCreate,
    GlossaryExtractResponse,
    GlossaryGenerateResponse,
    GlossaryListResponse,
    GlossaryResponse,
    GlossaryUpdate,
)
from src.services import glossary_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/glossary",
    tags=["glossary"],
)


@router.get("", response_model=GlossaryListResponse)
async def list_glossary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await glossary_svc.list_glossary(db, project_id)


@router.post("", response_model=GlossaryResponse, status_code=201)
async def create_glossary(
    project_id: uuid.UUID,
    body: GlossaryCreate,
    db: AsyncSession = Depends(get_db),
):
    return await glossary_svc.create_glossary(db, project_id, body)


@router.put("/{glossary_id}", response_model=GlossaryResponse)
async def update_glossary(
    project_id: uuid.UUID,
    glossary_id: uuid.UUID,
    body: GlossaryUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await glossary_svc.update_glossary(db, project_id, glossary_id, body)


@router.delete("/{glossary_id}", status_code=204)
async def delete_glossary(
    project_id: uuid.UUID,
    glossary_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await glossary_svc.delete_glossary(db, project_id, glossary_id)


@router.post("/generate", response_model=GlossaryGenerateResponse)
async def generate_glossary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """요구사항 기반 Glossary 초안 자동 생성 (레거시)"""
    return await glossary_svc.generate_glossary(db, project_id)


@router.post("/extract", response_model=GlossaryExtractResponse)
async def extract_glossary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """지식 문서 기반 용어 후보 추출"""
    return await glossary_svc.extract_glossary(db, project_id)


@router.post("/approve", response_model=GlossaryListResponse, status_code=201)
async def approve_glossary(
    project_id: uuid.UUID,
    body: GlossaryApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """추출된 용어 후보 일괄 승인 저장"""
    return await glossary_svc.approve_glossary(db, project_id, body)
