from pydantic import BaseModel, Field, model_validator

from .common import ProjectModule

# 허용되는 모듈 조합 (5가지)
VALID_MODULE_SETS: list[set[str]] = [
    {"requirements", "design", "testcase"},  # All
    {"requirements"},                         # Requirements Only
    {"requirements", "design"},               # Requirements + Design
    {"requirements", "testcase"},             # Requirements + Testcase
    {"testcase"},                              # Testcase Only
]


def _validate_modules(modules: list[ProjectModule]) -> list[ProjectModule]:
    given = {m.value for m in modules}
    if given not in VALID_MODULE_SETS:
        allowed = "All, Requirements Only, Requirements+Design, Requirements+Testcase, Testcase Only"
        raise ValueError(f"허용되지 않는 모듈 조합입니다. 가능한 조합: {allowed}")
    return modules


class ProjectCreate(BaseModel):
    """프로젝트 생성 요청"""
    name: str = Field(description="프로젝트 이름")
    description: str | None = Field(default=None, description="프로젝트 설명")
    domain: str | None = Field(default=None, description="도메인 (예: robotics)")
    product_type: str | None = Field(default=None, description="제품 유형 (예: embedded)")
    modules: list[ProjectModule] = Field(description="사용할 모듈 목록")

    @model_validator(mode="after")
    def check_modules(self):
        _validate_modules(self.modules)
        return self


class ProjectUpdate(BaseModel):
    """프로젝트 수정 요청"""
    name: str | None = Field(default=None, description="프로젝트 이름")
    description: str | None = Field(default=None, description="프로젝트 설명")
    domain: str | None = Field(default=None, description="도메인")
    product_type: str | None = Field(default=None, description="제품 유형")
    modules: list[ProjectModule] | None = Field(default=None, description="모듈 목록")

    @model_validator(mode="after")
    def check_modules(self):
        if self.modules is not None:
            _validate_modules(self.modules)
        return self


class ProjectReadiness(BaseModel):
    """프로젝트 준비도 요약 (목록용)"""
    knowledge: int = Field(default=0, description="활성 지식 문서 수")
    glossary: int = Field(default=0, description="승인 용어 수")
    sections: int = Field(default=0, description="활성 섹션 수")
    is_ready: bool = Field(default=False)


class ProjectResponse(BaseModel):
    """프로젝트 응답"""
    project_id: str = Field(description="프로젝트 ID")
    name: str = Field(description="프로젝트 이름")
    description: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    product_type: str | None = Field(default=None)
    modules: list[ProjectModule] = Field(default_factory=list)
    member_count: int = Field(default=0, description="멤버 수")
    status: str = Field(default="active", description="프로젝트 상태")
    readiness: ProjectReadiness | None = Field(default=None, description="준비도")
    created_at: str = Field(description="생성일시")
    updated_at: str = Field(description="수정일시")


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답"""
    projects: list[ProjectResponse] = Field(default_factory=list)


class ProjectSettingsResponse(BaseModel):
    """프로젝트 설정 응답"""
    llm_model: str = Field(default="gpt-4", description="LLM 모델")
    language: str = Field(default="ko", description="생성 언어")
    export_format: str = Field(default="pdf", description="기본 Export 형식")
    diagram_tool: str = Field(default="plantuml", description="다이어그램 도구")
    polarion_pat: str | None = Field(default=None, description="Polarion PAT (마스킹)")


class ProjectSettingsUpdate(BaseModel):
    """프로젝트 설정 수정"""
    llm_model: str | None = Field(default=None)
    language: str | None = Field(default=None)
    export_format: str | None = Field(default=None)
    diagram_tool: str | None = Field(default=None)
    polarion_pat: str | None = Field(default=None)


class ProjectDeletePreview(BaseModel):
    """프로젝트 삭제 시 영향받을 데이터 카운트.

    soft delete 단계에서는 데이터가 실제로 사라지지 않지만(휴지통),
    hard delete (30일 후 cron 또는 즉시) 시점에는 모두 영구 삭제.
    """

    project_id: str
    project_name: str
    knowledge_documents: int = 0
    knowledge_files_bytes: int = 0  # MinIO 누적 바이트
    sessions: int = 0
    session_messages: int = 0
    artifacts: int = 0
    artifact_versions: int = 0
    pull_requests: int = 0
    glossary_items: int = 0
    requirement_sections: int = 0


class ProjectDeleteRequest(BaseModel):
    """soft delete 호출 시 옵션. confirm_name 으로 type-to-confirm 검증."""

    confirm_name: str | None = Field(
        default=None,
        description=(
            "운영 환경 안전망: 프로젝트 이름과 일치해야 삭제 진행. "
            "비어 있으면 검증 생략(개발용)."
        ),
    )
