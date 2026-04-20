"""Record CRUD + 추출 API 라우터"""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.record import (
    RecordApproveRequest,
    RecordCreate,
    RecordListResponse,
    RecordReorderRequest,
    RecordResponse,
    RecordStatusUpdate,
    RecordUpdate,
)
from src.services import record_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/records",
    tags=["records"],
)


@router.get("", response_model=RecordListResponse)
async def list_records(
    project_id: uuid.UUID,
    section_id: uuid.UUID | None = Query(default=None, description="섹션 필터"),
    db: AsyncSession = Depends(get_db),
):
    return await record_svc.list_records(db, project_id, section_id)


@router.post("", response_model=RecordResponse, status_code=201)
async def create_record(
    project_id: uuid.UUID,
    body: RecordCreate,
    db: AsyncSession = Depends(get_db),
):
    return await record_svc.create_record(db, project_id, body)


@router.put("/reorder", response_model=dict)
async def reorder_records(
    project_id: uuid.UUID,
    body: RecordReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    updated = await record_svc.reorder_records(db, project_id, body)
    return {"updated_count": updated}


@router.put("/{record_id}", response_model=RecordResponse)
async def update_record(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    body: RecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await record_svc.update_record(db, project_id, record_id, body)


@router.patch("/{record_id}/status", response_model=RecordResponse)
async def update_record_status(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    body: RecordStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await record_svc.update_record_status(db, project_id, record_id, body)


@router.delete("/{record_id}", status_code=204)
async def delete_record(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await record_svc.delete_record(db, project_id, record_id)


@router.post("/extract")
async def extract_records(
    project_id: uuid.UUID,
    section_id: uuid.UUID | None = Query(default=None, description="특정 섹션만 추출"),
):
    """지식 문서 기반 레코드 추출 SSE 스트리밍 엔드포인트.

    LLM 호출이 길어도 프록시 keep-alive 타임아웃이 발생하지 않도록
    주기적으로 heartbeat를 보내고, 완료 시 candidates를 `done` 이벤트로 전달한다.

    DB 세션은 service 레이어에서 자체 관리 (StreamingResponse 수명 이슈 방지).

    이벤트:
    - data: {"type": "progress", "stage": "...", "message": "..."}
    - data: {"type": "done", "candidates": [...]}
    - data: {"type": "error", "message": "..."}
    """
    return StreamingResponse(
        record_svc.stream_extract_records(project_id, section_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/approve", response_model=RecordListResponse, status_code=201)
async def approve_records(
    project_id: uuid.UUID,
    body: RecordApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """추출된 레코드 후보 일괄 승인 저장"""
    return await record_svc.approve_records(db, project_id, body)
