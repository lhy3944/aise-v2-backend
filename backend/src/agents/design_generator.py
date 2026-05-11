"""DesignGeneratorAgent — 프로젝트의 SRS clean version 을 입력으로 설계 산출물을 생성한다.

`services.design_svc.generate_design` 의 thin wrapper.
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
from src.orchestration.state import AgentContext, AgentState
from src.schemas.events import ConfirmActions, ConfirmData, ConfirmImpact
from src.services import design_svc
from src.services.artifact_messages import MISSING_SRS_MESSAGE


@register_agent
class DesignGeneratorAgent(BaseAgent):
    capability = AgentCapability(
        name="design_generator",
        description=(
            "프로젝트의 완료된 SRS 문서를 기반으로 설계(Design) 산출물을 "
            "생성한다. 사용자가 '설계 생성', '설계 문서 만들어줘', "
            "'아키텍처/디자인 뽑아줘' 등 **명시적으로** 설계 산출물을 요청할 "
            "때만 선택한다. SRS 가 선행되어야 한다."
        ),
        triggers=[
            "설계 생성해줘",
            "설계 문서 만들어줘",
            "디자인 뽑아줘",
            "아키텍처 설계",
        ],
        input_schema={"project_id": "str"},
        output_schema={
            "final_answer": "str",
            "design_generated": "dict",
        },
        tags=["generation", "design", "artifact"],
        estimated_tokens=12000,
        requires_hitl=True,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        logger.info(f"DesignGeneratorAgent run: project={ctx.project_id}")

        try:
            response = await design_svc.generate_design(ctx.db, ctx.project_id)
        except AppException as exc:
            logger.warning(f"DesignGeneratorAgent: design_svc rejected: {exc.detail}")
            return {"error": exc.detail}

        based_on = (
            response.based_on_srs if isinstance(response.based_on_srs, dict) else {}
        )
        srs_v = based_on.get("version_number")
        srs_v_text = f", SRS v{srs_v} 기반" if srs_v else ""
        summary = (
            f"DESIGN v{response.version} 생성 완료 · "
            f"{len(response.sections)}개 섹션{srs_v_text}."
        )
        return {
            "final_answer": summary,
            "design_generated": {
                "design_id": response.design_id,
                "artifact_id": response.artifact_id,
                "version": response.version,
                "section_count": len(response.sections),
                "based_on_srs_version": srs_v,
            },
        }

    async def run_stream(self, state: AgentState, ctx: AgentContext):
        hitl_response = state.get("hitl_response")
        if hitl_response is None:
            srs_count = (
                await ctx.db.execute(
                    select(func.count(Artifact.id)).where(
                        Artifact.project_id == ctx.project_id,
                        Artifact.artifact_type == "srs",
                        Artifact.lifecycle_status == "active",
                    )
                )
            ).scalar() or 0
            if srs_count < 1:
                msg = f"{MISSING_SRS_MESSAGE} 먼저 SRS를 생성해 주세요."
                yield {"kind": "token", "text": msg}
                yield {"kind": "final", "update": {"final_answer": msg}}
                return

            yield {
                "kind": "interrupt",
                "data": ConfirmData(
                    interrupt_id=f"itp_design_{uuid.uuid4().hex[:12]}",
                    title="Design 문서를 생성할까요?",
                    description="승인하면 최신 SRS를 기반으로 Design 산출물을 생성합니다.",
                    impact=[ConfirmImpact(label="기반 SRS", detail=f"{srs_count}개 활성 산출물")],
                    context={"srs_count": int(srs_count)},
                    severity="warning",
                    actions=ConfirmActions(approve="생성", reject="취소"),
                ),
            }
            return

        approved = hitl_response.get("approved") is True or hitl_response.get("action") == "approve"
        if not approved:
            msg = "Design 문서 생성이 취소되었습니다."
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg}}
            return

        result = await self.run(state, ctx)
        if result.get("error"):
            yield {"kind": "final", "update": result}
            return
        yield {"kind": "token", "text": result.get("final_answer", "")}
        yield {"kind": "final", "update": result}


__all__ = ["DesignGeneratorAgent"]
