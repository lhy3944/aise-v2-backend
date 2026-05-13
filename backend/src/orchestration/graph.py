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

import asyncio
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
from sqlalchemy import func as sa_func, select
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
    ClarifyData,
    ConfirmActions,
    ConfirmData,
    DecisionData,
    DoneEvent,
    DoneEventData,
    ErrorEvent,
    ErrorEventData,
    InterruptEvent,
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
from src.services import hitl_state_svc


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
    workflow.add_node("project_status", _make_agent_node("project_status", session_factory))
    workflow.add_node("requirement", _make_agent_node("requirement", session_factory))
    workflow.add_node("record_manager", _make_agent_node("record_manager", session_factory))

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "knowledge_qa": "knowledge_qa",
            "project_status": "project_status",
            "requirement": "requirement",
            "record_manager": "record_manager",
            # Supervisor may emit `plan`; until increment 2 wires the
            # planner node, we terminate the graph so the fallback
            # clarification path in run_chat still emits a clean stream.
            "planner": END,
            "end": END,
        },
    )
    workflow.add_edge("knowledge_qa", END)
    workflow.add_edge("project_status", END)
    workflow.add_edge("requirement", END)
    workflow.add_edge("record_manager", END)

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
    approved_count = state.get("records_approved_count")
    if isinstance(approved_count, int):
        payload["records_approved_count"] = approved_count
    srs = state.get("srs_generated")
    if isinstance(srs, dict):
        if "section_count" in srs:
            payload["section_count"] = srs["section_count"]
        if "version" in srs:
            payload["srs_version"] = srs["version"]
    design = state.get("design_generated")
    if isinstance(design, dict):
        if "section_count" in design:
            payload["section_count"] = design["section_count"]
        if "version" in design:
            payload["design_version"] = design["version"]
        if "based_on_srs_version" in design:
            payload["srs_version"] = design["based_on_srs_version"]
    sm = state.get("system_model_generated")
    if isinstance(sm, dict):
        if "section_count" in sm:
            payload["system_model_section_count"] = sm["section_count"]
        if "version" in sm:
            payload["system_model_version"] = sm["version"]
    dm = state.get("data_model_generated")
    if isinstance(dm, dict):
        if "section_count" in dm:
            payload["data_model_section_count"] = dm["section_count"]
        if "version" in dm:
            payload["data_model_version"] = dm["version"]
    tcs = state.get("testcases_generated")
    if isinstance(tcs, dict):
        if "testcase_count" in tcs:
            payload["testcase_count"] = tcs["testcase_count"]
        if "srs_version" in tcs:
            payload["srs_version"] = tcs["srs_version"]
    critic = state.get("critic_report")
    if isinstance(critic, dict):
        if "passed" in critic:
            payload["critic_passed"] = critic["passed"]
        if "checked_citations" in critic:
            payload["checked_citations"] = critic["checked_citations"]
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
    allow_interrupt: bool = True,
) -> AsyncGenerator[Any, None]:
    """Consume an agent's `run_stream` and forward SSE events.

    Yields a terminal sentinel `{"__final__": dict}` (dict event, not a
    pydantic model) so the caller can pick up the merged state update
    for `tool_result` composition. All SSE models come through the same
    generator so the caller just re-yields everything but the sentinel.

    `allow_interrupt=False` 인 경로(현재는 plan 실행)에서는 에이전트가
    interrupt 를 발행해도 SSE 로 흘리지 않고 즉시 종료한다. PR-3 에서
    plan-path HITL 통합 시 True 로 전환 + 별도 처리 추가.
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
        elif kind == "partial":
            # 누적 state 갱신용 — interrupt 발행 전에 추출 결과 등을
            # accumulated_state 에 보관해 resume 시 복원할 수 있게 한다.
            update = ev.get("update")
            if isinstance(update, dict) and update:
                yield {"__partial__": update}
        elif kind == "interrupt":
            data = ev.get("data")
            if isinstance(data, (ClarifyData, ConfirmData, DecisionData)):
                if allow_interrupt:
                    yield InterruptEvent(data=data)
                    yield {"__interrupted__": data}
                else:
                    logger.warning(
                        f"agent {agent_name} issued an interrupt under "
                        "allow_interrupt=False; suppressed (PR-3 will support)"
                    )
                return
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
                    allow_interrupt=False,  # plan-path HITL 은 PR-3
                ):
                    if isinstance(ev, dict) and "__final__" in ev:
                        step_update = ev["__final__"]
                    elif isinstance(ev, dict) and "__partial__" in ev:
                        shared_state.update(ev["__partial__"])
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

    # 1. Retrieval gate — RAG score/rag_cache만 후보 신호로 수집.
    # 라우팅 결정권은 Supervisor에게 있다.
    gate_result = None
    try:
        project_uuid_for_gate = uuid.UUID(str(project_id))
    except (ValueError, TypeError):
        project_uuid_for_gate = None

    if session_factory is not None and project_uuid_for_gate is not None:
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

    # rag_cache는 knowledge_qa가 재사용하므로 state에 저장.
    # routing은 무시 — Supervisor가 최종 결정.
    if gate_result is not None:
        initial_state["rag_cache"] = gate_result.rag_cache

    # 2. ProjectContextSnapshot 구성 (Supervisor 입력용)
    if session_factory is not None and project_uuid_for_gate is not None:
        from src.orchestration.context import build_project_context

        rag_signal: dict[str, Any] | None = None
        if gate_result is not None and gate_result.rag_cache:
            rag_signal = {
                "max_score": gate_result.rag_cache.get("max_score"),
                "rewritten_query": gate_result.rag_cache.get("rewritten_query"),
            }
        try:
            async with session_factory() as db:
                snapshot = await build_project_context(
                    db, project_uuid_for_gate, rag_signal=rag_signal,
                )
                initial_state["project_context"] = snapshot
                if rag_signal:
                    initial_state["rag_signal"] = rag_signal
        except Exception:  # pragma: no cover — snapshot 실패는 치명적 아님
            logger.exception("build_project_context failed, proceeding without snapshot")

    # 3. Supervisor — tool-calling or JSON-based routing.
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

    # 3a. 생성 에이전트에 대한 사전 확인(confirm) interrupt.
    # 산출물 생성/수정/삭제는 되돌리기 어려운 작업이므로, 사용자에게
    # 한 번 더 확인한 후 진행한다. 기존 HITL resume 메커니즘을 그대로
    # 활용한다 — 사용자가 승인하면 resume_chat이 같은 에이전트를 재실행한다.
    _GENERATION_CONFIRM_AGENTS = frozenset({
        "srs_generator",
        "system_model_generator",
        "data_model_generator",
        "design_generator",
        "testcase_generator",
        "requirement",
    })

    if selected in _GENERATION_CONFIRM_AGENTS:
        try:
            project_uuid = uuid.UUID(str(project_id))
        except (ValueError, TypeError):
            project_uuid = None

        try:
            session_uuid = uuid.UUID(str(session_id))
        except (ValueError, TypeError):
            session_uuid = None

        interrupt_id = f"confirm_gen_{uuid.uuid4().hex[:12]}"

        _AGENT_LABELS: dict[str, str] = {
            "srs_generator": "SRS 문서 생성",
            "system_model_generator": "시스템 모델 생성",
            "data_model_generator": "데이터 모델 생성",
            "design_generator": "Design 문서 생성",
            "testcase_generator": "테스트케이스 생성",
            "requirement": "요구사항 레코드 추출",
        }
        action_label = _AGENT_LABELS.get(selected, selected)

        # 조사 자동 선택: 받침 있으면 '을', 없으면 '를'
        def _with_particle(word: str) -> str:
            if not word:
                return word
            last = word[-1]
            has_final = (ord(last) - 0xAC00) % 28 != 0
            return f"{word}{'을' if has_final else '를'}"

        # 기존 산출물 조회 — 있으면 "재생성" 안내
        existing_count = 0
        latest_version: int | None = None
        _ARTIFACT_TYPE_MAP: dict[str, str] = {
            "srs_generator": "srs",
            "system_model_generator": "system_model",
            "data_model_generator": "data_model",
            "design_generator": "design",
            "testcase_generator": "testcase",
            "requirement": "record",
        }
        artifact_type = _ARTIFACT_TYPE_MAP.get(selected)
        if session_factory is not None and project_uuid is not None and artifact_type:
            async with session_factory() as db:
                from src.models.artifact import Artifact as ArtifactModel
                from src.models.artifact import ArtifactVersion
                count_row = await db.execute(
                    select(sa_func.count()).where(
                        ArtifactModel.project_id == project_uuid,
                        ArtifactModel.artifact_type == artifact_type,
                        ArtifactModel.lifecycle_status == "active",
                    )
                )
                existing_count = count_row.scalar() or 0

                # 최신 버전 번호 조회
                if existing_count > 0:
                    from sqlalchemy import func as sa_func_mod
                    max_vn_row = await db.execute(
                        select(sa_func_mod.max(ArtifactVersion.version_number))
                        .join(ArtifactModel, ArtifactModel.id == ArtifactVersion.artifact_id)
                        .where(
                            ArtifactModel.project_id == project_uuid,
                            ArtifactModel.artifact_type == artifact_type,
                            ArtifactModel.lifecycle_status == "active",
                        )
                    )
                    latest_version = max_vn_row.scalar()

        is_regenerate = existing_count > 0
        if is_regenerate:
            version_info = f"최신 v{latest_version}" if latest_version else f"{existing_count}개"
            next_version = f"v{(latest_version or 0) + 1}"
            title = f"현재 {version_info}까지 생성됨. {next_version}으로 {_with_particle(action_label)} 진행할까요?"
            description = (
                f"승인하면 {next_version}이 추가됩니다. 기존 버전은 유지됩니다."
            )
            approve_label = f"{next_version} 생성"
            intro_text = f"현재 {version_info}의 결과가 있습니다. {next_version}으로 {_with_particle(action_label)} 진행할까요?"
        else:
            title = f"{_with_particle(action_label)} 진행할까요?"
            description = (
                f"{action_label} 작업을 실행합니다. "
                "이 작업은 실행 후 되돌리기 어려울 수 있습니다."
            )
            approve_label = "실행"
            intro_text = f"{_with_particle(action_label)} 진행하기 전에 확인이 필요합니다."

        confirm_data = ConfirmData(
            interrupt_id=interrupt_id,
            title=title,
            description=description,
            severity="info" if is_regenerate else "warning",
            context={"artifact_kind": selected, "existing_count": existing_count, "is_regenerate": is_regenerate},
            actions=ConfirmActions(
                approve=approve_label,
                reject="취소",
            ),
        )

        # HITL state 저장 — resume 시 같은 에이전트를 실행하도록.
        # hitl_response.approved=True 면 바로 에이전트 실행으로 진입.
        await hitl_state_svc.save_persistent(
            session_factory,
            hitl_state_svc.HitlState(
                thread_id=interrupt_id,
                session_id=str(session_id),
                project_id=str(project_id),
                user_input=user_input,
                selected_agent=selected,
                interrupt_id=interrupt_id,
                interrupt_kind="confirm",
                payload=confirm_data.model_dump(),
                history=history or [],
                routing=initial_state.get("routing"),
                accumulated_state=dict(initial_state),
            ),
        )

        # interrupt 전에 짧은 설명 텍스트를 스트리밍 —
        # Confirm 카드가 자연스럽게 등장하도록 에이전트가 먼저 상황을 설명.
        # 첫 토큰 전 대기 → 스피너 노출, 토큰 분할 → 타이핑 효과.
        await asyncio.sleep(0.6)
        yield TokenEvent(data=TokenEventData(text=intro_text[:8]))
        yield TokenEvent(data=TokenEventData(text=intro_text[8:]))
        yield TokenEvent(data=TokenEventData(text="\n\n"))
        yield InterruptEvent(data=confirm_data)
        yield DoneEvent(data=DoneEventData(finish_reason="interrupt"))
        return
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
    interrupted_data: ClarifyData | ConfirmData | DecisionData | None = None
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
                elif isinstance(ev, dict) and "__interrupted__" in ev:
                    interrupted_data = ev["__interrupted__"]
                elif isinstance(ev, dict) and "__partial__" in ev:
                    initial_state.update(ev["__partial__"])  # type: ignore[typeddict-item]
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

    if interrupted_data is not None:
        # HITL: 에이전트가 일시 정지를 요청. state 저장 후 SSE 종료.
        # resume 라우터가 thread_id (= interrupt_id) 로 hitl_state 를
        # 조회해 동일 에이전트의 run_stream 을 재개한다.
        await hitl_state_svc.save_persistent(
            session_factory,
            hitl_state_svc.HitlState(
                thread_id=interrupted_data.interrupt_id,
                session_id=str(session_id),
                project_id=str(project_id),
                user_input=user_input,
                selected_agent=selected,
                interrupt_id=interrupted_data.interrupt_id,
                interrupt_kind=interrupted_data.kind,
                payload=interrupted_data.model_dump(),
                history=history or [],
                routing=initial_state.get("routing"),
                accumulated_state=dict(initial_state),
            ),
        )
        yield DoneEvent(data=DoneEventData(finish_reason="interrupt"))
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


async def resume_chat(
    thread_id: str,
    response: dict[str, Any],
    *,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Any, None]:
    """HITL 일시 정지 상태에서 SSE 스트림을 재개.

    `hitl_state_svc.get_persistent(thread_id)` 로 저장된 컨텍스트(선택 에이전트, 누적
    state, history)를 복원한 뒤, 사용자 응답을 `state["hitl_response"]` 와
    `state["hitl_interrupt_id"]` 로 주입하고 같은 에이전트의 `run_stream`
    을 재호출한다. 에이전트는 첫 번째 yield 가 interrupt 였던 위치의 다음
    단계부터 진행하도록 자체 분기를 두어야 한다 (PR-2 의 책임).

    재개 도중 또 다른 interrupt 가 발행되면 새 thread_id 로 다시 저장된다.
    성공 종료 시 hitl_state 는 삭제된다.
    """
    saved = await hitl_state_svc.get_persistent(session_factory, thread_id)
    if saved is None:
        yield ErrorEvent(
            data=ErrorEventData(
                message=f"hitl thread not found or expired: {thread_id!r}",
                code="HITL_THREAD_NOT_FOUND",
                recoverable=False,
            )
        )
        return

    agent = try_get_agent(saved.selected_agent)
    if agent is None:
        yield ErrorEvent(
            data=ErrorEventData(
                message=f"unknown agent on resume: {saved.selected_agent!r}",
                code="AGENT_ERROR",
                recoverable=False,
            )
        )
        return

    try:
        project_uuid = uuid.UUID(saved.project_id)
        session_uuid: uuid.UUID | None = uuid.UUID(saved.session_id)
    except (ValueError, TypeError):
        yield ErrorEvent(
            data=ErrorEventData(
                message="invalid project_id/session_id in saved hitl state",
                code="HITL_STATE_INVALID",
                recoverable=False,
            )
        )
        return

    state: AgentState = dict(saved.accumulated_state)  # type: ignore[assignment]
    state["hitl_interrupt_id"] = thread_id
    state["hitl_response"] = response

    # 생성 에이전트 confirm 거부 시 — 에이전트 실행 없이 취소 메시지 반환.
    # 프론트엔드 HITLPromptModal 은 { action: 'reject' } 또는
    # { action: 'approve' } 를 전송하므로 두 형식 모두 지원.
    is_approved = response.get("approved") is True or response.get("action") == "approve"
    if saved.interrupt_kind == "confirm" and not is_approved:
        _AGENT_LABELS: dict[str, str] = {
            "srs_generator": "SRS 문서 생성",
            "system_model_generator": "시스템 모델 생성",
            "data_model_generator": "데이터 모델 생성",
            "design_generator": "Design 문서 생성",
            "testcase_generator": "테스트케이스 생성",
            "requirement": "요구사항 레코드 추출",
        }
        action_label = _AGENT_LABELS.get(saved.selected_agent, saved.selected_agent)
        cancel_msg = f"{action_label}이(가) 취소되었습니다."
        yield TokenEvent(data=TokenEventData(text=cancel_msg))
        await hitl_state_svc.delete_persistent(
            session_factory,
            thread_id,
            response=response,
        )
        yield DoneEvent(data=DoneEventData(finish_reason="stop"))
        return

    # 재개 직전에 hitl_state 삭제 — 재개 도중 새 interrupt 가 발행되면
    # _drive_agent_stream 가 새 thread_id 로 다시 save 한다.
    await hitl_state_svc.delete_persistent(
        session_factory,
        thread_id,
        response=response,
    )

    # 재생성 승인 시: 기존 산출물은 유지, 에이전트가 새 버전을 append.
    # (기존 삭제 로직 제거 — generate_srs/generate_design/regenerate_testcase
    # 가 기존 artifact 에 새 ArtifactVersion 을 추가하는 방식으로 동작)
    payload = saved.payload or {}
    _context = payload.get("context") or {}

    started = time.perf_counter()
    expose = getattr(agent.capability, "expose_as_tool", True)
    call_id = f"call_{uuid.uuid4().hex[:12]}"
    # Resume continues the tool invocation that emitted the HITL interrupt.
    # Emitting another tool_call creates a duplicate tool card in the chat UI,
    # so resume only emits the eventual tool_result for side effects.

    final_update: dict[str, Any] = {}
    interrupted_data: ClarifyData | ConfirmData | DecisionData | None = None
    try:
        async with session_factory() as db:
            ctx = AgentContext(
                db=db, project_id=project_uuid, session_id=session_uuid
            )
            async for ev in _drive_agent_stream(
                agent,
                state=state,
                ctx=ctx,
                agent_name=saved.selected_agent,
                forward_tokens=True,
            ):
                if isinstance(ev, dict) and "__final__" in ev:
                    final_update = ev["__final__"]
                elif isinstance(ev, dict) and "__interrupted__" in ev:
                    interrupted_data = ev["__interrupted__"]
                elif isinstance(ev, dict) and "__partial__" in ev:
                    state.update(ev["__partial__"])  # type: ignore[typeddict-item]
                else:
                    yield ev
    except Exception as exc:
        logger.exception(f"resume {saved.selected_agent}.run_stream failed")
        if expose:
            yield ToolResultEvent(
                data=ToolResultEventData(
                    tool_call_id=call_id,
                    name=saved.selected_agent,
                    status="error",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    result={"error": str(exc)[:200]},
                )
            )
        yield ErrorEvent(
            data=ErrorEventData(
                message=str(exc), code="AGENT_ERROR", recoverable=False,
            )
        )
        return

    if interrupted_data is not None:
        await hitl_state_svc.save_persistent(
            session_factory,
            hitl_state_svc.HitlState(
                thread_id=interrupted_data.interrupt_id,
                session_id=saved.session_id,
                project_id=saved.project_id,
                user_input=saved.user_input,
                selected_agent=saved.selected_agent,
                interrupt_id=interrupted_data.interrupt_id,
                interrupt_kind=interrupted_data.kind,
                payload=interrupted_data.model_dump(),
                history=saved.history,
                routing=saved.routing,
                accumulated_state=dict(state),
            ),
        )
        yield DoneEvent(data=DoneEventData(finish_reason="interrupt"))
        return

    if final_update.get("error"):
        if expose:
            yield ToolResultEvent(
                data=ToolResultEventData(
                    tool_call_id=call_id,
                    name=saved.selected_agent,
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
                name=saved.selected_agent,
                status="success",
                duration_ms=int((time.perf_counter() - started) * 1000),
                result=_result_payload(final_update),
            )
        )
    yield DoneEvent(data=DoneEventData(finish_reason="stop"))


__all__ = [
    "build_graph",
    "get_checkpointer",
    "resume_chat",
    "run_chat",
    "shutdown_checkpointer",
]
