"""SRS API 스키마"""

from datetime import datetime

from pydantic import BaseModel, Field


class SrsSectionResponse(BaseModel):
    section_id: str | None = None
    title: str
    content: str
    order_index: int


class SrsSectionUpdate(BaseModel):
    content: str


class SrsDocumentResponse(BaseModel):
    srs_id: str  # ArtifactVersion.id (Phase C 통합 후 — version 단위 식별자)
    artifact_id: str  # Artifact.id (staging/PR 워크플로우 키)
    project_id: str
    version: int
    status: str
    error_message: str | None = None
    sections: list[SrsSectionResponse] = Field(default_factory=list)
    based_on_records: dict | None = None
    based_on_documents: dict | None = None
    # Phase E lineage — 이 version 을 만들 때 입력으로 쓴 다른 artifact 들의 version.
    source_artifact_versions: dict | None = None
    created_at: datetime


class SrsListResponse(BaseModel):
    documents: list[SrsDocumentResponse]


class SrsExportRequest(BaseModel):
    format: str = Field(description="md 또는 pdf")
