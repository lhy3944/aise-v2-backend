"""DataModelGeneratorAgent — 프로젝트의 SRS + 시스템 모델을 입력으로 데이터 모델 산출물을 생성한다.

`services.data_model_svc.generate_data_model` 의 thin wrapper.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import data_model_svc


@register_agent
class DataModelGeneratorAgent(BaseAgent):
    capability = AgentCapability(
        name="data_model_generator",
        description=(
            "프로젝트의 완료된 SRS 문서와 시스템 모델을 기반으로 데이터 모델"
            "(Conceptual Data Model, Logical Data Model, Physical Data Model) "
            "산출물을 생성한다. 사용자가 '데이터 모델 생성', 'ERD 작성', "
            "'데이터베이스 설계' 등 **명시적으로** 데이터 모델을 요청할 때만 선택한다."
        ),
        triggers=[
            "데이터 모델 생성해줘",
            "ERD 작성해줘",
            "데이터베이스 설계해줘",
            "데이터 모델링",
        ],
        input_schema={"project_id": "str"},
        output_schema={
            "final_answer": "str",
            "data_model_generated": "dict",
        },
        tags=["generation", "design", "artifact"],
        estimated_tokens=10000,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        logger.info(f"DataModelGeneratorAgent run: project={ctx.project_id}")

        try:
            response = await data_model_svc.generate_data_model(ctx.db, ctx.project_id)
        except AppException as exc:
            logger.warning(f"DataModelGeneratorAgent: rejected: {exc.detail}")
            return {"error": exc.detail}

        based_on = response.based_on_srs if isinstance(response.based_on_srs, dict) else {}
        srs_v = based_on.get("version_number")
        srs_v_text = f", SRS v{srs_v} 기반" if srs_v else ""
        summary = (
            f"DATA_MODEL v{response.version} 생성 완료 · "
            f"{len(response.sections)}개 섹션{srs_v_text}."
        )
        return {
            "final_answer": summary,
            "data_model_generated": {
                "data_model_id": response.data_model_id,
                "artifact_id": response.artifact_id,
                "version": response.version,
                "section_count": len(response.sections),
                "based_on_srs_version": srs_v,
            },
        }


__all__ = ["DataModelGeneratorAgent"]
