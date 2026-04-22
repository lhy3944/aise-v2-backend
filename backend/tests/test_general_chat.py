"""GeneralChatAgent — small-talk fallback agent tests.

Two surfaces:
1. Unit: run_stream consumes llm_svc.chat_completion_stream and emits
   the contract (token × N → final) with no sources.
2. E2E: supervisor routes greetings/capability questions to general_chat
   via the registry-driven prompt, and run_chat streams the result.

LLM + embeddings are stubbed so tests are hermetic.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.agents import list_agents, load_builtin_agents
from src.agents.registry import get_agent
from src.models.project import Project
from src.orchestration.graph import build_graph, run_chat
from src.orchestration.state import AgentContext
from src.schemas.events import (
    DoneEvent,
    SourcesEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from src.services import embedding_svc, llm_svc


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents():
        load_builtin_agents(force_reload=True)
    yield


def _install_stream_stub(monkeypatch, *, answer: str):
    """Split the canned answer into 3 deltas so streaming is observable."""

    async def fake_chat_completion_stream(messages, **kwargs):
        third = max(1, len(answer) // 3)
        yield answer[:third]
        yield answer[third : third * 2]
        yield answer[third * 2 :]

    monkeypatch.setattr(llm_svc, "chat_completion_stream", fake_chat_completion_stream)


@pytest.mark.asyncio
async def test_run_stream_emits_tokens_and_final(monkeypatch, db):
    """Unit: run_stream chunks come through as token events + terminal final."""
    canned = "안녕하세요! 요구사항 정의를 도와드리는 AI예요."
    _install_stream_stub(monkeypatch, answer=canned)

    project = Project(name="gc-unit", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    agent = get_agent("general_chat")
    ctx = AgentContext(db=db, project_id=project.id, session_id=None)
    state = {
        "project_id": str(project.id),
        "session_id": None,
        "user_input": "안녕",
        "history": [],
    }

    events = [ev async for ev in agent.run_stream(state, ctx)]

    kinds = [e.get("kind") for e in events]
    # Stub emits 3 non-empty deltas → 3 token events; final is terminal.
    assert kinds == ["token", "token", "token", "final"]
    # Tokens reassemble to the canned answer.
    assembled = "".join(e["text"] for e in events if e["kind"] == "token")
    assert assembled == canned
    # No sources for general chat.
    assert not any(e.get("kind") == "sources" for e in events)
    final_update = events[-1]["update"]
    assert final_update["final_answer"] == canned
    assert "sources" not in final_update


@pytest.mark.asyncio
async def test_supervisor_routes_greeting_to_general_chat(monkeypatch, db):
    """E2E: supervisor picks general_chat; run_chat streams tokens."""
    canned = "안녕하세요. 무엇을 도와드릴까요?"

    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    async def fake_chat_completion(messages, **kwargs):
        # Supervisor routing prompt: return a JSON pointing at general_chat.
        last = messages[-1].get("content", "") if messages else ""
        if "## Decision policy" in last and "## Available agents" in last:
            return json.dumps(
                {
                    "action": "single",
                    "agent": "general_chat",
                    "plan": None,
                    "clarification": None,
                    "reasoning": "greeting",
                }
            )
        return canned  # not used by streaming path, defensive default

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    _install_stream_stub(monkeypatch, answer=canned)

    project = Project(name="gc-e2e", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events = [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input="안녕하세요",
            session_factory=session_factory,
        )
    ]

    types = [type(e).__name__ for e in events]
    # general_chat declares expose_as_tool=False — no tool_call/tool_result,
    # no sources. Just token stream + done.
    assert types == ["TokenEvent", "TokenEvent", "TokenEvent", "DoneEvent"]
    assert "ToolCallEvent" not in types
    assert "ToolResultEvent" not in types
    assert "SourcesEvent" not in types

    assembled = "".join(
        e.data.text for e in events if isinstance(e, TokenEvent)
    )
    assert assembled == canned


@pytest.mark.asyncio
async def test_run_stream_error_produces_final_error(monkeypatch, db):
    """LLM stream failure surfaces as `{'error': ...}` in the final event."""

    async def fake_stream(messages, **kwargs):
        raise RuntimeError("upstream boom")
        yield  # pragma: no cover — unreachable, keeps this an async generator

    monkeypatch.setattr(llm_svc, "chat_completion_stream", fake_stream)

    project = Project(name="gc-err", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    agent = get_agent("general_chat")
    ctx = AgentContext(db=db, project_id=project.id, session_id=None)
    state = {
        "project_id": str(project.id),
        "session_id": None,
        "user_input": "안녕",
        "history": [],
    }

    events = [ev async for ev in agent.run_stream(state, ctx)]
    # Defensive path: single terminal `final` with an error message.
    assert len(events) == 1
    assert events[0]["kind"] == "final"
    assert "error" in events[0]["update"]


# Silence unused-import warnings when these symbols aren't referenced in every
# test above (they document the canonical contract surface).
_ = (DoneEvent, SourcesEvent)
