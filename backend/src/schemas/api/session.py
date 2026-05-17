"""Session API schemas."""

from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    project_id: uuid.UUID = Field(description="Project ID")
    title: str | None = Field(
        default=None,
        description="Session title. If omitted, it can be generated from the first message.",
    )


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, description="Session title")
    is_favorite: bool | None = Field(default=None, description="Favorite session flag")


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
    is_favorite: bool = False
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SessionDetailResponse(SessionResponse):
    messages: list[SessionMessageResponse]


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    next_cursor: str | None = None
