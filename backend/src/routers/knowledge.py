"""Knowledge Repository API 라우터"""

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.knowledge import (
    KnowledgeChatRequest,
    KnowledgeChatResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentPreviewResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentToggleRequest,
)
from src.services import knowledge_svc, rag_svc

router = APIRouter(prefix="/api/v1/projects/{project_id}/knowledge", tags=["knowledge"])


@router.post("/documents", response_model=KnowledgeDocumentResponse, status_code=201)
async def upload_document(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    overwrite: bool = Query(False, description="중복 파일 덮어쓰기 여부"),
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.upload_document(project_id, file, db, background_tasks, overwrite=overwrite)


@router.get("/documents", response_model=KnowledgeDocumentListResponse)
async def list_documents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.list_documents(project_id, db)


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.get_document(project_id, document_id, db)


@router.patch("/documents/{document_id}/toggle", response_model=KnowledgeDocumentResponse)
async def toggle_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    body: KnowledgeDocumentToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.toggle_document(project_id, document_id, body.is_active, db)


@router.post("/documents/{document_id}/reprocess", response_model=KnowledgeDocumentResponse)
async def reprocess_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.reprocess_document(project_id, document_id, db, background_tasks)


@router.get("/documents/{document_id}/preview", response_model=KnowledgeDocumentPreviewResponse)
async def get_document_preview(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_svc.get_document_preview(project_id, document_id, db)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await knowledge_svc.delete_document(project_id, document_id, db)


@router.post("/chat", response_model=KnowledgeChatResponse)
async def knowledge_chat(
    project_id: uuid.UUID,
    body: KnowledgeChatRequest,
    db: AsyncSession = Depends(get_db),
):
    return await rag_svc.chat(project_id, body.message, body.history, body.top_k, db)


@router.get("/documents/{document_id}/chunks/{chunk_index}")
async def get_chunk(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    chunk_index: int,
    context: int = Query(1, ge=0, le=5, description="전후 청크 수"),
    db: AsyncSession = Depends(get_db),
):
    """특정 청크 + 전후 context 청크 반환 (원문 추적용)"""
    return await knowledge_svc.get_chunk_with_context(
        project_id, document_id, chunk_index, context, db,
    )
