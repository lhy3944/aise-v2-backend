"""RecordManagerAgent regressions.

The agent owns individual record mutations and must not write until HITL
approval is supplied on resume.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.agents import list_agents, load_builtin_agents
from src.agents.registry import get_agent
from src.models.artifact import Artifact
from src.models.project import Project
from src.models.requirement import RequirementSection
from src.orchestration.state import AgentContext
from src.schemas.api.artifact_record import ArtifactRecordCreate
from src.services import artifact_record_svc


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    names = {agent.capability.name for agent in list_agents()}
    if "record_manager" not in names:
        load_builtin_agents(force_reload=True)
    yield


async def _seed_project(db):
    project = Project(name="record-manager", description="x")
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
    await db.commit()
    await db.refresh(section)
    return project, section


async def _record_count(db, project_id: uuid.UUID) -> int:
    rows = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "record",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalars().all()
    return len(rows)


async def test_append_confirms_before_db_write_and_approve_creates_record(db):
    agent = get_agent("record_manager")
    project, section = await _seed_project(db)
    ctx = AgentContext(db=db, project_id=project.id)

    state = {
        "project_id": str(project.id),
        "user_input": "레코드에 MFA 추가해줘",
        "routing": {
            "action_params": {
                "action": "create",
                "content": "MFA를 지원해야 한다.",
                "section_id": str(section.id),
            }
        },
    }
    events = [ev async for ev in agent.run_stream(state, ctx)]

    assert [e["kind"] for e in events] == ["partial", "interrupt"]
    assert events[1]["data"].kind == "confirm"
    assert await _record_count(db, project.id) == 0

    proposal = events[0]["update"]["record_manager_proposal"]
    approve_state = {
        **state,
        "record_manager_proposal": proposal,
        "hitl_response": {"action": "approve"},
    }
    resumed = [ev async for ev in agent.run_stream(approve_state, ctx)]

    assert resumed[-1]["kind"] == "final"
    assert resumed[-1]["update"]["record_mutation"]["status"] == "created"
    assert await _record_count(db, project.id) == 1


async def test_reject_resume_keeps_db_unchanged(db):
    agent = get_agent("record_manager")
    project, section = await _seed_project(db)
    ctx = AgentContext(db=db, project_id=project.id)

    state = {
        "project_id": str(project.id),
        "record_manager_proposal": {
            "action": "create",
            "content": "거부될 레코드",
            "section_id": str(section.id),
        },
        "hitl_response": {"action": "reject"},
    }
    events = [ev async for ev in agent.run_stream(state, ctx)]

    assert "취소" in events[-1]["update"]["final_answer"]
    assert await _record_count(db, project.id) == 0


async def test_update_status_and_delete_run_only_after_approval(db):
    agent = get_agent("record_manager")
    project, section = await _seed_project(db)
    ctx = AgentContext(db=db, project_id=project.id)
    created = await artifact_record_svc.create_record(
        db,
        project.id,
        ArtifactRecordCreate(content="기존 내용", section_id=section.id),
    )

    update_state = {
        "project_id": str(project.id),
        "user_input": f"{created.display_id} 수정",
        "routing": {
            "action_params": {
                "action": "update",
                "display_id": created.display_id,
                "content": "수정된 내용",
            }
        },
    }
    first = [ev async for ev in agent.run_stream(update_state, ctx)]
    artifact = await artifact_record_svc.get_record_by_display_id(db, project.id, created.display_id)
    assert artifact.content["text"] == "기존 내용"

    update_resume = {
        **update_state,
        "record_manager_proposal": first[0]["update"]["record_manager_proposal"],
        "hitl_response": {"action": "approve"},
    }
    update_events = [ev async for ev in agent.run_stream(update_resume, ctx)]
    assert update_events[-1]["update"]["record_mutation"]["status"] == "updated"
    artifact = await artifact_record_svc.get_record_by_display_id(db, project.id, created.display_id)
    assert artifact.content["text"] == "수정된 내용"

    status_state = {
        "project_id": str(project.id),
        "user_input": f"{created.display_id} 상태 승인",
        "record_manager_proposal": {
            "action": "status_change",
            "artifact_id": str(artifact.id),
            "display_id": created.display_id,
            "status": "approved",
        },
        "hitl_response": {"action": "approve"},
    }
    status_events = [ev async for ev in agent.run_stream(status_state, ctx)]
    assert status_events[-1]["update"]["record_mutation"]["record_status"] == "approved"

    delete_state = {
        "project_id": str(project.id),
        "user_input": f"{created.display_id} 삭제",
        "record_manager_proposal": {
            "action": "delete",
            "artifact_id": str(artifact.id),
            "display_id": created.display_id,
        },
        "hitl_response": {"action": "approve"},
    }
    delete_events = [ev async for ev in agent.run_stream(delete_state, ctx)]
    assert delete_events[-1]["update"]["record_mutation"]["status"] == "deleted"
    assert await _record_count(db, project.id) == 0


async def test_missing_display_id_clarifies(db):
    agent = get_agent("record_manager")
    project, _section = await _seed_project(db)
    ctx = AgentContext(db=db, project_id=project.id)

    state = {
        "project_id": str(project.id),
        "user_input": "레코드 삭제해줘",
        "routing": {"action_params": {"action": "delete"}},
    }
    events = [ev async for ev in agent.run_stream(state, ctx)]

    assert [e["kind"] for e in events] == ["interrupt"]
    assert events[0]["data"].kind == "clarify"
    assert "display_id" in events[0]["data"].question
