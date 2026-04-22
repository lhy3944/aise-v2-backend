"""GeneralChatAgent — 프로젝트 지식과 무관한 일반 대화를 처리.

인사, 자기소개, 능력 문의, 감사 표현처럼 "명확하지만 비-RAG"인 입력을
Supervisor가 여기로 라우팅한다. clarify 경로는 *진짜 모호한* 질문만
담당하도록 책임이 좁혀진다.

`run_stream`은 `llm_svc.chat_completion_stream`으로 토큰을 실시간 방출
하므로 RAG 답변과 동일한 스트리밍 UX를 공유한다. sources는 없으니
emit하지 않는다.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.prompts.general import build_general_chat_prompt
from src.services import llm_svc


@register_agent
class GeneralChatAgent(BaseAgent):
    capability = AgentCapability(
        name="general_chat",
        description=(
            "프로젝트 지식 저장소와 무관한 일반 대화(인사, 자기소개, 에이전트 능력 문의, "
            "감사 표현, 짧은 잡담)에 친근하고 간결하게 응답한다. 지식 질의가 아닌 '명확한 "
            "비-RAG 입력'의 기본 목적지."
        ),
        triggers=[
            "안녕",
            "안녕하세요",
            "반가워",
            "이름이 뭐야",
            "뭐 할 수 있어",
            "너는 뭐야",
            "도와줘",
            "고마워",
            "hi",
            "hello",
            "what can you do",
        ],
        input_schema={"user_input": "str"},
        output_schema={"final_answer": "str"},
        tags=["chat", "general"],
        estimated_tokens=400,
        # Conversational agent — the streamed answer IS the response.
        # Suppress tool_call/tool_result SSE so the UI doesn't render an
        # invocation card for small talk.
        expose_as_tool=False,
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
                "update": {"error": "user_input is required for general_chat"},
            }
            return

        logger.info(f"GeneralChatAgent run_stream: query={query[:60]!r}")

        messages = build_general_chat_prompt(
            query=query,
            history=state.get("history", []) or [],
        )

        buffer = ""
        try:
            async for delta in llm_svc.chat_completion_stream(
                messages,
                client_type="srs",
                temperature=0.5,
                max_completion_tokens=512,
            ):
                if not delta:
                    continue
                buffer += delta
                yield {"kind": "token", "text": delta}
        except AppException as exc:
            yield {"kind": "final", "update": {"error": str(exc.detail)}}
            return
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("GeneralChatAgent LLM stream failed")
            yield {
                "kind": "final",
                "update": {"error": "AI 응답 생성에 실패했습니다."},
            }
            return

        yield {"kind": "final", "update": {"final_answer": buffer}}


__all__ = ["GeneralChatAgent"]
