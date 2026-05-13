"""Supervisor — routes user input to one or more agents.

Phase 2 (DESIGN.md §5): LLM classifier emits a `RoutingDecision` with one
of `single` / `plan` / `clarify`. Two backends:

- **Tool Use** (default): LLM receives tool definitions and calls the
  appropriate tool. This is the preferred path — the LLM sees project
  context, tool descriptions, and conversation history, and decides
  which agent to invoke (or asks for clarification via plain text).

- **JSON** (legacy): LLM outputs a JSON object parsed into RoutingDecision.
  Used when SUPERVISOR_TOOL_USE_ENABLED=false.

Fallbacks:
- LLM raises or returns unexpected response → `clarify` with a generic
  "다시 한 번 말씀해주세요" message so the user sees something useful
  rather than an opaque 5xx.
- LLM picks a `single` action with an unregistered agent name → same
  fallback (prevents dead-ending the graph).
- Empty registry → the routing node short-circuits to `clarify` before
  calling the LLM (cheap sanity check).
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger
from pydantic import ValidationError

from src.agents.registry import list_capabilities, list_tool_definitions, try_get_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentState, RoutingDecision
from src.prompts.supervisor import build_supervisor_prompt, build_supervisor_system_prompt
from src.services import llm_svc
from src.services.llm_svc import CompletionResponse, ToolCallInfo
from src.utils.json_parser import parse_llm_json


SUPERVISOR_MODEL: str | None = None  # use llm_svc's default

_USE_TOOL_USE = os.getenv("SUPERVISOR_TOOL_USE_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)


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


# ── JSON-based routing (legacy) ──────────────────────────────────────────


async def _decide_with_json(state: AgentState) -> RoutingDecision:
    """Classify the user's latest message into one of 3 actions (JSON output)."""
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


# ── Tool Use-based routing ───────────────────────────────────────────────


def _tool_call_to_decision(tc: ToolCallInfo) -> RoutingDecision:
    """Convert a supervisor tool_call into a RoutingDecision."""
    from src.agents.registry import PLAN_TOOL_DEFINITION

    name = tc.name
    args = tc.arguments

    # Plan tool
    if name == "execute_plan":
        plan = args.get("plan") or []
        if not plan:
            return _fallback_clarify(
                "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
                reason="execute_plan with empty plan",
            )
        return RoutingDecision(
            action="plan",
            plan=plan,
            action_params=args,
            reasoning=f"tool_call: execute_plan({plan})",
        )

    # Single agent tool
    if try_get_agent(name) is None:
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason=f"supervisor picked unknown tool/agent {name!r}",
        )

    # Extract mode for requirement agent
    extract_mode = None
    if name == "requirement":
        em = args.get("extract_mode")
        if em in ("document", "user_text"):
            extract_mode = em
        else:
            extract_mode = "document"

    return RoutingDecision(
        action="single",
        agent=name,
        extract_mode=extract_mode,
        action_params=args,
        reasoning=f"tool_call: {name}({args})",
    )


def _text_response_to_decision(text: str) -> RoutingDecision:
    """LLM이 tool 없이 텍스트로 응답한 경우 — 질문이면 clarify, 아니면 general_chat."""
    stripped = text.rstrip()
    is_question = stripped.endswith("?") or stripped.endswith("?")
    if is_question:
        return RoutingDecision(
            action="clarify",
            clarification=text,
            reasoning="supervisor text response is a question",
        )
    return RoutingDecision(
        action="single",
        agent="general_chat",
        reasoning="supervisor text response, no tool call",
    )


async def _decide_with_tools(state: AgentState) -> RoutingDecision:
    """Classify the user's latest message using tool-calling."""
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

    # 1. 프로젝트 상태 스냅샷과 RAG 신호
    snapshot = state.get("project_context")
    rag_signal = state.get("rag_signal")

    # 2. Tool definitions + 프롬프트 구성
    from src.agents.registry import PLAN_TOOL_DEFINITION

    tools = list_tool_definitions()
    tools.append(PLAN_TOOL_DEFINITION)

    system_prompt = build_supervisor_system_prompt(
        user_input=user_input,
        snapshot=snapshot,
        rag_signal=rag_signal,
        history=state.get("history") or [],
    )

    # 3. LLM 호출 (tool-calling)
    try:
        response: CompletionResponse = await llm_svc.chat_completion_with_tools(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            tools=tools,
            tool_choice="auto",
            model=SUPERVISOR_MODEL,
            temperature=0.0,
            max_completion_tokens=512,
        )
    except AppException:
        raise
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("supervisor tool-use LLM call failed")
        return _fallback_clarify(
            "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
            reason=f"llm failure: {exc!r}",
        )

    # 4. 응답 분기
    if response.tool_calls:
        decision = _tool_call_to_decision(response.tool_calls[0])
        logger.debug(f"Supervisor tool-use decision: {decision.model_dump()}")
        return decision

    # tool_calls 없음 → 텍스트 응답 (clarify 또는 general_chat)
    if response.content:
        decision = _text_response_to_decision(response.content)
        logger.debug(f"Supervisor text decision: {decision.model_dump()}")
        return decision

    return _fallback_clarify(
        "요청을 이해하지 못했습니다. 다시 말씀해주세요.",
        reason="supervisor returned empty response with no tool call",
    )


# ── Public API ───────────────────────────────────────────────────────────


async def decide(state: AgentState) -> RoutingDecision:
    """Classify the user's latest message into one of 3 actions."""
    if _USE_TOOL_USE:
        return await _decide_with_tools(state)
    return await _decide_with_json(state)


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
