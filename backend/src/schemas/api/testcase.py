from pydantic import BaseModel, Field

from .common import Message, Platform


class TestStep(BaseModel):
    """테스트 스텝"""
    step: str = Field(description="테스트 절차")
    data: str = Field(default="", description="테스트 데이터")
    expected_result: str = Field(description="기대 결과")


class TestCaseResponse(BaseModel):
    """TestCase 응답"""
    testcase_id: str = Field(description="TC ID")
    summary: str = Field(description="TC 요약")
    source_requirement_id: str | None = Field(default=None, description="출처 요구사항 ID")
    steps: list[TestStep] = Field(default_factory=list, description="테스트 스텝")
    technique: str = Field(description="적용된 기법")
    platform: str = Field(default="jira", description="대상 플랫폼")
    is_selected: bool = Field(default=True, description="선택 여부")
    created_at: str = Field(description="생성일시")


class TestCaseListResponse(BaseModel):
    """TestCase 목록 응답"""
    testcases: list[TestCaseResponse] = Field(default_factory=list)


# --- 연동 모드 TC 생성 ---

class TCGenerateRequest(BaseModel):
    """연동 모드 TC 생성 요청"""
    requirement_ids: list[str] = Field(description="대상 요구사항 ID 목록")
    techniques: list[str] = Field(
        default=["equivalence_partitioning", "boundary_value"],
        description="적용할 테스트 기법"
    )
    platform: Platform = Field(default=Platform.JIRA, description="대상 플랫폼")


class RequirementMapping(BaseModel):
    """요구사항-TC 매핑"""
    requirement_id: str = Field(description="요구사항 ID")
    testcase_ids: list[str] = Field(default_factory=list, description="연결된 TC ID 목록")


class TCGenerateResponse(BaseModel):
    """TC 생성 응답"""
    testcases: list[TestCaseResponse] = Field(default_factory=list)
    requirement_mapping: list[RequirementMapping] = Field(default_factory=list, description="매핑 관계")


# --- 독립 모드 TC 생성 ---

class TCStandaloneGenerateRequest(BaseModel):
    """독립 모드 TC 생성 요청"""
    content: str = Field(description="요구사항 텍스트 또는 자연어 입력")
    techniques: list[str] = Field(
        default=["equivalence_partitioning", "boundary_value"],
        description="적용할 테스트 기법"
    )
    platform: Platform = Field(default=Platform.JIRA, description="대상 플랫폼")


class ClassifiedRequirements(BaseModel):
    """자동 분류된 요구사항"""
    fr: list[str] = Field(default_factory=list)
    qa: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class TCStandaloneResponse(BaseModel):
    """독립 모드 TC 생성 응답 (분류 결과 포함)"""
    classified: ClassifiedRequirements = Field(description="자동 분류 결과")
    testcases: list[TestCaseResponse] = Field(default_factory=list)


# --- TC 수정/선택/Chat ---

class TCUpdate(BaseModel):
    """TC 수정 요청"""
    summary: str | None = Field(default=None)
    steps: list[TestStep] | None = Field(default=None)


class TCSelectionUpdate(BaseModel):
    """TC 일괄 선택/해제"""
    testcase_ids: list[str] = Field(description="대상 TC ID 목록")
    is_selected: bool = Field(description="선택 여부")


class TCChatRequest(BaseModel):
    """Chat으로 TC 수정 요청"""
    message: str = Field(description="사용자 메시지")
    history: list[Message] = Field(default_factory=list, description="대화 이력")


class TCChatResponse(BaseModel):
    """Chat TC 수정 응답"""
    testcases: list[TestCaseResponse] = Field(default_factory=list, description="생성/수정된 TC")
    message: str = Field(description="AI 응답 메시지")


# --- TC Export ---

class TCExportRequest(BaseModel):
    """TC 내보내기 요청"""
    testcase_ids: list[str] = Field(description="대상 TC ID 목록")
    format: str = Field(description="내보내기 형식 (jira | polarion | excel | markdown)")
