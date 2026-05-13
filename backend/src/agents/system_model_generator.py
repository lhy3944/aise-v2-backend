"""SystemModelGeneratorAgent — 프로젝트의 SRS 를 입력으로 시스템 모델 산출물을 생성한다.

`services.system_model_svc.generate_system_model` 의 thin wrapper.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import system_model_svc


@register_agent
class SystemModelGeneratorAgent(BaseAgent):
    capability = AgentCapability(
        name="system_model_generator",
        description=(
            "프로젝트의 완료된 SRS 문서를 기반으로 시스템 모델(Use Case Diagram, "
            "Use Case Specifications, Interaction Diagrams, System Conceptual Design) "
            "산출물을 생성한다. 사용자가 '시스템 모델 생성', '유스케이스 작성', "
            "'시퀀스 다이어그램' 등 **명시적으로** 시스템 모델을 요청할 때만 선택한다."
        ),
        triggers=[
            "시스템 모델 생성해줘",
            "유스케이스 작성해줘",
            "시퀀스 다이어그램 그려줘",
            "시스템 모델링",
        ],
        input_schema={"project_id": "str"},
        output_schema={
            "final_answer": "str",
            "system_model_generated": "dict",
        },
        tags=["generation", "design", "artifact"],
        estimated_tokens=10000,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        logger.info(f"SystemModelGeneratorAgent run: project={ctx.project_id}")

        try:
            response = await system_model_svc.generate_system_model(ctx.db, ctx.project_id)
        except AppException as exc:
            logger.warning(f"SystemModelGeneratorAgent: rejected: {exc.detail}")
            return {"error": exc.detail}

        based_on = response.based_on_srs if isinstance(response.based_on_srs, dict) else {}
        srs_v = based_on.get("version_number")
        srs_v_text = f", SRS v{srs_v} 기반" if srs_v else ""
        summary = (
            f"SYSTEM_MODEL v{response.version} 생성 완료 · "
            f"{len(response.sections)}개 섹션{srs_v_text}."
        )
        return {
            "final_answer": summary,
            "system_model_generated": {
                "system_model_id": response.system_model_id,
                "artifact_id": response.artifact_id,
                "version": response.version,
                "section_count": len(response.sections),
                "based_on_srs_version": srs_v,
            },
        }


__all__ = ["SystemModelGeneratorAgent"]
