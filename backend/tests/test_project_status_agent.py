"""ProjectStatusAgent — 프로젝트 현황 질의 에이전트 테스트.

1. Unit: _fetch_project_summary 집계 정확성
2. Unit: run_stream 토큰 방출 + final 이벤트 계약
3. E2E: supervisor가 "개수/상태/현황" 질문을 project_status로 라우팅
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.agents import list_agents, load_builtin_agents
from src.agents.project_status import ProjectStatusAgent, _fetch_project_summary
from src.agents.registry import get_agent
from src.models.artifact import Artifact
from src.models.project import Project
from src.orchestration.graph import build_graph, run_chat
from src.orchestration.state import AgentContext
from src.schemas.events import DoneEvent, TokenEvent
from src.services import llm_svc


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents():
        load_builtin_agents(force_reload=True)
    yield


def _install_stream_stub(monkeypatch, *, answer: str):
    async def fake_chat_completion_stream(messages, **kwargs):
        third = max(1, len(answer) // 3)
        yield answer[:third]
        yield answer[third : third * 2]
        yield answer[third * 2 :]

    monkeypatch.setattr(llm_svc, "chat_completion_stream", fake_chat_completion_stream)


async def _seed_project_with_records(db, project_id: uuid.UUID) -> None:
    """Create a project with sample records for testing."""
    project = Project(
        id=project_id,
        name="status-test",
        description="project status agent test",
    )
    db.add(project)
    await db.flush()

    for i in range(3):
        artifact = Artifact(
            project_id=project_id,
            artifact_type="record",
            display_id=f"FR-{i+1:03d}",
            title=f"Record {i+1}",
            content={
                "text": f"요구사항 {i+1}",
                "section_id": None,
                "source_document_id": None,
                "source_location": None,
                "confidence_score": None,
                "is_auto_extracted": True,
                "order_index": i,
                "metadata": {"status": "approved" if i < 2 else "draft"},
            },
            working_status="clean",
            lifecycle_status="active",
        )
        db.add(artifact)
    await db.flush()


@pytest.mark.asyncio
async def test_fetch_project_summary_counts(db):
    """_fetch_project_summary returns correct record count and status breakdown."""
    pid = uuid.uuid4()
    await _seed_project_with_records(db, pid)

    summary = await _fetch_project_summary(db, pid)

    assert "레코드: 총 3개" in summary
    assert "승인 2개" in summary
    assert "초안 1개" in summary


@pytest.mark.asyncio
async def test_fetch_project_summary_empty(db):
    """_fetch_project_summary returns 'no artifacts' message when empty."""
    project = Project(
        id=uuid.uuid4(),
        name="empty-project",
        description="no artifacts",
    )
    db.add(project)
    await db.flush()

    summary = await _fetch_project_summary(db, project.id)
    assert "아직 생성된 산출물이 없습니다" in summary


@pytest.mark.asyncio
async def test_run_stream_emits_tokens_and_final(monkeypatch, db):
    """Unit: run_stream produces token events and a terminal final event."""
    canned = "현재 레코드는 3개입니다."
    _install_stream_stub(monkeypatch, answer=canned)

    project = Project(
        id=uuid.uuid4(),
        name="ps-unit",
        description="unit test",
    )
    db.add(project)
    await db.flush()

    agent = get_agent("project_status")
    assert isinstance(agent, ProjectStatusAgent)

    state = {
        "project_id": str(project.id),
        "user_input": "레코드 몇 개야?",
        "history": [],
    }
    ctx = AgentContext(db=db, project_id=project.id)

    events: list[dict] = []
    async for ev in agent.run_stream(state, ctx):
        events.append(ev)

    token_events = [e for e in events if e.get("kind") == "token"]
    final_events = [e for e in events if e.get("kind") == "final"]

    assert len(token_events) > 0, "should emit at least one token event"
    assert len(final_events) == 1, "should emit exactly one final event"
    assert final_events[0]["update"].get("final_answer") == canned


@pytest.mark.asyncio
async def test_run_chat_routes_status_query(monkeypatch, db):
    """E2E: '레코드 개수' query routes to project_status and streams answer."""
    canned = "현재 레코드는 3개, 승인 2개, 초안 1개입니다."
    _install_stream_stub(monkeypatch, answer=canned)

    # Also stub supervisor LLM so it routes to project_status.
    async def fake_chat_completion(messages, **kwargs):
        return (
            '{"action":"single","agent":"project_status","plan":null,'
            '"clarification":null,"extract_mode":null,'
            '"reasoning":"user asks about record count"}'
        )

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)

    pid = uuid.uuid4()
    await _seed_project_with_records(db, pid)

    graph = build_graph(TestSession)
    events: list = []
    async for ev in run_chat(
        graph,
        project_id=pid,
        session_id=uuid.uuid4(),
        user_input="레코드 개수가 어떻게 돼?",
        history=[],
        session_factory=TestSession,
    ):
        events.append(ev)

    token_events = [e for e in events if isinstance(e, TokenEvent)]
    done_events = [e for e in events if isinstance(e, DoneEvent)]

    assert len(token_events) > 0, "should stream tokens"
    assert len(done_events) == 1, "should emit one DoneEvent"

    # Verify the streamed text contains the answer
    full_text = "".join(e.data.text for e in token_events)
    assert "3개" in full_text or "레코드" in full_text
