"""Session API 라우터"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionDetailResponse,
    SessionListResponse,
)
from src.services import session_svc

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """세션 생성"""
    return await session_svc.create_session(db, body)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    project_id: uuid.UUID = Query(description="프로젝트 ID"),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트별 세션 목록 조회"""
    return await session_svc.list_sessions(db, project_id)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """세션 상세 조회 (메시지 포함)"""
    return await session_svc.get_session(db, session_id)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """세션 제목 수정"""
    return await session_svc.update_session(db, session_id, body.title)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """세션 삭제"""
    await session_svc.delete_session(db, session_id)
