import os
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://aise:aise1234@localhost:5432/aise",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"ssl": False},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI Depends용 DB 세션 제공"""
    async with async_session() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """FastAPI-Depends accessor for the session factory.

    Routes that need to pass a factory into long-lived closures (e.g. the
    LangGraph orchestrator, which compiles nodes that open their own
    sessions) should depend on this rather than importing `async_session`
    directly. Tests override it via `app.dependency_overrides` so the
    LangGraph path hits the test DB instead of the dev DB.
    """
    return async_session
