"""Shared state and context types for the LangGraph orchestrator.

`AgentState` is the LangGraph state — TypedDict, must be JSON-serializable
(it is checkpointed via PostgresSaver in Phase 3+).

`AgentContext` carries runtime-only dependencies (DB session, current
project/session ids). It is built per-request by graph node closures and
NEVER stored in the LangGraph state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


RoutingAction = Literal["single", "plan", "clarify"]
ExtractMode = Literal["document", "user_text"]


class RoutingDecision(BaseModel):
    """Supervisor's routing output (DESIGN.md §5.1)."""

    action: RoutingAction
    agent: str | None = Field(
        default=None,
        description="Used when action == 'single'.",
    )
    plan: list[str] | None = Field(
        default=None,
        description="Sequence of agent names. Used when action == 'plan'. (Phase 2)",
    )
    clarification: str | None = Field(
        default=None,
        description="Question to ask the user. Used when action == 'clarify'. (Phase 3)",
    )
    extract_mode: ExtractMode | None = Field(
        default=None,
        description=(
            "RequirementAgent 라우팅 시 추출 모드를 명시. "
            "'document' = 활성 지식 문서에서 추출 (기존). "
            "'user_text' = user_input 자체를 추출 대상으로 사용 (자유 진술문). "
            "다른 에이전트 라우팅 시에는 None."
        ),
    )
    reasoning: str = Field(default="", description="Why this decision was made (debug/audit only)")


class AgentState(TypedDict, total=False):
    """LangGraph state for the agent chat graph.

    All fields are optional (`total=False`) so partial updates merge cleanly.
    Anything that must persist across an HITL `interrupt()` MUST live here.
    """

    # input
    project_id: str  # UUID as str (TypedDict friendliness)
    session_id: str | None  # = LangGraph thread_id
    user_input: str
    history: list[dict[str, Any]]

    # supervisor output
    routing: dict[str, Any] | None  # serialized RoutingDecision

    # agent intermediate
    rag_chunks: list[dict[str, Any]] | None
    # Retrieval-first gate가 임베딩·검색을 선행 수행한 결과를 KnowledgeQA가
    # 재사용하기 위한 캐시. gate가 작동하지 않은 경로에서는 None.
    # {
    #   "rewritten_query": str,             # query rewriter가 반환한 standalone 질의
    #   "query_embedding": list[float],     # 위 query의 임베딩
    #   "chunks": list[dict],               # [{chunk_id, document_id, chunk_index, content, score}, ...]
    #   "max_score": float,
    # }
    rag_cache: dict[str, Any] | None

    # final agent output
    final_answer: str | None
    sources: list[dict[str, Any]] | None
    # RequirementAgent output: candidate records pending approval.
    records_extracted: list[dict[str, Any]] | None
    # SrsGeneratorAgent output: {srs_id, version, section_count,
    # based_on_records_count}
    srs_generated: dict[str, Any] | None
    # TestCaseGeneratorAgent output: {based_on_srs_id, srs_version,
    # testcase_count, skipped_section_count}
    testcases_generated: dict[str, Any] | None
    # CriticAgent output: citation integrity + sanity checks
    # {
    #   "passed": bool,
    #   "issues": list[str],
    #   "checked_citations": int,
    #   "valid_citations": int,
    # }
    critic_report: dict[str, Any] | None

    # error / control
    error: str | None


@dataclass
class AgentContext:
    """Per-request runtime dependencies. Built by node closures.

    DO NOT add fields that need to persist across an interrupt — those go
    into AgentState above.
    """

    db: AsyncSession
    project_id: uuid.UUID
    session_id: uuid.UUID | None = None


__all__ = [
    "AgentContext",
    "AgentState",
    "RoutingAction",
    "ExtractMode",
    "RoutingDecision",
]
