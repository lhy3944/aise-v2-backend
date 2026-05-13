"""System Model API 스키마 — Design과 동일한 형태."""

from datetime import datetime

from pydantic import BaseModel, Field


class SystemModelSectionResponse(BaseModel):
    section_id: str | None = None
    title: str
    content: str
    order_index: int


class SystemModelDocumentResponse(BaseModel):
    system_model_id: str  # ArtifactVersion.id
    artifact_id: str  # Artifact.id
    project_id: str
    version: int
    status: str
    error_message: str | None = None
    sections: list[SystemModelSectionResponse] = Field(default_factory=list)
    based_on_srs: dict | None = None
    source_artifact_versions: dict | None = None
    created_at: datetime


class SystemModelListResponse(BaseModel):
    documents: list[SystemModelDocumentResponse]
