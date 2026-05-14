"""Review API 스키마 -- 요구사항 충돌(conflict) + 중복(duplicate) 검출 + 해결 힌트 제공."""

from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, Field


# ── 요구사항 Review ──


class ReviewRequest(BaseModel):
    """요구사항 Review 요청"""
    requirement_ids: list[uuid.UUID] = Field(default_factory=list, description="리뷰 대상 요구사항 ID 목록 (빈 배열이면 전체 리뷰)")


class ReviewIssue(BaseModel):
    """Review에서 발견된 이슈"""
    issue_id: str = Field(description="이슈 ID")
    type: Literal["conflict", "duplicate"] = Field(description="이슈 유형 (conflict | duplicate)")
    description: str = Field(description="이슈 설명")
    related_requirements: list[str] = Field(default_factory=list, description="관련 요구사항 display_id")
    hint: str = Field(default="", description="해결 힌트 1줄")


class ReviewSummary(BaseModel):
    """Review 요약"""
    total_issues: int = Field(default=0)
    conflicts: int = Field(default=0)
    duplicates: int = Field(default=0)
    ready_for_next: bool = Field(default=True, description="다음 단계 진행 가능 여부 (v1: 항상 true)")
    feedback: str = Field(default="", description="종합 피드백")


class ReviewResponse(BaseModel):
    """Review 결과 응답"""
    review_id: str = Field(description="리뷰 결과 ID")
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: ReviewSummary = Field(description="요약")


# ── 제안 수락/거절 (v2 예정) ──



# ── 최근 리뷰 결과 조회 ──


class LatestReviewResponse(BaseModel):
    """최근 리뷰 결과 응답"""
    review_id: str
    created_at: datetime
    reviewed_requirement_ids: list[str]
    issues: list[ReviewIssue]
    summary: ReviewSummary
