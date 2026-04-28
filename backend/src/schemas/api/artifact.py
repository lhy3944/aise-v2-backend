"""Artifact / PullRequest / Version API 스키마

Git-like Artifact Governance의 API 계약. 백엔드 모델(src/models/artifact.py)과
1:1로 대응하며, 프론트엔드 types/project.ts와도 형상 일치.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ArtifactType = Literal["record", "srs", "design", "testcase"]
WorkingStatus = Literal["clean", "dirty", "staged"]
LifecycleStatus = Literal["active", "archived", "deleted"]
PRStatus = Literal["open", "approved", "rejected", "merged", "superseded"]
DependencyType = Literal["derives_from", "references", "covers"]
ChangeAction = Literal[
    "created",
    "edited",
    "staged",
    "pr_opened",
    "pr_approved",
    "pr_merged",
    "pr_rejected",
    "reverted",
]


# ─── Artifact ─────────────────────────────────────────────────────────────────

class ArtifactCreate(BaseModel):
    artifact_type: ArtifactType
    content: dict[str, Any] = Field(
        default_factory=dict, description="타입별 payload",
    )
    title: str | None = None
    display_id: str | None = Field(
        default=None,
        description="미지정 시 서버에서 타입별 prefix로 자동 채번",
    )


class ArtifactUpdate(BaseModel):
    content: dict[str, Any] | None = None
    title: str | None = None


class ArtifactResponse(BaseModel):
    artifact_id: str
    project_id: str
    artifact_type: ArtifactType
    display_id: str
    title: str | None = None
    content: dict[str, Any]
    working_status: WorkingStatus
    lifecycle_status: LifecycleStatus
    current_version_id: str | None = None
    current_version_number: int | None = None
    # Phase E lineage — current_version_id 의 source_artifact_versions 인라인 노출.
    current_source_artifact_versions: dict[str, Any] | None = None
    open_pr_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactResponse]
    total: int


# ─── ArtifactVersion ──────────────────────────────────────────────────────────

class ArtifactVersionResponse(BaseModel):
    version_id: str
    artifact_id: str
    artifact_type: ArtifactType
    version_number: int
    parent_version_id: str | None = None
    snapshot: dict[str, Any]
    content_hash: str
    commit_message: str
    author_id: str
    committed_at: datetime
    merged_from_pr_id: str | None = None
    # Phase E lineage. {"record": [{"artifact_id":..., "version_number":...}], ...}
    source_artifact_versions: dict[str, Any] | None = None


class ArtifactVersionListResponse(BaseModel):
    versions: list[ArtifactVersionResponse]


# ─── Diff ─────────────────────────────────────────────────────────────────────

DiffFormat = Literal["unified", "deepdiff"]


class DiffHunk(BaseModel):
    op: Literal["equal", "add", "delete"] = Field(description="eq/add/del")
    text: str


class DiffFieldEntry(BaseModel):
    field_path: str
    kind: Literal["added", "removed", "modified", "unchanged"]
    before: Any | None = None
    after: Any | None = None
    hunks: list[DiffHunk] | None = None


class DiffResult(BaseModel):
    format: DiffFormat
    base_version_id: str | None = None
    head_version_id: str
    entries: list[DiffFieldEntry]
    unified_text: str | None = None


# ─── PullRequest ──────────────────────────────────────────────────────────────

class PullRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class PullRequestReject(BaseModel):
    reason: str | None = None


class PullRequestResponse(BaseModel):
    pr_id: str
    project_id: str
    artifact_id: str
    artifact_type: ArtifactType
    base_version_id: str | None = None
    head_version_id: str
    status: PRStatus
    title: str
    description: str | None = None
    author_id: str
    reviewer_id: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    merged_at: datetime | None = None
    auto_generated: bool = False


class PullRequestListResponse(BaseModel):
    pull_requests: list[PullRequestResponse]
    total: int


# ─── ChangeEvent ──────────────────────────────────────────────────────────────

class ChangeEventResponse(BaseModel):
    event_id: str
    project_id: str
    artifact_id: str | None = None
    pr_id: str | None = None
    version_id: str | None = None
    action: ChangeAction
    actor: str
    diff_summary: dict[str, Any] | None = None
    impact_summary: dict[str, Any] | None = None
    occurred_at: datetime


# ─── ArtifactDependency / Impact ──────────────────────────────────────────────

class ArtifactDependencyCreate(BaseModel):
    upstream_artifact_id: uuid.UUID
    downstream_artifact_id: uuid.UUID
    dependency_type: DependencyType = "derives_from"
    upstream_version_pinned_id: uuid.UUID | None = None


class ImpactedArtifactRef(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    display_id: str
    reason: Literal[
        "upstream_version_bumped",
        "upstream_status_changed",
        "upstream_deleted",
    ]
    pinned_version_number: int | None = None


class ImpactResponse(BaseModel):
    source_artifact_id: str
    impacted: list[ImpactedArtifactRef]
