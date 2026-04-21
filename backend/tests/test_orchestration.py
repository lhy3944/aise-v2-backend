"""End-to-end LangGraph orchestration test.

Verifies the Phase 1 path:
  START -> supervisor (single -> knowledge_qa) -> KnowledgeQAAgent -> END
  ... and that run_chat emits the contract'd SSE events in order.

LLM and embeddings are stubbed so the test is hermetic.
"""

from __future__ import annotations

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


@pytest.fixture
def stub_llm_and_embeddings(monkeypatch):
    async def fake_embeddings(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]

    async def fake_chat_completion(messages, **kwargs):
        return "Stubbed answer based on retrieved chunks."

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    # rag_svc imports chat_completion directly into its namespace.
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)


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
