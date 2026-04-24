"""KnowledgeQAAgent — RAG-based Q&A over project knowledge documents.

`run_stream` is the hot path: it splits retrieval (`rag_svc.search_and_prepare`)
from generation (`llm_svc.chat_completion_stream`) so that sources can be
emitted immediately and tokens flow through to the SSE stream as they
arrive. `run()` stays for non-streaming callers and unit tests — internally
it drains `run_stream`.

Project isolation is enforced inside `rag_svc.search_similar_chunks` (P0
fix); this agent only forwards `ctx.project_id`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import llm_svc, rag_svc


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
        """Non-streaming convenience wrapper — drains `run_stream`."""
        final: dict[str, Any] = {}
        async for ev in self.run_stream(state, ctx):
            if ev.get("kind") == "final":
                final = ev.get("update", {}) or {}
        return final

    async def run_stream(
        self, state: AgentState, ctx: AgentContext
    ) -> AsyncGenerator[dict[str, Any], None]:
        query = state.get("user_input", "")
        if not query:
            yield {
                "kind": "final",
                "update": {"error": "user_input is required for knowledge_qa"},
            }
            return

        # Retrieval-first gate가 앞서 계산한 결과를 재사용한다. 캐시에는 임베딩
        # 벡터와 standalone query만 들어있고, pgvector 검색은 이 함수에서 한 번
        # 더 수행하지만 임베딩 API call은 건너뛴다.
        rag_cache = state.get("rag_cache") or {}
        cached_embedding = rag_cache.get("query_embedding")
        rewritten_query = rag_cache.get("rewritten_query")

        logger.info(
            f"KnowledgeQAAgent run_stream: project={ctx.project_id} "
            f"query={query[:60]!r} cache={'hit' if cached_embedding else 'miss'}"
        )

        try:
            messages, sources = await rag_svc.search_and_prepare(
                project_id=ctx.project_id,
                message=query,
                history=state.get("history", []) or [],
                top_k=5,
                db=ctx.db,
                query_embedding=cached_embedding,
                rewritten_query=rewritten_query,
            )
        except AppException as exc:
            yield {"kind": "final", "update": {"error": str(exc.detail)}}
            return

        source_dicts = [s.model_dump() for s in sources]
        if source_dicts:
            yield {"kind": "sources", "sources": source_dicts}

        buffer = ""
        try:
            async for delta in llm_svc.chat_completion_stream(
                messages,
                client_type="srs",
                temperature=0.3,
                max_completion_tokens=2048,
            ):
                if not delta:
                    continue
                buffer += delta
                yield {"kind": "token", "text": delta}
        except AppException as exc:
            yield {
                "kind": "final",
                "update": {"error": str(exc.detail), "sources": source_dicts},
            }
            return
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("KnowledgeQAAgent LLM stream failed")
            yield {
                "kind": "final",
                "update": {
                    "error": "AI 응답 생성에 실패했습니다.",
                    "sources": source_dicts,
                },
            }
            return

        yield {
            "kind": "final",
            "update": {"final_answer": buffer, "sources": source_dicts},
        }


__all__ = ["KnowledgeQAAgent"]
