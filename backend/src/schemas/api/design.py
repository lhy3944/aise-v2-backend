"""Design API 스키마 — SRS 와 동일한 형태로 통일."""

from datetime import datetime

from pydantic import BaseModel, Field


class DesignSectionResponse(BaseModel):
    section_id: str | None = None
    title: str
    content: str
    order_index: int


class DesignDocumentResponse(BaseModel):
    design_id: str  # ArtifactVersion.id (version 단위 식별자)
    artifact_id: str  # Artifact.id (staging/PR 워크플로우 키)
    project_id: str
    version: int
    status: str
    error_message: str | None = None
    sections: list[DesignSectionResponse] = Field(default_factory=list)
    based_on_srs: dict | None = None  # {"version_id": "uuid", "version_number": int}
    # Phase E lineage — 이 version 을 만들 때 입력으로 쓴 다른 artifact 들의 version.
    source_artifact_versions: dict | None = None
    created_at: datetime


class DesignListResponse(BaseModel):
    documents: list[DesignDocumentResponse]
