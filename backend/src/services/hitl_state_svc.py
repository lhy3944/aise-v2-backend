"""HITL (Human-in-the-loop) 일시 정지 상태 저장소.

Phase 3 PR-1: 단일 프로세스 in-memory dict. thread_id (= interrupt_id) 키로
일시 정지 시점의 컨텍스트를 보관하고, resume 라우터가 같은 thread_id 로
조회해 SSE 스트림을 재개한다.

상태는 24시간 TTL 후 자동 만료. PR-3 에서 LangGraph PostgresSaver 또는
별도 hitl_states 테이블로 마이그레이션 가능 (인터페이스 그대로 유지).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

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


def save(state: HitlState) -> None:
    _store[state.thread_id] = state


def get(thread_id: str) -> HitlState | None:
    state = _store.get(thread_id)
    if state is None:
        return None
    if datetime.now(timezone.utc) - state.created_at > _TTL:
        _store.pop(thread_id, None)
        return None
    return state


def delete(thread_id: str) -> None:
    _store.pop(thread_id, None)


def reset() -> None:
    """테스트 전용 초기화."""
    _store.clear()


__all__ = ["HitlState", "save", "get", "delete", "reset"]
