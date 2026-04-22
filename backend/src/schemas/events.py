"""Agent SSE event schema.

Single source of truth for events streamed from /api/v1/agent/chat and
/api/v1/chat/{session_id}/resume (Phase 3+).

Changes here MUST be mirrored in:
- docs/events.md (human contract)
- frontend/src/types/agent-events.ts (consumer types)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


# ---------- Phase 1 events ----------


class TokenEventData(BaseModel):
    text: str


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    data: TokenEventData


class ToolCallEventData(BaseModel):
    tool_call_id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    agent: str | None = None


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    data: ToolCallEventData


class ToolResultEventData(BaseModel):
    tool_call_id: str
    name: str
    status: Literal["success", "error"]
    duration_ms: int | None = None
    result: Any = None


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    data: ToolResultEventData


FinishReason = Literal["stop", "tool_calls", "length", "content_filter", "interrupt", "error"]


class DoneEventData(BaseModel):
    finish_reason: FinishReason


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    data: DoneEventData


class ErrorEventData(BaseModel):
    message: str
    code: str | None = None
    recoverable: bool | None = None


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    data: ErrorEventData


# ---------- Phase 2 events ----------


PlanStepStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class PlanStep(BaseModel):
    agent: str
    status: PlanStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_summary: str | None = None


class PlanUpdateEventData(BaseModel):
    plan: list[PlanStep]
    current_step: int | None = None


class PlanUpdateEvent(BaseModel):
    type: Literal["plan_update"] = "plan_update"
    data: PlanUpdateEventData


ArtifactType = Literal["srs", "design", "testcase", "requirement_list", "records"]


class ArtifactCreatedEventData(BaseModel):
    artifact_id: UUID
    artifact_type: ArtifactType
    title: str
    project_id: UUID
    version: str | None = None


class ArtifactCreatedEvent(BaseModel):
    type: Literal["artifact_created"] = "artifact_created"
    data: ArtifactCreatedEventData


class SourceRef(BaseModel):
    """1:1 with frontend SourceData."""

    ref: int
    document_id: str
    document_name: str
    chunk_index: int
    file_type: str | None = None
    content_preview: str | None = None
    score: float | None = None


class SourcesEventData(BaseModel):
    sources: list[SourceRef]
    agent: str | None = None


class SourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    data: SourcesEventData


# ---------- Phase 3 events (HITL) ----------


class ClarifyOption(BaseModel):
    value: str
    label: str
    description: str | None = None


class ClarifyData(BaseModel):
    kind: Literal["clarify"] = "clarify"
    interrupt_id: str
    question: str
    options: list[ClarifyOption] | None = None
    allow_custom: bool = False
    context: dict[str, Any] | None = None


class ConfirmImpact(BaseModel):
    label: str
    detail: str


ConfirmSeverity = Literal["info", "warning", "danger"]


class ConfirmActions(BaseModel):
    approve: str
    reject: str
    modify: str | None = None


class ConfirmData(BaseModel):
    kind: Literal["confirm"] = "confirm"
    interrupt_id: str
    title: str
    description: str
    impact: list[ConfirmImpact] | None = None
    severity: ConfirmSeverity = "info"
    actions: ConfirmActions


class DecisionOption(BaseModel):
    id: str
    label: str
    default: bool | None = None


class DecisionData(BaseModel):
    kind: Literal["decision"] = "decision"
    interrupt_id: str
    question: str
    options: list[DecisionOption]
    min_selection: int | None = None
    max_selection: int | None = None


HitlData = Annotated[
    Union[ClarifyData, ConfirmData, DecisionData],
    Field(discriminator="kind"),
]


class InterruptEvent(BaseModel):
    type: Literal["interrupt"] = "interrupt"
    data: HitlData


# ---------- Discriminated union ----------


AgentStreamEvent = Annotated[
    Union[
        TokenEvent,
        ToolCallEvent,
        ToolResultEvent,
        PlanUpdateEvent,
        InterruptEvent,
        ArtifactCreatedEvent,
        SourcesEvent,
        DoneEvent,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]


# ---------- Resume request ----------


class ResumeRequest(BaseModel):
    """POST /api/v1/chat/{session_id}/resume body."""

    interrupt_id: str
    response: dict[str, Any]


__all__ = [
    "AgentStreamEvent",
    "ArtifactCreatedEvent",
    "ArtifactCreatedEventData",
    "ArtifactType",
    "ClarifyData",
    "ClarifyOption",
    "ConfirmActions",
    "ConfirmData",
    "ConfirmImpact",
    "ConfirmSeverity",
    "DecisionData",
    "DecisionOption",
    "DoneEvent",
    "DoneEventData",
    "ErrorEvent",
    "ErrorEventData",
    "FinishReason",
    "HitlData",
    "InterruptEvent",
    "PlanStep",
    "PlanStepStatus",
    "PlanUpdateEvent",
    "PlanUpdateEventData",
    "ResumeRequest",
    "SourceRef",
    "SourcesEvent",
    "SourcesEventData",
    "TokenEvent",
    "TokenEventData",
    "ToolCallEvent",
    "ToolCallEventData",
    "ToolResultEvent",
    "ToolResultEventData",
]
