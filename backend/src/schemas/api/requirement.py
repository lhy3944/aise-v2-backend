import uuid

from pydantic import BaseModel, Field, field_validator

from .common import RequirementType


# ── Section 스키마 ──────────────────────────────────────────


class SectionCreate(BaseModel):
    """섹션 생성 요청"""
    name: str = Field(min_length=1, max_length=200, description="섹션명")
    type: str = Field(description="섹션 유형 (자유 문자열)")
    description: str | None = Field(default=None, description="섹션 설명/목적")
    output_format_hint: str | None = Field(default=None, description="출력 형식 힌트")


class SectionUpdate(BaseModel):
    """섹션 수정 요청"""
    name: str | None = Field(default=None, min_length=1, max_length=200, description="섹션명")
    description: str | None = Field(default=None, description="섹션 설명/목적")
    output_format_hint: str | None = Field(default=None, description="출력 형식 힌트")


class SectionReorderRequest(BaseModel):
    """섹션 순서 변경 요청"""
    ordered_ids: list[uuid.UUID] = Field(description="변경된 순서대로 섹션 ID 배열")


class SectionResponse(BaseModel):
    """섹션 응답"""
    section_id: str = Field(description="섹션 ID")
    name: str = Field(description="섹션명")
    type: str = Field(description="유형")
    description: str | None = Field(default=None)
    output_format_hint: str | None = Field(default=None)
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)
    order_index: int = Field(description="표시 순서")
    created_at: str = Field(description="생성일시")
    updated_at: str = Field(description="수정일시")


class SectionListResponse(BaseModel):
    """섹션 목록 응답"""
    sections: list[SectionResponse] = Field(default_factory=list)


# ── Requirement 스키마 ──────────────────────────────────────


class RequirementCreate(BaseModel):
    """요구사항 생성 요청"""
    type: RequirementType = Field(description="요구사항 유형")
    original_text: str = Field(description="사용자 입력 원문")
    section_id: uuid.UUID | None = Field(default=None, description="소속 섹션 ID (미분류 시 null)")

    @field_validator("section_id", mode="before")
    @classmethod
    def normalize_section_id(cls, value: object) -> object:
        if value == "":
            return None
        return value


class RequirementUpdate(BaseModel):
    """요구사항 수정 요청"""
    original_text: str | None = Field(default=None, description="원문")
    refined_text: str | None = Field(default=None, description="정제된 문장")
    is_selected: bool | None = Field(default=None, description="선택 여부")
    section_id: uuid.UUID | None = Field(default=None, description="소속 섹션 ID (미분류 시 null)")

    @field_validator("section_id", mode="before")
    @classmethod
    def normalize_section_id(cls, value: object) -> object:
        if value == "":
            return None
        return value


class RequirementResponse(BaseModel):
    """요구사항 응답"""
    requirement_id: str = Field(description="요구사항 ID")
    display_id: str = Field(description="표시용 넘버링 (예: FR-001)")
    order_index: int = Field(description="표시 순서")
    type: RequirementType = Field(description="유형")
    original_text: str = Field(description="원문")
    refined_text: str | None = Field(default=None, description="정제된 문장")
    is_selected: bool = Field(default=False, description="선택 여부")
    status: str = Field(default="draft", description="상태")
    section_id: str | None = Field(default=None, description="소속 섹션 ID")
    created_at: str = Field(description="생성일시")
    updated_at: str = Field(description="수정일시")


class RequirementListResponse(BaseModel):
    """요구사항 목록 응답"""
    requirements: list[RequirementResponse] = Field(default_factory=list)


class RequirementSelectionUpdate(BaseModel):
    """요구사항 일괄 선택/해제"""
    requirement_ids: list[uuid.UUID] = Field(description="대상 요구사항 ID 목록")
    is_selected: bool = Field(description="선택 여부")


class RequirementReorderRequest(BaseModel):
    """요구사항 순서 변경 요청"""
    ordered_ids: list[uuid.UUID] = Field(description="변경된 순서대로 요구사항 ID 배열")


class RequirementSaveResponse(BaseModel):
    """요구사항 저장 응답"""
    version: int = Field(description="저장된 버전 번호")
    saved_count: int = Field(description="저장된 요구사항 수")
    saved_at: str = Field(description="저장 일시")
