"""Supervisor — routes user input to one or more agents.

Phase 2 (DESIGN.md §5): LLM classifier emits a `RoutingDecision` with one
of `single` / `plan` / `clarify`. We call `llm_svc.chat_completion` with a
small deterministic prompt (`prompts/supervisor.md`) and validate the
returned JSON into `RoutingDecision`.

Fallbacks:
- LLM raises or returns unparseable JSON → `clarify` with a generic
  "다시 한 번 말씀해주세요" message so the user sees something useful
  rather than an opaque 5xx.
- LLM picks a `single` action with an unregistered agent name → same
  fallback (prevents dead-ending the graph).
- Empty registry → the routing node short-circuits to `clarify` before
  calling the LLM (cheap sanity check).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from pydantic import ValidationError

from src.agents.registry import list_capabilities, try_get_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentState, RoutingDecision
from src.prompts.supervisor import build_supervisor_prompt
from src.services import llm_svc
from src.utils.json_parser import parse_llm_json


SUPERVISOR_MODEL: str | None = None  # use llm_svc's default


def _fallback_clarify(message: str, *, reason: str) -> RoutingDecision:
    return RoutingDecision(
        action="clarify",
        clarification=message,
        reasoning=reason,
    )


def _validate_decision(payload: dict[str, Any]) -> RoutingDecision:
    """Turn the LLM's JSON into a RoutingDecision and sanity-check it."""
    decision = RoutingDecision.model_validate(payload)

    if decision.action == "single":
        if not decision.agent or try_get_agent(decision.agent) is None:
            raise ValueError(
                f"supervisor picked unknown agent {decision.agent!r}"
            )
    elif decision.action == "plan":
        if not decision.plan:
            raise ValueError("supervisor returned action=plan with empty plan")
        for name in decision.plan:
            if try_get_agent(name) is None:
                raise ValueError(f"supervisor plan names unknown agent {name!r}")
    elif decision.action == "clarify":
        if not decision.clarification:
            raise ValueError(
                "supervisor returned action=clarify without a clarification question"
            )

    return decision


async def decide(state: AgentState) -> RoutingDecision:
    """Classify the user's latest message into one of 3 actions."""
    capabilities = list_capabilities()
    if not capabilities:
        return _fallback_clarify(
            "현재 사용 가능한 에이전트가 없습니다. 시스템 관리자에게 문의해주세요.",
            reason="agent registry is empty",
        )

    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return _fallback_clarify(
            "질문을 입력해주세요.",
            reason="empty user_input",
        )

    prompt = build_supervisor_prompt(
        user_input=user_input,
        capabilities=capabilities,
        history=state.get("history") or [],
    )

    try:
        raw = await llm_svc.chat_completion(
            messages=[
                {"role": "system", "content": "You only output one JSON object."},
                {"role": "user", "content": prompt},
            ],
            model=SUPERVISOR_MODEL,
            temperature=0.0,
            max_completion_tokens=512,
        )
    except AppException:
        raise
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("supervisor LLM call failed")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason=f"llm failure: {exc!r}",
        )

    try:
        payload = parse_llm_json(raw, error_msg="supervisor JSON parse failed")
    except AppException:
        logger.warning(f"supervisor JSON parse failed, raw={raw[:200]!r}")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason="unparseable supervisor JSON",
        )

    try:
        return _validate_decision(payload)
    except (ValidationError, ValueError) as exc:
        logger.warning(f"supervisor decision invalid: {exc}; payload={payload!r}")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason=f"invalid decision: {exc}",
        )


async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node — runs `decide()` and writes the result into state."""
    decision = await decide(state)
    logger.debug(f"Supervisor decision: {decision.model_dump()}")
    return {"routing": decision.model_dump()}


def route_after_supervisor(state: AgentState) -> str:
    """Conditional edge target name. Returns the next node id.

    `single` → the selected agent node.
    `plan` → "planner" (wired by graph.py only when a planner node is
             registered; Phase 2 increment 2 adds it). Until then the
             graph maps "planner" to END so the chat terminates cleanly.
    `clarify` → END (Phase 2: run_chat surfaces the clarification as a
                regular `token` event; Phase 3 upgrades this to an HITL
                interrupt).
    """
    routing = state.get("routing") or {}
    action = routing.get("action")
    if action == "single":
        agent = routing.get("agent")
        if agent and try_get_agent(agent) is not None:
            return agent
    if action == "plan":
        return "planner"
    return "end"


__all__ = ["decide", "route_after_supervisor", "supervisor_node"]
