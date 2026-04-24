"""RequirementAgent (Phase 2 increment 1B).

Verifies the agent correctly wraps artifact_record_svc.extract_records:
- happy path: service returns candidates → summary + records_extracted
- no candidates: agent returns the "nothing to extract" summary
- service raises AppException: agent surfaces `error` in state update
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.agents import list_agents, load_builtin_agents
from src.agents.registry import get_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext
from src.schemas.api.artifact_record import (
    ArtifactRecordExtractedItem as RecordExtractedItem,
    ArtifactRecordExtractResponse as RecordExtractResponse,
)


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents() or not any(a.capability.name == "requirement" for a in list_agents()):
        load_builtin_agents(force_reload=True)
    yield


def _candidate(section_name: str, content: str = "x") -> RecordExtractedItem:
    return RecordExtractedItem(
        content=content,
        section_id=str(uuid.uuid4()),
        section_name=section_name,
        source_document_id=None,
        source_document_name="doc.md",
        source_location="p.1",
        confidence_score=0.8,
    )


@pytest.mark.asyncio
async def test_requirement_agent_summarises_extraction():
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    fake_response = RecordExtractResponse(
        candidates=[_candidate("FR"), _candidate("FR"), _candidate("QA")]
    )
    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=fake_response),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    assert "3개의 요구사항 후보" in update["final_answer"]
    # Section histogram is rendered most-common first.
    assert "FR(2)" in update["final_answer"]
    assert "QA(1)" in update["final_answer"]
    assert len(update["records_extracted"]) == 3
    assert update["records_extracted"][0]["section_name"] == "FR"


@pytest.mark.asyncio
async def test_requirement_agent_empty_extraction():
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=RecordExtractResponse(candidates=[])),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    assert update["records_extracted"] == []
    assert "없습니다" in update["final_answer"]


@pytest.mark.asyncio
async def test_requirement_agent_surfaces_app_exception_as_state_error():
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    boom = AppException(400, "활성 지식 문서가 없습니다.")
    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(side_effect=boom),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    # The agent converts AppException into a state["error"] rather than
    # bubbling up, so run_chat can emit a clean AGENT_ERROR SSE event.
    assert update == {"error": "활성 지식 문서가 없습니다."}


# ---------- End-to-end via the graph ----------


@pytest.mark.asyncio
async def test_graph_routes_supervisor_to_requirement_agent(monkeypatch, db):
    """Supervisor picks `requirement`; graph runs the agent; run_chat emits
    the tool_call/tool_result pair with records_count in the result."""
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
                    "agent": "requirement",
                    "plan": None,
                    "clarification": None,
                    "reasoning": "stub",
                }
            )
        return "Unused — agent uses artifact_record_svc directly."

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)

    project = Project(name="r-e2e", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    fake_response = RecordExtractResponse(candidates=[_candidate("FR"), _candidate("QA")])
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)

    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=fake_response),
    ):
        graph = build_graph(session_factory)
        events = [
            ev
            async for ev in run_chat(
                graph,
                project_id=project.id,
                session_id=uuid.uuid4(),
                user_input="프로젝트의 요구사항을 뽑아줘",
                session_factory=session_factory,
            )
        ]

    # Requirement agent doesn't override run_stream → default fallback
    # surfaces its final_answer as a single Token. Streaming order:
    #   tool_call → token → tool_result → done
    # (no SourcesEvent; requirement doesn't populate state["sources"])
    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "TokenEvent", "ToolResultEvent", "DoneEvent"]
    tool_call, token, tool_result, _done = events
    assert tool_call.data.name == "requirement"
    assert tool_result.data.result == {"records_count": 2}
    assert "2개의 요구사항 후보" in token.data.text
