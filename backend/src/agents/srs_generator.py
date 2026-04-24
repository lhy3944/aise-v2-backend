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

from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import srs_svc


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


__all__ = ["SrsGeneratorAgent"]
