"""Agent Chat API 스키마"""

import uuid

from pydantic import BaseModel, Field


class AgentAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    text_preview: str | None = None


class AgentAttachmentUploadResponse(BaseModel):
    attachments: list[AgentAttachment]


class AgentChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_name: str | None = None  # for tool messages
    tool_data: dict | None = None  # structured data (e.g., clarify questions, requirements)


class AgentChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str
    attachments: list[AgentAttachment] = Field(default_factory=list)
