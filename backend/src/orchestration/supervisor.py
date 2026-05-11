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
import os
from typing import Any

from loguru import logger
from pydantic import ValidationError

from src.agents.registry import list_capabilities, list_tool_definitions, try_get_agent
from src.core.exceptions import AppException
from src.orchestration.context import format_snapshot_for_prompt
from src.orchestration.state import AgentState, RoutingDecision
from src.prompts.supervisor import build_supervisor_prompt, build_supervisor_tooluse_messages
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

    if decision.action == "general_chat":
        decision = decision.model_copy(update={"action": "single", "agent": "general_chat"})

    if decision.action == "single":
        if not decision.agent or try_get_agent(decision.agent) is None:
            raise ValueError(
                f"supervisor picked unknown agent {decision.agent!r}"
            )
        # RequirementAgent 라우팅 시 extract_mode 디폴트 — supervisor LLM 이
        # 누락하면 안전하게 'document' 모드로 (기존 동작 보존).
        if decision.agent == "requirement" and decision.extract_mode is None:
            decision = decision.model_copy(update={"extract_mode": "document"})
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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _confidence(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        value = float(value)
        if 0 <= value <= 1:
            return value
    return None


def _decision_from_tool_response(response: llm_svc.CompletionResponse) -> RoutingDecision:
    calls = response.tool_calls
    if not calls:
        content = (response.content or "").strip()
        if content.upper().startswith("CLARIFY:"):
            question = content.split(":", 1)[1].strip()
            if question:
                return RoutingDecision(
                    action="clarify",
                    clarification=question,
                    confidence=0.7,
                    reasoning="tool supervisor requested clarification",
                )
        if content:
            return RoutingDecision(
                action="clarify",
                clarification=content,
                confidence=0.5,
                reasoning="tool supervisor returned content without a tool call",
            )
        return _fallback_clarify(
            "조금 더 구체적으로 말씀해주시겠어요?",
            reason="tool supervisor returned no tool call and no content",
        )

    for call in calls:
        if try_get_agent(call.name) is None:
            raise ValueError(f"supervisor tool call names unknown agent {call.name!r}")

    if len(calls) == 1:
        call = calls[0]
        args = dict(call.arguments)
        extract_mode = args.get("extract_mode")
        if extract_mode not in ("document", "user_text"):
            extract_mode = None
        reasoning = str(
            args.get("reasoning")
            or args.get("intent")
            or call.arguments_error
            or "tool-use supervisor selected agent"
        )
        return RoutingDecision(
            action="single",
            agent=call.name,
            action_params=args,
            extract_mode=extract_mode,
            confidence=_confidence(args.get("confidence")),
            reasoning=reasoning,
        )

    return RoutingDecision(
        action="plan",
        plan=[call.name for call in calls],
        action_params={
            "tool_calls": [
                {
                    "agent": call.name,
                    "arguments": call.arguments,
                    "arguments_error": call.arguments_error,
                }
                for call in calls
            ]
        },
        confidence=min(
            (
                _confidence(call.arguments.get("confidence")) or 0.5
                for call in calls
            ),
            default=0.5,
        ),
        reasoning="tool-use supervisor selected a multi-agent plan",
    )


async def _decide_with_tools(state: AgentState) -> RoutingDecision:
    tools = list_tool_definitions()
    if not tools:
        return _fallback_clarify(
            "현재 사용 가능한 에이전트가 없습니다. 시스템 관리자에게 문의해주세요.",
            reason="agent registry is empty",
        )

    user_input = (state.get("user_input") or "").strip()
    snapshot = format_snapshot_for_prompt(state.get("project_snapshot"))
    messages = build_supervisor_tooluse_messages(
        user_input=user_input,
        snapshot=snapshot,
        rag_signal=state.get("rag_signal"),
    )
    response = await llm_svc.chat_completion_with_tools(
        messages=messages,
        tools=tools,
        tool_choice="auto",
        model=SUPERVISOR_MODEL,
        temperature=0.0,
        max_completion_tokens=768,
    )
    return _decision_from_tool_response(response)


async def _decide_with_json(state: AgentState) -> RoutingDecision:
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

    raw = await llm_svc.chat_completion(
        messages=[
            {"role": "system", "content": "You only output one JSON object."},
            {"role": "user", "content": prompt},
        ],
        model=SUPERVISOR_MODEL,
        temperature=0.0,
        max_completion_tokens=512,
    )

    try:
        payload = parse_llm_json(raw, error_msg="supervisor JSON parse failed")
    except AppException:
        logger.warning(f"supervisor JSON parse failed, raw={raw[:200]!r}")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason="unparseable supervisor JSON",
        )
    return _validate_decision(payload)


async def decide(state: AgentState) -> RoutingDecision:
    """Classify the user's latest message into one of 3 actions."""
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return _fallback_clarify(
            "질문을 입력해주세요.",
            reason="empty user_input",
        )

    try:
        if _env_bool("SUPERVISOR_TOOL_USE_ENABLED", True):
            return _validate_decision((await _decide_with_tools(state)).model_dump())
        return await _decide_with_json(state)
    except AppException:
        raise
    except (ValidationError, ValueError) as exc:
        logger.warning(f"supervisor tool decision invalid: {exc}")
        if _env_bool("SUPERVISOR_TOOL_USE_ENABLED", True):
            try:
                return await _decide_with_json(state)
            except AppException:
                raise
            except Exception:
                logger.exception("supervisor JSON fallback failed")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason=f"invalid decision: {exc}",
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("supervisor LLM call failed")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason=f"llm failure: {exc!r}",
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
    if action == "general_chat":
        return "general_chat"
    if action == "plan":
        return "planner"
    return "end"


__all__ = ["decide", "route_after_supervisor", "supervisor_node"]
