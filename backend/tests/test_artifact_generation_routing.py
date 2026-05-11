"""Deterministic artifact-generation routing regressions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.agents import list_agents, load_builtin_agents
from src.models.artifact import Artifact
from src.models.requirement import RequirementSection
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


async def _run_generation_command(monkeypatch, db, *, user_input: str, agent_name: str):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from src.models.project import Project
    from src.orchestration.graph import build_graph, run_chat
    from src.services import llm_svc

    monkeypatch.setenv("RAG_GATE_ENABLED", "false")
    monkeypatch.setenv("SUPERVISOR_TOOL_USE_ENABLED", "true")

    async def fake_with_tools(messages, tools, **kwargs):
        return llm_svc.CompletionResponse(
            tool_calls=[
                llm_svc.ToolCallInfo(
                    id=f"call_{agent_name}",
                    name=agent_name,
                    arguments={"confidence": 1.0, "reasoning": "explicit generation request"},
                )
            ],
            finish_reason="tool_calls",
        )

    monkeypatch.setattr(llm_svc, "chat_completion_with_tools", fake_with_tools)

    project = Project(name="artifact-routing", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    section = RequirementSection(
        id=uuid.uuid4(),
        project_id=project.id,
        type="fr",
        name="Functional Requirements",
        is_default=True,
        is_active=True,
        order_index=0,
    )
    db.add(section)
    if agent_name == "srs_generator":
        db.add(
            Artifact(
                project_id=project.id,
                artifact_type="record",
                display_id="FR-001",
                content={
                    "text": "로그인을 지원해야 한다.",
                    "section_id": str(section.id),
                    "metadata": {"status": "approved"},
                    "order_index": 0,
                },
                working_status="dirty",
                lifecycle_status="active",
            )
        )
    if agent_name == "design_generator":
        db.add(
            Artifact(
                project_id=project.id,
                artifact_type="srs",
                display_id="SRS-001",
                content={"sections": [{"title": "FR", "content": "로그인"}]},
                working_status="dirty",
                lifecycle_status="active",
            )
        )
    await db.commit()

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
    ) as generate_mock:
        events = await _run_generation_command(
            monkeypatch,
            db,
            user_input="SRS 문서 만들어줘",
            agent_name="srs_generator",
        )

    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "InterruptEvent", "DoneEvent"]
    tool_call, interrupt, done = events
    assert tool_call.data.name == "srs_generator"
    assert interrupt.data.kind == "confirm"
    assert "SRS" in interrupt.data.title
    assert done.data.finish_reason == "interrupt"
    generate_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_chat_routes_design_generation_before_rag(monkeypatch, db):
    with patch(
        "src.services.design_svc.generate_design",
        new=AsyncMock(return_value=_fake_design_response()),
    ) as generate_mock:
        events = await _run_generation_command(
            monkeypatch,
            db,
            user_input="설계 문서 만들어줘",
            agent_name="design_generator",
        )

    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "InterruptEvent", "DoneEvent"]
    tool_call, interrupt, done = events
    assert tool_call.data.name == "design_generator"
    assert interrupt.data.kind == "confirm"
    assert "Design" in interrupt.data.title
    assert done.data.finish_reason == "interrupt"
    generate_mock.assert_not_awaited()
