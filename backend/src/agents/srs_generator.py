"""SrsGeneratorAgent — produces an SRS document from the project's active
record artifacts.

Thin wrapper around `services.srs_svc.generate_srs`; the heavy lifting
(section assembly, per-section LLM calls, glossary merge) stays in the
service so HTTP callers (`POST /api/v1/projects/{id}/srs/generate`) can
reuse the same code path.

Output contract (partial state update):
    - `final_answer`: short human-readable summary (version + section count)
    - `srs_generated`: dict
        {
          "srs_id": str,
          "version": int,
          "section_count": int,
          "based_on_records_count": int,
        }
      Consumed later by the UI (N4 SrsEditor → opens the new document)
      and by `plan` executors chaining SRS → TestCase.
    - `error`: set if prerequisites (active sections / records) are missing —
      surfaces as a clean AGENT_ERROR rather than a 5xx.
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger
from sqlalchemy import func, select

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.models.artifact import Artifact
from src.models.requirement import RequirementSection
from src.orchestration.state import AgentContext, AgentState
from src.schemas.events import ConfirmActions, ConfirmData, ConfirmImpact
from src.services import srs_svc
from src.services.artifact_messages import MISSING_RECORDS_MESSAGE


@register_agent
class SrsGeneratorAgent(BaseAgent):
    capability = AgentCapability(
        name="srs_generator",
        description=(
            "프로젝트의 활성 레코드(요구사항 Artifact)를 취합해 SRS 문서를 "
            "생성한다. 사용자가 'SRS 생성', 'SRS 문서 만들어줘', "
            "'요구사항 명세서 뽑아줘' 등 **명시적으로** SRS 산출물을 요청할 "
            "때만 선택한다. 레코드 자체 추출은 requirement 에이전트."
        ),
        triggers=[
            "SRS 생성해줘",
            "SRS 문서 만들어줘",
            "요구사항 명세서 뽑아줘",
            "소프트웨어 명세서 작성",
        ],
        input_schema={"project_id": "str"},
        output_schema={
            "final_answer": "str",
            "srs_generated": "dict",
        },
        tags=["generation", "srs", "artifact"],
        estimated_tokens=12000,
        requires_hitl=True,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        logger.info(f"SrsGeneratorAgent run: project={ctx.project_id}")

        try:
            response = await srs_svc.generate_srs(ctx.db, ctx.project_id)
        except AppException as exc:
            logger.warning(f"SrsGeneratorAgent: srs_svc rejected: {exc.detail}")
            return {"error": exc.detail}

        record_ids = (
            response.based_on_records.get("artifact_ids", [])
            if isinstance(response.based_on_records, dict)
            else []
        )
        summary = (
            f"SRS v{response.version} 생성 완료 · "
            f"{len(response.sections)}개 섹션, "
            f"{len(record_ids)}개 레코드 기반."
        )
        return {
            "final_answer": summary,
            "srs_generated": {
                "srs_id": response.srs_id,
                "version": response.version,
                "section_count": len(response.sections),
                "based_on_records_count": len(record_ids),
            },
        }

    async def run_stream(self, state: AgentState, ctx: AgentContext):
        hitl_response = state.get("hitl_response")
        if hitl_response is None:
            record_count = (
                await ctx.db.execute(
                    select(func.count(Artifact.id)).where(
                        Artifact.project_id == ctx.project_id,
                        Artifact.artifact_type == "record",
                        Artifact.lifecycle_status == "active",
                    )
                )
            ).scalar() or 0
            section_count = (
                await ctx.db.execute(
                    select(func.count(RequirementSection.id)).where(
                        RequirementSection.project_id == ctx.project_id,
                        RequirementSection.is_active == True,  # noqa: E712
                    )
                )
            ).scalar() or 0
            if section_count < 1:
                msg = "SRS를 생성하려면 먼저 활성 섹션이 필요합니다."
                yield {"kind": "token", "text": msg}
                yield {"kind": "final", "update": {"final_answer": msg}}
                return
            if record_count < 1:
                msg = f"{MISSING_RECORDS_MESSAGE} 먼저 레코드를 추가하거나 문서에서 추출해 주세요."
                yield {"kind": "token", "text": msg}
                yield {"kind": "final", "update": {"final_answer": msg}}
                return

            yield {
                "kind": "interrupt",
                "data": ConfirmData(
                    interrupt_id=f"itp_srs_{uuid.uuid4().hex[:12]}",
                    title="SRS 문서를 생성할까요?",
                    description="승인하면 현재 활성 레코드를 기반으로 새 SRS 버전을 생성합니다.",
                    impact=[
                        ConfirmImpact(label="기반 레코드", detail=f"{record_count}개"),
                        ConfirmImpact(label="섹션", detail=f"{section_count}개"),
                    ],
                    context={"record_count": int(record_count), "section_count": int(section_count)},
                    severity="warning",
                    actions=ConfirmActions(approve="생성", reject="취소"),
                ),
            }
            return

        approved = hitl_response.get("approved") is True or hitl_response.get("action") == "approve"
        if not approved:
            msg = "SRS 문서 생성이 취소되었습니다."
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg}}
            return

        result = await self.run(state, ctx)
        if result.get("error"):
            yield {"kind": "final", "update": result}
            return
        yield {"kind": "token", "text": result.get("final_answer", "")}
        yield {"kind": "final", "update": result}


__all__ = ["SrsGeneratorAgent"]
