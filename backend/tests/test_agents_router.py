"""GET /api/v1/agents endpoint tests."""

from __future__ import annotations

import pytest

from src.agents import list_agents, load_builtin_agents


@pytest.fixture(autouse=True)
def _ensure_builtin_agents():
    if not list_agents():
        load_builtin_agents(force_reload=True)
    yield


async def test_list_agents_returns_knowledge_qa(client):
    res = await client.get("/api/v1/agents")
    assert res.status_code == 200
    body = res.json()
    names = [a["name"] for a in body]
    assert "knowledge_qa" in names

    kqa = next(a for a in body if a["name"] == "knowledge_qa")
    assert "rag" in kqa["tags"]
    assert kqa["description"]
    assert isinstance(kqa["triggers"], list)


async def test_get_agent_detail_ok(client):
    res = await client.get("/api/v1/agents/knowledge_qa")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "knowledge_qa"


async def test_get_agent_detail_404(client):
    res = await client.get("/api/v1/agents/does_not_exist")
    assert res.status_code == 404
