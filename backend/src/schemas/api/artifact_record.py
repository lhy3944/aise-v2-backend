"""Record-flavoured artifact 의 API 스키마.

`artifacts(artifact_type='record')` 전용 입출력 형태. 공통 artifact 스키마는
`schemas/api/artifact.py` 에 있고, 여기 있는 스키마는 record 의 도메인 필드
(section/source_document/status 등)를 평탄화해 UI 에서 접근하기 편하도록
정리한 것이다.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RecordStatus = Literal["draft", "approved", "excluded"]


class ArtifactRecordCreate(BaseModel):
    content: str = Field(description="레코드 본문")
    section_id: uuid.UUID | None = Field(default=None, description="섹션 ID")
    source_document_id: uuid.UUID | None = Field(default=None)
    source_location: str | None = Field(default=None)


class ArtifactRecordUpdate(BaseModel):
    content: str | None = Field(default=None)
    section_id: uuid.UUID | None = Field(default=None)


class ArtifactRecordStatusUpdate(BaseModel):
    status: RecordStatus


class ArtifactRecordReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(description="변경된 순서대로 artifact ID 배열")


class ArtifactRecordResponse(BaseModel):
    artifact_id: str
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
    # Phase 후속 — record 도 ArtifactVersion 체인을 보유. 카드에 "버전" 버튼을
    # 노출할지 결정하는 용도. None / 0 이면 아직 머지된 버전 없음.
    current_version_number: int | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactRecordListResponse(BaseModel):
    records: list[ArtifactRecordResponse]
    total: int


class ArtifactRecordExtractedItem(BaseModel):
    """AI 추출 후보 — Artifact 생성 전 단계."""
    content: str
    section_id: str | None = None
    section_name: str | None = None
    source_document_id: str | None = None
    source_document_name: str | None = None
    source_location: str | None = None
    confidence_score: float | None = None


class ArtifactRecordExtractResponse(BaseModel):
    candidates: list[ArtifactRecordExtractedItem]


class ArtifactRecordApproveRequest(BaseModel):
    items: list[ArtifactRecordCreate] = Field(description="승인할 레코드 목록")
