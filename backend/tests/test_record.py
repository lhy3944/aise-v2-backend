"""Record API 테스트"""

import uuid

import pytest

from src.models.knowledge import KnowledgeDocument

async def create_test_project(client, name: str = "레코드 테스트 프로젝트") -> str:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "modules": ["requirements"]},
    )
    assert resp.status_code == 201
    return resp.json()["project_id"]


@pytest.mark.asyncio
async def test_create_record_invalid_section_id_returns_422(client):
    project_id = await create_test_project(client)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/records",
        json={"content": "테스트 레코드", "section_id": "not-a-uuid"},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_records_invalid_section_id_returns_422(client):
    project_id = await create_test_project(client)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/records?section_id=not-a-uuid",
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_rejects_section_from_another_project(client):
    project_1 = await create_test_project(client, "레코드 프로젝트 1")
    project_2 = await create_test_project(client, "레코드 프로젝트 2")

    section_resp = await client.get(f"/api/v1/projects/{project_2}/requirement-sections")
    assert section_resp.status_code == 200
    section_id = section_resp.json()["sections"][0]["section_id"]

    resp = await client.post(
        f"/api/v1/projects/{project_1}/records",
        json={"content": "다른 프로젝트 섹션 참조", "section_id": section_id},
    )

    assert resp.status_code == 400
    assert "유효하지 않은 섹션 ID" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approve_records_keeps_incremental_display_ids(client):
    project_id = await create_test_project(client)

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/records",
        json={"content": "기본 레코드"},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["display_id"] == "OTH-001"

    approve_resp = await client.post(
        f"/api/v1/projects/{project_id}/records/approve",
        json={
            "items": [
                {"content": "후보 레코드 A"},
                {"content": "후보 레코드 B"},
            ],
        },
    )
    assert approve_resp.status_code == 201

    body = approve_resp.json()
    assert body["total"] == 2
    assert [record["display_id"] for record in body["records"]] == ["OTH-002", "OTH-003"]
    assert all(record["status"] == "approved" for record in body["records"])


@pytest.mark.asyncio
async def test_reorder_records_partial_non_prefix_keeps_consistent_order(client):
    project_id = await create_test_project(client, "레코드 순서 테스트 프로젝트")

    rec1 = await client.post(
        f"/api/v1/projects/{project_id}/records",
        json={"content": "A"},
    )
    rec2 = await client.post(
        f"/api/v1/projects/{project_id}/records",
        json={"content": "B"},
    )
    rec3 = await client.post(
        f"/api/v1/projects/{project_id}/records",
        json={"content": "C"},
    )
    assert rec1.status_code == 201
    assert rec2.status_code == 201
    assert rec3.status_code == 201

    rec1_id = rec1.json()["record_id"]
    rec2_id = rec2.json()["record_id"]
    rec3_id = rec3.json()["record_id"]

    reorder_resp = await client.put(
        f"/api/v1/projects/{project_id}/records/reorder",
        json={"ordered_ids": [rec3_id, rec1_id]},
    )
    assert reorder_resp.status_code == 200
    assert reorder_resp.json()["updated_count"] == 3

    list_resp = await client.get(f"/api/v1/projects/{project_id}/records")
    assert list_resp.status_code == 200
    records = list_resp.json()["records"]
    assert [r["record_id"] for r in records] == [rec3_id, rec1_id, rec2_id]
    assert [r["order_index"] for r in records] == [0, 1, 2]


@pytest.mark.asyncio
async def test_reorder_records_invalid_uuid_returns_422(client):
    project_id = await create_test_project(client, "레코드 UUID 검증 프로젝트")

    resp = await client.put(
        f"/api/v1/projects/{project_id}/records/reorder",
        json={"ordered_ids": ["not-a-uuid"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_rejects_source_document_from_another_project(client, db):
    project_1 = await create_test_project(client, "레코드 문서 프로젝트 1")
    project_2 = await create_test_project(client, "레코드 문서 프로젝트 2")

    foreign_doc = KnowledgeDocument(
        project_id=uuid.UUID(project_2),
        name="foreign.md",
        file_type="md",
        size_bytes=128,
        storage_key="tests/foreign.md",
        status="completed",
    )
    db.add(foreign_doc)
    await db.commit()
    await db.refresh(foreign_doc)

    resp = await client.post(
        f"/api/v1/projects/{project_1}/records",
        json={
            "content": "외부 프로젝트 문서 참조",
            "source_document_id": str(foreign_doc.id),
        },
    )

    assert resp.status_code == 400
    assert "유효하지 않은 지식 문서 ID" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approve_records_rejects_source_document_from_another_project(client, db):
    project_1 = await create_test_project(client, "레코드 승인 문서 프로젝트 1")
    project_2 = await create_test_project(client, "레코드 승인 문서 프로젝트 2")

    foreign_doc = KnowledgeDocument(
        project_id=uuid.UUID(project_2),
        name="foreign-approve.md",
        file_type="md",
        size_bytes=64,
        storage_key="tests/foreign-approve.md",
        status="completed",
    )
    db.add(foreign_doc)
    await db.commit()
    await db.refresh(foreign_doc)

    resp = await client.post(
        f"/api/v1/projects/{project_1}/records/approve",
        json={
            "items": [
                {
                    "content": "외부 문서 참조 후보",
                    "source_document_id": str(foreign_doc.id),
                }
            ]
        },
    )

    assert resp.status_code == 400
    assert "유효하지 않은 지식 문서 ID" in resp.json()["detail"]
