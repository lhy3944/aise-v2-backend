"""TestCaseGeneratorAgent (Phase 2 increment 3b).

Verifies the agent wraps testcase_svc.generate_testcases:
- happy path: service returns TestCases → summary + testcases_generated
- AppException (no SRS): agent surfaces `error`
- graph E2E: supervisor routes to testcase_generator, emits
  tool_call/tool_result with testcase_count.
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
from src.schemas.api.artifact_testcase import (
    TestCaseArtifactResponse,
    TestCaseContent,
    TestCaseGenerateResponse,
)


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents() or not any(
        a.capability.name == "testcase_generator" for a in list_agents()
    ):
        load_builtin_agents(force_reload=True)
    yield


def _fake_tc(display_id: str = "TC-001") -> TestCaseArtifactResponse:
    return TestCaseArtifactResponse(
        artifact_id=str(uuid.uuid4()),
        display_id=display_id,
        content=TestCaseContent(
            title="테스트 제목",
            precondition="없음",
            steps=["step1"],
            expected_result="성공",
        ),
        working_status="dirty",
        lifecycle_status="active",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _fake_response(
    *, tc_count: int = 3, srs_version: int = 2, skipped: int = 0
) -> TestCaseGenerateResponse:
    return TestCaseGenerateResponse(
        based_on_srs_id=str(uuid.uuid4()),
        srs_version=srs_version,
        testcases=[_fake_tc(f"TC-{i + 1:03d}") for i in range(tc_count)],
        section_coverage={"기능 요구사항": tc_count},
        skipped_sections=[f"비기능 섹션 #{i}" for i in range(skipped)],
    )


@pytest.mark.asyncio
async def test_testcase_generator_summarises_generation():
    agent = get_agent("testcase_generator")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    fake = _fake_response(tc_count=5, srs_version=3, skipped=0)
    with patch(
        "src.services.testcase_svc.generate_testcases",
        new=AsyncMock(return_value=fake),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    assert "SRS v3" in update["final_answer"]
    assert "5개 생성" in update["final_answer"]
    assert "생략" not in update["final_answer"]
    assert update["testcases_generated"]["testcase_count"] == 5
    assert update["testcases_generated"]["srs_version"] == 3
    assert update["testcases_generated"]["skipped_section_count"] == 0


@pytest.mark.asyncio
async def test_testcase_generator_reports_skipped_sections():
    agent = get_agent("testcase_generator")
    ctx = AgentContext(db=AsyncMock(), project_id=uuid.uuid4())

    fake = _fake_response(tc_count=2, skipped=3)
    with patch(
        "src.services.testcase_svc.generate_testcases",
        new=AsyncMock(return_value=fake),
    ):
        update = await agent.run({}, ctx)

    assert "2개 생성" in update["final_answer"]
    assert "생략된 섹션: 3건" in update["final_answer"]
    assert update["testcases_generated"]["skipped_section_count"] == 3


@pytest.mark.asyncio
async def test_testcase_generator_surfaces_app_exception_as_state_error():
    agent = get_agent("testcase_generator")
    ctx = AgentContext(db=AsyncMock(), project_id=uuid.uuid4())

    boom = AppException(400, "완료된 SRS 문서가 없습니다. 먼저 SRS를 생성하세요.")
    with patch(
        "src.services.testcase_svc.generate_testcases",
        new=AsyncMock(side_effect=boom),
    ):
        update = await agent.run({}, ctx)

    assert update == {"error": "완료된 SRS 문서가 없습니다. 먼저 SRS를 생성하세요."}


# ---------- End-to-end via the graph ----------


@pytest.mark.asyncio
async def test_graph_routes_supervisor_to_testcase_generator(monkeypatch, db):
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
                    "agent": "testcase_generator",
                    "plan": None,
                    "clarification": None,
                    "reasoning": "stub",
                }
            )
        return "unused"

    monkeypatch.setattr(llm_svc, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(rag_svc, "chat_completion", fake_chat_completion)

    project = Project(name="tc-e2e", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    fake = _fake_response(tc_count=4, srs_version=2)
    session_factory = async_sessionmaker(db.bind, expire_on_commit=False)

    with patch(
        "src.services.testcase_svc.generate_testcases",
        new=AsyncMock(return_value=fake),
    ):
        graph = build_graph(session_factory)
        events = [
            ev
            async for ev in run_chat(
                graph,
                project_id=project.id,
                session_id=uuid.uuid4(),
                user_input="테스트케이스 만들어줘",
                session_factory=session_factory,
            )
        ]

    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "TokenEvent", "ToolResultEvent", "DoneEvent"]
    tool_call, token, tool_result, _done = events
    assert tool_call.data.name == "testcase_generator"
    assert tool_result.data.result == {"testcase_count": 4, "srs_version": 2}
    assert "4개 생성" in token.data.text
