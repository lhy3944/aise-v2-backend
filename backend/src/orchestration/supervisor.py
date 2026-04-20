"""Supervisor — routes user input to one or more agents.

Phase 1: hardcoded single-action router that always picks `knowledge_qa`
when the agent is registered, else returns an error. This keeps the
LangGraph wiring exercise-able end to end without depending on LLM.

Phase 2 will replace `decide()` with a hybrid (embedding top-k filter +
LLM judge) per DESIGN.md §5.3.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents.registry import try_get_agent
from src.orchestration.state import AgentState, RoutingDecision

DEFAULT_AGENT = "knowledge_qa"


def decide(state: AgentState) -> RoutingDecision:
    """Phase 1 stub: route everything to the default agent if registered."""
    if try_get_agent(DEFAULT_AGENT) is None:
        return RoutingDecision(
            action="clarify",
            clarification=f"기본 에이전트 '{DEFAULT_AGENT}'가 등록되지 않았습니다.",
            reasoning="default agent missing in registry",
        )
    return RoutingDecision(
        action="single",
        agent=DEFAULT_AGENT,
        reasoning="phase 1 default routing",
    )


async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node — runs `decide()` and writes the result into state."""
    decision = decide(state)
    logger.debug(f"Supervisor decision: {decision.model_dump()}")
    return {"routing": decision.model_dump()}


def route_after_supervisor(state: AgentState) -> str:
    """Conditional edge target name. Returns the next node id.

    Phase 1 supports `single` only. `plan` and `clarify` short-circuit to END;
    Phase 2/3 will wire them to dedicated nodes.
    """
    routing = state.get("routing") or {}
    action = routing.get("action")
    if action == "single":
        agent = routing.get("agent")
        if agent and try_get_agent(agent) is not None:
            return agent
    # Phase 1: anything else terminates. Future: planner / clarify nodes.
    return "end"


__all__ = ["DEFAULT_AGENT", "decide", "route_after_supervisor", "supervisor_node"]
