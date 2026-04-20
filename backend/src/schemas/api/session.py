"""Session API 스키마"""

from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    project_id: uuid.UUID = Field(description="프로젝트 ID")
    title: str | None = Field(default=None, description="세션 제목 (없으면 첫 메시지에서 자동 생성)")


class SessionUpdate(BaseModel):
    title: str = Field(description="세션 제목")


class SessionMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_data: dict | None = None
    created_at: datetime


class SessionResponse(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SessionDetailResponse(SessionResponse):
    messages: list[SessionMessageResponse]


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
