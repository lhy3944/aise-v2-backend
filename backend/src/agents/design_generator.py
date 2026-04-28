"""DesignGeneratorAgent — 프로젝트의 SRS clean version 을 입력으로 설계 산출물을 생성한다.

`services.design_svc.generate_design` 의 thin wrapper.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import design_svc


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


__all__ = ["DesignGeneratorAgent"]
