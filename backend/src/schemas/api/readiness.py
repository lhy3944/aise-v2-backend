"""프로젝트 준비도 스키마"""

from pydantic import BaseModel, Field


class ReadinessItem(BaseModel):
    label: str
    count: int
    sufficient: bool


class ReadinessResponse(BaseModel):
    knowledge: ReadinessItem = Field(description="활성 지식 문서 (completed 상태)")
    glossary: ReadinessItem = Field(description="승인된 용어")
    sections: ReadinessItem = Field(description="활성 섹션")
    is_ready: bool = Field(description="최소 기준 충족 여부")
