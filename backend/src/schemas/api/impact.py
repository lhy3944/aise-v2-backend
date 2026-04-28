"""Impact / Stale 분석 API 스키마.

Phase F (PLAN_ARTIFACT_LINEAGE.md §F):
어떤 artifact 의 current version 이 가리키는 source 들 중 하나라도
"가리키는 version_number < source artifact 의 현재 version_number" 라면
그 artifact 는 stale 로 판정한다 — 입력으로 사용한 source 가 갱신됐다는 뜻.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StaleReason(BaseModel):
    source_artifact_id: str
    source_artifact_type: str  # 'record' / 'srs' / 'design' / 'testcase'
    source_display_id: str | None = None
    referenced_version: int | None = None  # lineage 에 기록된 version_number
    current_version: int | None = None  # source artifact 의 현재 version_number
    section_id: str | None = None  # SRS section 등 부분 참조


class ImpactedArtifact(BaseModel):
    artifact_id: str
    artifact_type: str
    display_id: str
    current_version_number: int | None = None
    stale_reasons: list[StaleReason] = Field(default_factory=list)


class ImpactResponse(BaseModel):
    """프로젝트의 모든 stale artifact 목록.

    빈 리스트면 모든 산출물이 최신 입력을 반영 중.
    """

    stale: list[ImpactedArtifact] = Field(default_factory=list)


# ─── Apply (Phase G — 자동 재생성) ────────────────────────────────────────────


class ImpactApplyRequest(BaseModel):
    """선택된 stale artifact 들을 일괄 재생성 요청.

    artifact_ids 가 비어 있으면 프로젝트의 모든 stale 을 대상으로 한다.
    """

    artifact_ids: list[str] = Field(
        default_factory=list,
        description="대상 artifact_id 목록. 비어 있으면 전체 stale.",
    )


class ImpactApplyEntry(BaseModel):
    artifact_id: str
    artifact_type: str
    display_id: str | None = None
    new_version_id: str | None = None
    new_version_number: int | None = None
    error: str | None = None  # 실패 시 사유, 성공 시 None
    skipped_reason: str | None = None  # auto-regenerate 미지원 등


class ImpactApplyResponse(BaseModel):
    regenerated: list[ImpactApplyEntry] = Field(default_factory=list)
    skipped: list[ImpactApplyEntry] = Field(default_factory=list)
    failed: list[ImpactApplyEntry] = Field(default_factory=list)
