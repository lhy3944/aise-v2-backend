"""Agent plugin contract.

DESIGN.md §4. Every agent declares an `AgentCapability` and implements
`async run(state) -> state`. Registration happens via the `@register_agent`
decorator in `src.agents.registry` (auto-instantiates a singleton).

`AgentState` is defined in `src.orchestration.state` and passed through
the LangGraph StateGraph nodes — agents receive the current state and
return a (possibly partial) update dict that LangGraph merges.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # avoid runtime circular import with orchestration
    from src.orchestration.state import AgentState


class AgentCapability(BaseModel):
    """Self-description used by the Supervisor to route requests.

    The `description` and `triggers` fields are the only signals the
    Supervisor sees; keep them precise and user-language-friendly.
    """

    name: str = Field(..., description="Unique stable identifier (e.g. 'knowledge_qa')")
    description: str = Field(..., description="Single sentence the Supervisor uses to decide routing")
    triggers: list[str] = Field(
        default_factory=list,
        description="Example natural-language phrases that should route here",
    )
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    requires_hitl: bool = False
    estimated_tokens: int = Field(default=2000, description="Rough budget hint for cost prediction")
    tags: list[str] = Field(default_factory=list, description="e.g. ['rag', 'generation']")


class BaseAgent(ABC):
    """Base class for agent plugins.

    Subclasses MUST:
    - declare a class-level `capability: AgentCapability` (not an instance attribute)
    - implement `async run(state)` returning a state update dict (or full state)

    Subclasses are typically registered via `@register_agent`.
    """

    capability: ClassVar[AgentCapability]

    @abstractmethod
    async def run(self, state: "AgentState") -> dict[str, Any] | "AgentState":
        """Execute the agent. Receives the current AgentState; returns either
        a partial update dict (LangGraph merges) or a full new state."""
        raise NotImplementedError

    # Convenience for nicer repr/debugging.
    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.capability.name!r}>"


__all__ = ["AgentCapability", "BaseAgent"]
