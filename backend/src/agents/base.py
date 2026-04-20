"""Agent plugin contract.

DESIGN.md §4. Every agent declares an `AgentCapability` and implements
`async run(state, ctx) -> dict`. Registration happens via the
`@register_agent` decorator in `src.agents.registry`.

`AgentState` and `AgentContext` are defined in `src.orchestration.state`.
The state flows through the LangGraph StateGraph; the context carries
non-serializable runtime dependencies (DB session, project_id, ...) that
must NOT live inside the LangGraph state (which is checkpointed).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # avoid runtime circular import with orchestration
    from src.orchestration.state import AgentContext, AgentState


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
    - implement `async run(state, ctx)` returning a state update dict that
      LangGraph merges into the global state.
    """

    capability: ClassVar[AgentCapability]

    @abstractmethod
    async def run(self, state: "AgentState", ctx: "AgentContext") -> dict[str, Any]:
        """Execute the agent.

        Args:
            state: current LangGraph state (TypedDict; treat as read-only).
            ctx:   non-serializable runtime context (DB session, project_id).

        Returns:
            Partial state update dict. LangGraph merges with the running state.
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.capability.name!r}>"


__all__ = ["AgentCapability", "BaseAgent"]
