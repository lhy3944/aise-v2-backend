r"""LangGraph builder + SSE event stream.

Phase 1 wiring:
    START -> supervisor -(conditional)-> knowledge_qa -> END
                          \-> end (when routing != single or agent missing)

Checkpointer policy (D7):
    - LANGGRAPH_CHECKPOINT_URL unset (default): `MemorySaver`. Fine for
      Phase 1 because no node issues `interrupt()` yet, so there is
      nothing to persist across requests.
    - LANGGRAPH_CHECKPOINT_URL set: `AsyncPostgresSaver` backed by a
      `psycopg_pool.AsyncConnectionPool`. The saver's `setup()` runs once
      (idempotent — creates the checkpoints tables if missing).

Callers who compile graphs ad-hoc (tests, scripts) can pass `checkpointer=`
directly to `build_graph`. The router path uses `get_checkpointer()` which
reads the env once and caches the saver for the process lifetime.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, AsyncGenerator, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from loguru import logger
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.agents import load_builtin_agents
from src.agents.registry import get_agent
from src.orchestration.state import AgentContext, AgentState
from src.orchestration.supervisor import (
    route_after_supervisor,
    supervisor_node,
)
from src.schemas.events import (
    DoneEvent,
    DoneEventData,
    ErrorEvent,
    ErrorEventData,
    TokenEvent,
    TokenEventData,
    ToolCallEvent,
    ToolCallEventData,
    ToolResultEvent,
    ToolResultEventData,
)


# ---------- Node helpers ----------


def _make_agent_node(name: str, session_factory: async_sessionmaker[AsyncSession]):
    """Wrap a registered agent as a LangGraph node.

    The closure captures the DB session factory so the LangGraph state can
    stay JSON-serializable.
    """

    async def node(state: AgentState) -> dict[str, Any]:
        agent = get_agent(name)
        project_id_str = state.get("project_id")
        if not project_id_str:
            return {"error": "project_id missing in state"}
        try:
            project_id = uuid.UUID(project_id_str)
        except (ValueError, TypeError):
            return {"error": f"invalid project_id: {project_id_str!r}"}

        session_id_str = state.get("session_id")
        session_id = (
            uuid.UUID(session_id_str)
            if session_id_str and isinstance(session_id_str, str)
            else None
        )

        async with session_factory() as db:
            ctx = AgentContext(db=db, project_id=project_id, session_id=session_id)
            return await agent.run(state, ctx)

    node.__name__ = f"agent_node_{name}"
    return node


# ---------- Checkpointer ----------


_pg_pool: AsyncConnectionPool | None = None
_pg_saver: AsyncPostgresSaver | None = None


def _normalise_checkpoint_url(url: str) -> str:
    """Accept SQLAlchemy-style URLs by stripping the driver dialect suffix.

    `postgresql+asyncpg://...` and `postgresql+psycopg://...` are both
    commonly pasted from DATABASE_URL; psycopg itself only parses the
    vanilla `postgresql://...` form.
    """
    for dialect in ("+asyncpg", "+psycopg2", "+psycopg"):
        if dialect in url:
            return url.replace(dialect, "", 1)
    return url


async def _init_postgres_checkpointer(url: str) -> AsyncPostgresSaver:
    """Open a shared pool and initialise the checkpoints tables once."""
    global _pg_pool, _pg_saver
    if _pg_saver is not None:
        return _pg_saver

    conninfo = _normalise_checkpoint_url(url)
    _pg_pool = AsyncConnectionPool(
        conninfo=conninfo,
        open=False,
        max_size=20,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    await _pg_pool.open()
    _pg_saver = AsyncPostgresSaver(conn=_pg_pool)
    await _pg_saver.setup()
    logger.info("LangGraph checkpointer initialised: AsyncPostgresSaver")
    return _pg_saver


async def get_checkpointer() -> BaseCheckpointSaver:
    """Return the process-wide checkpointer per D7 policy.

    No env → MemorySaver. Env set → AsyncPostgresSaver (lazy once).
    """
    url = os.getenv("LANGGRAPH_CHECKPOINT_URL")
    if url:
        return await _init_postgres_checkpointer(url)
    return MemorySaver()


async def shutdown_checkpointer() -> None:
    """Close the shared pool if one was opened. Safe to call unconditionally."""
    global _pg_pool, _pg_saver
    if _pg_pool is not None:
        await _pg_pool.close()
    _pg_pool = None
    _pg_saver = None


# ---------- Graph builder ----------


def build_graph(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Compile the Phase 1 agent graph.

    Idempotently loads built-in agents into the registry so node lookups
    succeed even on first call. Pass `checkpointer=` to override the
    default `MemorySaver`; production callers go through the router's
    `_get_graph`, which pulls from `get_checkpointer()`.
    """
    load_builtin_agents()

    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("knowledge_qa", _make_agent_node("knowledge_qa", session_factory))

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "knowledge_qa": "knowledge_qa",
            "end": END,
        },
    )
    workflow.add_edge("knowledge_qa", END)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


# ---------- SSE driver ----------


async def run_chat(
    graph,
    *,
    project_id: uuid.UUID | str,
    session_id: uuid.UUID | str,
    user_input: str,
    history: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[Any, None]:
    """Invoke the graph and yield AgentStreamEvent objects.

    Phase 1 emits a single `token` event with the final answer; real
    per-token streaming arrives with the LLM streaming integration in
    later phases. The contract in docs/events.md is honored either way.
    """
    initial_state: AgentState = {
        "project_id": str(project_id),
        "session_id": str(session_id),
        "user_input": user_input,
        "history": history or [],
    }
    config = {"configurable": {"thread_id": str(session_id)}}

    started = time.perf_counter()
    try:
        final_state: AgentState = await graph.ainvoke(initial_state, config)
    except Exception as e:
        logger.exception("graph.ainvoke failed")
        yield ErrorEvent(
            data=ErrorEventData(
                message=str(e),
                code="GRAPH_FAILURE",
                recoverable=False,
            )
        )
        return

    if final_state.get("error"):
        yield ErrorEvent(
            data=ErrorEventData(
                message=str(final_state["error"]),
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    routing = final_state.get("routing") or {}
    selected = routing.get("agent")
    if selected:
        # Surface the agent invocation as a single tool_call/tool_result pair so
        # the frontend's AgentInvocationCard can render even in Phase 1.
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        yield ToolCallEvent(
            data=ToolCallEventData(
                tool_call_id=call_id,
                name=selected,
                arguments={"user_input": user_input},
                agent=selected,
            )
        )
        sources_count = len(final_state.get("sources") or [])
        yield ToolResultEvent(
            data=ToolResultEventData(
                tool_call_id=call_id,
                name=selected,
                status="success",
                duration_ms=int((time.perf_counter() - started) * 1000),
                result={"sources_count": sources_count},
            )
        )

    answer = final_state.get("final_answer") or ""
    if answer:
        yield TokenEvent(data=TokenEventData(text=answer))

    yield DoneEvent(data=DoneEventData(finish_reason="stop"))


__all__ = [
    "build_graph",
    "get_checkpointer",
    "run_chat",
    "shutdown_checkpointer",
]
