"""Session API 테스트"""

import pytest
import uuid
from sqlalchemy import text


async def create_test_project(client, name: str = "세션 테스트 프로젝트") -> str:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "modules": ["requirements"]},
    )
    assert resp.status_code == 201
    return resp.json()["project_id"]


async def ensure_sessions_table(db) -> None:
    result = await db.execute(
        text("SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'sessions'")
    )
    if result.scalar() != 1:
        pytest.skip("sessions 테이블이 없어 session API 테스트를 건너뜁니다.")


@pytest.mark.asyncio
async def test_create_session(client, db):
    await ensure_sessions_table(db)
    project_id = await create_test_project(client)

    resp = await client.post(
        "/api/v1/sessions",
        json={"project_id": project_id, "title": "세션 제목"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["project_id"] == project_id
    assert body["title"] == "세션 제목"
    assert body["message_count"] == 0


@pytest.mark.asyncio
async def test_create_session_invalid_project_id_returns_422(client, db):
    await ensure_sessions_table(db)
    resp = await client.post(
        "/api/v1/sessions",
        json={"project_id": "not-a-uuid"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_session_project_not_found_returns_404(client, db):
    await ensure_sessions_table(db)
    resp = await client.post(
        "/api/v1/sessions",
        json={"project_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_session_can_toggle_favorite(client, db):
    await ensure_sessions_table(db)
    project_id = await create_test_project(client, "favorite project")

    created = await client.post(
        "/api/v1/sessions",
        json={"project_id": project_id, "title": "favorite me"},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"is_favorite": True},
    )

    assert resp.status_code == 200
    assert resp.json()["is_favorite"] is True


@pytest.mark.asyncio
async def test_list_sessions_sorts_by_created_and_can_pin_favorites(client, db):
    await ensure_sessions_table(db)
    project_id = await create_test_project(client, "sorting project")

    older = await client.post(
        "/api/v1/sessions",
        json={"project_id": project_id, "title": "older"},
    )
    newer = await client.post(
        "/api/v1/sessions",
        json={"project_id": project_id, "title": "newer"},
    )
    assert older.status_code == 201
    assert newer.status_code == 201
    older_id = older.json()["id"]
    newer_id = newer.json()["id"]

    # Make the older session the most recently updated session.
    renamed = await client.patch(
        f"/api/v1/sessions/{older_id}",
        json={"title": "older updated"},
    )
    assert renamed.status_code == 200

    by_created = await client.get(
        f"/api/v1/sessions?project_id={project_id}&sort_by=created"
    )

    assert by_created.status_code == 200
    assert [item["id"] for item in by_created.json()["sessions"][:2]] == [
        newer_id,
        older_id,
    ]

    favorited = await client.patch(
        f"/api/v1/sessions/{older_id}",
        json={"is_favorite": True},
    )
    assert favorited.status_code == 200

    favorite_first = await client.get(
        f"/api/v1/sessions?project_id={project_id}&sort_by=created&favorite_first=true"
    )

    assert favorite_first.status_code == 200
    assert favorite_first.json()["sessions"][0]["id"] == older_id
