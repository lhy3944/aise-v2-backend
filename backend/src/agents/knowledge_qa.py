"""KnowledgeQAAgent — RAG-based Q&A over project knowledge documents.

Wraps the existing `services.rag_svc.chat()` pipeline (search → context →
LLM) and exposes it through the BaseAgent contract.

Project isolation is enforced inside `rag_svc.search_similar_chunks` (P0
fix); this agent only forwards `ctx.project_id`.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.orchestration.state import AgentContext, AgentState
from src.services import rag_svc


@register_agent
class KnowledgeQAAgent(BaseAgent):
    capability = AgentCapability(
        name="knowledge_qa",
        description=(
            "프로젝트 지식 저장소(업로드된 문서, 청크, 용어집)에서 정보를 검색하여 "
            "사용자 질문에 답변한다. 단일 턴 질의응답에 적합."
        ),
        triggers=[
            "~이 뭐야",
            "~에 대해 알려줘",
            "~문서 찾아줘",
            "프로젝트 내 ~ 정보를 요약해줘",
        ],
        input_schema={"user_input": "str", "project_id": "str"},
        output_schema={"final_answer": "str", "sources": "list"},
        tags=["rag", "qa"],
        estimated_tokens=2500,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        query = state.get("user_input", "")
        if not query:
            return {"error": "user_input is required for knowledge_qa"}

        logger.info(
            f"KnowledgeQAAgent run: project={ctx.project_id} query={query[:60]!r}"
        )

        response = await rag_svc.chat(
            project_id=ctx.project_id,
            message=query,
            history=state.get("history", []) or [],
            top_k=5,
            db=ctx.db,
        )

        sources = [s.model_dump() for s in response.sources]
        return {"final_answer": response.answer, "sources": sources}


__all__ = ["KnowledgeQAAgent"]
