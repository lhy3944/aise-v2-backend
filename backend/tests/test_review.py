"""요구사항 Review API 테스트 -- LLM 호출을 mock하여 review 엔드포인트 검증 (conflict + duplicate)."""

import json
import uuid

import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """src.services.review_svc 내부에서 import된 chat_completion을 mock한다."""
    with patch("src.services.review_svc.chat_completion", new_callable=AsyncMock) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_project(client) -> str:
    """테스트용 프로젝트를 생성하고 project_id를 반환한다."""
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "테스트 프로젝트", "modules": ["requirements"]},
    )
    assert resp.status_code == 201 or resp.status_code == 200, f"프로젝트 생성 실패: {resp.text}"
    return resp.json()["project_id"]


async def create_requirement(client, project_id: str, text: str = "로봇이 멈춰야 한다", req_type: str = "fr") -> str:
    """테스트용 요구사항을 생성하고 requirement_id를 반환한다."""
    resp = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"type": req_type, "original_text": text},
    )
    assert resp.status_code == 201 or resp.status_code == 200, f"요구사항 생성 실패: {resp.text}"
    return resp.json()["requirement_id"]


async def setup_project_with_requirements(client, count: int = 2) -> tuple[str, list[str]]:
    """프로젝트 + 요구사항 n건을 생성하고 (project_id, [requirement_ids]) 튜플을 반환한다."""
    project_id = await create_project(client)
    req_ids = []
    texts = [
        "시스템은 비상 정지 시 모든 동작을 중단해야 한다.",
        "시스템은 100ms 이내에 응답해야 한다.",
        "시스템은 비상 시 모든 프로세스를 정지해야 한다.",
    ]
    for i in range(count):
        req_id = await create_requirement(client, project_id, text=texts[i % len(texts)])
        req_ids.append(req_id)
    return project_id, req_ids


def make_review_response(req_ids: list[str], issues=None, summary_override=None) -> str:
    """v1 간소화 스키마에 맞는 mock LLM 응답을 생성한다."""
    if issues is None:
        issues = [
            {
                "type": "conflict",
                "description": "req-001과 req-003이 충돌합니다.",
                "related_requirements": ["FR-001", "FR-002"],
                "hint": "응답 시간 제약을 통일하세요.",
            }
        ]

    default_summary = {
        "total_issues": len(issues),
        "conflicts": len(issues),
        "ready_for_next": True,
        "feedback": "충돌 이슈가 있습니다.",
    }
    if summary_override:
        default_summary.update(summary_override)

    return json.dumps({"issues": issues, "summary": default_summary})


# ---------------------------------------------------------------------------
# Tests: POST /review/requirements
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_requirements(client, mock_llm):
    """정상적인 review 요청 -- issues + summary + review_id 반환."""
    project_id, req_ids = await setup_project_with_requirements(client, count=2)

    mock_llm.return_value = make_review_response(req_ids)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    assert resp.status_code == 200
    body = resp.json()

    # review_id 검증
    assert "review_id" in body
    assert isinstance(body["review_id"], str)
    assert len(body["review_id"]) > 0

    # issues 검증
    assert "issues" in body
    assert len(body["issues"]) == 1
    issue = body["issues"][0]
    assert issue["type"] == "conflict"
    assert "issue_id" in issue
    assert len(issue["related_requirements"]) == 2
    assert "hint" in issue
    assert issue["hint"] == "응답 시간 제약을 통일하세요."

    # summary 검증
    assert "summary" in body
    summary = body["summary"]
    assert summary["total_issues"] == 1
    assert summary["conflicts"] == 1
    assert summary["ready_for_next"] is True
    assert summary["feedback"] == "충돌 이슈가 있습니다."

    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_full_project(client, mock_llm):
    """빈 requirement_ids로 전체 리뷰 요청 -- 프로젝트 전체 요구사항 리뷰."""
    project_id, req_ids = await setup_project_with_requirements(client, count=2)

    mock_llm.return_value = make_review_response(req_ids, issues=[], summary_override={
        "total_issues": 0,
        "ready_for_next": True,
        "feedback": "모든 요구사항이 명확합니다.",
    })

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": []},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "review_id" in body
    assert body["issues"] == []
    assert body["summary"]["ready_for_next"] is True

    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_no_requirements(client, mock_llm):
    """존재하지 않는 requirement_id로 review 요청 -- 404 에러."""
    project_id = await create_project(client)
    fake_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": [fake_id]},
    )

    assert resp.status_code == 404
    mock_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_review_llm_error(client, mock_llm):
    """review 시 LLM 호출 예외 -- 500 에러."""
    mock_llm.side_effect = Exception("Azure OpenAI timeout")

    project_id, req_ids = await setup_project_with_requirements(client, count=2)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_review_invalid_json(client, mock_llm):
    """review 시 LLM이 유효하지 않은 JSON 반환 -- 502 에러."""
    mock_llm.return_value = "이것은 JSON이 아닙니다"

    project_id, req_ids = await setup_project_with_requirements(client, count=2)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_review_no_issues(client, mock_llm):
    """이슈가 없는 경우 -- 빈 배열 + ready_for_next=true."""
    project_id, req_ids = await setup_project_with_requirements(client, count=2)

    mock_llm.return_value = json.dumps({
        "issues": [],
        "summary": {
            "total_issues": 0,
            "conflicts": 0,
            "ready_for_next": True,
            "feedback": "모든 요구사항이 명확하고 일관적입니다.",
        },
    })

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    assert resp.status_code == 200
    body = resp.json()

    assert body["issues"] == []
    assert body["summary"]["total_issues"] == 0
    assert body["summary"]["ready_for_next"] is True
    assert body["summary"]["feedback"] == "모든 요구사항이 명확하고 일관적입니다."

    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_invalid_uuid(client, mock_llm):
    """유효하지 않은 UUID 형식의 requirement_id -- 422 검증 에러."""
    project_id = await create_project(client)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": ["not-a-uuid"]},
    )

    assert resp.status_code == 422
    mock_llm.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests: duplicate detection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_duplicate_detection(client, mock_llm):
    """duplicate 타입 이슈가 올바르게 파싱되고 summary.duplicates가 카운트된다."""
    project_id, req_ids = await setup_project_with_requirements(client, count=3)

    mock_issues = [
        {
            "type": "conflict",
            "description": "req-001과 req-002가 충돌합니다.",
            "related_requirements": ["FR-001", "FR-002"],
            "hint": "응답 시간 제약을 통일하세요.",
        },
        {
            "type": "duplicate",
            "description": "req-001과 req-003이 동일한 의도를 표현합니다.",
            "related_requirements": ["FR-001", "FR-003"],
            "hint": "하나로 통합하세요.",
        },
    ]
    mock_llm.return_value = make_review_response(req_ids, issues=mock_issues)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    assert resp.status_code == 200
    body = resp.json()

    # issues 검증
    assert len(body["issues"]) == 2
    types = [i["type"] for i in body["issues"]]
    assert "conflict" in types
    assert "duplicate" in types

    # duplicate 이슈 상세 검증
    dup_issue = next(i for i in body["issues"] if i["type"] == "duplicate")
    assert "FR-001" in dup_issue["related_requirements"]
    assert "FR-003" in dup_issue["related_requirements"]
    assert dup_issue["hint"] == "하나로 통합하세요."

    # summary 검증
    summary = body["summary"]
    assert summary["total_issues"] == 2
    assert summary["conflicts"] == 1
    assert summary["duplicates"] == 1
    assert summary["ready_for_next"] is True

    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_only_duplicates(client, mock_llm):
    """duplicate만 있는 경우 conflicts=0, duplicates=N."""
    project_id, req_ids = await setup_project_with_requirements(client, count=2)

    mock_issues = [
        {
            "type": "duplicate",
            "description": "동일한 요구사항이 중복됩니다.",
            "related_requirements": ["FR-001", "FR-002"],
            "hint": "중복 제거하세요.",
        },
    ]
    mock_llm.return_value = make_review_response(req_ids, issues=mock_issues)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    assert resp.status_code == 200
    body = resp.json()

    assert len(body["issues"]) == 1
    assert body["issues"][0]["type"] == "duplicate"
    assert body["summary"]["conflicts"] == 0
    assert body["summary"]["duplicates"] == 1
    assert body["summary"]["total_issues"] == 1


# ---------------------------------------------------------------------------
# Tests: POST /review/suggestions/{issue_id}/accept & reject -- v2 예정 (엔드포인트 주석 처리됨)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tests: GET /review/results/latest
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_latest_review(client, mock_llm):
    """최근 리뷰 결과 조회 -- 리뷰 실행 후 조회 가능."""
    project_id, req_ids = await setup_project_with_requirements(client, count=2)

    mock_llm.return_value = make_review_response(req_ids)
    await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": req_ids},
    )

    resp = await client.get(
        f"/api/v1/projects/{project_id}/review/results/latest",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "review_id" in body
    assert "created_at" in body
    assert "reviewed_requirement_ids" in body
    assert "issues" in body
    assert "summary" in body
    assert len(body["reviewed_requirement_ids"]) == 2
    assert len(body["issues"]) == 1


@pytest.mark.asyncio
async def test_get_latest_review_not_found(client, mock_llm):
    """리뷰 이력이 없는 프로젝트에서 조회 -- 404."""
    project_id = await create_project(client)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/review/results/latest",
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_review_full_project_saves_to_db(client, mock_llm):
    """빈 requirement_ids로 전체 리뷰 후 DB에 결과가 저장되고 latest로 조회 가능."""
    project_id, req_ids = await setup_project_with_requirements(client, count=3)

    mock_llm.return_value = make_review_response(req_ids, issues=[], summary_override={
        "total_issues": 0,
        "ready_for_next": True,
        "feedback": "전체 리뷰 완료, 이슈 없음.",
    })

    # 1. 빈 requirement_ids로 전체 리뷰 수행
    review_resp = await client.post(
        f"/api/v1/projects/{project_id}/review/requirements",
        json={"requirement_ids": []},
    )
    assert review_resp.status_code == 200

    # 2. GET /results/latest로 DB 저장 확인
    latest_resp = await client.get(
        f"/api/v1/projects/{project_id}/review/results/latest",
    )
    assert latest_resp.status_code == 200
    body = latest_resp.json()

    # 3. 기본 필드 존재 확인
    assert "review_id" in body
    assert "created_at" in body
    assert "reviewed_requirement_ids" in body
    assert "issues" in body
    assert "summary" in body

    # 4. reviewed_requirement_ids에 모든 요구사항이 포함되었는지 확인
    reviewed_ids = set(body["reviewed_requirement_ids"])
    for rid in req_ids:
        assert rid in reviewed_ids, f"요구사항 {rid}가 reviewed_requirement_ids에 포함되어야 한다"
    assert len(reviewed_ids) == 3

    # 5. summary 값 검증
    assert body["summary"]["ready_for_next"] is True
    assert body["issues"] == []
