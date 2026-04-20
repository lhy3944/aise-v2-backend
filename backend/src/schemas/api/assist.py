from typing import Literal
import uuid

from pydantic import BaseModel, Field

from .common import RequirementType


class RefineRequest(BaseModel):
    """자연어 → 요구사항 정제 요청"""
    text: str = Field(description="사용자 입력 자연어")
    type: RequirementType = Field(description="요구사항 유형")


class RefineResponse(BaseModel):
    """정제 결과 응답"""
    original_text: str = Field(description="원문")
    refined_text: str = Field(description="정제된 요구사항 문장")
    type: RequirementType = Field(description="유형")


class SuggestRequest(BaseModel):
    """보완 제안 요청"""
    requirement_ids: list[uuid.UUID] = Field(description="대상 요구사항 ID 목록")


class Suggestion(BaseModel):
    """개별 제안"""
    type: RequirementType = Field(description="제안 유형")
    text: str = Field(description="제안 문장")
    reason: str = Field(description="제안 이유")


class SuggestResponse(BaseModel):
    """보완 제안 응답"""
    suggestions: list[Suggestion] = Field(default_factory=list)


# ── Chat (대화 모드) ──


class ChatMessage(BaseModel):
    """대화 히스토리 메시지"""
    role: Literal["user", "assistant"] = Field(description="메시지 역할 (user | assistant)")
    content: str = Field(description="메시지 내용")


class ChatRequest(BaseModel):
    """대화 모드 요청"""
    message: str = Field(description="사용자 메시지")
    history: list[ChatMessage] = Field(
        default_factory=list, description="이전 대화 히스토리"
    )


class ExtractedRequirement(BaseModel):
    """대화에서 추출된 요구사항"""
    type: RequirementType = Field(description="요구사항 유형")
    text: str = Field(description="추출된 요구사항 문장")
    reason: str = Field(description="추출 근거")


class ChatResponse(BaseModel):
    """대화 모드 응답"""
    reply: str = Field(description="AI 응답 메시지")
    extracted_requirements: list[ExtractedRequirement] = Field(
        default_factory=list, description="대화에서 추출된 요구사항"
    )
