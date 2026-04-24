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
    SourcesEvent,
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


_STUB_RAG_ANSWER = "Stubbed answer based on retrieved chunks."


def _stub_llm(monkeypatch, *, supervisor_response: str | None = None):
    """Install fakes for both non-streaming and streaming LLM calls.

    - `chat_completion` handles the Supervisor routing prompt (single call)
      and the non-streaming `rag_svc.chat()` HTTP path (if a test hits it).
    - `chat_completion_stream` is what `KnowledgeQAAgent.run_stream` uses;
      we chunk the canned answer into two deltas so tests see ≥2
      `TokenEvent`s and exercise real streaming ordering.

    Supervisor and rag_svc/knowledge_qa all import `llm_svc` as a module,
    so a single `setattr` on the module covers all call sites.

    Also disables the retrieval-first gate so tests that exercise
    supervisor routing semantics (clarify / plan / invalid JSON / unknown
    agent) see the supervisor LLM decision instead of the gate short-
    circuiting to knowledge_qa. Gate-specific tests re-enable the env var.
    """
    monkeypatch.setenv("RAG_GATE_ENABLED", "false")
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
        return _STUB_RAG_ANSWER

    async def fake_chat_completion_stream(messages, **kwargs):
        # Split into two deltas so tests can observe streaming.
        half = len(_STUB_RAG_ANSWER) // 2
        yield _STUB_RAG_ANSWER[:half]
        yield _STUB_RAG_ANSWER[half:]

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(llm_svc, "chat_completion_stream", fake_chat_completion_stream)


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
        session_factory=session_factory,
    ):
        events.append(ev)

    # Streaming sequence: tool_call → sources (seeded 1 chunk) →
    #                    token × N → tool_result → done.
    # Stub splits the canned answer into 2 deltas.
    types = [type(ev).__name__ for ev in events]
    assert types == [
        "ToolCallEvent",
        "SourcesEvent",
        "TokenEvent",
        "TokenEvent",
        "ToolResultEvent",
        "DoneEvent",
    ]

    tool_call: ToolCallEvent = events[0]
    sources: SourcesEvent = events[1]
    tool_result: ToolResultEvent = events[4]
    done: DoneEvent = events[5]

    assert tool_call.data.name == "knowledge_qa"
    assert tool_call.data.agent == "knowledge_qa"
    assert sources.data.agent == "knowledge_qa"
    assert len(sources.data.sources) == 1
    first = sources.data.sources[0]
    assert first.ref == 1
    assert first.document_name == "seed.md"
    assert first.file_type == "md"
    assert first.chunk_index == 0
    # Tokens reassemble into the full canned answer.
    token_events = [ev for ev in events if isinstance(ev, TokenEvent)]
    assert "".join(t.data.text for t in token_events) == (
        "Stubbed answer based on retrieved chunks."
    )
    assert tool_result.data.tool_call_id == tool_call.data.tool_call_id
    assert tool_result.data.status == "success"
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
        session_factory=session_factory,
    ):
        events.append(ev)

    # Supervisor runs first and picks `single` → we catch the bad
    # project_id at the single-path validation gate.
    assert any(type(e).__name__ == "ErrorEvent" for e in events)
    err = next(e for e in events if type(e).__name__ == "ErrorEvent")
    assert "invalid project_id" in err.data.message


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
            session_factory=session_factory,
        )
    ]
    types = [type(e).__name__ for e in events]
    assert types == [
        "ToolCallEvent",
        "SourcesEvent",
        "TokenEvent",
        "TokenEvent",
        "ToolResultEvent",
        "DoneEvent",
    ]


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


async def test_supervisor_plan_placeholder_when_factory_absent(monkeypatch, db):
    """Without session_factory the plan branch falls back to a token."""
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
        )  # no session_factory
    ]
    types = [type(e).__name__ for e in events]
    assert types == ["TokenEvent", "DoneEvent"]
    assert "아직 준비 중" in events[0].data.text


async def test_supervisor_plan_executes_sequentially_with_plan_updates(
    monkeypatch, db
):
    """With session_factory, plan executes each agent in order and the
    stream carries plan_update + tool_call/tool_result pairs per step."""
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    _stub_llm(
        monkeypatch,
        supervisor_response=json.dumps(
            {
                "action": "plan",
                "agent": None,
                "plan": ["knowledge_qa", "requirement"],
                "clarification": None,
                "reasoning": "stub multi-step",
            }
        ),
    )

    # Stub artifact_record_svc so requirement step is deterministic.
    from unittest.mock import AsyncMock, patch

    from src.schemas.api.artifact_record import (
        ArtifactRecordExtractedItem as RecordExtractedItem,
        ArtifactRecordExtractResponse as RecordExtractResponse,
    )

    fake_records = RecordExtractResponse(
        candidates=[
            RecordExtractedItem(
                content="one",
                section_id=None,
                section_name="FR",
                source_document_id=None,
                source_document_name="doc.md",
                source_location="p.1",
                confidence_score=0.9,
            )
        ]
    )

    project = await _seed(db)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)

    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=fake_records),
    ):
        events = [
            ev
            async for ev in run_chat(
                graph,
                project_id=project.id,
                session_id=uuid.uuid4(),
                user_input="먼저 검색하고 요구사항까지 뽑아줘",
                session_factory=session_factory,
            )
        ]

    types = [type(e).__name__ for e in events]
    # Streaming plan sequence:
    #   PlanUpdate(all pending)
    #   PlanUpdate(step 0 running), ToolCall, Sources(knowledge_qa),
    #     [tokens suppressed — not last step],
    #     ToolResult, PlanUpdate(step 0 completed)
    #   PlanUpdate(step 1 running), ToolCall,
    #     Token(requirement final_answer, via default run_stream fallback),
    #     ToolResult, PlanUpdate(step 1 completed),
    #   Done
    assert types == [
        "PlanUpdateEvent",
        "PlanUpdateEvent",
        "ToolCallEvent",
        "SourcesEvent",
        "ToolResultEvent",
        "PlanUpdateEvent",
        "PlanUpdateEvent",
        "ToolCallEvent",
        "TokenEvent",
        "ToolResultEvent",
        "PlanUpdateEvent",
        "DoneEvent",
    ]

    # Last plan_update before Done: both steps completed.
    final_plan = events[-2]
    assert [s.agent for s in final_plan.data.plan] == ["knowledge_qa", "requirement"]
    assert [s.status for s in final_plan.data.plan] == ["completed", "completed"]

    # Terminal token is the requirement agent's summary (forwarded because
    # it's the last step).
    last_token = next(e for e in reversed(events) if isinstance(e, TokenEvent))
    assert "1개의 요구사항 후보" in last_token.data.text


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
