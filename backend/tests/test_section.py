"""Requirement Section API 테스트"""

import uuid

import pytest
from sqlalchemy import select

from src.models.requirement import DEFAULT_SECTIONS, RequirementSection

async def create_test_project(client, name: str = "섹션 테스트 프로젝트") -> str:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "modules": ["requirements"]},
    )
    assert resp.status_code == 201
    return resp.json()["project_id"]


@pytest.mark.asyncio
async def test_list_sections_creates_default_sections(client):
    """GET /requirement-sections -> 기본 섹션 자동 생성 확인"""
    project_id = await create_test_project(client)

    resp = await client.get(f"/api/v1/projects/{project_id}/requirement-sections")
    assert resp.status_code == 200
    sections = resp.json()["sections"]
    assert len(sections) >= 5


@pytest.mark.asyncio
async def test_list_sections_does_not_duplicate_defaults_on_repeated_calls(client):
    """GET /requirement-sections 반복 호출 시 기본 섹션이 중복 생성되지 않는다."""
    project_id = await create_test_project(client, "섹션 중복 방지 프로젝트")

    first_resp = await client.get(f"/api/v1/projects/{project_id}/requirement-sections")
    assert first_resp.status_code == 200
    first_sections = first_resp.json()["sections"]

    second_resp = await client.get(f"/api/v1/projects/{project_id}/requirement-sections")
    assert second_resp.status_code == 200
    second_sections = second_resp.json()["sections"]

    assert len(second_sections) == len(first_sections)


@pytest.mark.asyncio
async def test_list_sections_recovers_missing_defaults(client, db):
    """기본 섹션이 일부만 존재해도 누락된 기본 섹션을 자동 보강한다."""
    project_id = await create_test_project(client, "섹션 복구 프로젝트")

    existing_defaults_result = await db.execute(
        select(RequirementSection).where(
            RequirementSection.project_id == uuid.UUID(project_id),
            RequirementSection.is_default == True,  # noqa: E712
        )
    )
    existing_defaults = existing_defaults_result.scalars().all()
    assert len(existing_defaults) == len(DEFAULT_SECTIONS)

    for section in existing_defaults[:2]:
        await db.delete(section)
    await db.commit()

    resp = await client.get(f"/api/v1/projects/{project_id}/requirement-sections")
    assert resp.status_code == 200
    sections = resp.json()["sections"]

    default_types = {s["type"] for s in sections if s["is_default"]}
    expected_types = {section_def["type"] for section_def in DEFAULT_SECTIONS}

    assert expected_types.issubset(default_types)
    assert len([s for s in sections if s["is_default"]]) == len(expected_types)


@pytest.mark.asyncio
async def test_reorder_sections_invalid_uuid_returns_422(client):
    """PUT /requirement-sections/reorder invalid section_id -> 422"""
    project_id = await create_test_project(client)

    resp = await client.put(
        f"/api/v1/projects/{project_id}/requirement-sections/reorder",
        json={"ordered_ids": ["not-a-uuid"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reorder_sections_partial_non_prefix_keeps_consistent_order(client):
    """부분 reorder가 앞부분이 아니어도 전체 order_index를 일관되게 재정렬한다."""
    project_id = await create_test_project(client, "섹션 재정렬 프로젝트")

    list_resp = await client.get(f"/api/v1/projects/{project_id}/requirement-sections")
    assert list_resp.status_code == 200
    sections = list_resp.json()["sections"]
    assert len(sections) >= 3

    first = sections[0]["section_id"]
    second = sections[1]["section_id"]
    third = sections[2]["section_id"]

    reorder_resp = await client.put(
        f"/api/v1/projects/{project_id}/requirement-sections/reorder",
        json={"ordered_ids": [third, first]},
    )
    assert reorder_resp.status_code == 200
    assert reorder_resp.json()["updated_count"] >= 3

    reloaded_resp = await client.get(f"/api/v1/projects/{project_id}/requirement-sections")
    assert reloaded_resp.status_code == 200
    reloaded = reloaded_resp.json()["sections"]

    assert [s["section_id"] for s in reloaded[:3]] == [third, first, second]
    assert [s["order_index"] for s in reloaded] == list(range(len(reloaded)))
