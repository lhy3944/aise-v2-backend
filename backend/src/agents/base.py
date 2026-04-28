"""Agent plugin contract.

DESIGN.md §4. Every agent declares an `AgentCapability` and implements
`async run(state, ctx) -> dict`. Registration happens via the
`@register_agent` decorator in `src.agents.registry`.

`AgentState` and `AgentContext` are defined in `src.orchestration.state`.
The state flows through the LangGraph StateGraph; the context carries
non-serializable runtime dependencies (DB session, project_id, ...) that
must NOT live inside the LangGraph state (which is checkpointed).

Streaming
---------
Agents that can stream tokens override `run_stream(state, ctx)` to yield
discriminated events the orchestrator forwards as SSE:

    {"kind": "sources",   "sources": list[dict]} → SourcesEvent
    {"kind": "token",     "text":    str}        → TokenEvent
    {"kind": "interrupt", "data":    HitlData}   → InterruptEvent (Phase 3);
                                                    SSE 드라이버는 hitl_state
                                                    저장 후 done(interrupt)
                                                    로 종료. resume 라우터가
                                                    재개한다. interrupt 다음에
                                                    final 을 발행하면 안 됨.
    {"kind": "final",     "update":  dict}       → merged into state;
                                                    drives `_result_payload`
                                                    (MUST be the last event)

The default `run_stream` calls `run()` once and surfaces its result as
`sources?` + a single `token(final_answer)` + `final` — i.e. agents that
don't care about streaming keep implementing `run()` and get a working
(albeit non-streaming) stream for free.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
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
    expose_as_tool: bool = Field(
        default=True,
        description=(
            "When True (default), the orchestrator emits tool_call + "
            "tool_result SSE events around the agent run so the UI renders "
            "a visible invocation card. Set False for conversational "
            "agents whose output IS the response (e.g. general_chat) — "
            "only token/sources/done events are emitted and the chat UI "
            "shows just the streamed answer without a tool card."
        ),
    )


class BaseAgent(ABC):
    """Base class for agent plugins.

    Subclasses MUST:
    - declare a class-level `capability: AgentCapability` (not an instance attribute)
    - implement `async run(state, ctx)` returning a state update dict.

    Subclasses MAY:
    - override `async run_stream(state, ctx)` to emit tokens/sources
      incrementally. Default implementation wraps `run()` once.
    """

    capability: ClassVar[AgentCapability]

    @abstractmethod
    async def run(self, state: "AgentState", ctx: "AgentContext") -> dict[str, Any]:
        """Execute the agent (non-streaming).

        Args:
            state: current LangGraph state (TypedDict; treat as read-only).
            ctx:   non-serializable runtime context (DB session, project_id).

        Returns:
            Partial state update dict. LangGraph merges with the running state.
        """
        raise NotImplementedError

    async def run_stream(
        self, state: "AgentState", ctx: "AgentContext"
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream agent output.

        Default: call `run()` once, then surface the result as:
          - a single `sources` event (if `result["sources"]` is truthy),
          - a single `token` event (if `result["final_answer"]` is truthy),
          - a terminal `final` event carrying the whole `result`.

        Agents that talk to a streaming LLM override this to yield tokens
        as they arrive.
        """
        result = await self.run(state, ctx)
        if result.get("error"):
            yield {"kind": "final", "update": result}
            return
        srcs = result.get("sources")
        if srcs:
            yield {"kind": "sources", "sources": srcs}
        answer = result.get("final_answer") or ""
        if answer:
            yield {"kind": "token", "text": answer}
        yield {"kind": "final", "update": result}

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.capability.name!r}>"


__all__ = ["AgentCapability", "BaseAgent"]
