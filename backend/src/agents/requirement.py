"""RequirementAgent — extracts candidate requirement records from a
project's active knowledge documents.

Thin wrapper around `services.artifact_record_svc.extract_records`; the
heavy lifting (section/glossary context assembly, LLM call, JSON parsing)
lives there and is reused as-is.

Output contract (partial state update):
    - `final_answer`: short human-readable summary (count + section mix)
    - `records_extracted`: list[dict] of candidate records (each matches
      RecordExtractedItem.model_dump()). Consumed later by the UI
      (N1 AgentInvocationCard → opens a Records preview) and by the
      `plan` executor when chained into a longer workflow.
    - `error`: set if the project has no active sections/documents —
      lets run_chat surface a clean AGENT_ERROR rather than a 5xx.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import artifact_record_svc


def _section_histogram(candidates: list[dict[str, Any]]) -> str:
    counts: Counter[str] = Counter()
    for cand in candidates:
        counts[cand.get("section_name") or "(미분류)"] += 1
    return ", ".join(f"{name}({n})" for name, n in counts.most_common())


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
        },
        tags=["extraction", "records"],
        estimated_tokens=6000,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        logger.info(
            f"RequirementAgent run: project={ctx.project_id}"
        )

        try:
            response = await artifact_record_svc.extract_records(ctx.db, ctx.project_id)
        except AppException as exc:
            logger.warning(f"RequirementAgent: artifact_record_svc rejected: {exc.detail}")
            return {"error": exc.detail}

        candidates = [c.model_dump() for c in response.candidates]
        if not candidates:
            return {
                "final_answer": "추출된 요구사항 후보가 없습니다. 지식 문서와 활성 섹션 설정을 확인해주세요.",
                "records_extracted": [],
            }

        summary = (
            f"{len(candidates)}개의 요구사항 후보를 추출했습니다. "
            f"섹션 분포: {_section_histogram(candidates)}."
        )
        return {
            "final_answer": summary,
            "records_extracted": candidates,
        }


__all__ = ["RequirementAgent"]
