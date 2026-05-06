"""ProjectStatusAgent — 프로젝트 산출물 현황 질의 응답.

"레코드 몇 개야?", "SRS 상태 어때?", "진행 상황 알려줘" 같은
실시간 프로젝트 상태 질문을 DB에서 직접 조회해 답변한다.
KnowledgeQAAgent는 RAG(문서 검색)만 가능하므로,
시스템 상태 질의는 반드시 이 에이전트로 라우팅되어야 한다.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.models.artifact import Artifact, ArtifactVersion
from src.orchestration.state import AgentContext, AgentState
from src.prompts.project_status.chat import build_project_status_prompt
from src.services import llm_svc

_STATUS_LABELS: dict[str, str] = {
    "draft": "초안",
    "approved": "승인",
    "excluded": "제외",
}

_WORKING_LABELS: dict[str, str] = {
    "clean": "변경 없음",
    "dirty": "수정 중",
    "staged": "리뷰 대기",
}


async def _fetch_project_summary(db: AsyncSession, project_id: Any) -> str:
    """DB에서 프로젝트 산출물 현황을 집계해 텍스트 요약 반환."""
    pid = project_id

    # 1) 타입별 artifact 수와 working_status 분포
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

    # 2) Record 상태별 분포 (content JSONB의 metadata.status 기반)
    record_status_counts: dict[str, int] = {}
    if "record" in type_counts:
        record_artifacts = (
            await db.execute(
                select(Artifact.content)
                .where(
                    Artifact.project_id == pid,
                    Artifact.artifact_type == "record",
                    Artifact.lifecycle_status == "active",
                )
            )
        ).scalars().all()

        for content in record_artifacts:
            payload = content if isinstance(content, dict) else {}
            status = payload.get("metadata", {}).get("status", "draft")
            record_status_counts[status] = record_status_counts.get(status, 0) + 1

    # 3) SRS/Design/TestCase 버전 정보
    version_info: dict[str, list[dict[str, Any]]] = {}
    for artifact_type in ("srs", "design", "testcase"):
        artifacts = (
            await db.execute(
                select(Artifact.id)
                .where(
                    Artifact.project_id == pid,
                    Artifact.artifact_type == artifact_type,
                    Artifact.lifecycle_status == "active",
                )
            )
        ).scalars().all()

        if not artifacts:
            continue

        versions = (
            await db.execute(
                select(
                    ArtifactVersion.version_number,
                    ArtifactVersion.committed_at,
                )
                .where(ArtifactVersion.artifact_id.in_(artifacts))
                .order_by(ArtifactVersion.version_number.desc())
                .limit(3)
            )
        ).all()

        version_info[artifact_type] = [
            {
                "version": vn,
                "committed_at": str(ca) if ca else None,
            }
            for vn, ca in versions
        ]

    # 4) 텍스트 요약 조합
    lines: list[str] = []

    # Records
    rec = type_counts.get("record", {"total": 0, "by_status": {}})
    lines.append(f"- 레코드: 총 {rec['total']}개")
    if record_status_counts:
        status_parts = [
            f"{_STATUS_LABELS.get(s, s)} {c}개"
            for s, c in record_status_counts.items()
        ]
        lines.append(f"  상태별: {', '.join(status_parts)}")

    # SRS
    srs = type_counts.get("srs", {"total": 0, "by_status": {}})
    lines.append(f"- SRS: 총 {srs['total']}개")
    if "srs" in version_info and version_info["srs"]:
        latest = version_info["srs"][0]
        lines.append(f"  최신 버전: v{latest['version']}")
    if srs.get("by_status"):
        ws_parts = [
            f"{_WORKING_LABELS.get(ws, ws)} {c}개"
            for ws, c in srs["by_status"].items()
        ]
        lines.append(f"  작업 상태: {', '.join(ws_parts)}")

    # Design
    dsg = type_counts.get("design", {"total": 0, "by_status": {}})
    lines.append(f"- Design: 총 {dsg['total']}개")
    if "design" in version_info and version_info["design"]:
        latest = version_info["design"][0]
        lines.append(f"  최신 버전: v{latest['version']}")
    if dsg.get("by_status"):
        ws_parts = [
            f"{_WORKING_LABELS.get(ws, ws)} {c}개"
            for ws, c in dsg["by_status"].items()
        ]
        lines.append(f"  작업 상태: {', '.join(ws_parts)}")

    # TestCase
    tc = type_counts.get("testcase", {"total": 0, "by_status": {}})
    lines.append(f"- 테스트케이스: 총 {tc['total']}개")
    if "testcase" in version_info and version_info["testcase"]:
        latest = version_info["testcase"][0]
        lines.append(f"  최신 버전: v{latest['version']}")
    if tc.get("by_status"):
        ws_parts = [
            f"{_WORKING_LABELS.get(ws, ws)} {c}개"
            for ws, c in tc["by_status"].items()
        ]
        lines.append(f"  작업 상태: {', '.join(ws_parts)}")

    if not lines:
        return "아직 생성된 산출물이 없습니다."

    return "\n".join(lines)


@register_agent
class ProjectStatusAgent(BaseAgent):
    capability = AgentCapability(
        name="project_status",
        description=(
            "프로젝트의 현재 산출물 현황(레코드 개수, SRS/Design/TestCase 상태 및 버전, "
            "진행 상황)을 실시간으로 조회하여 답변한다. "
            "숫자, 상태, 버전, 진척도 등 '지금 어떤가?' 형태의 질문에 적합."
        ),
        triggers=[
            "몇 개야",
            "개수",
            "상태 어때",
            "진행 상황",
            "현황",
            "얼마나",
            "어디까지",
            "레코드 수",
            "SRS 상태",
            "진척도",
            "how many",
            "status",
            "progress",
            "current state",
        ],
        input_schema={"user_input": "str", "project_id": "str"},
        output_schema={"final_answer": "str"},
        tags=["status", "query"],
        estimated_tokens=600,
        expose_as_tool=False,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        final: dict[str, Any] = {}
        async for ev in self.run_stream(state, ctx):
            if ev.get("kind") == "final":
                final = ev.get("update", {}) or {}
        return final

    async def run_stream(
        self, state: AgentState, ctx: AgentContext
    ) -> AsyncGenerator[dict[str, Any], None]:
        query = state.get("user_input", "")
        if not query:
            yield {
                "kind": "final",
                "update": {"error": "user_input is required for project_status"},
            }
            return

        logger.info(
            f"ProjectStatusAgent run_stream: project={ctx.project_id} "
            f"query={query[:60]!r}"
        )

        try:
            summary = await _fetch_project_summary(ctx.db, ctx.project_id)
        except Exception as exc:
            logger.exception("ProjectStatusAgent DB query failed")
            yield {
                "kind": "final",
                "update": {"error": "프로젝트 현황 조회에 실패했습니다."},
            }
            return

        messages = build_project_status_prompt(
            query=query,
            project_summary=summary,
            history=state.get("history", []) or [],
        )

        buffer = ""
        try:
            async for delta in llm_svc.chat_completion_stream(
                messages,
                client_type="srs",
                temperature=0.2,
                max_completion_tokens=512,
            ):
                if not delta:
                    continue
                buffer += delta
                yield {"kind": "token", "text": delta}
        except AppException as exc:
            yield {"kind": "final", "update": {"error": str(exc.detail)}}
            return
        except Exception as exc:
            logger.exception("ProjectStatusAgent LLM stream failed")
            yield {
                "kind": "final",
                "update": {"error": "AI 응답 생성에 실패했습니다."},
            }
            return

        yield {"kind": "final", "update": {"final_answer": buffer}}


__all__ = ["ProjectStatusAgent"]
