"""Artifact Governance 서비스/라우터 테스트 (plan step 3)."""

from __future__ import annotations

import uuid

import pytest


async def _create_project(client, name: str = "artifact 테스트 프로젝트") -> str:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "modules": ["requirements"]},
    )
    assert resp.status_code == 201
    return resp.json()["project_id"]


@pytest.mark.asyncio
async def test_create_artifact_starts_dirty_with_no_version(client):
    project_id = await _create_project(client)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "record",
            "content": {"text": "초기 레코드", "source": "doc-1"},
            "title": "FR 초안",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["artifact_type"] == "record"
    assert body["working_status"] == "dirty"
    assert body["current_version_id"] is None
    assert body["current_version_number"] is None
    assert body["open_pr_id"] is None
    assert body["display_id"].startswith("REC-")


@pytest.mark.asyncio
async def test_list_artifacts_filters_by_type_and_status(client):
    project_id = await _create_project(client)
    # record 2개, srs 1개 생성
    for i in range(2):
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": f"R{i}"}},
        )
    await client.post(
        f"/api/v1/projects/{project_id}/artifacts",
        json={"artifact_type": "srs", "content": {"sections": []}},
    )

    resp = await client.get(
        f"/api/v1/projects/{project_id}/artifacts?artifact_type=record"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(a["artifact_type"] == "record" for a in body["artifacts"])

    resp_staged = await client.get(
        f"/api/v1/projects/{project_id}/artifacts?working_status=staged"
    )
    assert resp_staged.status_code == 200
    assert resp_staged.json()["total"] == 0


@pytest.mark.asyncio
async def test_patch_artifact_updates_content_keeps_dirty(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "원본"}},
        )
    ).json()
    artifact_id = created["artifact_id"]

    resp = await client.patch(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}",
        json={"content": {"text": "수정됨"}, "title": "새 제목"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"]["text"] == "수정됨"
    assert body["title"] == "새 제목"
    assert body["working_status"] == "dirty"


@pytest.mark.asyncio
async def test_create_pr_transitions_to_staged_and_snapshots_version(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "첫 커밋"}},
        )
    ).json()
    artifact_id = created["artifact_id"]

    pr_resp = await client.post(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
        json={"title": "FR-001 초안 등록", "description": "처음 올림"},
    )
    assert pr_resp.status_code == 201, pr_resp.text
    pr = pr_resp.json()
    assert pr["status"] == "open"
    assert pr["base_version_id"] is None  # 첫 커밋
    assert pr["head_version_id"]

    # artifact 상태 확인
    detail = await client.get(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}"
    )
    assert detail.json()["working_status"] == "staged"
    assert detail.json()["open_pr_id"] == pr["pr_id"]

    # versions 1개
    versions = await client.get(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/versions"
    )
    assert versions.status_code == 200
    assert len(versions.json()["versions"]) == 1
    assert versions.json()["versions"][0]["version_number"] == 1


@pytest.mark.asyncio
async def test_patch_on_staged_artifact_returns_409(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    artifact_id = created["artifact_id"]
    await client.post(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
        json={"title": "stage"},
    )

    resp = await client.patch(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}",
        json={"content": {"text": "편집 시도"}},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_open_pr_returns_409(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    artifact_id = created["artifact_id"]
    first = await client.post(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
        json={"title": "first"},
    )
    assert first.status_code == 201
    second = await client.post(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
        json={"title": "duplicate"},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_merge_pr_bumps_current_version_to_clean(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    artifact_id = created["artifact_id"]

    pr = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
            json={"title": "v1 등록"},
        )
    ).json()
    pr_id = pr["pr_id"]

    merged = await client.post(f"/api/v1/prs/{pr_id}/merge")
    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "merged"

    detail = (
        await client.get(f"/api/v1/projects/{project_id}/artifacts/{artifact_id}")
    ).json()
    assert detail["working_status"] == "clean"
    assert detail["open_pr_id"] is None
    assert detail["current_version_id"] == pr["head_version_id"]
    assert detail["current_version_number"] == 1


@pytest.mark.asyncio
async def test_reject_pr_restores_dirty_and_keeps_head_version(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    artifact_id = created["artifact_id"]

    pr = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
            json={"title": "검토 요청"},
        )
    ).json()

    rej = await client.post(
        f"/api/v1/prs/{pr['pr_id']}/reject",
        json={"reason": "내용 부족"},
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"

    detail = (
        await client.get(f"/api/v1/projects/{project_id}/artifacts/{artifact_id}")
    ).json()
    assert detail["working_status"] == "dirty"
    assert detail["open_pr_id"] is None
    # head_version_id 는 보존되어 versions 목록에 남아있어야 한다
    versions = (
        await client.get(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/versions"
        )
    ).json()
    assert len(versions["versions"]) == 1


@pytest.mark.asyncio
async def test_second_pr_after_merge_bumps_version_number(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    artifact_id = created["artifact_id"]
    pr1 = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
            json={"title": "first"},
        )
    ).json()
    await client.post(f"/api/v1/prs/{pr1['pr_id']}/merge")

    # 편집 → 두 번째 PR
    await client.patch(
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}",
        json={"content": {"text": "v2"}},
    )
    pr2 = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
            json={"title": "second"},
        )
    ).json()
    assert pr2["base_version_id"] == pr1["head_version_id"]

    versions = (
        await client.get(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/versions"
        )
    ).json()
    numbers = sorted(v["version_number"] for v in versions["versions"])
    assert numbers == [1, 2]


@pytest.mark.asyncio
async def test_diff_first_version_marks_all_added(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={
                "artifact_type": "record",
                "content": {"text": "첫 내용", "confidence": 0.8},
            },
        )
    ).json()
    artifact_id = created["artifact_id"]
    pr = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/prs",
            json={"title": "v1"},
        )
    ).json()

    diff = await client.get(f"/api/v1/versions/{pr['head_version_id']}/diff")
    assert diff.status_code == 200
    body = diff.json()
    assert body["base_version_id"] is None
    kinds = {e["field_path"]: e["kind"] for e in body["entries"]}
    assert kinds == {"text": "added", "confidence": "added"}


@pytest.mark.asyncio
async def test_list_prs_returns_created_prs(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    await client.post(
        f"/api/v1/projects/{project_id}/artifacts/{created['artifact_id']}/prs",
        json={"title": "pr"},
    )

    resp = await client.get(f"/api/v1/projects/{project_id}/prs?status=open")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["pull_requests"][0]["status"] == "open"


@pytest.mark.asyncio
async def test_get_missing_artifact_returns_404(client):
    project_id = await _create_project(client)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/artifacts/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_impact_empty_when_no_dependencies(client):
    project_id = await _create_project(client)
    created = (
        await client.post(
            f"/api/v1/projects/{project_id}/artifacts",
            json={"artifact_type": "record", "content": {"text": "v1"}},
        )
    ).json()
    resp = await client.get(
        f"/api/v1/projects/{project_id}/artifacts/{created['artifact_id']}/impact"
    )
    assert resp.status_code == 200
    assert resp.json()["impacted"] == []
