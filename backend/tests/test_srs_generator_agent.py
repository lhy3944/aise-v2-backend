"""SrsGeneratorAgent (Phase 2 increment 3a).

Verifies the agent correctly wraps srs_svc.generate_srs:
- happy path: service returns SrsDocumentResponse → summary + srs_generated
- service raises AppException: agent surfaces `error` in state update
- graph E2E: supervisor routes to srs_generator; run_chat emits
  tool_call/tool_result with section_count.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.agents import list_agents, load_builtin_agents
from src.agents.registry import get_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext
from src.schemas.api.srs import SrsDocumentResponse, SrsSectionResponse


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents() or not any(
        a.capability.name == "srs_generator" for a in list_agents()
    ):
        load_builtin_agents(force_reload=True)
    yield


def _fake_srs_response(
    *, version: int = 1, section_count: int = 3, record_ids_count: int = 5
) -> SrsDocumentResponse:
    return SrsDocumentResponse(
        srs_id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        version=version,
        status="completed",
        error_message=None,
        sections=[
            SrsSectionResponse(
                section_id=str(uuid.uuid4()),
                title=f"Section {i}",
                content=f"content {i}",
                order_index=i,
            )
            for i in range(section_count)
        ],
        based_on_records={
            "artifact_ids": [str(uuid.uuid4()) for _ in range(record_ids_count)]
        },
        based_on_documents={"documents": []},
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_srs_generator_summarises_generation():
    agent = get_agent("srs_generator")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    fake = _fake_srs_response(version=2, section_count=4, record_ids_count=7)
    with patch(
        "src.services.srs_svc.generate_srs",
        new=AsyncMock(return_value=fake),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    assert "SRS v2" in update["final_answer"]
    assert "4개 섹션" in update["final_answer"]
    assert "7개 레코드" in update["final_answer"]
    assert update["srs_generated"]["srs_id"] == fake.srs_id
    assert update["srs_generated"]["version"] == 2
    assert update["srs_generated"]["section_count"] == 4
    assert update["srs_generated"]["based_on_records_count"] == 7


@pytest.mark.asyncio
async def test_srs_generator_surfaces_app_exception_as_state_error():
    agent = get_agent("srs_generator")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    boom = AppException(400, "레코드가 없습니다. 먼저 레코드를 추출하세요.")
    with patch(
        "src.services.srs_svc.generate_srs",
        new=AsyncMock(side_effect=boom),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    assert update == {"error": "레코드가 없습니다. 먼저 레코드를 추출하세요."}


# ---------- End-to-end via the graph ----------


@pytest.mark.asyncio
async def test_graph_routes_supervisor_to_srs_generator(monkeypatch, db):
    """Supervisor picks `srs_generator`; graph runs the agent; run_chat emits
    the tool_call/tool_result pair with section_count in the result."""
    import json as _json

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from src.models.project import Project
    from src.orchestration.graph import build_graph, run_chat
    from src.services import llm_svc, rag_svc

    async def fake_chat_completion(messages, **kwargs):
        last = messages[-1].get("content", "") if messages else ""
        if "## Decision policy" in last:
            return _json.dumps(
                {
                    "action": "single",
                    "agent": "srs_generator",
                    "plan": None,
                    "clarification": None,
                    "reasoning": "stub",
                }
            )
        return "unused"

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)

    project = Project(name="srs-e2e", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    fake = _fake_srs_response(version=1, section_count=3, record_ids_count=5)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)

    with patch(
        "src.services.srs_svc.generate_srs",
        new=AsyncMock(return_value=fake),
    ):
        graph = build_graph(session_factory)
        events = [
            ev
            async for ev in run_chat(
                graph,
                project_id=project.id,
                session_id=uuid.uuid4(),
                user_input="SRS 문서 만들어줘",
                session_factory=session_factory,
            )
        ]

    # Default run_stream fallback: tool_call → token → tool_result → done
    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "TokenEvent", "ToolResultEvent", "DoneEvent"]
    tool_call, token, tool_result, _done = events
    assert tool_call.data.name == "srs_generator"
    assert tool_result.data.result == {"section_count": 3, "srs_version": 1}
    assert "SRS v1" in token.data.text
