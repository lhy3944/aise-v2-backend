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


# ---------- Phase 2 events (Artifact Governance) ----------
#
# Git-like 워크플로우 이벤트. 프론트엔드는 이들을 받아 StagedChangesTray / PR
# 패널 / ImpactBanner를 갱신한다. `ArtifactKind`는 통합 artifact 모델의 단수형
# 타입 이름을 사용하며(`record/srs/design/testcase`), 위의 레거시 `ArtifactType`
# (복수형 "records" 등)과는 별개로 병행한다 — Phase 3에서 단일화 예정.


ArtifactKind = Literal["record", "srs", "design", "testcase"]
PRStatus = Literal["open", "approved", "rejected", "merged", "superseded"]


class ArtifactStagedEventData(BaseModel):
    artifact_id: UUID
    artifact_kind: ArtifactKind
    project_id: UUID
    version_id: UUID
    version_number: int
    author_id: str


class ArtifactStagedEvent(BaseModel):
    type: Literal["artifact_staged"] = "artifact_staged"
    data: ArtifactStagedEventData


class PRCreatedEventData(BaseModel):
    pr_id: UUID
    artifact_id: UUID
    artifact_kind: ArtifactKind
    project_id: UUID
    title: str
    author_id: str
    base_version_id: UUID | None = None
    head_version_id: UUID
    auto_generated: bool = False


class PRCreatedEvent(BaseModel):
    type: Literal["pr_created"] = "pr_created"
    data: PRCreatedEventData


class PRMergedEventData(BaseModel):
    pr_id: UUID
    artifact_id: UUID
    artifact_kind: ArtifactKind
    project_id: UUID
    merged_version_id: UUID
    version_number: int
    merger_id: str


class PRMergedEvent(BaseModel):
    type: Literal["pr_merged"] = "pr_merged"
    data: PRMergedEventData


class PRRejectedEventData(BaseModel):
    pr_id: UUID
    artifact_id: UUID
    artifact_kind: ArtifactKind
    project_id: UUID
    reviewer_id: str
    reason: str | None = None


class PRRejectedEvent(BaseModel):
    type: Literal["pr_rejected"] = "pr_rejected"
    data: PRRejectedEventData


ImpactReason = Literal[
    "upstream_version_bumped",
    "upstream_status_changed",
    "upstream_deleted",
]


class ImpactedRef(BaseModel):
    artifact_id: UUID
    artifact_kind: ArtifactKind
    display_id: str
    reason: ImpactReason
    pinned_version_number: int | None = None


class ImpactDetectedEventData(BaseModel):
    source_artifact_id: UUID
    source_artifact_kind: ArtifactKind
    project_id: UUID
    impacted: list[ImpactedRef]


class ImpactDetectedEvent(BaseModel):
    type: Literal["impact_detected"] = "impact_detected"
    data: ImpactDetectedEventData


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
        ArtifactStagedEvent,
        PRCreatedEvent,
        PRMergedEvent,
        PRRejectedEvent,
        ImpactDetectedEvent,
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
    "ArtifactKind",
    "ArtifactStagedEvent",
    "ArtifactStagedEventData",
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
    "ImpactDetectedEvent",
    "ImpactDetectedEventData",
    "ImpactReason",
    "ImpactedRef",
    "InterruptEvent",
    "PRCreatedEvent",
    "PRCreatedEventData",
    "PRMergedEvent",
    "PRMergedEventData",
    "PRRejectedEvent",
    "PRRejectedEventData",
    "PRStatus",
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
