from pydantic import BaseModel, Field

from .common import DiagramTool, Message


class UseCaseDiagramGenerateRequest(BaseModel):
    """Use Case Diagram 생성 요청"""
    requirement_ids: list[str] = Field(description="요구사항 ID 목록")
    diagram_tool: DiagramTool = Field(default=DiagramTool.PLANTUML, description="다이어그램 도구")


class UseCaseDiagramResponse(BaseModel):
    """Use Case Diagram 응답"""
    diagram_id: str = Field(description="다이어그램 ID")
    code: str = Field(description="다이어그램 코드 (PlantUML/Mermaid)")
    diagram_tool: DiagramTool = Field(description="다이어그램 도구")
    source_requirements_version: int | None = Field(default=None, description="기반 요구사항 버전")
    is_outdated: bool = Field(default=False, description="최신 요구사항 기반 여부")
    created_at: str = Field(description="생성일시")


class UseCaseDiagramUpdate(BaseModel):
    """Use Case Diagram 코드 수정"""
    code: str = Field(description="수정된 다이어그램 코드")


class UseCaseDiagramChatRequest(BaseModel):
    """LLM을 통한 Diagram 수정 요청"""
    message: str = Field(description="사용자 메시지")
    history: list[Message] = Field(default_factory=list, description="대화 이력")


class UseCaseDiagramChatResponse(BaseModel):
    """LLM Diagram 수정 응답"""
    code: str = Field(description="수정된 다이어그램 코드")
    message: str = Field(description="AI 응답 메시지")


class UseCaseDiagramSaveResponse(BaseModel):
    """Use Case Diagram 저장 응답"""
    diagram_id: str = Field(description="다이어그램 ID")
    version: int = Field(description="저장된 버전")
    saved_at: str = Field(description="저장 일시")


# --- Use Case Specification ---

class UseCaseSpecCandidate(BaseModel):
    """Use Case Specification 후보"""
    candidate_id: str = Field(description="후보 ID")
    description: str = Field(description="Use Case 설명")
    actors: list[str] = Field(default_factory=list, description="액터 목록")
    preconditions: list[str] = Field(default_factory=list, description="사전 조건")
    steps: list[str] = Field(default_factory=list, description="기본 흐름 단계")
    exceptions: list[str] = Field(default_factory=list, description="예외 흐름")
    postconditions: list[str] = Field(default_factory=list, description="사후 조건")


class UseCaseSpecItem(BaseModel):
    """Use Case Specification 항목"""
    spec_id: str = Field(description="Specification ID")
    use_case_name: str = Field(description="Use Case 이름")
    candidates: list[UseCaseSpecCandidate] = Field(default_factory=list, description="후보 목록")


class UseCaseSpecGenerateRequest(BaseModel):
    """Use Case Specification 생성 요청"""
    diagram_id: str = Field(description="Use Case Diagram ID")


class UseCaseSpecGenerateResponse(BaseModel):
    """Use Case Specification 생성 응답"""
    specifications: list[UseCaseSpecItem] = Field(default_factory=list)
    source_diagram_version: int | None = Field(default=None)


class UseCaseSpecSelectRequest(BaseModel):
    """Use Case Specification 후보 선택"""
    selected_candidate_id: str = Field(description="선택한 후보 ID")
