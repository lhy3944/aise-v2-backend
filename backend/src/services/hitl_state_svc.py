"""HITL (Human-in-the-loop) 일시 정지 상태 저장소.

Phase 3 persistence:
- DB `hitl_requests` 테이블에 pending interrupt context 저장
- 같은 thread_id 로 resume 할 때 컨텍스트 복원
- completed row 는 audit 용으로 `resumed` 상태 보존

테스트/마이그레이션 전 환경은 기존 in-memory dict 로 fallback 한다.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.models.hitl import HitlRequest

_TTL = timedelta(hours=24)


@dataclass
class HitlState:
    """interrupt 발행 시점에 SSE 드라이버가 캡처해 두는 컨텍스트."""

    thread_id: str
    session_id: str
    project_id: str
    user_input: str
    selected_agent: str
    interrupt_id: str
    interrupt_kind: str  # "clarify" | "confirm" | "decision"
    payload: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    routing: dict[str, Any] | None = None
    accumulated_state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_store: dict[str, HitlState] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at(created_at: datetime) -> datetime:
    return created_at + _TTL


def _is_expired(state: HitlState) -> bool:
    return _now() - state.created_at > _TTL


def _json_safe(value: Any) -> Any:
    """Return a JSONB-safe structure, stringifying UUID/datetime leftovers."""
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(str(value))


def _from_row(row: HitlRequest) -> HitlState:
    return HitlState(
        thread_id=row.thread_id,
        session_id=str(row.session_id),
        project_id=str(row.project_id),
        user_input=row.user_input,
        selected_agent=row.selected_agent,
        interrupt_id=row.interrupt_id,
        interrupt_kind=row.interrupt_kind,
        payload=row.payload or {},
        history=row.history or [],
        routing=row.routing,
        accumulated_state=row.accumulated_state or {},
        created_at=row.created_at,
    )


async def _rollback_quietly(db: Any) -> None:
    if isinstance(db, AsyncSession):
        try:
            await db.rollback()
        except SQLAlchemyError:
            pass


def save(state: HitlState) -> None:
    _store[state.thread_id] = state


def get(thread_id: str) -> HitlState | None:
    state = _store.get(thread_id)
    if state is None:
        return None
    if _is_expired(state):
        _store.pop(thread_id, None)
        return None
    return state


def delete(thread_id: str) -> None:
    _store.pop(thread_id, None)


def reset() -> None:
    """테스트 전용 초기화."""
    _store.clear()


async def save_persistent(session_factory: Any, state: HitlState) -> None:
    """Persist a pending HITL state.

    Always updates the in-memory fallback first. DB write failures are logged
    and tolerated so local/unit-test flows continue to work before migrations.
    """
    save(state)
    db: Any = None
    try:
        async with session_factory() as db:
            if db is None or not hasattr(db, "execute"):
                return

            existing = (
                await db.execute(
                    select(HitlRequest).where(HitlRequest.thread_id == state.thread_id)
                )
            ).scalar_one_or_none()
            if existing is None:
                existing = HitlRequest(
                    id=uuid.uuid4(),
                    thread_id=state.thread_id,
                    session_id=_uuid(state.session_id),
                    project_id=_uuid(state.project_id),
                    expires_at=_expires_at(state.created_at),
                )
                db.add(existing)

            existing.session_id = _uuid(state.session_id)
            existing.project_id = _uuid(state.project_id)
            existing.user_input = state.user_input
            existing.selected_agent = state.selected_agent
            existing.interrupt_id = state.interrupt_id
            existing.interrupt_kind = state.interrupt_kind
            existing.status = "pending"
            existing.payload = _json_safe(state.payload)
            existing.history = _json_safe(state.history)
            existing.routing = _json_safe(state.routing)
            existing.accumulated_state = _json_safe(state.accumulated_state)
            existing.response = None
            existing.created_at = state.created_at
            existing.expires_at = _expires_at(state.created_at)
            existing.completed_at = None
            await db.commit()
    except SQLAlchemyError:
        await _rollback_quietly(db)
        logger.opt(exception=True).warning(
            "HITL DB save failed; falling back to in-memory state"
        )


async def get_persistent(session_factory: Any, thread_id: str) -> HitlState | None:
    """Load pending HITL state from DB, with in-memory fallback."""
    db: Any = None
    try:
        async with session_factory() as db:
            if db is None or not hasattr(db, "execute"):
                return get(thread_id)

            row = (
                await db.execute(
                    select(HitlRequest).where(
                        HitlRequest.thread_id == thread_id,
                        HitlRequest.status == "pending",
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return get(thread_id)

            state = _from_row(row)
            if _is_expired(state):
                row.status = "expired"
                row.completed_at = _now()
                await db.commit()
                delete(thread_id)
                return None

            save(state)
            return state
    except SQLAlchemyError:
        await _rollback_quietly(db)
        logger.opt(exception=True).warning(
            "HITL DB load failed; falling back to in-memory state"
        )
        return get(thread_id)


async def delete_persistent(
    session_factory: Any,
    thread_id: str,
    *,
    response: dict[str, Any] | None = None,
    status: str = "resumed",
) -> None:
    """Mark a HITL request completed in DB and remove it from memory."""
    delete(thread_id)
    db: Any = None
    try:
        async with session_factory() as db:
            if db is None or not hasattr(db, "execute"):
                return

            row = (
                await db.execute(
                    select(HitlRequest).where(
                        HitlRequest.thread_id == thread_id,
                        HitlRequest.status == "pending",
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return
            row.status = status
            row.response = _json_safe(response)
            row.completed_at = _now()
            await db.commit()
    except SQLAlchemyError:
        await _rollback_quietly(db)
        logger.opt(exception=True).warning(
            "HITL DB completion update failed; in-memory state already removed"
        )


__all__ = [
    "HitlState",
    "save",
    "get",
    "delete",
    "reset",
    "save_persistent",
    "get_persistent",
    "delete_persistent",
]
