"""Artifact testcase schemas — artifact_type='testcase' 의 content payload.

레거시 schemas/api/testcase.py 는 Jira/Polarion export 등 외부 연동용이고,
Artifact governance 하의 TestCase 는 별도 payload 스키마를 갖는다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TestCasePriority = Literal["high", "medium", "low"]
TestCaseType = Literal["functional", "non_functional", "boundary", "negative"]


class TestCaseContent(BaseModel):
    """Artifact.content JSONB 로 저장되는 TC payload."""

    title: str = Field(min_length=1, max_length=200)
    precondition: str = Field(default="없음")
    steps: list[str] = Field(default_factory=list)
    expected_result: str = Field(default="")
    priority: TestCasePriority = "medium"
    type: TestCaseType = "functional"
    related_srs_section_id: str | None = None


class TestCaseArtifactResponse(BaseModel):
    artifact_id: str
    display_id: str
    content: TestCaseContent
    working_status: str
    lifecycle_status: str
    created_at: str


class TestCaseGenerateResponse(BaseModel):
    based_on_srs_id: str
    srs_version: int
    testcases: list[TestCaseArtifactResponse] = Field(default_factory=list)
    section_coverage: dict[str, int] = Field(default_factory=dict)
    skipped_sections: list[str] = Field(default_factory=list)


__all__ = [
    "TestCaseArtifactResponse",
    "TestCaseContent",
    "TestCaseGenerateResponse",
    "TestCasePriority",
    "TestCaseType",
]
