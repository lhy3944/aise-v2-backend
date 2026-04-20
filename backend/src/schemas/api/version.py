from pydantic import BaseModel, Field

from .common import ArtifactType


class VersionInfo(BaseModel):
    """버전 정보"""
    version: int = Field(description="버전 번호")
    artifact_type: ArtifactType = Field(description="산출물 유형")
    created_by: str = Field(description="생성자 ID")
    created_at: str = Field(description="생성 일시")


class VersionListResponse(BaseModel):
    """버전 이력 응답"""
    versions: list[VersionInfo] = Field(default_factory=list)
