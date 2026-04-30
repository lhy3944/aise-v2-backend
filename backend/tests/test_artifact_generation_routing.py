"""Deterministic artifact-generation routing regressions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.agents import list_agents, load_builtin_agents
from src.schemas.api.design import DesignDocumentResponse, DesignSectionResponse
from src.schemas.api.srs import SrsDocumentResponse, SrsSectionResponse


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    names = {agent.capability.name for agent in list_agents()}
    if not {"srs_generator", "design_generator"}.issubset(names):
        load_builtin_agents(force_reload=True)
    yield


def _fake_srs_response(*, version: int = 3, section_count: int = 4):
    return SrsDocumentResponse(
        srs_id=str(uuid.uuid4()),
        artifact_id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        version=version,
        status="completed",
        error_message=None,
        sections=[
            SrsSectionResponse(
                section_id=str(uuid.uuid4()),
                title=f"SRS Section {i}",
                content=f"content {i}",
                order_index=i,
            )
            for i in range(section_count)
        ],
        based_on_records={"artifact_ids": [str(uuid.uuid4())]},
        based_on_documents={"documents": []},
        created_at=datetime.now(timezone.utc),
    )


def _fake_design_response(
    *, version: int = 2, section_count: int = 5, srs_version: int = 3
):
    return DesignDocumentResponse(
        design_id=str(uuid.uuid4()),
        artifact_id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        version=version,
        status="completed",
        error_message=None,
        sections=[
            DesignSectionResponse(
                section_id=str(uuid.uuid4()),
                title=f"Design Section {i}",
                content=f"content {i}",
                order_index=i,
            )
            for i in range(section_count)
        ],
        based_on_srs={
            "version_id": str(uuid.uuid4()),
            "version_number": srs_version,
        },
        source_artifact_versions=None,
        created_at=datetime.now(timezone.utc),
    )


async def _run_generation_command(monkeypatch, db, *, user_input: str):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from src.models.project import Project
    from src.orchestration import graph as graph_mod
    from src.orchestration.graph import build_graph, run_chat

    async def fail_gate(**kwargs):  # pragma: no cover - asserted by no raise
        raise AssertionError("retrieval gate should not handle generation commands")

    async def fail_supervisor(state):  # pragma: no cover - asserted by no raise
        raise AssertionError("supervisor should not handle explicit generation")

    monkeypatch.setattr(graph_mod, "evaluate_gate", fail_gate)
    monkeypatch.setattr(graph_mod, "supervisor_node", fail_supervisor)

    project = Project(name="artifact-routing", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)
    graph = build_graph(session_factory)
    return [
        ev
        async for ev in run_chat(
            graph,
            project_id=project.id,
            session_id=uuid.uuid4(),
            user_input=user_input,
            session_factory=session_factory,
        )
    ]


@pytest.mark.asyncio
async def test_run_chat_routes_srs_generation_before_rag(monkeypatch, db):
    with patch(
        "src.services.srs_svc.generate_srs",
        new=AsyncMock(return_value=_fake_srs_response()),
    ):
        events = await _run_generation_command(
            monkeypatch,
            db,
            user_input="SRS 문서 만들어줘",
        )

    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "TokenEvent", "ToolResultEvent", "DoneEvent"]
    tool_call, token, tool_result, _done = events
    assert tool_call.data.name == "srs_generator"
    assert tool_result.data.result == {"section_count": 4, "srs_version": 3}
    assert "SRS v3" in token.data.text


@pytest.mark.asyncio
async def test_run_chat_routes_design_generation_before_rag(monkeypatch, db):
    with patch(
        "src.services.design_svc.generate_design",
        new=AsyncMock(return_value=_fake_design_response()),
    ):
        events = await _run_generation_command(
            monkeypatch,
            db,
            user_input="설계 문서 만들어줘",
        )

    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "TokenEvent", "ToolResultEvent", "DoneEvent"]
    tool_call, token, tool_result, _done = events
    assert tool_call.data.name == "design_generator"
    assert tool_result.data.result == {
        "section_count": 5,
        "design_version": 2,
        "srs_version": 3,
    }
    assert "DESIGN v2" in token.data.text
