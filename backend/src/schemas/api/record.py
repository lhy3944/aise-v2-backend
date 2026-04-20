"""Record API 스키마"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RecordStatus = Literal["draft", "approved", "excluded"]


class RecordCreate(BaseModel):
    content: str = Field(description="레코드 본문")
    section_id: uuid.UUID | None = Field(default=None, description="섹션 ID")
    source_document_id: uuid.UUID | None = Field(default=None)
    source_location: str | None = Field(default=None)


class RecordUpdate(BaseModel):
    content: str | None = Field(default=None)
    section_id: uuid.UUID | None = Field(default=None)


class RecordStatusUpdate(BaseModel):
    status: RecordStatus


class RecordReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(description="변경된 순서대로 레코드 ID 배열")


class RecordResponse(BaseModel):
    record_id: str
    project_id: str
    section_id: str | None = None
    section_name: str | None = None
    content: str
    display_id: str
    source_document_id: str | None = None
    source_document_name: str | None = None
    source_location: str | None = None
    confidence_score: float | None = None
    status: RecordStatus
    is_auto_extracted: bool
    order_index: int
    created_at: datetime
    updated_at: datetime


class RecordListResponse(BaseModel):
    records: list[RecordResponse]
    total: int


class RecordExtractedItem(BaseModel):
    """AI 추출 후보 레코드"""
    content: str
    section_id: str | None = None
    section_name: str | None = None
    source_document_id: str | None = None
    source_document_name: str | None = None
    source_location: str | None = None
    confidence_score: float | None = None


class RecordExtractResponse(BaseModel):
    candidates: list[RecordExtractedItem]


class RecordApproveRequest(BaseModel):
    items: list[RecordCreate] = Field(description="승인할 레코드 목록")
