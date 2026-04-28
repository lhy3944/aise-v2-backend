"""RequirementAgent — extracts candidate requirement records from a
project's active knowledge documents.

Phase 3 PR-2: 추출 후 사용자 승인을 요청하는 HITL 게이트가 도입됐다.
첫 호출에서 후보를 추출하면 ConfirmData interrupt 를 발행해 SSE 를 일시
정지하고, resume 라우터가 사용자 결정 (`approve` / `reject`) 을 주입해
같은 에이전트의 `run_stream` 을 재호출한다. approve 면 `approve_records`
가 실행돼 DB 에 commit, reject 면 거부 메시지로 종료한다.

Output contract (partial state update):
    - `final_answer`: short human-readable summary
    - `records_extracted`: 추출된 후보 목록 (interrupt 직전에 partial 로
      누적 → resume 시 복원). 거부/오류 시에도 빈 리스트 반환.
    - `records_approved_count`: int (resume + approve 시에만)
    - `error`: 활성 섹션/문서가 없을 때 등 명시적 거부.
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.schemas.api.artifact_record import (
    ArtifactRecordApproveRequest,
    ArtifactRecordCreate,
)
from src.schemas.events import ConfirmActions, ConfirmData
from src.services import artifact_record_svc


def _section_histogram(candidates: list[dict[str, Any]]) -> str:
    counts: Counter[str] = Counter()
    for cand in candidates:
        counts[cand.get("section_name") or "(미분류)"] += 1
    return ", ".join(f"{name}({n})" for name, n in counts.most_common())


def _to_create(c: dict[str, Any]) -> ArtifactRecordCreate:
    """추출 후보 dict → ArtifactRecordCreate (UUID 캐스팅은 pydantic 위임)."""
    return ArtifactRecordCreate(
        content=c.get("content", ""),
        section_id=c.get("section_id"),
        source_document_id=c.get("source_document_id"),
        source_location=c.get("source_location"),
        confidence_score=c.get("confidence_score"),
    )


@register_agent
class RequirementAgent(BaseAgent):
    capability = AgentCapability(
        name="requirement",
        description=(
            "프로젝트의 활성 지식 문서에서 요구사항 레코드 후보를 추출한다. "
            "사용자가 '레코드 추출', '요구사항을 뽑아줘', '요구사항 후보 생성' 등 "
            "**명시적으로** 추출을 요청할 때만 선택한다. 단순 문서 질의(요약, "
            "검색)에는 knowledge_qa 에이전트를 쓴다."
        ),
        triggers=[
            "요구사항 추출해줘",
            "레코드 뽑아줘",
            "문서에서 요구사항 후보 만들어줘",
            "요구사항 리스트 생성",
        ],
        input_schema={"project_id": "str"},
        output_schema={
            "final_answer": "str",
            "records_extracted": "list[dict]",
            "records_approved_count": "int",
        },
        tags=["extraction", "records"],
        estimated_tokens=6000,
        requires_hitl=True,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        # 비-스트리밍 호출 경로 — HITL 게이트 없이 추출만 수행한다 (legacy).
        # 스트리밍 경로는 run_stream 을 사용한다.
        logger.info(f"RequirementAgent.run (non-streaming): project={ctx.project_id}")
        try:
            response = await artifact_record_svc.extract_records(ctx.db, ctx.project_id)
        except AppException as exc:
            return {"error": exc.detail}

        candidates = [c.model_dump() for c in response.candidates]
        if not candidates:
            return {
                "final_answer": "추출된 요구사항 후보가 없습니다. 지식 문서와 활성 섹션 설정을 확인해주세요.",
                "records_extracted": [],
            }
        return {
            "final_answer": (
                f"{len(candidates)}개의 요구사항 후보를 추출했습니다. "
                f"섹션 분포: {_section_histogram(candidates)}."
            ),
            "records_extracted": candidates,
        }

    async def run_stream(self, state: AgentState, ctx: AgentContext):
        # ── resume 경로 ────────────────────────────────────────────────
        hitl_response = state.get("hitl_response")
        if hitl_response is not None:
            action = (hitl_response or {}).get("action")
            candidates: list[dict[str, Any]] = list(state.get("records_extracted") or [])
            if action == "approve" and candidates:
                try:
                    items = [_to_create(c) for c in candidates]
                    request = ArtifactRecordApproveRequest(items=items)
                    result = await artifact_record_svc.approve_records(
                        ctx.db, ctx.project_id, request,
                    )
                except AppException as exc:
                    yield {"kind": "final", "update": {"error": exc.detail}}
                    return

                approved_count = len(result.records)
                msg = f"{approved_count}개 요구사항 후보를 승인했습니다."
                yield {"kind": "token", "text": msg}
                yield {
                    "kind": "final",
                    "update": {
                        "final_answer": msg,
                        "records_extracted": candidates,
                        "records_approved_count": approved_count,
                    },
                }
                return

            # reject (또는 빈 후보)
            msg = "요구사항 후보를 거부했습니다." if action == "reject" else "승인할 후보가 없습니다."
            yield {"kind": "token", "text": msg}
            yield {
                "kind": "final",
                "update": {
                    "final_answer": msg,
                    "records_extracted": candidates,
                    "records_approved_count": 0,
                },
            }
            return

        # ── 첫 호출 경로 — 추출 후 confirm interrupt ────────────────────
        logger.info(f"RequirementAgent.run_stream: project={ctx.project_id}")
        try:
            response = await artifact_record_svc.extract_records(ctx.db, ctx.project_id)
        except AppException as exc:
            yield {"kind": "final", "update": {"error": exc.detail}}
            return

        candidates = [c.model_dump() for c in response.candidates]
        if not candidates:
            msg = (
                "추출된 요구사항 후보가 없습니다. 지식 문서와 활성 섹션 설정을 확인해주세요."
            )
            yield {"kind": "token", "text": msg}
            yield {
                "kind": "final",
                "update": {"final_answer": msg, "records_extracted": []},
            }
            return

        # 후보를 partial 로 누적 — interrupt 시 hitl_state.accumulated_state
        # 에 반영돼 resume 호출에서 복원된다.
        yield {"kind": "partial", "update": {"records_extracted": candidates}}

        interrupt_id = f"itp_req_{uuid.uuid4().hex[:12]}"
        yield {
            "kind": "interrupt",
            "data": ConfirmData(
                interrupt_id=interrupt_id,
                title=f"{len(candidates)}개 요구사항 후보를 승인하시겠습니까?",
                description=(
                    f"섹션 분포: {_section_histogram(candidates)}. "
                    "승인 시 모든 후보가 records 로 등록되며, 거부 시 폐기됩니다."
                ),
                severity="info",
                actions=ConfirmActions(approve="승인", reject="거부"),
            ),
        }


__all__ = ["RequirementAgent"]
