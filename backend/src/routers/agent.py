"""Agent Chat API 라우터.

LangGraph-only: orchestration.run_chat 기반. SSE AgentStreamEvent envelope
`{"type": "...", "data": {...}}` per docs/events.md.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import get_db, get_session_factory
from src.models.session import Session as SessionModel
from src.orchestration.graph import build_graph, get_checkpointer, resume_chat, run_chat
from src.schemas.api.agent import AgentChatRequest
from src.schemas.events import ResumeRequest
from src.services import hitl_state_svc, session_svc

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# Lazy per-factory graph cache. Compiling a LangGraph StateGraph captures
# the session factory inside node closures, so if tests (or multiple
# environments) inject a different factory via Depends(get_session_factory),
# we need a separate compiled graph per factory instance. Keyed by id()
# because async_sessionmaker is not hashable in general.
_graph_cache: dict[int, object] = {}


async def _get_graph(session_factory: async_sessionmaker[AsyncSession]):
    key = id(session_factory)
    graph = _graph_cache.get(key)
    if graph is None:
        logger.info("Compiling LangGraph orchestrator for factory id=%s", key)
        checkpointer = await get_checkpointer()
        graph = build_graph(session_factory, checkpointer=checkpointer)
        _graph_cache[key] = graph
    return graph


async def _resolve_project_id(session_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    result = await db.execute(
        select(SessionModel.project_id).where(SessionModel.id == session_id)
    )
    project_id = result.scalar_one_or_none()
    if project_id is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return project_id


async def _stream_chat(
    session_id: uuid.UUID,
    message: str,
    session_factory: async_sessionmaker[AsyncSession],
):
    """SSE generator using the AgentStreamEvent envelope per docs/events.md.

    Persists the turn to `session_messages`:
      1. 과거 history 로드 (현재 user 입력 제외) → LangGraph에 전달
      2. user 메시지 commit (실행 전 — 에이전트 실패해도 사용자 입력은 보존)
      3. 스트림 진행하면서 token/tool_call/sources 수집
      4. finally에서 assistant 메시지 commit
    """
    async with session_factory() as db:
        try:
            project_id = await _resolve_project_id(session_id, db)
        except HTTPException as e:
            payload = (
                f'{{"type":"error","data":{{"message":"{e.detail}","code":"SESSION_NOT_FOUND",'
                f'"recoverable":false}}}}'
            )
            yield f"data: {payload}\n\n"
            return

        history = await session_svc.get_history(db, session_id, limit=50)
        await session_svc.add_message(db, session_id, role="user", content=message)
        await session_svc.update_session_title_if_first(db, session_id, message)
        await db.commit()

    graph = await _get_graph(session_factory)
    assistant_parts: list[str] = []
    # tool_call_id → 누적 entry. tool_result 이벤트가 도착하면 동일 id에
    # duration_ms/status/result를 덧붙여 저장용 레코드를 완성한다.
    tool_calls_by_id: dict[str, dict[str, Any]] = {}
    tool_call_order: list[str] = []
    sources_acc: list[dict[str, Any]] | None = None
    had_error = False

    try:
        async for event in run_chat(
            graph,
            project_id=project_id,
            session_id=session_id,
            user_input=message,
            history=history,
            session_factory=session_factory,
        ):
            etype = event.type
            if etype == "token":
                assistant_parts.append(event.data.text)
            elif etype == "tool_call":
                tcid = event.data.tool_call_id
                tool_calls_by_id[tcid] = {
                    "name": event.data.name,
                    "arguments": event.data.arguments,
                }
                tool_call_order.append(tcid)
            elif etype == "tool_result":
                tcid = event.data.tool_call_id
                entry = tool_calls_by_id.get(tcid)
                if entry is not None:
                    if event.data.duration_ms is not None:
                        entry["duration_ms"] = event.data.duration_ms
                    if event.data.status is not None:
                        entry["status"] = event.data.status
                    if event.data.result is not None:
                        entry["result"] = event.data.result
            elif etype == "sources":
                sources_acc = [s.model_dump() for s in event.data.sources]
            elif etype == "error":
                had_error = True
            yield f"data: {event.model_dump_json()}\n\n"
    finally:
        content = "".join(assistant_parts)
        tool_calls_acc = [tool_calls_by_id[tcid] for tcid in tool_call_order]
        # 빈 content + tool_call/sources/에러도 없으면 저장하지 않음
        if content or tool_calls_acc or sources_acc or had_error:
            try:
                async with session_factory() as db:
                    tool_data = {"sources": sources_acc} if sources_acc else None
                    await session_svc.add_message(
                        db,
                        session_id,
                        role="assistant",
                        content=content,
                        tool_calls=tool_calls_acc or None,
                        tool_data=tool_data,
                    )
                    await db.commit()
            except Exception:
                logger.exception(
                    "Failed to persist assistant message for session %s", session_id
                )


@router.post("/chat")
async def agent_chat(
    body: AgentChatRequest,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """Agent Chat SSE 엔드포인트."""
    logger.info(f"agent/chat: session={body.session_id}")
    return StreamingResponse(
        _stream_chat(body.session_id, body.message, session_factory),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _stream_resume(
    thread_id: str,
    body: ResumeRequest,
    session_factory: async_sessionmaker[AsyncSession],
):
    """HITL resume SSE generator.

    `hitl_state_svc` 에서 저장 컨텍스트를 조회 → resume_chat 으로 SSE 재개
    → 응답 turn 을 session_messages 에 append 한다. body.interrupt_id 는
    경로의 thread_id 와 일치해야 한다 (CSRF/오접속 방지).
    """
    if body.interrupt_id != thread_id:
        payload = (
            f'{{"type":"error","data":{{"message":"interrupt_id mismatch",'
            f'"code":"HITL_ID_MISMATCH","recoverable":false}}}}'
        )
        yield f"data: {payload}\n\n"
        return

    saved = hitl_state_svc.get(thread_id)
    if saved is None:
        payload = (
            f'{{"type":"error","data":{{"message":"hitl thread not found or expired",'
            f'"code":"HITL_THREAD_NOT_FOUND","recoverable":false}}}}'
        )
        yield f"data: {payload}\n\n"
        return

    try:
        session_uuid = uuid.UUID(saved.session_id)
    except (ValueError, TypeError):
        payload = (
            f'{{"type":"error","data":{{"message":"invalid session_id in hitl state",'
            f'"code":"HITL_STATE_INVALID","recoverable":false}}}}'
        )
        yield f"data: {payload}\n\n"
        return

    assistant_parts: list[str] = []
    tool_calls_by_id: dict[str, dict[str, Any]] = {}
    tool_call_order: list[str] = []
    sources_acc: list[dict[str, Any]] | None = None
    had_error = False

    try:
        async for event in resume_chat(
            thread_id, body.response, session_factory=session_factory,
        ):
            etype = event.type
            if etype == "token":
                assistant_parts.append(event.data.text)
            elif etype == "tool_call":
                tcid = event.data.tool_call_id
                tool_calls_by_id[tcid] = {
                    "name": event.data.name,
                    "arguments": event.data.arguments,
                }
                tool_call_order.append(tcid)
            elif etype == "tool_result":
                tcid = event.data.tool_call_id
                entry = tool_calls_by_id.get(tcid)
                if entry is not None:
                    if event.data.duration_ms is not None:
                        entry["duration_ms"] = event.data.duration_ms
                    if event.data.status is not None:
                        entry["status"] = event.data.status
                    if event.data.result is not None:
                        entry["result"] = event.data.result
            elif etype == "sources":
                sources_acc = [s.model_dump() for s in event.data.sources]
            elif etype == "error":
                had_error = True
            yield f"data: {event.model_dump_json()}\n\n"
    finally:
        content = "".join(assistant_parts)
        tool_calls_acc = [tool_calls_by_id[tcid] for tcid in tool_call_order]
        if content or tool_calls_acc or sources_acc or had_error:
            try:
                async with session_factory() as db:
                    tool_data = {"sources": sources_acc} if sources_acc else None
                    await session_svc.add_message(
                        db,
                        session_uuid,
                        role="assistant",
                        content=content,
                        tool_calls=tool_calls_acc or None,
                        tool_data=tool_data,
                    )
                    await db.commit()
            except Exception:
                logger.exception(
                    "Failed to persist resume assistant message for session %s",
                    session_uuid,
                )


@router.post("/resume/{thread_id}")
async def agent_resume(
    thread_id: str,
    body: ResumeRequest,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """HITL 일시 정지 상태에서 사용자 응답으로 SSE 스트림을 재개."""
    logger.info(f"agent/resume: thread={thread_id}")
    return StreamingResponse(
        _stream_resume(thread_id, body, session_factory),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
