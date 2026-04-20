"""Agent registry contract tests (DESIGN §4)."""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import (
    clear_registry,
    find_by_tag,
    get_agent,
    list_agents,
    list_capabilities,
    load_builtin_agents,
    register_agent,
    try_get_agent,
)


@pytest.fixture(autouse=True)
def isolate_registry():
    """Clear before AND after every test so registrations don't leak.

    After each test we re-load the built-in agents (with force_reload, since
    `clear_registry` removed instances but importlib's module cache means
    a plain import wouldn't re-fire `@register_agent`). This keeps later
    test files (e.g. test_orchestration, test_agents_router) green.
    """
    clear_registry()
    yield
    clear_registry()
    load_builtin_agents(force_reload=True)


def _make_agent(name: str, *, tags: list[str] | None = None):
    @register_agent
    class _Agent(BaseAgent):
        capability = AgentCapability(
            name=name,
            description=f"{name} description",
            triggers=[f"call {name}"],
            tags=tags or [],
        )

        async def run(self, state):  # type: ignore[override]
            return {}

    return _Agent


def test_register_creates_singleton_instance():
    cls = _make_agent("agent_a")
    instance = get_agent("agent_a")
    assert isinstance(instance, BaseAgent)
    assert isinstance(instance, cls)
    # Lookup returns the same instance every time.
    assert get_agent("agent_a") is instance


def test_register_rejects_missing_capability():
    with pytest.raises(TypeError):

        @register_agent
        class Broken(BaseAgent):  # type: ignore[misc]
            async def run(self, state):
                return {}


def test_register_rejects_duplicate_name():
    _make_agent("dup")
    with pytest.raises(ValueError):
        _make_agent("dup")


def test_list_agents_returns_all_registered():
    _make_agent("a")
    _make_agent("b")
    names = {a.capability.name for a in list_agents()}
    assert names == {"a", "b"}


def test_list_capabilities_matches_list_agents():
    _make_agent("a")
    _make_agent("b")
    cap_names = {c.name for c in list_capabilities()}
    assert cap_names == {"a", "b"}


def test_try_get_agent_returns_none_when_missing():
    assert try_get_agent("ghost") is None


def test_get_agent_raises_keyerror_when_missing():
    with pytest.raises(KeyError):
        get_agent("ghost")


def test_find_by_tag_filters_correctly():
    _make_agent("rag1", tags=["rag"])
    _make_agent("rag2", tags=["rag", "qa"])
    _make_agent("gen1", tags=["generation"])
    rag_names = {a.capability.name for a in find_by_tag("rag")}
    assert rag_names == {"rag1", "rag2"}
    gen_names = {a.capability.name for a in find_by_tag("generation")}
    assert gen_names == {"gen1"}
    assert find_by_tag("nope") == []


def test_capability_round_trip_serialization():
    cap = AgentCapability(name="x", description="d", triggers=["t1", "t2"], tags=["a"])
    data = cap.model_dump()
    restored = AgentCapability.model_validate(data)
    assert restored == cap
