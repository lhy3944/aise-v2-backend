"""Session 비즈니스 로직 서비스"""

import uuid

from loguru import logger
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.project import Project
from src.models.session import Session, SessionMessage
from src.schemas.api.session import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    SessionMessageResponse,
    SessionListResponse,
)
from src.utils.db import get_or_404


def _to_session_response(session: Session, message_count: int = 0) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        project_id=str(session.project_id),
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=message_count,
    )


def _to_message_response(msg: SessionMessage) -> SessionMessageResponse:
    return SessionMessageResponse(
        id=str(msg.id),
        role=msg.role,
        content=msg.content,
        tool_calls=msg.tool_calls,
        tool_data=msg.tool_data,
        created_at=msg.created_at,
    )


async def create_session(db: AsyncSession, data: SessionCreate) -> SessionResponse:
    """세션 생성"""
    await get_or_404(
        db, Project, Project.id == data.project_id,
        error_msg="프로젝트를 찾을 수 없습니다.",
    )

    session = Session(
        project_id=data.project_id,
        title=data.title or "새 대화",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info(f"Session created: {session.id} for project {data.project_id}")
    return _to_session_response(session)


async def list_sessions(db: AsyncSession, project_id: uuid.UUID) -> SessionListResponse:
    """프로젝트별 세션 목록 조회 (최신순)"""
    # 세션 + 메시지 수 서브쿼리
    msg_count = (
        select(SessionMessage.session_id, func.count().label("cnt"))
        .group_by(SessionMessage.session_id)
        .subquery()
    )

    result = await db.execute(
        select(Session, func.coalesce(msg_count.c.cnt, 0).label("message_count"))
        .outerjoin(msg_count, Session.id == msg_count.c.session_id)
        .where(Session.project_id == project_id)
        .order_by(Session.updated_at.desc())
    )

    sessions = [
        _to_session_response(row.Session, row.message_count)
        for row in result.all()
    ]
    return SessionListResponse(sessions=sessions)


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> SessionDetailResponse:
    """세션 + 메시지 조회"""
    session = await get_or_404(db, Session, Session.id == session_id, error_msg="세션을 찾을 수 없습니다.")

    # 메시지 로드
    msg_result = await db.execute(
        select(SessionMessage)
        .where(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.created_at)
    )
    messages = msg_result.scalars().all()

    return SessionDetailResponse(
        id=str(session.id),
        project_id=str(session.project_id),
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages),
        messages=[_to_message_response(m) for m in messages],
    )


async def update_session(db: AsyncSession, session_id: uuid.UUID, title: str) -> SessionResponse:
    """세션 제목 수정"""
    session = await get_or_404(db, Session, Session.id == session_id, error_msg="세션을 찾을 수 없습니다.")
    session.title = title
    await db.commit()
    await db.refresh(session)
    return _to_session_response(session)


async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    """세션 삭제 (메시지 CASCADE)"""
    session = await get_or_404(db, Session, Session.id == session_id, error_msg="세션을 찾을 수 없습니다.")
    await db.delete(session)
    await db.commit()
    logger.info(f"Session deleted: {session_id}")


async def add_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    tool_calls: list[dict] | None = None,
    tool_data: dict | None = None,
) -> SessionMessage:
    """세션에 메시지 추가"""
    msg = SessionMessage(
        session_id=session_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_data=tool_data,
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_history(db: AsyncSession, session_id: uuid.UUID, limit: int = 50) -> list[dict]:
    """세션 최근 N개 메시지를 history 형식으로 반환"""
    result = await db.execute(
        select(SessionMessage)
        .where(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]


async def update_session_title_if_first(db: AsyncSession, session_id: uuid.UUID, first_message: str) -> None:
    """첫 메시지가 추가된 경우 세션 제목을 자동 설정"""
    count_result = await db.execute(
        select(func.count()).where(SessionMessage.session_id == session_id)
    )
    count = count_result.scalar()
    if count <= 1:  # 방금 추가한 첫 메시지
        session = await db.get(Session, session_id)
        if session and session.title == "새 대화":
            session.title = first_message[:40]
