from enum import Enum

from pydantic import BaseModel, Field


# --- Enums ---

class RequirementType(str, Enum):
    FR = "fr"
    QA = "qa"
    CONSTRAINTS = "constraints"
    OTHER = "other"


class MemberRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Platform(str, Enum):
    JIRA = "jira"
    POLARION = "polarion"


class DiagramTool(str, Enum):
    PLANTUML = "plantuml"
    MERMAID = "mermaid"


class ExportFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    WORD = "word"
    EXCEL = "excel"
    JIRA = "jira"
    POLARION = "polarion"


class ArtifactType(str, Enum):
    REQUIREMENTS = "requirements"
    USECASE_DIAGRAM = "usecase_diagram"
    USECASE_SPEC = "usecase_spec"
    TESTCASES = "testcases"
    SRS = "srs"


class ProjectModule(str, Enum):
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TESTCASE = "testcase"


# --- 공통 모델 ---

class Message(BaseModel):
    """AI Chat 대화 이력"""
    role: str = Field(description="메시지 역할 (user | assistant)")
    content: str = Field(description="메시지 내용")


class ErrorDetail(BaseModel):
    """공통 에러 응답"""
    code: str = Field(description="에러 코드")
    message: str = Field(description="에러 메시지")
    detail: str | None = Field(default=None, description="상세 정보")


class ErrorResponse(BaseModel):
    error: ErrorDetail
