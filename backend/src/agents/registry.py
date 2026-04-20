"""Agent registry — DESIGN.md §4.2.

Use the `@register_agent` decorator to register an agent class. The class is
instantiated immediately and stored under `capability.name`.

```python
@register_agent
class KnowledgeQAAgent(BaseAgent):
    capability = AgentCapability(name="knowledge_qa", ...)
    async def run(self, state): ...
```

Lookup helpers:
- `get_agent(name)`          — KeyError if missing
- `try_get_agent(name)`      — None if missing
- `list_agents()`            — list[BaseAgent]
- `list_capabilities()`      — list[AgentCapability]
- `find_by_tag(tag)`         — list[BaseAgent]

`load_builtin_agents()` imports all known agent modules so their decorators
fire. Call this once on app startup.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Type

from loguru import logger

if TYPE_CHECKING:
    from src.agents.base import AgentCapability, BaseAgent


_REGISTRY: dict[str, "BaseAgent"] = {}

# Modules under src.agents.* that contain @register_agent declarations.
# Keep the list explicit (not a directory walk) so registration is deterministic
# and so deleting a file doesn't silently change behavior.
_BUILTIN_AGENT_MODULES: tuple[str, ...] = (
    "src.agents.knowledge_qa",
    # Phase 2 will add: requirement, srs_generator, testcase_generator, critic
)


def register_agent(cls: Type["BaseAgent"]) -> Type["BaseAgent"]:
    """Class decorator — instantiate and register under cls.capability.name."""
    cap = getattr(cls, "capability", None)
    if cap is None or not getattr(cap, "name", None):
        raise TypeError(
            f"{cls.__name__} must declare a class-level `capability: AgentCapability` with a non-empty name"
        )

    name = cap.name
    if name in _REGISTRY and type(_REGISTRY[name]) is not cls:
        raise ValueError(
            f"Agent name conflict: '{name}' already registered by {type(_REGISTRY[name]).__name__}"
        )

    instance = cls()
    _REGISTRY[name] = instance
    logger.debug(f"Registered agent: {name} ({cls.__name__})")
    return cls


def get_agent(name: str) -> "BaseAgent":
    return _REGISTRY[name]


def try_get_agent(name: str) -> "BaseAgent | None":
    return _REGISTRY.get(name)


def list_agents() -> list["BaseAgent"]:
    return list(_REGISTRY.values())


def list_capabilities() -> list["AgentCapability"]:
    return [agent.capability for agent in _REGISTRY.values()]


def find_by_tag(tag: str) -> list["BaseAgent"]:
    return [agent for agent in _REGISTRY.values() if tag in agent.capability.tags]


def clear_registry() -> None:
    """Test-only helper. Do not call from production code."""
    _REGISTRY.clear()


def load_builtin_agents() -> None:
    """Import every built-in agent module so their @register_agent decorators run.

    Idempotent — re-importing a module is a no-op for registration because the
    decorator is class-scoped, not instance-scoped, and conflicts are rejected
    by `register_agent`.
    """
    for module_path in _BUILTIN_AGENT_MODULES:
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            logger.warning(f"Skipping agent module {module_path}: {e}")


__all__ = [
    "clear_registry",
    "find_by_tag",
    "get_agent",
    "list_agents",
    "list_capabilities",
    "load_builtin_agents",
    "register_agent",
    "try_get_agent",
]
