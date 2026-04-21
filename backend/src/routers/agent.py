"""Agent Chat API 라우터.

Phase 1: feature-flag based dual path.

- USE_LANGGRAPH=false (default): legacy path through services.agent_svc
  (the prototype's OpenAI Function Calling loop). Emits the legacy SSE
  envelope `{"type": "...", "content": "...", ...}` (flat).

- USE_LANGGRAPH=true: new path through orchestration.run_chat. Emits the
  AgentStreamEvent envelope `{"type": "...", "data": {...}}` per
  docs/events.md.

The two paths share the same endpoint URL so the frontend's USE_LANGGRAPH
choice can be made by env. Phase 2 will retire the legacy path.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import get_db, get_session_factory
from src.models.session import Session as SessionModel
from src.orchestration.graph import build_graph, get_checkpointer, run_chat
from src.schemas.api.agent import AgentChatRequest
from src.services import agent_svc

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _use_langgraph() -> bool:
    return os.getenv("USE_LANGGRAPH", "false").lower() in {"1", "true", "yes", "on"}


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


async def _langgraph_stream(
    session_id: uuid.UUID,
    message: str,
    session_factory: async_sessionmaker[AsyncSession],
):
    """SSE generator using the new event envelope per docs/events.md."""
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

    graph = await _get_graph(session_factory)
    async for event in run_chat(
        graph,
        project_id=project_id,
        session_id=session_id,
        user_input=message,
    ):
        yield f"data: {event.model_dump_json()}\n\n"


@router.post("/chat")
async def agent_chat(
    body: AgentChatRequest,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """Agent Chat SSE 엔드포인트.

    Path is chosen at request time by USE_LANGGRAPH env var so a single
    deployment can flip between legacy and new orchestrator without
    restart (when the env file is reloaded).
    """
    if _use_langgraph():
        logger.info(f"agent/chat: LangGraph path session={body.session_id}")
        return StreamingResponse(
            _langgraph_stream(body.session_id, body.message, session_factory),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    logger.info(f"agent/chat: legacy agent_svc path session={body.session_id}")
    return StreamingResponse(
        agent_svc.stream_chat(body.session_id, body.message),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
