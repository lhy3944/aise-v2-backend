"""RequirementAgent — 요구사항 record 후보를 추출.

세 가지 입력 경로를 단일 에이전트 안에서 처리한다:

1. **document mode** (default): 활성 지식 문서에서 LLM 으로 추출 — 사용자가
   "레코드 추출", "요구사항 뽑아줘" 등 명시적 명령을 내릴 때.
2. **user_text mode**: 사용자가 채팅에 직접 적은 진술문 ("우리 시스템은
   OAuth 2.0 을 지원해야 한다") 을 한 문장 = 한 후보로 분해 — 지식 문서가
   없는 신규 프로젝트에서도 동작. Supervisor 가 routing.extract_mode
   = "user_text" 로 라우팅한다.
3. **manual** (수동 폼): 우측 Records 패널에서 직접 폼 입력 — 본 에이전트는
   관여하지 않으며 `POST /api/v1/projects/{pid}/artifacts/record` 라우터로
   직접 처리된다 (`is_auto_extracted=false`).

추출 (1, 2) 후엔 ConfirmData interrupt 를 발행해 SSE 를 일시 정지하고,
resume 라우터가 사용자 결정 (`approve` / `reject`) 을 주입하면 같은
에이전트의 run_stream 을 재호출한다.

추출 실패 (활성 문서/섹션 부재 등) 시에는 ErrorEvent 가 아닌 token + final
로 사용자 친화 가이드를 채팅 답변으로 노출한다 (참조: `_requirement_guides`).

Output contract (partial state update):
    - `final_answer`: short human-readable summary
    - `records_extracted`: 추출된 후보 목록
    - `records_approved_count`: int (resume + approve 시에만)
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from loguru import logger

from src.agents._requirement_guides import (
    no_candidates_guide,
    to_user_friendly_guide,
)
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


def _resolve_extract_mode(state: AgentState) -> str:
    """state.routing.extract_mode 를 안전하게 읽는다 (디폴트 'document')."""
    routing = state.get("routing") or {}
    mode = routing.get("extract_mode")
    if mode in ("document", "user_text"):
        return mode
    return "document"


@register_agent
class RequirementAgent(BaseAgent):
    capability = AgentCapability(
        name="requirement",
        description=(
            "프로젝트의 요구사항 레코드 후보를 추출한다. "
            "(1) '레코드 추출', '요구사항 뽑아줘' 같은 **명시적 명령** 일 때 "
            "선택 (extract_mode=document — 활성 지식 문서에서 추출). "
            "(2) 사용자가 '우리 시스템은 ~~ 해야 한다', '~~ 기능이 필요하다' "
            "같은 **요구사항 진술문을 직접** 적었을 때 선택 "
            "(extract_mode=user_text — 채팅 본문 자체에서 추출). "
            "단순 인사/질문/문서 요약 요청에는 선택하지 말 것."
        ),
        triggers=[
            "요구사항 추출해줘",
            "레코드 뽑아줘",
            "문서에서 요구사항 후보 만들어줘",
            "요구사항 리스트 생성",
            "우리 시스템은 ~~ 해야 한다",
            "사용자는 ~~ 가능해야 한다",
            "응답 시간은 ~~ 이내여야 한다",
        ],
        input_schema={"project_id": "str", "user_input": "str"},
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
        # 비-스트리밍 호출 경로 — HITL 게이트 없이 추출만 수행한다 (legacy
        # 테스트 호환). 스트리밍 경로는 run_stream 을 사용한다.
        logger.info(f"RequirementAgent.run (non-streaming): project={ctx.project_id}")
        mode = _resolve_extract_mode(state)
        user_text = state.get("user_input") if mode == "user_text" else None

        try:
            response = await artifact_record_svc.extract_records(
                ctx.db, ctx.project_id, user_text=user_text,
            )
        except AppException as exc:
            guide = to_user_friendly_guide(exc.detail)
            return {"final_answer": guide, "records_extracted": []}

        candidates = [c.model_dump() for c in response.candidates]
        if not candidates:
            return {
                "final_answer": no_candidates_guide(),
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
                    guide = to_user_friendly_guide(exc.detail)
                    yield {"kind": "token", "text": guide}
                    yield {
                        "kind": "final",
                        "update": {
                            "final_answer": guide,
                            "records_extracted": candidates,
                            "records_approved_count": 0,
                        },
                    }
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

        # ── 첫 호출 경로 — 모드 분기 → 추출 → confirm interrupt ─────────
        mode = _resolve_extract_mode(state)
        user_text = state.get("user_input") if mode == "user_text" else None
        logger.info(
            f"RequirementAgent.run_stream: project={ctx.project_id}, mode={mode}"
        )

        try:
            response = await artifact_record_svc.extract_records(
                ctx.db, ctx.project_id, user_text=user_text,
            )
        except AppException as exc:
            # 추출 실패는 ErrorEvent 가 아닌 token + final 로 친절한 가이드를
            # 채팅 답변으로 노출. (final_answer 만 채우고 error 는 비움 — 빨간
            # 토스트가 아니라 일반 어시스턴트 메시지로 표시되도록.)
            guide = to_user_friendly_guide(exc.detail)
            yield {"kind": "token", "text": guide}
            yield {
                "kind": "final",
                "update": {"final_answer": guide, "records_extracted": []},
            }
            return

        candidates = [c.model_dump() for c in response.candidates]
        if not candidates:
            msg = no_candidates_guide()
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
        if mode == "user_text":
            description = (
                f"채팅 입력에서 {len(candidates)}개 요구사항 후보를 추출했습니다. "
                f"섹션 분포: {_section_histogram(candidates)}. "
                "승인 시 모든 후보가 records 로 등록되며, 거부 시 폐기됩니다."
            )
        else:
            description = (
                f"섹션 분포: {_section_histogram(candidates)}. "
                "승인 시 모든 후보가 records 로 등록되며, 거부 시 폐기됩니다."
            )

        yield {
            "kind": "interrupt",
            "data": ConfirmData(
                interrupt_id=interrupt_id,
                title=f"{len(candidates)}개 요구사항 후보를 승인하시겠습니까?",
                description=description,
                severity="info",
                actions=ConfirmActions(approve="승인", reject="거부"),
            ),
        }


__all__ = ["RequirementAgent"]
