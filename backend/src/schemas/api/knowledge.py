"""Knowledge Repository API 스키마"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# 문서 상태 타입
DocumentStatus = Literal["pending", "processing", "completed", "failed"]


class KnowledgeDocumentResponse(BaseModel):
    document_id: str
    project_id: str
    name: str
    file_type: str
    size_bytes: int
    status: DocumentStatus
    is_active: bool
    error_message: str | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDocumentListResponse(BaseModel):
    documents: list[KnowledgeDocumentResponse]
    total: int


class KnowledgeDocumentToggleRequest(BaseModel):
    is_active: bool


class KnowledgeDocumentPreviewResponse(BaseModel):
    document_id: str
    name: str
    file_type: str
    preview_text: str
    total_characters: int


class KnowledgeChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)  # [{"role": "user"|"assistant", "content": "..."}]
    top_k: int = 5


class KnowledgeChatSource(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    content: str
    score: float
    file_type: str | None = None


class KnowledgeChatResponse(BaseModel):
    answer: str
    sources: list[KnowledgeChatSource]
