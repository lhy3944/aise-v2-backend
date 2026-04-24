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
from src.agents.base import BaseAgent
from src.agents.registry import get_agent, try_get_agent
from src.orchestration.retrieval_gate import evaluate_gate
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
    PlanStep,
    PlanUpdateEvent,
    PlanUpdateEventData,
    SourceRef,
    SourcesEvent,
    SourcesEventData,
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
    workflow.add_node("requirement", _make_agent_node("requirement", session_factory))

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "knowledge_qa": "knowledge_qa",
            "requirement": "requirement",
            # Supervisor may emit `plan`; until increment 2 wires the
            # planner node, we terminate the graph so the fallback
            # clarification path in run_chat still emits a clean stream.
            "planner": END,
            "end": END,
        },
    )
    workflow.add_edge("knowledge_qa", END)
    workflow.add_edge("requirement", END)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


# ---------- SSE driver ----------


def _result_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Derive the `tool_result.result` payload from an agent's state update.

    Includes counters that are present; absent keys stay out of the dict
    so the frontend's AgentInvocationCard only renders what the agent
    actually produced.
    """
    payload: dict[str, Any] = {}
    sources = state.get("sources")
    if sources is not None:
        payload["sources_count"] = len(sources)
    extracted = state.get("records_extracted")
    if extracted is not None:
        payload["records_count"] = len(extracted)
    return payload


def _sources_event(raw: Any, *, agent: str | None) -> SourcesEvent | None:
    """Build a SourcesEvent from the `sources` list an agent stored in state.

    Agents emit `rag_svc`-style dicts (document_id, document_name,
    chunk_index, content, score, file_type?); we renumber them into the
    frontend's 1-based `ref` contract and forward the preview/metadata.
    Returns None when the list is empty or malformed so the caller can
    just skip the yield.
    """
    if not raw or not isinstance(raw, list):
        return None
    refs: list[SourceRef] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        doc_id = item.get("document_id")
        doc_name = item.get("document_name")
        chunk_index = item.get("chunk_index")
        if doc_id is None or doc_name is None or chunk_index is None:
            continue
        content = item.get("content")
        refs.append(
            SourceRef(
                ref=idx,
                document_id=str(doc_id),
                document_name=str(doc_name),
                chunk_index=int(chunk_index),
                file_type=item.get("file_type"),
                content_preview=str(content) if isinstance(content, str) else None,
                score=item.get("score") if isinstance(item.get("score"), (int, float)) else None,
            )
        )
    if not refs:
        return None
    return SourcesEvent(data=SourcesEventData(sources=refs, agent=agent))


async def _drive_agent_stream(
    agent: BaseAgent,
    *,
    state: AgentState,
    ctx: AgentContext,
    agent_name: str,
    forward_tokens: bool,
) -> AsyncGenerator[Any, None]:
    """Consume an agent's `run_stream` and forward SSE events.

    Yields a terminal sentinel `{"__final__": dict}` (dict event, not a
    pydantic model) so the caller can pick up the merged state update
    for `tool_result` composition. All SSE models come through the same
    generator so the caller just re-yields everything but the sentinel.
    """
    async for ev in agent.run_stream(state, ctx):
        kind = ev.get("kind")
        if kind == "sources":
            s_ev = _sources_event(ev.get("sources"), agent=agent_name)
            if s_ev is not None:
                yield s_ev
        elif kind == "token" and forward_tokens:
            text = ev.get("text", "")
            if text:
                yield TokenEvent(data=TokenEventData(text=text))
        elif kind == "final":
            yield {"__final__": ev.get("update", {}) or {}}
            return


async def _execute_plan(
    plan_names: list[str],
    *,
    initial_state: AgentState,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Any, None]:
    """Run a plan sequentially, emitting plan_update + per-step tool events.

    Yielded event sequence per plan:
        plan_update(all pending)
        for each step i:
            plan_update(step i running)
            tool_call(agent_i)
            [sources(agent_i)]
            [token × N]     — only from the *last* step; intermediates
                              propagate into shared_state but stay silent
            tool_result(agent_i, success|error)
            plan_update(step i completed|failed)

    Terminates early on the first failed step (remaining steps stay
    `pending`). The caller (run_chat) emits the DoneEvent after this
    generator drains.
    """
    from datetime import datetime, timezone

    steps: list[PlanStep] = [
        PlanStep(agent=name, status="pending") for name in plan_names
    ]

    def _plan_update(current: int | None) -> PlanUpdateEvent:
        return PlanUpdateEvent(
            data=PlanUpdateEventData(
                plan=[s.model_copy() for s in steps],
                current_step=current,
            )
        )

    yield _plan_update(current=None)

    project_id_str = initial_state.get("project_id")
    session_id_str = initial_state.get("session_id")
    try:
        project_id = uuid.UUID(project_id_str) if project_id_str else None
    except (ValueError, TypeError):
        project_id = None

    if project_id is None:
        for step in steps:
            step.status = "failed"
            step.result_summary = "invalid project_id"
        yield _plan_update(current=None)
        yield ErrorEvent(
            data=ErrorEventData(
                message=f"invalid project_id: {project_id_str!r}",
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    session_id = (
        uuid.UUID(session_id_str)
        if isinstance(session_id_str, str) and session_id_str
        else None
    )

    shared_state: dict[str, Any] = dict(initial_state)

    # One session for the whole plan — agents only read, so sharing keeps
    # connection churn minimal under pytest's NullPool.
    async with session_factory() as db:
        ctx = AgentContext(db=db, project_id=project_id, session_id=session_id)

        for idx, name in enumerate(plan_names):
            step = steps[idx]
            agent = try_get_agent(name)
            if agent is None:
                step.status = "failed"
                step.completed_at = datetime.now(timezone.utc)
                step.result_summary = f"unknown agent {name!r}"
                yield _plan_update(current=idx)
                yield ErrorEvent(
                    data=ErrorEventData(
                        message=f"unknown agent in plan: {name!r}",
                        code="AGENT_ERROR",
                        recoverable=False,
                    )
                )
                return

            step.status = "running"
            step.started_at = datetime.now(timezone.utc)
            yield _plan_update(current=idx)

            # Conversational agents are step-visible via plan_update but
            # don't render their own tool invocation card.
            expose = getattr(agent.capability, "expose_as_tool", True)

            call_id = f"call_{uuid.uuid4().hex[:12]}"
            step_started = time.perf_counter()
            if expose:
                yield ToolCallEvent(
                    data=ToolCallEventData(
                        tool_call_id=call_id,
                        name=name,
                        arguments={"user_input": shared_state.get("user_input", "")},
                        agent=name,
                    )
                )

            is_last = idx == len(plan_names) - 1
            step_update: dict[str, Any] = {}
            try:
                async for ev in _drive_agent_stream(
                    agent,
                    state=shared_state,  # type: ignore[arg-type]
                    ctx=ctx,
                    agent_name=name,
                    forward_tokens=is_last,
                ):
                    if isinstance(ev, dict) and "__final__" in ev:
                        step_update = ev["__final__"]
                    else:
                        yield ev
            except Exception as exc:  # pragma: no cover — defensive
                logger.exception(f"Plan step {name} raised")
                step.status = "failed"
                step.completed_at = datetime.now(timezone.utc)
                step.result_summary = str(exc)[:200]
                if expose:
                    yield ToolResultEvent(
                        data=ToolResultEventData(
                            tool_call_id=call_id,
                            name=name,
                            status="error",
                            duration_ms=int((time.perf_counter() - step_started) * 1000),
                            result={"error": str(exc)[:200]},
                        )
                    )
                yield _plan_update(current=idx)
                yield ErrorEvent(
                    data=ErrorEventData(
                        message=str(exc),
                        code="AGENT_ERROR",
                        recoverable=False,
                    )
                )
                return

            if step_update.get("error"):
                step.status = "failed"
                step.completed_at = datetime.now(timezone.utc)
                step.result_summary = str(step_update["error"])[:200]
                if expose:
                    yield ToolResultEvent(
                        data=ToolResultEventData(
                            tool_call_id=call_id,
                            name=name,
                            status="error",
                            duration_ms=int((time.perf_counter() - step_started) * 1000),
                            result={"error": str(step_update["error"])[:200]},
                        )
                    )
                yield _plan_update(current=idx)
                yield ErrorEvent(
                    data=ErrorEventData(
                        message=str(step_update["error"]),
                        code="AGENT_ERROR",
                        recoverable=False,
                    )
                )
                return

            # Merge step output into shared state so the next agent sees
            # accumulated context (e.g. requirement's records_extracted
            # visible to a downstream srs_generator).
            shared_state.update(step_update)

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc)
            summary = step_update.get("final_answer") or ""
            step.result_summary = summary[:200] if summary else None

            if expose:
                yield ToolResultEvent(
                    data=ToolResultEventData(
                        tool_call_id=call_id,
                        name=name,
                        status="success",
                        duration_ms=int((time.perf_counter() - step_started) * 1000),
                        result=_result_payload(step_update),
                    )
                )
            yield _plan_update(current=idx)


async def run_chat(
    graph,  # preserved for backward compat; streaming path bypasses graph.ainvoke
    *,
    project_id: uuid.UUID | str,
    session_id: uuid.UUID | str,
    user_input: str,
    history: list[dict[str, Any]] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncGenerator[Any, None]:
    """Route via the supervisor and stream the selected agent's tokens.

    Streaming contract (single path):
        tool_call → [sources] → token × N → tool_result → done

    The `graph` parameter is retained so existing callers (router,
    scripts, plan tests) can compile a `StateGraph` and pass it in; the
    common paths now bypass `graph.ainvoke` and drive
    `supervisor_node` + `agent.run_stream` directly. This keeps
    `_execute_plan` composable and makes token-level streaming possible
    without reaching for LangGraph's custom writer plumbing.
    """
    initial_state: AgentState = {
        "project_id": str(project_id),
        "session_id": str(session_id),
        "user_input": user_input,
        "history": history or [],
    }

    # 1a. Retrieval-first gate — 결정적 게이트. 통과 시 supervisor LLM을
    # 건너뛰고 knowledge_qa로 직결한다. 통과하지 못하면(가벼운 질의·문서
    # 없음·score 미달) supervisor LLM이 판단한다.
    gate_result = None
    if session_factory is not None:
        try:
            project_uuid_for_gate = uuid.UUID(str(project_id))
        except (ValueError, TypeError):
            project_uuid_for_gate = None
        if project_uuid_for_gate is not None:
            try:
                async with session_factory() as db:
                    gate_result = await evaluate_gate(
                        user_input=user_input,
                        history=history or [],
                        project_id=project_uuid_for_gate,
                        db=db,
                    )
            except Exception:  # pragma: no cover — gate 실패는 LLM로 폴백
                logger.exception("retrieval_gate failed, falling back to supervisor LLM")
                gate_result = None

    if gate_result is not None:
        initial_state["routing"] = gate_result.routing
        initial_state["rag_cache"] = gate_result.rag_cache
    else:
        # 1b. Supervisor — direct call, no graph invocation needed.
        try:
            supervisor_update = await supervisor_node(initial_state)
        except Exception as e:  # pragma: no cover — defensive
            logger.exception("supervisor_node failed")
            yield ErrorEvent(
                data=ErrorEventData(
                    message=str(e),
                    code="SUPERVISOR_FAILURE",
                    recoverable=False,
                )
            )
            return
        initial_state.update(supervisor_update)

    if initial_state.get("error"):
        yield ErrorEvent(
            data=ErrorEventData(
                message=str(initial_state["error"]),
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    routing = initial_state.get("routing") or {}
    action = routing.get("action")

    # 2. Terminal routings (clarify / plan) are handled in-place.
    if action == "clarify":
        question = routing.get("clarification") or "조금 더 구체적으로 말씀해주시겠어요?"
        yield TokenEvent(data=TokenEventData(text=question))
        yield DoneEvent(data=DoneEventData(finish_reason="stop"))
        return

    if action == "plan":
        plan_names = routing.get("plan") or []
        if session_factory is not None and plan_names:
            async for ev in _execute_plan(
                plan_names,
                initial_state=initial_state,
                session_factory=session_factory,
            ):
                yield ev
        else:
            # Fallback: no factory available (unit tests, ad-hoc callers).
            yield TokenEvent(
                data=TokenEventData(
                    text=f"(plan 실행은 아직 준비 중입니다: {', '.join(plan_names)})",
                )
            )
        yield DoneEvent(data=DoneEventData(finish_reason="stop"))
        return

    # 3. Single-agent route — stream the agent directly.
    selected = routing.get("agent") if action == "single" else None
    if not selected:
        # Unknown/unhandled routing (shouldn't happen with current supervisor
        # fallbacks, but keep the stream well-formed).
        yield DoneEvent(data=DoneEventData(finish_reason="stop"))
        return

    agent = try_get_agent(selected)
    if agent is None:
        yield ErrorEvent(
            data=ErrorEventData(
                message=f"unknown agent: {selected!r}",
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    if session_factory is None:
        # Ad-hoc callers (legacy unit tests) without a factory — emit a
        # minimal stream so tests can still assert the shape.
        yield DoneEvent(data=DoneEventData(finish_reason="stop"))
        return

    try:
        project_uuid = uuid.UUID(str(project_id))
    except (ValueError, TypeError):
        yield ErrorEvent(
            data=ErrorEventData(
                message=f"invalid project_id: {project_id!r}",
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    try:
        session_uuid: uuid.UUID | None = uuid.UUID(str(session_id))
    except (ValueError, TypeError):
        session_uuid = None

    # Conversational agents (capability.expose_as_tool=False) are "the
    # agent IS the response" — suppress tool_call/tool_result SSE so the
    # UI doesn't render a bogus invocation card around plain answers.
    expose = getattr(agent.capability, "expose_as_tool", True)

    call_id = f"call_{uuid.uuid4().hex[:12]}"
    if expose:
        yield ToolCallEvent(
            data=ToolCallEventData(
                tool_call_id=call_id,
                name=selected,
                arguments={"user_input": user_input},
                agent=selected,
            )
        )

    started = time.perf_counter()
    final_update: dict[str, Any] = {}
    try:
        async with session_factory() as db:
            ctx = AgentContext(
                db=db, project_id=project_uuid, session_id=session_uuid
            )
            async for ev in _drive_agent_stream(
                agent,
                state=initial_state,
                ctx=ctx,
                agent_name=selected,
                forward_tokens=True,
            ):
                if isinstance(ev, dict) and "__final__" in ev:
                    final_update = ev["__final__"]
                else:
                    yield ev
    except Exception as exc:
        logger.exception(f"{selected}.run_stream failed")
        if expose:
            yield ToolResultEvent(
                data=ToolResultEventData(
                    tool_call_id=call_id,
                    name=selected,
                    status="error",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    result={"error": str(exc)[:200]},
                )
            )
        yield ErrorEvent(
            data=ErrorEventData(
                message=str(exc),
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    if final_update.get("error"):
        if expose:
            yield ToolResultEvent(
                data=ToolResultEventData(
                    tool_call_id=call_id,
                    name=selected,
                    status="error",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    result={"error": str(final_update["error"])[:200]},
                )
            )
        yield ErrorEvent(
            data=ErrorEventData(
                message=str(final_update["error"]),
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    if expose:
        yield ToolResultEvent(
            data=ToolResultEventData(
                tool_call_id=call_id,
                name=selected,
                status="success",
                duration_ms=int((time.perf_counter() - started) * 1000),
                result=_result_payload(final_update),
            )
        )
    yield DoneEvent(data=DoneEventData(finish_reason="stop"))


__all__ = [
    "build_graph",
    "get_checkpointer",
    "run_chat",
    "shutdown_checkpointer",
]
