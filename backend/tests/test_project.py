import pytest
import uuid


@pytest.mark.asyncio
async def test_create_project(client):
    """POST /api/v1/projects -> 201, 프로젝트 생성"""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "테스트 프로젝트", "modules": ["requirements"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "project_id" in body
    assert body["name"] == "테스트 프로젝트"
    assert body["modules"] == ["requirements"]
    assert "created_at" in body
    assert "updated_at" in body
    assert body["status"] == "active"
    assert body["member_count"] == 0


@pytest.mark.asyncio
async def test_list_projects(client):
    """GET /api/v1/projects -> 200, 프로젝트 목록 반환"""
    # 먼저 하나 생성
    await client.post(
        "/api/v1/projects",
        json={"name": "목록 테스트", "modules": ["requirements"]},
    )
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert "projects" in body
    assert isinstance(body["projects"], list)


@pytest.mark.asyncio
async def test_get_project(client):
    """GET /api/v1/projects/{id} -> 200"""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "조회 테스트", "modules": ["requirements"]},
    )
    project_id = create_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["project_id"] == project_id
    assert resp.json()["name"] == "조회 테스트"


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    """GET /api/v1/projects/{fake-uuid} -> 404"""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/projects/{fake_id}")
    assert resp.status_code == 404
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_update_project(client):
    """PUT /api/v1/projects/{id} -> 200, 수정된 값 반환"""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "수정 전", "modules": ["requirements"]},
    )
    project_id = create_resp.json()["project_id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "수정 후", "description": "설명 추가"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "수정 후"
    assert body["description"] == "설명 추가"


@pytest.mark.asyncio
async def test_delete_project(client):
    """DELETE /api/v1/projects/{id} -> 204"""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "삭제 테스트", "modules": ["requirements"]},
    )
    project_id = create_resp.json()["project_id"]

    resp = await client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 204

    # 삭제 후 조회하면 404
    resp = await client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_settings(client):
    """GET /api/v1/projects/{id}/settings -> 200, 기본값 확인"""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "설정 테스트", "modules": ["requirements"]},
    )
    project_id = create_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_model"] == "gpt-5.2"
    assert body["language"] == "ko"
    assert body["export_format"] == "pdf"
    assert body["diagram_tool"] == "plantuml"


@pytest.mark.asyncio
async def test_update_settings(client):
    """PUT /api/v1/projects/{id}/settings -> 200, 수정된 설정 반환"""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "설정 수정 테스트", "modules": ["requirements"]},
    )
    project_id = create_resp.json()["project_id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}/settings",
        json={"llm_model": "gpt-5", "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_model"] == "gpt-5"
    assert body["language"] == "en"
    # 변경하지 않은 필드는 기본값 유지
    assert body["export_format"] == "pdf"


# ---------------------------------------------------------------------------
# Tests: 모듈 조합 검증
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("modules", [
    ["requirements", "design", "testcase"],  # All
    ["requirements"],                         # Requirements Only
    ["requirements", "design"],               # Requirements + Design
    ["requirements", "testcase"],             # Requirements + Testcase
    ["testcase"],                              # Testcase Only
])
async def test_create_project_valid_modules(client, modules):
    """유효한 5가지 모듈 조합 — 201 성공."""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": f"모듈 테스트 {modules}", "modules": modules},
    )
    assert resp.status_code == 201
    assert set(resp.json()["modules"]) == set(modules)


@pytest.mark.asyncio
@pytest.mark.parametrize("modules", [
    ["design"],                    # Design 단독 불가
    ["design", "testcase"],        # Design+TC (Requirements 없음)
])
async def test_create_project_invalid_modules(client, modules):
    """허용되지 않는 모듈 조합 — 422 검증 에러."""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "잘못된 모듈", "modules": modules},
    )
    assert resp.status_code == 422
