import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from sqlalchemy.pool import NullPool

from src.main import app
from src.core.database import get_db, get_session_factory

TEST_DATABASE_URL = "postgresql+asyncpg://aise:aise1234@localhost:5432/aise_test"

_SETUP_HINT = (
    "Test database is not initialised. Run `./backend/scripts/setup_test_db.sh` once, "
    "then retry pytest. (This project does not auto-create the test DB; see "
    "PROGRESS.md for the policy.)"
)

# NullPool: 각 요청마다 새 커넥션을 생성하여 "operation in progress" 문제를 방지
engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _verify_test_db_ready():
    """Fail fast with a helpful pointer if the test DB is missing.

    We do NOT create the database — team policy is that this is an explicit
    one-shot setup step (see `backend/scripts/setup_test_db.sh`). Without this
    check, every test fails with an opaque `InvalidCatalogNameError`.

    Probe uses the sync psycopg2 driver to stay out of the event loop that
    pytest-asyncio owns.
    """
    import psycopg2

    sync_url = TEST_DATABASE_URL.replace("+asyncpg", "")
    try:
        conn = psycopg2.connect(sync_url)
    except psycopg2.OperationalError as exc:
        msg = str(exc)
        if "does not exist" in msg:
            pytest.exit(f"{_SETUP_HINT}\n  Underlying error: {msg}", returncode=4)
        raise
    conn.close()
    yield

# 테이블 정리 순서 (FK 의존성 고려). artifacts ↔ artifact_versions 의 순환
# FK 때문에 artifacts 포인터를 먼저 NULL 로 풀어야 한다.
CLEANUP_TABLES = [
    "session_messages",
    "sessions",
    "srs_sections",
    "srs_documents",
    "change_events",
    "artifact_dependencies",
    "__null_artifact_pointers",
    "pull_requests",
    "artifact_versions",
    "artifacts",
    "knowledge_chunks",
    "knowledge_documents",
    "requirement_reviews",
    "glossary_items",
    "requirement_versions",
    "requirements",
    "requirement_sections",
    "project_settings",
    "projects",
]


async def _cleanup_db():
    """테스트 후 모든 테이블 데이터를 삭제한다."""
    async with AsyncSession(engine) as cleanup_session:
        async with cleanup_session.begin():
            existing_tables_result = await cleanup_session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing_tables = {row[0] for row in existing_tables_result.all()}
            for table in CLEANUP_TABLES:
                if table == "__null_artifact_pointers":
                    # circular FK 해제: DELETE 전에 포인터를 먼저 NULL 처리
                    # working_status='dirty' 로 재설정해 check constraints
                    # (ck_artifacts_clean_requires_version / ck_artifacts_staged_requires_pr)
                    # 위반 방지
                    if "artifacts" in existing_tables:
                        await cleanup_session.execute(
                            text(
                                "UPDATE artifacts SET current_version_id=NULL, "
                                "open_pr_id=NULL, working_status='dirty'"
                            )
                        )
                    continue
                if table in existing_tables:
                    await cleanup_session.execute(text(f"DELETE FROM {table}"))


@pytest_asyncio.fixture
async def db():
    """각 테스트에 독립된 DB 세션을 제공하고 테스트 후 데이터를 정리한다.

    각 FastAPI 요청마다 새로운 세션을 생성하여 에러 발생 시에도
    다음 요청에 영향을 주지 않도록 격리한다.
    """

    async def override_get_db():
        async with TestSession() as session:
            yield session

    def override_get_session_factory():
        return TestSession

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = override_get_session_factory

    # 테스트 본문에서 직접 DB 접근이 필요할 경우를 위한 세션
    async with TestSession() as session:
        yield session

    app.dependency_overrides.clear()

    # 별도의 세션으로 데이터 정리
    await _cleanup_db()


@pytest_asyncio.fixture
async def client(db):
    """httpx AsyncClient for FastAPI"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
