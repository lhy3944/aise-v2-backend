"""End-to-end LangGraph orchestration test.

Verifies the Phase 1 path:
  START -> supervisor (single -> knowledge_qa) -> KnowledgeQAAgent -> END
  ... and that run_chat emits the contract'd SSE events in order.

LLM and embeddings are stubbed so the test is hermetic.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.agents import list_agents, load_builtin_agents
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.orchestration.graph import build_graph, run_chat
from src.schemas.events import (
    DoneEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from src.services import embedding_svc, llm_svc, rag_svc


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    """Force-reload registry — protects against earlier tests that called clear_registry()."""
    if not list_agents():
        load_builtin_agents(force_reload=True)
    yield


def _is_supervisor_prompt(messages: list[dict]) -> bool:
    """Detect the Supervisor's routing call by looking at the user prompt."""
    last = messages[-1].get("content", "") if messages else ""
    return "## Decision policy" in last and "## Available agents" in last


def _stub_llm(monkeypatch, *, supervisor_response: str | None = None):
    """Install a shared fake `chat_completion` that disambiguates callers.

    - If the prompt matches the Supervisor template, return the supplied
      `supervisor_response` (or a default `single`→`knowledge_qa` JSON).
    - Otherwise, return the canned RAG answer used by the happy-path test.

    We patch the module attribute once; Supervisor and rag_svc both import
    `llm_svc`, so a single patch covers both.
    """
    default_routing = json.dumps(
        {
            "action": "single",
            "agent": "knowledge_qa",
            "plan": None,
            "clarification": None,
            "reasoning": "stub: default single routing",
        }
    )
    routing_payload = supervisor_response if supervisor_response is not None else default_routing

    async def fake_chat_completion(messages, **kwargs):
        if _is_supervisor_prompt(messages):
            return routing_payload
        return "Stubbed answer based on retrieved chunks."

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)


@pytest.fixture
def stub_llm_and_embeddings(monkeypatch):
    async def fake_embeddings(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(monkeypatch)


async def _seed(db, *, project_name: str = "P") -> Project:
    project = Project(name=project_name, description="test")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    doc = KnowledgeDocument(
        project_id=project.id,
        name="seed.md",
        file_type="md",
        size_bytes=100,
        storage_key=f"{uuid.uuid4()}.md",
        status="completed",
        chunk_count=1,
        is_active=True,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    chunk = KnowledgeChunk(
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="hello world",
        token_count=2,
        embedding=[0.1] * 1536,
    )
    db.add(chunk)
    await db.commit()
    return project


async def test_run_chat_happy_path_emits_contract_events(stub_llm_and_embeddings, db):
    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events: list[Any] = []
    async for ev in run_chat(
        graph,
        project_id=project.id,
        session_id=uuid.uuid4(),
        user_input="What is in the docs?",
    ):
        events.append(ev)

    # Sequence must be: tool_call, tool_result, token, done
    types = [type(ev).__name__ for ev in events]
    assert types == ["ToolCallEvent", "ToolResultEvent", "TokenEvent", "DoneEvent"]

    tool_call: ToolCallEvent = events[0]
    tool_result: ToolResultEvent = events[1]
    token: TokenEvent = events[2]
    done: DoneEvent = events[3]

    assert tool_call.data.name == "knowledge_qa"
    assert tool_call.data.agent == "knowledge_qa"
    assert tool_result.data.tool_call_id == tool_call.data.tool_call_id
    assert tool_result.data.status == "success"
    assert token.data.text == "Stubbed answer based on retrieved chunks."
    assert done.data.finish_reason == "stop"


async def test_run_chat_invalid_project_id_emits_error(stub_llm_and_embeddings, db):
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events: list[Any] = []
    async for ev in run_chat(
        graph,
        project_id="not-a-uuid",
        session_id=uuid.uuid4(),
        user_input="anything",
    ):
        events.append(ev)

    assert len(events) == 1
    assert type(events[0]).__name__ == "ErrorEvent"
    assert "invalid project_id" in events[0].data.message


async def test_get_checkpointer_memory_by_default(monkeypatch):
    """D7: with no LANGGRAPH_CHECKPOINT_URL set, we get MemorySaver."""
    from langgraph.checkpoint.memory import MemorySaver

    from src.orchestration import graph as graph_module

    monkeypatch.delenv("LANGGRAPH_CHECKPOINT_URL", raising=False)
    checkpointer = await graph_module.get_checkpointer()
    assert isinstance(checkpointer, MemorySaver)


async def test_get_checkpointer_postgres_when_env_set(monkeypatch):
    """D7: env present → AsyncPostgresSaver branch is taken with the URL
    threaded through. Uses a stub to avoid opening a real psycopg pool
    that would outlive the test and interfere with the shared test DB."""
    from src.orchestration import graph as graph_module

    await graph_module.shutdown_checkpointer()
    called_with: dict[str, str] = {}

    class _StubSaver:
        pass

    async def _fake_init(url: str):
        called_with["url"] = url
        graph_module._pg_saver = _StubSaver()  # pretend we cached it
        return graph_module._pg_saver

    monkeypatch.setattr(graph_module, "_init_postgres_checkpointer", _fake_init)
    monkeypatch.setenv(
        "LANGGRAPH_CHECKPOINT_URL",
        "postgresql+asyncpg://aise:aise1234@localhost:5432/aise",
    )
    try:
        checkpointer = await graph_module.get_checkpointer()
        assert isinstance(checkpointer, _StubSaver)
        assert called_with["url"] == (
            "postgresql+asyncpg://aise:aise1234@localhost:5432/aise"
        )
    finally:
        graph_module._pg_saver = None
        graph_module._pg_pool = None


def test_normalise_checkpoint_url_strips_sqlalchemy_dialects():
    from src.orchestration.graph import _normalise_checkpoint_url

    cases = {
        "postgresql+asyncpg://u:p@h:5432/db": "postgresql://u:p@h:5432/db",
        "postgresql+psycopg://u:p@h/db": "postgresql://u:p@h/db",
        "postgresql+psycopg2://u:p@h/db": "postgresql://u:p@h/db",
        "postgresql://u:p@h/db": "postgresql://u:p@h/db",
    }
    for raw, expected in cases.items():
        assert _normalise_checkpoint_url(raw) == expected


# ---------- Supervisor routing (Phase 2 increment 1A) ----------


async def test_supervisor_single_routes_to_agent(monkeypatch, db):
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(
        monkeypatch,
        supervisor_response=json.dumps(
            {
                "action": "single",
                "agent": "knowledge_qa",
                "plan": None,
                "clarification": None,
                "reasoning": "stub",
            }
        ),
    )

    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events = [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input="이 프로젝트의 문서 요약 좀 해줘",
        )
    ]
    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "ToolResultEvent", "TokenEvent", "DoneEvent"]


async def test_supervisor_clarify_emits_question_as_token(monkeypatch, db):
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(
        monkeypatch,
        supervisor_response=json.dumps(
            {
                "action": "clarify",
                "agent": None,
                "plan": None,
                "clarification": "구체적으로 어떤 기능에 대한 질문인지 알려주세요.",
                "reasoning": "ambiguous",
            }
        ),
    )

    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events = [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input="저거 좀",
        )
    ]
    types = [type(e).__name__ for e in events]
    assert types == ["TokenEvent", "DoneEvent"]
    assert "구체적으로" in events[0].data.text


async def test_supervisor_plan_emits_placeholder_until_planner_wired(monkeypatch, db):
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(
        monkeypatch,
        supervisor_response=json.dumps(
            {
                "action": "plan",
                "agent": None,
                "plan": ["knowledge_qa"],
                "clarification": None,
                "reasoning": "stub plan",
            }
        ),
    )

    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events = [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input="뭐 여러 단계짜리 작업 해줘",
        )
    ]
    types = [type(e).__name__ for e in events]
    assert types == ["TokenEvent", "DoneEvent"]
    assert "아직 준비 중" in events[0].data.text


async def test_supervisor_invalid_json_falls_back_to_clarify(monkeypatch, db):
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(
        monkeypatch,
        supervisor_response="this is not JSON at all",
    )

    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events = [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input="뭐든",
        )
    ]
    types = [type(e).__name__ for e in events]
    assert types == ["TokenEvent", "DoneEvent"]
    # Fallback clarification message includes "다시 말씀해주세요".
    assert "다시 말씀" in events[0].data.text


async def test_supervisor_unknown_agent_falls_back_to_clarify(monkeypatch, db):
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(
        monkeypatch,
        supervisor_response=json.dumps(
            {
                "action": "single",
                "agent": "nonexistent_agent",
                "plan": None,
                "clarification": None,
                "reasoning": "stub",
            }
        ),
    )

    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    events = [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input="아무거나",
        )
    ]
    types = [type(e).__name__ for e in events]
    assert types == ["TokenEvent", "DoneEvent"]
    assert "다시 말씀" in events[0].data.text
