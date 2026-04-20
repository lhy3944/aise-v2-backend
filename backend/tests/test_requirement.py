"""Requirement CRUD API 테스트"""

import pytest
import uuid


async def create_test_project(client) -> str:
    """테스트용 프로젝트 생성 헬퍼"""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "테스트 프로젝트", "modules": ["requirements"]},
    )
    assert resp.status_code == 201
    return resp.json()["project_id"]


async def create_test_requirement(client, project_id: str, **kwargs) -> dict:
    """테스트용 요구사항 생성 헬퍼"""
    body = {
        "type": kwargs.get("type", "fr"),
        "original_text": kwargs.get("original_text", "로봇 중앙 버튼 클릭하면 멈춤"),
    }
    resp = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json=body,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_requirement(client):
    """POST /requirements -> 201, requirement_id/type/original_text/status=draft"""
    project_id = await create_test_project(client)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"type": "fr", "original_text": "로봇 중앙 버튼 클릭하면 멈춤"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "requirement_id" in body
    assert body["type"] == "fr"
    assert body["original_text"] == "로봇 중앙 버튼 클릭하면 멈춤"
    assert body["status"] == "draft"
    assert body["is_selected"] is True
    assert body["display_id"] == "FR-001"
    assert body["order_index"] == 0
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_list_requirements(client):
    """GET /requirements -> 200, requirements 배열"""
    project_id = await create_test_project(client)
    await create_test_requirement(client, project_id)
    await create_test_requirement(client, project_id, original_text="두 번째 요구사항")

    resp = await client.get(f"/api/v1/projects/{project_id}/requirements")
    assert resp.status_code == 200
    body = resp.json()
    assert "requirements" in body
    assert isinstance(body["requirements"], list)
    assert len(body["requirements"]) == 2


@pytest.mark.asyncio
async def test_list_requirements_filter_type(client):
    """GET /requirements?type=fr -> FR만 반환"""
    project_id = await create_test_project(client)
    await create_test_requirement(client, project_id, type="fr", original_text="FR 요구사항")
    await create_test_requirement(client, project_id, type="qa", original_text="QA 요구사항")
    await create_test_requirement(client, project_id, type="constraints", original_text="제약사항")

    # FR만 필터
    resp = await client.get(f"/api/v1/projects/{project_id}/requirements?type=fr")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["requirements"]) == 1
    assert body["requirements"][0]["type"] == "fr"

    # QA만 필터
    resp = await client.get(f"/api/v1/projects/{project_id}/requirements?type=qa")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["requirements"]) == 1
    assert body["requirements"][0]["type"] == "qa"


@pytest.mark.asyncio
async def test_update_requirement(client):
    """PUT /requirements/{id} -> 200, 수정된 값"""
    project_id = await create_test_project(client)
    req = await create_test_requirement(client, project_id)
    requirement_id = req["requirement_id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}",
        json={
            "original_text": "수정된 원문",
            "refined_text": "정제된 문장",
            "is_selected": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["original_text"] == "수정된 원문"
    assert body["refined_text"] == "정제된 문장"
    assert body["is_selected"] is True


@pytest.mark.asyncio
async def test_update_requirement_section_id_empty_string_to_null(client):
    """PUT /requirements/{id} section_id='' -> 200, section_id=null (프론트 호환)"""
    project_id = await create_test_project(client)
    req = await create_test_requirement(client, project_id)
    requirement_id = req["requirement_id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}",
        json={"section_id": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["section_id"] is None


@pytest.mark.asyncio
async def test_delete_requirement(client):
    """DELETE /requirements/{id} -> 204"""
    project_id = await create_test_project(client)
    req = await create_test_requirement(client, project_id)
    requirement_id = req["requirement_id"]

    resp = await client.delete(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}"
    )
    assert resp.status_code == 204

    # 삭제 후 목록에서 사라졌는지 확인
    resp = await client.get(f"/api/v1/projects/{project_id}/requirements")
    assert resp.status_code == 200
    assert len(resp.json()["requirements"]) == 0


@pytest.mark.asyncio
async def test_delete_requirement_not_found(client):
    """DELETE /requirements/{fake-uuid} -> 404"""
    project_id = await create_test_project(client)
    fake_id = str(uuid.uuid4())

    resp = await client.delete(
        f"/api/v1/projects/{project_id}/requirements/{fake_id}"
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_update_selection(client):
    """PUT /requirements/selection -> 200, updated_count"""
    project_id = await create_test_project(client)
    req1 = await create_test_requirement(client, project_id, original_text="요구사항 1")
    req2 = await create_test_requirement(client, project_id, original_text="요구사항 2")
    req3 = await create_test_requirement(client, project_id, original_text="요구사항 3")

    # 기본값이 True이므로, req3만 선택 해제하여 테스트
    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/selection",
        json={
            "requirement_ids": [req3["requirement_id"]],
            "is_selected": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["updated_count"] == 1

    # 선택 상태 확인
    resp = await client.get(f"/api/v1/projects/{project_id}/requirements")
    reqs = resp.json()["requirements"]
    selected = {r["requirement_id"]: r["is_selected"] for r in reqs}
    assert selected[req1["requirement_id"]] is True
    assert selected[req2["requirement_id"]] is True
    assert selected[req3["requirement_id"]] is False


@pytest.mark.asyncio
async def test_update_selection_invalid_uuid_returns_422(client):
    """PUT /requirements/selection invalid requirement_id -> 422"""
    project_id = await create_test_project(client)

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/selection",
        json={
            "requirement_ids": ["not-a-uuid"],
            "is_selected": True,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_save_version(client):
    """POST /requirements/save -> 200, version=1, saved_count"""
    project_id = await create_test_project(client)
    await create_test_requirement(client, project_id, original_text="요구사항 1")
    await create_test_requirement(client, project_id, original_text="요구사항 2")

    resp = await client.post(f"/api/v1/projects/{project_id}/requirements/save")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == 1
    assert body["saved_count"] == 2
    assert "saved_at" in body


@pytest.mark.asyncio
async def test_save_version_increments(client):
    """POST /requirements/save 두 번 -> version=1, 2"""
    project_id = await create_test_project(client)
    await create_test_requirement(client, project_id)

    # 첫 번째 저장
    resp1 = await client.post(f"/api/v1/projects/{project_id}/requirements/save")
    assert resp1.status_code == 200
    assert resp1.json()["version"] == 1

    # 두 번째 저장
    resp2 = await client.post(f"/api/v1/projects/{project_id}/requirements/save")
    assert resp2.status_code == 200
    assert resp2.json()["version"] == 2


@pytest.mark.asyncio
async def test_display_id_auto_numbering(client):
    """display_id가 타입별로 자동 채번 (FR-001, FR-002, QA-001 등)"""
    project_id = await create_test_project(client)

    req1 = await create_test_requirement(client, project_id, type="fr", original_text="FR 첫 번째")
    req2 = await create_test_requirement(client, project_id, type="fr", original_text="FR 두 번째")
    req3 = await create_test_requirement(client, project_id, type="qa", original_text="QA 첫 번째")
    req4 = await create_test_requirement(client, project_id, type="constraints", original_text="제약사항 첫 번째")

    assert req1["display_id"] == "FR-001"
    assert req2["display_id"] == "FR-002"
    assert req3["display_id"] == "QA-001"
    assert req4["display_id"] == "CON-001"


@pytest.mark.asyncio
async def test_order_index_auto_increment(client):
    """order_index가 프로젝트 내에서 자동 증가 (0, 1, 2, ...)"""
    project_id = await create_test_project(client)

    req1 = await create_test_requirement(client, project_id, original_text="첫 번째")
    req2 = await create_test_requirement(client, project_id, original_text="두 번째")
    req3 = await create_test_requirement(client, project_id, original_text="세 번째")

    assert req1["order_index"] == 0
    assert req2["order_index"] == 1
    assert req3["order_index"] == 2


@pytest.mark.asyncio
async def test_list_requirements_ordered_by_order_index(client):
    """GET /requirements -> order_index 순서대로 반환"""
    project_id = await create_test_project(client)

    await create_test_requirement(client, project_id, original_text="첫 번째")
    await create_test_requirement(client, project_id, original_text="두 번째")
    await create_test_requirement(client, project_id, original_text="세 번째")

    resp = await client.get(f"/api/v1/projects/{project_id}/requirements")
    assert resp.status_code == 200
    reqs = resp.json()["requirements"]
    assert len(reqs) == 3
    assert reqs[0]["order_index"] == 0
    assert reqs[1]["order_index"] == 1
    assert reqs[2]["order_index"] == 2
    assert reqs[0]["original_text"] == "첫 번째"


@pytest.mark.asyncio
async def test_reorder_requirements(client):
    """PUT /reorder -> 순서 변경 후 목록에서 반영 확인"""
    project_id = await create_test_project(client)

    req1 = await create_test_requirement(client, project_id, original_text="A")
    req2 = await create_test_requirement(client, project_id, original_text="B")
    req3 = await create_test_requirement(client, project_id, original_text="C")

    # 순서를 C, A, B로 변경
    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/reorder",
        json={
            "ordered_ids": [
                req3["requirement_id"],
                req1["requirement_id"],
                req2["requirement_id"],
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["updated_count"] == 3

    # 변경된 순서 확인
    resp = await client.get(f"/api/v1/projects/{project_id}/requirements")
    reqs = resp.json()["requirements"]
    assert reqs[0]["original_text"] == "C"
    assert reqs[0]["order_index"] == 0
    assert reqs[1]["original_text"] == "A"
    assert reqs[1]["order_index"] == 1
    assert reqs[2]["original_text"] == "B"
    assert reqs[2]["order_index"] == 2


@pytest.mark.asyncio
async def test_reorder_partial(client):
    """PUT /reorder -> 일부만 순서 변경해도 동작"""
    project_id = await create_test_project(client)

    req1 = await create_test_requirement(client, project_id, original_text="A")
    req2 = await create_test_requirement(client, project_id, original_text="B")
    await create_test_requirement(client, project_id, original_text="C")

    # A, B만 순서 변경 (B를 0번, A를 1번)
    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/reorder",
        json={
            "ordered_ids": [
                req2["requirement_id"],
                req1["requirement_id"],
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 2


@pytest.mark.asyncio
async def test_reorder_partial_non_prefix_keeps_consistent_order(client):
    """부분 reorder가 앞부분이 아니어도 전체 order_index를 일관되게 재정렬한다."""
    project_id = await create_test_project(client)

    req1 = await create_test_requirement(client, project_id, original_text="A")
    req2 = await create_test_requirement(client, project_id, original_text="B")
    req3 = await create_test_requirement(client, project_id, original_text="C")

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/reorder",
        json={
            "ordered_ids": [
                req3["requirement_id"],
                req1["requirement_id"],
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 3

    list_resp = await client.get(f"/api/v1/projects/{project_id}/requirements")
    assert list_resp.status_code == 200
    reqs = list_resp.json()["requirements"]
    assert [r["requirement_id"] for r in reqs] == [
        req3["requirement_id"],
        req1["requirement_id"],
        req2["requirement_id"],
    ]
    assert [r["order_index"] for r in reqs] == [0, 1, 2]


@pytest.mark.asyncio
async def test_reorder_invalid_uuid_returns_422(client):
    """PUT /requirements/reorder invalid requirement_id -> 422"""
    project_id = await create_test_project(client)
    await create_test_requirement(client, project_id, original_text="A")

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/reorder",
        json={"ordered_ids": ["not-a-uuid"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_display_id_no_reuse_after_delete(client):
    """삭제된 display_id 번호를 재사용하지 않는다 (FR-001 삭제 후 새 FR은 FR-003)"""
    project_id = await create_test_project(client)

    req1 = await create_test_requirement(client, project_id, type="fr", original_text="FR 첫 번째")
    req2 = await create_test_requirement(client, project_id, type="fr", original_text="FR 두 번째")
    assert req1["display_id"] == "FR-001"
    assert req2["display_id"] == "FR-002"

    # FR-001 삭제
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/requirements/{req1['requirement_id']}"
    )
    assert resp.status_code == 204

    # 새 FR 생성 -> FR-003이어야 함 (FR-001 재사용 안 됨)
    req3 = await create_test_requirement(client, project_id, type="fr", original_text="FR 세 번째")
    assert req3["display_id"] == "FR-003"


@pytest.mark.asyncio
async def test_reorder_empty_ids(client):
    """reorder에 빈 배열 전송 -> 정상 응답, updated_count=0"""
    project_id = await create_test_project(client)

    # 요구사항 생성 (reorder 대상 없이 테스트)
    await create_test_requirement(client, project_id, original_text="A")

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirements/reorder",
        json={"ordered_ids": []},
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 0


@pytest.mark.asyncio
async def test_save_version_includes_display_id(client):
    """POST /requirements/save -> 스냅샷에 display_id, order_index 포함 확인"""
    project_id = await create_test_project(client)

    req = await create_test_requirement(client, project_id, original_text="요구사항")
    assert req["display_id"] == "FR-001"
    assert req["order_index"] == 0

    resp = await client.post(f"/api/v1/projects/{project_id}/requirements/save")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == 1
    assert body["saved_count"] == 1
