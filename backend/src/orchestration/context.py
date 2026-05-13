"""Project context snapshot for Supervisor routing.

Supervisor가 프로젝트 상태를 읽고 `inspect → decide → clarify/confirm/act`
흐름으로 판단할 수 있도록, 매 요청마다 DB에서 프로젝트 현황을
구조화된 스냅샷으로 제공한다.

기존 ProjectStatusAgent._fetch_project_summary()의 집계 로직을
재사용하되 텍스트 요약 대신 dataclass로 제공한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.artifact import Artifact, ArtifactVersion
from src.models.knowledge import KnowledgeDocument
from src.models.requirement import RequirementSection


@dataclass
class ProjectContextSnapshot:
    """Supervisor 입력용 프로젝트 상태 스냅샷."""

    project_id: str
    # 활성 리소스 현황
    active_documents: int = 0
    active_sections: int = 0
    record_count: int = 0
    record_status_breakdown: dict[str, int] = field(default_factory=dict)
    srs_exists: bool = False
    srs_latest_version: str | None = None
    system_model_exists: bool = False
    system_model_latest_version: str | None = None
    data_model_exists: bool = False
    data_model_latest_version: str | None = None
    design_exists: bool = False
    design_latest_version: str | None = None
    testcase_exists: bool = False
    testcase_latest_version: str | None = None
    # 상태 신호
    has_staged_changes: bool = False
    # RAG 게이트 신호 (retrieval gate에서 전달)
    rag_score: float | None = None
    rag_query_rewritten: str | None = None

    def to_prompt_text(self) -> str:
        """Supervisor 프롬프트에 삽입할 텍스트 표현."""
        lines: list[str] = []
        lines.append(f"Project ID: {self.project_id}")
        lines.append(f"- Active knowledge documents: {self.active_documents}")
        lines.append(f"- Active sections: {self.active_sections}")
        lines.append(f"- Records: {self.record_count}")
        if self.record_status_breakdown:
            parts = [
                f"{status} {count}개"
                for status, count in self.record_status_breakdown.items()
            ]
            lines.append(f"  Status breakdown: {', '.join(parts)}")
        lines.append(f"- SRS: {'exists' if self.srs_exists else 'none'}"
                     + (f" (latest v{self.srs_latest_version})" if self.srs_latest_version else ""))
        lines.append(f"- System Model: {'exists' if self.system_model_exists else 'none'}"
                     + (f" (latest v{self.system_model_latest_version})" if self.system_model_latest_version else ""))
        lines.append(f"- Data Model: {'exists' if self.data_model_exists else 'none'}"
                     + (f" (latest v{self.data_model_latest_version})" if self.data_model_latest_version else ""))
        lines.append(f"- Design: {'exists' if self.design_exists else 'none'}"
                     + (f" (latest v{self.design_latest_version})" if self.design_latest_version else ""))
        lines.append(f"- TestCase: {'exists' if self.testcase_exists else 'none'}"
                     + (f" (latest v{self.testcase_latest_version})" if self.testcase_latest_version else ""))
        if self.has_staged_changes:
            lines.append("- Has staged (uncommitted) changes: YES")
        if self.rag_score is not None:
            lines.append(f"- RAG signal: score={self.rag_score:.2f}"
                         + (f", rewritten_query=\"{self.rag_query_rewritten}\"" if self.rag_query_rewritten else ""))
        return "\n".join(lines)


async def build_project_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    rag_signal: dict[str, Any] | None = None,
) -> ProjectContextSnapshot:
    """DB에서 프로젝트 상태 스냅샷을 생성."""
    pid = project_id

    # 1) 활성 지식 문서 수
    doc_count = (
        await db.execute(
            select(func.count()).where(
                KnowledgeDocument.project_id == pid,
                KnowledgeDocument.is_active == True,  # noqa: E712
            )
        )
    ).scalar() or 0

    # 2) 활성 섹션 수
    section_count = (
        await db.execute(
            select(func.count()).where(
                RequirementSection.project_id == pid,
                RequirementSection.is_active == True,  # noqa: E712
            )
        )
    ).scalar() or 0

    # 3) 타입별 artifact 수와 working_status 분포
    type_counts: dict[str, dict[str, Any]] = {}
    rows = (
        await db.execute(
            select(
                Artifact.artifact_type,
                Artifact.working_status,
                func.count(),
            )
            .where(
                Artifact.project_id == pid,
                Artifact.lifecycle_status == "active",
            )
            .group_by(Artifact.artifact_type, Artifact.working_status)
        )
    ).all()

    for artifact_type, ws, cnt in rows:
        if artifact_type not in type_counts:
            type_counts[artifact_type] = {"total": 0, "by_status": {}}
        type_counts[artifact_type]["total"] += cnt
        type_counts[artifact_type]["by_status"][ws] = cnt

    # 4) Record 상태별 분포
    record_status_counts: dict[str, int] = {}
    if "record" in type_counts:
        record_artifacts = (
            await db.execute(
                select(Artifact.content).where(
                    Artifact.project_id == pid,
                    Artifact.artifact_type == "record",
                    Artifact.lifecycle_status == "active",
                )
            )
        ).scalars().all()

        for content in record_artifacts:
            payload = content if isinstance(content, dict) else {}
            meta = payload.get("metadata") or {}
            status = meta.get("status")
            if status not in ("draft", "approved", "excluded"):
                status = "approved"  # _status_of()와 동일한 기본값
            record_status_counts[status] = record_status_counts.get(status, 0) + 1

    record_count = type_counts.get("record", {}).get("total", 0)

    # 5) SRS/Design/TestCase 버전 정보
    version_info: dict[str, str | None] = {}
    has_staged = False
    for artifact_type in ("srs", "system_model", "data_model", "design", "testcase"):
        artifacts = (
            await db.execute(
                select(Artifact.id, Artifact.working_status).where(
                    Artifact.project_id == pid,
                    Artifact.artifact_type == artifact_type,
                    Artifact.lifecycle_status == "active",
                )
            )
        ).all()

        if not artifacts:
            version_info[artifact_type] = None
            continue

        for _, ws in artifacts:
            if ws in ("dirty", "staged"):
                has_staged = True

        artifact_ids = [aid for aid, _ in artifacts]
        latest = (
            await db.execute(
                select(ArtifactVersion.version_number)
                .where(ArtifactVersion.artifact_id.in_(artifact_ids))
                .order_by(ArtifactVersion.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        version_info[artifact_type] = str(latest) if latest is not None else None

    # 6) RAG 신호
    rag_score = None
    rag_query_rewritten = None
    if rag_signal:
        rag_score = rag_signal.get("max_score")
        rag_query_rewritten = rag_signal.get("rewritten_query")

    snapshot = ProjectContextSnapshot(
        project_id=str(pid),
        active_documents=doc_count,
        active_sections=section_count,
        record_count=record_count,
        record_status_breakdown=record_status_counts,
        srs_exists="srs" in type_counts,
        srs_latest_version=version_info.get("srs"),
        system_model_exists="system_model" in type_counts,
        system_model_latest_version=version_info.get("system_model"),
        data_model_exists="data_model" in type_counts,
        data_model_latest_version=version_info.get("data_model"),
        design_exists="design" in type_counts,
        design_latest_version=version_info.get("design"),
        testcase_exists="testcase" in type_counts,
        testcase_latest_version=version_info.get("testcase"),
        has_staged_changes=has_staged,
        rag_score=rag_score,
        rag_query_rewritten=rag_query_rewritten,
    )

    logger.debug(
        f"ProjectContextSnapshot: docs={doc_count}, sections={section_count}, "
        f"records={record_count}, srs={snapshot.srs_exists}, "
        f"sm={snapshot.system_model_exists}, dm={snapshot.data_model_exists}, "
        f"design={snapshot.design_exists}, tc={snapshot.testcase_exists}"
    )

    return snapshot


__all__ = ["ProjectContextSnapshot", "build_project_context"]
