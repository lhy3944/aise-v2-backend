"""ProjectStatusAgent — 프로젝트 산출물 현황 질의 응답.

"레코드 몇 개야?", "SRS 상태 어때?", "진행 상황 알려줘" 같은
실시간 프로젝트 상태 질문을 DB에서 직접 조회해 답변한다.

2단계 LLM 패턴:
1. 질의 분석 — 기본 현황으로 답변 가능한지, 추가 집계가 필요한지 판별
2. 데이터 보강 후 응답 — 필요한 집계를 on-demand 조회하여 답변

빠른 경로: Supervisor가 tool_parameters에서 artifact_type/field를
지정하면 1단계 분석 없이 바로 집계 → 응답.
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
from src.prompts.project_status.query_analysis import build_query_analysis_prompt
from src.services import content_aggregation_svc, llm_svc
from src.utils.json_parser import parse_llm_json

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

_PRIORITY_LABELS: dict[str, str] = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

_TC_TYPE_LABELS: dict[str, str] = {
    "functional": "기능",
    "non_functional": "비기능",
    "boundary": "경계값",
    "negative": "부정",
}

# artifact_type + field_path → 한국어 라벨 매핑
_FIELD_LABELS: dict[str, dict[str, str]] = {
    "priority": _PRIORITY_LABELS,
    "type": _TC_TYPE_LABELS,
    "metadata.status": _STATUS_LABELS,
}


def _format_aggregation(
    artifact_type: str,
    field_path: str,
    counts: dict[str, int],
) -> str:
    """집계 결과를 사람이 읽기 쉬운 텍스트로 변환."""
    labels = _FIELD_LABELS.get(field_path, {})
    total = sum(counts.values())
    parts = []
    for value, cnt in counts.items():
        label = labels.get(value, value)
        parts.append(f"{label} {cnt}개")
    type_label = {"record": "레코드", "testcase": "테스트케이스", "srs": "SRS", "design": "설계서"}.get(
        artifact_type, artifact_type
    )
    field_label = {
        "priority": "우선순위",
        "type": "유형",
        "metadata.status": "상태",
    }.get(field_path, field_path)
    return f"- {type_label} {field_label}별: 총 {total}개 ({', '.join(parts)})"


def _format_content_list(
    artifact_type: str,
    field_path: str,
    field_value: str,
    items: list[dict[str, Any]],
) -> str:
    """필터링된 content 항목 목록을 텍스트로 변환."""
    type_label = {"record": "레코드", "testcase": "테스트케이스", "srs": "SRS", "design": "설계서"}.get(
        artifact_type, artifact_type
    )
    field_labels = _FIELD_LABELS.get(field_path, {})
    value_label = field_labels.get(field_value, field_value)

    lines = [f"- {type_label} ({value_label}): {len(items)}개 항목"]

    for item in items:
        display_id = item.get("display_id", "?")
        if artifact_type == "testcase":
            title = item.get("title", "")
            tc_type = item.get("type", "")
            steps_count = len(item.get("steps", []))
            expected = item.get("expected_result", "")
            lines.append(
                f"  [{display_id}] {title} (유형: {tc_type}, 스텝: {steps_count}개, 기대결과: {expected})"
            )
        elif artifact_type == "record":
            text = item.get("text", "")
            status = item.get("metadata", {}).get("status", "")
            preview = text[:100] + ("..." if len(text) > 100 else "")
            lines.append(f"  [{display_id}] {preview} (상태: {status})")
        else:
            title = item.get("title", "")
            lines.append(f"  [{display_id}] {title}")

    return "\n".join(lines)


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

    # 2) Record 상태별 분포 — content_aggregation_svc 재사용
    record_status_section = ""
    if "record" in type_counts:
        status_counts = await content_aggregation_svc.aggregate_field(
            db, pid, "record", "metadata.status"
        )
        if status_counts:
            parts = [
                f"{_STATUS_LABELS.get(s, s)} {c}개"
                for s, c in status_counts.items()
            ]
            record_status_section = f"  상태별: {', '.join(parts)}"

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
    if record_status_section:
        lines.append(record_status_section)

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


async def _resolve_aggregation_queries(
    db: AsyncSession,
    project_id: Any,
    query: str,
    base_summary: str,
) -> str | None:
    """1단계 LLM으로 질의 분석 후 필요한 집계를 수행.

    Returns:
        집계 결과 텍스트 (필요 없으면 None)
    """
    messages = build_query_analysis_prompt(
        base_summary=base_summary,
        query=query,
    )

    try:
        raw = await llm_svc.chat_completion(
            messages,
            client_type="srs",
            temperature=0.0,
            max_completion_tokens=256,
        )
    except Exception as exc:
        logger.warning(f"query analysis LLM failed: {exc!r}")
        return None

    parsed = parse_llm_json(raw, error_msg="query analysis parse failed")
    if not parsed:
        return None

    if parsed.get("answerable") is True:
        return None

    queries = parsed.get("queries") or []
    if not queries:
        return None

    aggregation_parts: list[str] = []
    for q in queries:
        artifact_type = q.get("artifact_type", "")
        field_path = q.get("field", "")
        if not artifact_type or not field_path:
            continue

        try:
            counts = await content_aggregation_svc.aggregate_field(
                db, project_id, artifact_type, field_path
            )
            if counts:
                aggregation_parts.append(
                    _format_aggregation(artifact_type, field_path, counts)
                )
        except Exception as exc:
            logger.warning(
                f"aggregation failed: type={artifact_type}, field={field_path}: {exc!r}"
            )

    return "\n".join(aggregation_parts) if aggregation_parts else None


@register_agent
class ProjectStatusAgent(BaseAgent):
    capability = AgentCapability(
        name="project_status",
        description=(
            "프로젝트의 현재 산출물 현황(레코드 개수, SRS/Design/TestCase 상태 및 버전, "
            "진행 상황, 상세 집계, 내용 요약)을 실시간으로 조회하여 답변한다. "
            "숫자, 상태, 버전, 진척도, 필드별 분포 등 '지금 어떤가?' 형태의 질문에 적합. "
            "artifact_type과 field를 지정하면 해당 필드의 상세 집계를 조회. "
            "field_value와 summary를 지정하면 특정 값의 항목 목록/요약을 제공."
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
            "내용 요약",
            "목록",
        ],
        tool_parameters={
            "type": "object",
            "properties": {
                "artifact_type": {
                    "type": "string",
                    "enum": ["record", "testcase", "srs", "design"],
                    "description": "질의 대상 artifact 타입. 생략하면 전체 현황.",
                },
                "field": {
                    "type": "string",
                    "description": "집계할 content 필드 경로. 예: 'priority', 'type', 'metadata.status'. 생략하면 전체 요약.",
                },
                "field_value": {
                    "type": "string",
                    "description": "field 값으로 필터링. 예: 'high', 'draft', 'functional'. summary=true와 함께 사용.",
                },
                "summary": {
                    "type": "boolean",
                    "description": "true면 필터링된 항목의 내용을 요약/목록 형태로 제공. false면 집계만.",
                },
            },
        },
        input_schema={"user_input": "str", "project_id": "str"},
        output_schema={"final_answer": "str"},
        tags=["status", "query"],
        estimated_tokens=600,
        expose_as_tool=True,
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

        # ── 빠른 경로: Supervisor가 artifact_type/field를 지정한 경우 ──
        routing = state.get("routing") or {}
        action_params = routing.get("action_params") or {}
        fast_artifact_type = action_params.get("artifact_type")
        fast_field = action_params.get("field")
        fast_field_value = action_params.get("field_value")
        fast_summary = action_params.get("summary") is True

        aggregation_results: str | None = None
        content_list_text: str | None = None

        if fast_artifact_type and fast_field:
            if fast_summary and fast_field_value:
                # ── Content 쿼리: 특정 필드값의 항목 목록/요약 ──
                try:
                    items = await content_aggregation_svc.query_content_by_field(
                        ctx.db, ctx.project_id, fast_artifact_type, fast_field, fast_field_value
                    )
                    if items:
                        content_list_text = _format_content_list(
                            fast_artifact_type, fast_field, fast_field_value, items
                        )
                except Exception as exc:
                    logger.warning(
                        f"content query failed: type={fast_artifact_type}, "
                        f"field={fast_field}, value={fast_field_value}: {exc!r}"
                    )
            else:
                # ── 집계 쿼리: 필드값별 개수 ──
                try:
                    counts = await content_aggregation_svc.aggregate_field(
                        ctx.db, ctx.project_id, fast_artifact_type, fast_field
                    )
                    if counts:
                        aggregation_results = _format_aggregation(
                            fast_artifact_type, fast_field, counts
                        )
                except Exception as exc:
                    logger.warning(
                        f"fast-path aggregation failed: type={fast_artifact_type}, "
                        f"field={fast_field}: {exc!r}"
                    )
        else:
            # ── 일반 경로: 1단계 LLM 질의 분석 ──
            try:
                aggregation_results = await _resolve_aggregation_queries(
                    ctx.db, ctx.project_id, query, summary
                )
            except Exception as exc:
                logger.warning(f"aggregation resolution failed: {exc!r}")

        # ── 2단계: 보강된 현황으로 최종 답변 ──
        combined_aggregation = aggregation_results
        if content_list_text:
            combined_aggregation = (
                f"{aggregation_results}\n{content_list_text}"
                if aggregation_results
                else content_list_text
            )

        messages = build_project_status_prompt(
            query=query,
            project_summary=summary,
            history=state.get("history", []) or [],
            aggregation_results=combined_aggregation,
        )

        buffer = ""
        try:
            async for delta in llm_svc.chat_completion_stream(
                messages,
                client_type="srs",
                temperature=0.2,
                max_completion_tokens=1024,
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
