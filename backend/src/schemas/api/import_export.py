from pydantic import BaseModel, Field

from .common import ArtifactType, ExportFormat


class FileImportResponse(BaseModel):
    """파일 Import 응답"""
    import_id: str = Field(description="Import ID")
    filename: str = Field(description="파일명")
    file_type: str = Field(description="파일 형식")
    status: str = Field(default="uploaded", description="상태")
    uploaded_at: str = Field(description="업로드 일시")


class JiraImportRequest(BaseModel):
    """Jira Import 요청"""
    jira_project: str = Field(description="Jira 프로젝트 키")
    ticket_ids: list[str] = Field(description="가져올 티켓 ID 목록")


class PolarionImportRequest(BaseModel):
    """Polarion Import 요청"""
    project: str = Field(description="Polarion 프로젝트")
    work_item_ids: list[str] = Field(description="가져올 Work Item ID 목록")


class ClassifyRequest(BaseModel):
    """Import된 문서 분류 요청"""
    import_ids: list[str] = Field(description="분류할 Import ID 목록")


class ClassifiedItem(BaseModel):
    """분류된 개별 항목"""
    text: str = Field(description="분류된 텍스트")
    confidence: float = Field(description="신뢰도 (0.0 ~ 1.0)")


class UnclassifiedItem(BaseModel):
    """미분류 항목"""
    text: str = Field(description="텍스트")
    reason: str = Field(description="미분류 사유")


class ClassifyResponse(BaseModel):
    """분류 결과 응답"""
    classified: "ClassifiedResult" = Field(description="분류 결과")


class ClassifiedResult(BaseModel):
    fr: list[ClassifiedItem] = Field(default_factory=list)
    qa: list[ClassifiedItem] = Field(default_factory=list)
    constraints: list[ClassifiedItem] = Field(default_factory=list)
    other: list[ClassifiedItem] = Field(default_factory=list)
    unclassified: list[UnclassifiedItem] = Field(default_factory=list)


class ExportRequest(BaseModel):
    """산출물 내보내기 요청"""
    target: ExportFormat = Field(description="내보내기 형식")
    artifact_type: ArtifactType = Field(description="산출물 유형")
    version: int | None = Field(default=None, description="버전 (없으면 최신)")
