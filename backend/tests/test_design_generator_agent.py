"""DesignGeneratorAgent precondition regressions."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.agents import list_agents, load_builtin_agents
from src.agents.registry import get_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext
from src.services.artifact_messages import MISSING_SRS_MESSAGE


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents() or not any(
        a.capability.name == "design_generator" for a in list_agents()
    ):
        load_builtin_agents(force_reload=True)
    yield


@pytest.mark.asyncio
async def test_design_generator_surfaces_missing_srs_message():
    agent = get_agent("design_generator")
    ctx = AgentContext(db=AsyncMock(), project_id=uuid.uuid4())

    boom = AppException(400, MISSING_SRS_MESSAGE)
    with patch(
        "src.services.design_svc.generate_design",
        new=AsyncMock(side_effect=boom),
    ):
        update = await agent.run({}, ctx)

    assert update == {"error": MISSING_SRS_MESSAGE}
