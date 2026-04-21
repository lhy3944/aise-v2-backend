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

    # final agent output
    final_answer: str | None
    sources: list[dict[str, Any]] | None
    # RequirementAgent output: candidate records pending approval.
    records_extracted: list[dict[str, Any]] | None

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
    "RoutingDecision",
]
