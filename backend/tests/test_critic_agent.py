"""CriticAgent (Phase 2 increment 3c).

The critic verifies that [N] citations in a prior final_answer map to valid
source refs. Deterministic — no LLM mock required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.agents import list_agents, load_builtin_agents
from src.agents.registry import get_agent
from src.orchestration.state import AgentContext


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents() or not any(
        a.capability.name == "critic" for a in list_agents()
    ):
        load_builtin_agents(force_reload=True)
    yield


def _ctx() -> AgentContext:
    return AgentContext(db=AsyncMock(), project_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_critic_passes_when_all_citations_resolve():
    agent = get_agent("critic")
    update = await agent.run(
        {
            "final_answer": "설계 원칙은 [1] 과 같이 정의되며, [2] 에서 구체화된다.",
            "sources": [
                {"ref": 1, "document_name": "A.md"},
                {"ref": 2, "document_name": "B.md"},
            ],
        },
        _ctx(),
    )

    assert update["critic_report"]["passed"] is True
    assert update["critic_report"]["checked_citations"] == 2
    assert update["critic_report"]["valid_citations"] == 2
    assert update["critic_report"]["issues"] == []
    assert "검증 통과" in update["final_answer"]


@pytest.mark.asyncio
async def test_critic_flags_unknown_citation():
    agent = get_agent("critic")
    update = await agent.run(
        {
            "final_answer": "한 번 [1] 그리고 다시 [3] 을 참조합니다.",
            "sources": [
                {"ref": 1, "document_name": "A.md"},
                {"ref": 2, "document_name": "B.md"},
            ],
        },
        _ctx(),
    )

    assert update["critic_report"]["passed"] is False
    assert update["critic_report"]["checked_citations"] == 2
    assert update["critic_report"]["valid_citations"] == 1
    assert any("[3]" in msg for msg in update["critic_report"]["issues"])
    assert "검증 실패" in update["final_answer"]


@pytest.mark.asyncio
async def test_critic_flags_citation_without_sources():
    agent = get_agent("critic")
    update = await agent.run(
        {
            "final_answer": "여기 [1] 인용.",
            "sources": [],
        },
        _ctx(),
    )

    assert update["critic_report"]["passed"] is False
    # 두 가지 문제가 동시에 기록됨: unknown ref + empty sources.
    assert len(update["critic_report"]["issues"]) >= 1


@pytest.mark.asyncio
async def test_critic_passes_when_no_citations_and_no_sources():
    agent = get_agent("critic")
    update = await agent.run(
        {
            "final_answer": "간단한 요약 답변입니다. 인용 없음.",
            "sources": [],
        },
        _ctx(),
    )

    assert update["critic_report"]["passed"] is True
    assert update["critic_report"]["checked_citations"] == 0
    assert "검증 통과" in update["final_answer"]


@pytest.mark.asyncio
async def test_critic_errors_when_no_prior_answer():
    agent = get_agent("critic")
    update = await agent.run({"final_answer": "", "sources": []}, _ctx())

    assert "error" in update
    assert "직전 답변이 없습니다" in update["error"]


@pytest.mark.asyncio
async def test_critic_falls_back_to_positional_refs():
    """sources 에 `ref` 필드가 없으면 배열 인덱스 + 1 을 ref 로 인정."""
    agent = get_agent("critic")
    update = await agent.run(
        {
            "final_answer": "첫 번째 [1], 두 번째 [2].",
            # ref 필드가 없는 소스 (레거시 / partial payload)
            "sources": [
                {"document_name": "A.md"},
                {"document_name": "B.md"},
            ],
        },
        _ctx(),
    )

    assert update["critic_report"]["passed"] is True
    assert update["critic_report"]["valid_citations"] == 2
