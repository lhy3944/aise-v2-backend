"""Session API routes."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionDetailResponse,
    SessionListResponse,
)
from src.services import session_svc

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a session."""
    return await session_svc.create_session(db, body)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    project_id: uuid.UUID = Query(description="Project ID"),
    cursor: str | None = Query(default=None, description="Cursor from the previous page"),
    limit: int = Query(default=30, ge=1, le=100, description="Page size"),
    sort_by: str = Query(default="updated", pattern="^(created|updated)$"),
    favorite_first: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """List sessions for a project."""
    return await session_svc.list_sessions(
        db,
        project_id,
        cursor=cursor,
        limit=limit,
        sort_by=sort_by,
        favorite_first=favorite_first,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get session detail with messages."""
    return await session_svc.get_session(db, session_id)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a session."""
    return await session_svc.update_session(db, session_id, body)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a session."""
    await session_svc.delete_session(db, session_id)
