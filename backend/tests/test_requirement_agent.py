"""RequirementAgent (Phase 2 increment 1B).

Verifies the agent correctly wraps artifact_record_svc.extract_records:
- happy path: service returns candidates → summary + records_extracted
- no candidates: agent returns the "nothing to extract" summary
- service raises AppException: agent surfaces `error` in state update
"""

from __future__ import annotations

import uuid
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
    """후보 0개 → no_candidates_guide 의 친절한 안내 문구 반환."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=RecordExtractResponse(candidates=[])),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    assert update["records_extracted"] == []
    # 새 가이드 문구는 대체 경로(직접 입력 / 수동 폼)를 함께 안내한다.
    assert "후보" in update["final_answer"]
    assert "직접" in update["final_answer"]


@pytest.mark.asyncio
async def test_requirement_agent_surfaces_app_exception_as_friendly_guide():
    """AppException → state['error'] 가 아닌 final_answer 에 친절 가이드.

    Phase 3 후속: 빨간 ErrorEvent 가 아닌 일반 답변으로 표시되도록 변경.
    """
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    boom = AppException(400, "활성 지식 문서가 없습니다.")
    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(side_effect=boom),
    ):
        update = await agent.run({"project_id": str(project_id)}, ctx)

    # error 키는 채워지지 않아야 한다 (ErrorEvent 안 발행 → 일반 답변).
    assert "error" not in update
    assert update["records_extracted"] == []
    assert "지식 문서" in update["final_answer"]
    assert "직접" in update["final_answer"]


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

    # Phase 3 PR-2: RequirementAgent 가 추출 후 ConfirmData interrupt 를
    # 발행한다. 흐름:
    #   tool_call → InterruptEvent(confirm) → done(finish_reason="interrupt")
    # tool_result 는 발행되지 않으며, hitl_state_svc 에 thread_id 가 저장돼
    # POST /api/v1/agent/resume/{thread_id} 가 같은 에이전트를 재호출한다.
    types = [type(e).__name__ for e in events]
    assert types == ["ToolCallEvent", "InterruptEvent", "DoneEvent"]
    tool_call, interrupt, done = events
    assert tool_call.data.name == "requirement"
    assert interrupt.data.kind == "confirm"
    assert "2개 요구사항 후보" in interrupt.data.title
    assert done.data.finish_reason == "interrupt"

    # hitl_state 에 후보가 누적된 상태로 저장돼야 한다 (resume 복원용).
    from src.services import hitl_state_svc

    saved = hitl_state_svc.get(interrupt.data.interrupt_id)
    assert saved is not None
    assert saved.selected_agent == "requirement"
    assert len(saved.accumulated_state.get("records_extracted", [])) == 2
    hitl_state_svc.delete(interrupt.data.interrupt_id)


# ---------- Phase 3 PR-2: HITL run_stream branches (unit, no DB) ----------


@pytest.mark.asyncio
async def test_run_stream_extract_then_interrupt():
    """첫 호출: 후보 추출 → partial(records_extracted) → ConfirmData interrupt."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    fake = RecordExtractResponse(candidates=[_candidate("FR"), _candidate("QA")])
    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=fake),
    ):
        events = [ev async for ev in agent.run_stream({"project_id": str(project_id)}, ctx)]

    kinds = [e.get("kind") for e in events]
    assert kinds == ["partial", "interrupt"]
    assert len(events[0]["update"]["records_extracted"]) == 2
    assert events[1]["data"].kind == "confirm"
    assert "2개 요구사항 후보" in events[1]["data"].title


@pytest.mark.asyncio
async def test_run_stream_resume_approve_calls_approve_records():
    """resume + action=approve → approve_records 호출 + records_approved_count."""
    from src.schemas.api.artifact_record import (
        ArtifactRecordListResponse,
        ArtifactRecordResponse,
    )

    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    candidates = [
        _candidate("FR").model_dump(mode="json"),
        _candidate("QA").model_dump(mode="json"),
    ]
    state = {
        "project_id": str(project_id),
        "records_extracted": candidates,
        "hitl_response": {"action": "approve"},
        "hitl_interrupt_id": "itp_test",
    }

    def _mk_resp(content: str) -> ArtifactRecordResponse:
        return ArtifactRecordResponse(
            artifact_id=str(uuid.uuid4()),
            project_id=str(project_id),
            content=content,
            display_id="REC-001",
            status="approved",
            is_auto_extracted=True,
            order_index=0,
            created_at="2026-04-28T00:00:00Z",
            updated_at="2026-04-28T00:00:00Z",
        )

    approve_mock = AsyncMock(
        return_value=ArtifactRecordListResponse(
            records=[_mk_resp("a"), _mk_resp("b")], total=2,
        )
    )
    with patch("src.services.artifact_record_svc.approve_records", new=approve_mock):
        events = [ev async for ev in agent.run_stream(state, ctx)]

    approve_mock.assert_awaited_once()
    final = next(e for e in events if e.get("kind") == "final")
    assert final["update"]["records_approved_count"] == 2
    assert "2개 요구사항 후보를 승인" in final["update"]["final_answer"]


@pytest.mark.asyncio
async def test_run_stream_resume_reject_skips_approve():
    """resume + action=reject → approve_records 호출 안 됨, 거부 메시지."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    state = {
        "project_id": str(project_id),
        "records_extracted": [_candidate("FR").model_dump(mode="json")],
        "hitl_response": {"action": "reject"},
        "hitl_interrupt_id": "itp_test",
    }

    approve_mock = AsyncMock()
    with patch("src.services.artifact_record_svc.approve_records", new=approve_mock):
        events = [ev async for ev in agent.run_stream(state, ctx)]

    approve_mock.assert_not_awaited()
    final = next(e for e in events if e.get("kind") == "final")
    assert final["update"]["records_approved_count"] == 0
    assert "거부" in final["update"]["final_answer"]


@pytest.mark.asyncio
async def test_run_stream_no_candidates_skips_interrupt():
    """후보 0개 → interrupt 없이 바로 final."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(return_value=RecordExtractResponse(candidates=[])),
    ):
        events = [ev async for ev in agent.run_stream({"project_id": str(project_id)}, ctx)]

    kinds = [e.get("kind") for e in events]
    assert "interrupt" not in kinds
    assert kinds[-1] == "final"
    assert events[-1]["update"]["records_extracted"] == []


# ---------- Phase 3 후속: 가이드 메시지 + user_text 모드 ----------


@pytest.mark.asyncio
async def test_run_stream_app_exception_yields_guide_token_not_error():
    """추출 실패 (활성 지식 문서 없음) → ErrorEvent 가 아닌 친절 가이드 token+final."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    with patch(
        "src.services.artifact_record_svc.extract_records",
        new=AsyncMock(side_effect=AppException(400, "활성 지식 문서가 없습니다.")),
    ):
        events = [ev async for ev in agent.run_stream({"project_id": str(project_id)}, ctx)]

    kinds = [e.get("kind") for e in events]
    assert kinds == ["token", "final"]
    final = events[-1]
    # 'error' 키는 비어 있어야 한다 — ErrorEvent 가 아닌 일반 답변으로 표시되도록.
    assert "error" not in final["update"]
    assert "지식 문서" in final["update"]["final_answer"]
    assert "직접" in final["update"]["final_answer"]


@pytest.mark.asyncio
async def test_run_stream_user_text_mode_passes_user_input_to_extractor():
    """routing.extract_mode='user_text' → extract_records 에 user_text 인자 전달."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    fake = RecordExtractResponse(candidates=[_candidate("FR", "OAuth 2.0 지원")])
    extract_mock = AsyncMock(return_value=fake)
    with patch(
        "src.services.artifact_record_svc.extract_records", new=extract_mock,
    ):
        state = {
            "project_id": str(project_id),
            "user_input": "우리 시스템은 OAuth 2.0 을 지원해야 한다",
            "routing": {"extract_mode": "user_text"},
        }
        events = [ev async for ev in agent.run_stream(state, ctx)]

    # extract_records 호출 인자 검증 — user_text 가 그대로 전달돼야 함
    extract_mock.assert_awaited_once()
    call_kwargs = extract_mock.await_args.kwargs
    assert call_kwargs.get("user_text") == "우리 시스템은 OAuth 2.0 을 지원해야 한다"

    # ConfirmData interrupt + 채팅 입력 안내 문구 검증
    interrupt_ev = next(e for e in events if e.get("kind") == "interrupt")
    assert "채팅 입력에서" in interrupt_ev["data"].description


@pytest.mark.asyncio
async def test_run_stream_document_mode_does_not_pass_user_text():
    """routing.extract_mode='document' (또는 None) → user_text 인자 None."""
    agent = get_agent("requirement")
    project_id = uuid.uuid4()
    ctx = AgentContext(db=AsyncMock(), project_id=project_id)

    fake = RecordExtractResponse(candidates=[_candidate("FR")])
    extract_mock = AsyncMock(return_value=fake)
    with patch(
        "src.services.artifact_record_svc.extract_records", new=extract_mock,
    ):
        state = {
            "project_id": str(project_id),
            "user_input": "레코드 추출해줘",
            "routing": {"extract_mode": "document"},
        }
        async for _ in agent.run_stream(state, ctx):
            pass

    call_kwargs = extract_mock.await_args.kwargs
    assert call_kwargs.get("user_text") is None
