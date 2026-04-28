"""HITL interrupt + resume 인프라 단위 테스트 (Phase 3 PR-1).

mock 에이전트가 interrupt 이벤트를 발행하는 시나리오를 통해 다음을 검증:
  1. run_chat 가 InterruptEvent 와 done(finish_reason="interrupt") 를 발행하고
     hitl_state_svc 에 컨텍스트가 저장된다.
  2. resume_chat 이 같은 thread_id 로 저장된 컨텍스트를 복구하고, 같은
     에이전트의 run_stream 을 재호출하여 정상 종료(SSE done(stop))까지 흘려준다.

DB 연결 / Supervisor LLM 은 모두 mock 처리하여 hermetic 하게 동작한다.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

import pytest

from src.agents import list_agents, load_builtin_agents
from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import _REGISTRY, register_agent
from src.orchestration.graph import resume_chat, run_chat
from src.schemas.events import (
    ClarifyData,
    DoneEvent,
    InterruptEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from src.services import hitl_state_svc, llm_svc


_AGENT_NAME = "hitl_test_agent"
_INTERRUPT_ID = "itp_test_001"


class _HitlTestAgent(BaseAgent):
    """interrupt → resume 라운드트립을 검증하는 mock 에이전트.

    state["hitl_response"] 가 없으면 interrupt 발행으로 종료.
    있으면 사용자 응답을 echo 한 token + final 로 정상 종료.
    """

    capability = AgentCapability(
        name=_AGENT_NAME,
        description="HITL test agent",
        triggers=[],
        requires_hitl=True,
        expose_as_tool=True,
    )

    async def run(self, state, ctx):  # pragma: no cover — run_stream override
        return {}

    async def run_stream(self, state, ctx):
        response = state.get("hitl_response")
        if response is None:
            yield {
                "kind": "interrupt",
                "data": ClarifyData(
                    interrupt_id=_INTERRUPT_ID,
                    question="approve?",
                    allow_custom=False,
                ),
            }
            return
        answer = f"resumed:{response.get('value', '')}"
        yield {"kind": "token", "text": answer}
        yield {"kind": "final", "update": {"final_answer": answer}}


@pytest.fixture(autouse=True)
def _hitl_state_isolation():
    hitl_state_svc.reset()
    yield
    hitl_state_svc.reset()


@pytest.fixture(autouse=True)
def _register_test_agent():
    if not list_agents():
        load_builtin_agents(force_reload=True)
    register_agent(_HitlTestAgent)
    yield
    _REGISTRY.pop(_AGENT_NAME, None)


@pytest.fixture
def fake_session_factory():
    """session_factory 호출이 인터럽트 경로에서는 DB 를 만지지 않도록 stub."""

    @asynccontextmanager
    async def _ctx():
        yield None  # _drive_agent_stream 의 ctx.db 는 사용되지 않음

    def _factory():
        return _ctx()

    return _factory


@pytest.fixture(autouse=True)
def _stub_supervisor(monkeypatch):
    """Supervisor LLM 호출을 mock — 우리 _AGENT_NAME 으로 single 라우팅."""
    monkeypatch.setenv("RAG_GATE_ENABLED", "false")
    routing_payload = json.dumps(
        {
            "action": "single",
            "agent": _AGENT_NAME,
            "plan": None,
            "clarification": None,
            "reasoning": "stub",
        }
    )

    async def fake_chat_completion(messages, **kwargs):
        return routing_payload

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)


@pytest.mark.asyncio
async def test_run_chat_emits_interrupt_and_saves_state(fake_session_factory):
    project_id = uuid.uuid4()
    session_id = uuid.uuid4()

    events: list[Any] = []
    async for ev in run_chat(
        graph=None,
        project_id=project_id,
        session_id=session_id,
        user_input="hello",
        history=[],
        session_factory=fake_session_factory,
    ):
        events.append(ev)

    # InterruptEvent 가 있어야 함
    interrupts = [e for e in events if isinstance(e, InterruptEvent)]
    assert len(interrupts) == 1
    assert interrupts[0].data.interrupt_id == _INTERRUPT_ID
    assert interrupts[0].data.kind == "clarify"

    # 종료는 done(finish_reason="interrupt")
    dones = [e for e in events if isinstance(e, DoneEvent)]
    assert len(dones) == 1
    assert dones[0].data.finish_reason == "interrupt"

    # tool_call 은 발행되지만 tool_result 는 발행되지 않아야 함
    tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_calls) == 1
    assert len(tool_results) == 0

    # hitl_state 가 thread_id 로 저장됨
    saved = hitl_state_svc.get(_INTERRUPT_ID)
    assert saved is not None
    assert saved.selected_agent == _AGENT_NAME
    assert saved.interrupt_kind == "clarify"
    assert saved.session_id == str(session_id)
    assert saved.project_id == str(project_id)


@pytest.mark.asyncio
async def test_resume_chat_restores_state_and_completes(fake_session_factory):
    project_id = uuid.uuid4()
    session_id = uuid.uuid4()

    # 1차: interrupt 발행으로 state 저장
    async for _ in run_chat(
        graph=None,
        project_id=project_id,
        session_id=session_id,
        user_input="hello",
        history=[],
        session_factory=fake_session_factory,
    ):
        pass

    assert hitl_state_svc.get(_INTERRUPT_ID) is not None

    # 2차: resume → 정상 종료
    events: list[Any] = []
    async for ev in resume_chat(
        _INTERRUPT_ID,
        {"value": "approve"},
        session_factory=fake_session_factory,
    ):
        events.append(ev)

    tokens = [e for e in events if isinstance(e, TokenEvent)]
    assert len(tokens) == 1
    assert tokens[0].data.text == "resumed:approve"

    dones = [e for e in events if isinstance(e, DoneEvent)]
    assert len(dones) == 1
    assert dones[0].data.finish_reason == "stop"

    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].data.status == "success"

    # 정상 종료 후 hitl_state 는 삭제돼야 함
    assert hitl_state_svc.get(_INTERRUPT_ID) is None


@pytest.mark.asyncio
async def test_resume_with_unknown_thread_id_emits_error(fake_session_factory):
    events: list[Any] = []
    async for ev in resume_chat(
        "itp_does_not_exist",
        {"value": "x"},
        session_factory=fake_session_factory,
    ):
        events.append(ev)

    assert any(getattr(e, "type", None) == "error" for e in events)


def test_hitl_state_ttl_expiration():
    from datetime import datetime, timedelta, timezone

    state = hitl_state_svc.HitlState(
        thread_id="itp_ttl",
        session_id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        user_input="x",
        selected_agent=_AGENT_NAME,
        interrupt_id="itp_ttl",
        interrupt_kind="clarify",
    )
    # 25시간 전으로 인위적 backdating
    state.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    hitl_state_svc.save(state)
    assert hitl_state_svc.get("itp_ttl") is None
