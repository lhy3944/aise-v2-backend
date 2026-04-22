"""Agent API 테스트"""

import json
import uuid

import pytest

from src.agents import list_agents, load_builtin_agents
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.models.session import Session as SessionModel
from src.services import embedding_svc, llm_svc, rag_svc


@pytest.mark.asyncio
async def test_agent_chat_invalid_session_id_returns_422(client):
    resp = await client.post(
        "/api/v1/agent/chat",
        json={"session_id": "not-a-uuid", "message": "안녕하세요"},
    )

    assert resp.status_code == 422


_ROUTING_JSON = json.dumps(
    {
        "action": "single",
        "agent": "knowledge_qa",
        "plan": None,
        "clarification": None,
        "reasoning": "stub: default single routing",
    }
)


@pytest.fixture
def _stub_agent_deps(monkeypatch):
    async def fake_embeddings(texts):
        return [[0.1] * 1536 for _ in texts]

    async def fake_chat_completion(messages, **kwargs):
        # Supervisor calls include the routing prompt headers; return JSON
        # so the 3-action classifier can validate and pick `single`.
        last = messages[-1].get("content", "") if messages else ""
        if "## Decision policy" in last and "## Available agents" in last:
            return _ROUTING_JSON
        return "Stubbed answer from DI override test."

    async def fake_chat_completion_stream(messages, **kwargs):
        # Split into two deltas so streaming is observable.
        answer = "Stubbed answer from DI override test."
        half = len(answer) // 2
        yield answer[:half]
        yield answer[half:]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(llm_svc, "chat_completion_stream", fake_chat_completion_stream)

    if not list_agents():
        load_builtin_agents(force_reload=True)


@pytest.mark.asyncio
async def test_langgraph_path_honors_session_factory_override(
    _stub_agent_deps, client, db
):
    """Gate B regression: the agent route must use the test DB's session
    factory, not the production `async_session`. Proven by seeding a session
    in the test DB and confirming the endpoint finds it (vs emitting the
    SESSION_NOT_FOUND error that the prod DB would yield)."""
    # Bypass the module-level cache so a prior non-override run does not win.
    from src.routers import agent as agent_router

    agent_router._graph_cache.clear()

    project = Project(name="di-override", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    doc = KnowledgeDocument(
        project_id=project.id,
        name="seed.md",
        file_type="md",
        size_bytes=1,
        storage_key=f"{uuid.uuid4()}.md",
        status="completed",
        chunk_count=1,
        is_active=True,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    db.add(
        KnowledgeChunk(
            document_id=doc.id,
            project_id=project.id,
            chunk_index=0,
            content="hello",
            token_count=1,
            embedding=[0.1] * 1536,
        )
    )
    session = SessionModel(project_id=project.id, title="t")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    resp = await client.post(
        "/api/v1/agent/chat",
        json={"session_id": str(session.id), "message": "hi"},
    )
    assert resp.status_code == 200

    events = []
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))

    types = [e["type"] for e in events]
    assert "error" not in types, f"LangGraph path fell back to prod DB: {events!r}"
    # Streaming order: tool_call → sources → token × N → tool_result → done.
    # We don't assert exact N (depends on LLM stub chunking in conftest); just
    # verify the structural shape and no error events.
    assert types[0] == "tool_call"
    assert types[1] == "sources"
    assert types[-2] == "tool_result"
    assert types[-1] == "done"
    assert all(t in {"tool_call", "sources", "token", "tool_result", "done"} for t in types)
