"""Record-flavoured artifact API 라우터.

URL: /api/v1/projects/{project_id}/artifacts/record/*

공통 artifact workflow(Create/PR/Merge)는 `routers/artifact.py` 의
`project_router` / `global_router` 에서 처리하며, 이 라우터는 record 도메인
특수 기능(section/source_document enrich, SSE 추출, 일괄 승인)만 담당한다.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.artifact_record import (
    ArtifactRecordApproveRequest,
    ArtifactRecordCreate,
    ArtifactRecordListResponse,
    ArtifactRecordReorderRequest,
    ArtifactRecordResponse,
    ArtifactRecordStatusUpdate,
    ArtifactRecordUpdate,
)
from src.services import artifact_record_svc

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/artifacts/record",
    tags=["artifacts:record"],
)


@router.get("", response_model=ArtifactRecordListResponse)
async def list_records(
    project_id: uuid.UUID,
    section_id: uuid.UUID | None = Query(default=None, description="섹션 필터"),
    db: AsyncSession = Depends(get_db),
):
    return await artifact_record_svc.list_records(db, project_id, section_id)


@router.post("", response_model=ArtifactRecordResponse, status_code=201)
async def create_record(
    project_id: uuid.UUID,
    body: ArtifactRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_record_svc.create_record(db, project_id, body)


@router.put("/reorder", response_model=dict)
async def reorder_records(
    project_id: uuid.UUID,
    body: ArtifactRecordReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    updated = await artifact_record_svc.reorder_records(db, project_id, body)
    return {"updated_count": updated}


@router.put("/{artifact_id}", response_model=ArtifactRecordResponse)
async def update_record(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    body: ArtifactRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_record_svc.update_record(db, project_id, artifact_id, body)


@router.patch("/{artifact_id}/status", response_model=ArtifactRecordResponse)
async def update_record_status(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    body: ArtifactRecordStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_record_svc.update_record_status(
        db, project_id, artifact_id, body
    )


@router.delete("/{artifact_id}", status_code=204)
async def delete_record(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await artifact_record_svc.delete_record(db, project_id, artifact_id)


@router.post("/extract")
async def extract_records(
    project_id: uuid.UUID,
    section_id: uuid.UUID | None = Query(default=None, description="특정 섹션만 추출"),
):
    """지식 문서 기반 레코드 추출 SSE 스트리밍."""
    return StreamingResponse(
        artifact_record_svc.stream_extract_records(project_id, section_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/approve", response_model=ArtifactRecordListResponse, status_code=201)
async def approve_records(
    project_id: uuid.UUID,
    body: ArtifactRecordApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_record_svc.approve_records(db, project_id, body)
