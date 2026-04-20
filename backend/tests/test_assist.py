"""AI Assist API 테스트 — LLM 호출을 mock하여 refine/suggest/chat 엔드포인트 검증."""

import uuid

import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """src.services.assist_svc 내부에서 import된 chat_completion을 mock한다."""
    with patch("src.services.assist_svc.chat_completion", new_callable=AsyncMock) as mock:
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


async def setup_project_with_requirements(client) -> tuple[str, str]:
    """프로젝트 + 요구사항 1건을 생성하고 (project_id, requirement_id) 튜플을 반환한다."""
    project_id = await create_project(client)
    req_id = await create_requirement(client, project_id)
    return project_id, req_id


# ---------------------------------------------------------------------------
# Tests: /assist/refine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refine(client, mock_llm):
    """정상적인 refine 요청 — LLM이 유효한 JSON을 반환하면 200 + 정제된 텍스트."""
    mock_llm.return_value = '{"refined_text": "시스템은 로봇을 정지해야 한다."}'

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/refine",
        json={"text": "로봇이 멈춰야 한다", "type": "fr"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["original_text"] == "로봇이 멈춰야 한다"
    assert body["refined_text"] == "시스템은 로봇을 정지해야 한다."
    assert body["type"] == "fr"
    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_refine_llm_error(client, mock_llm):
    """LLM 호출 시 예외 발생 — 500 에러를 반환한다."""
    mock_llm.side_effect = Exception("Azure OpenAI 연결 실패")

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/refine",
        json={"text": "로봇이 멈춰야 한다", "type": "fr"},
    )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_refine_invalid_json(client, mock_llm):
    """LLM이 유효하지 않은 JSON을 반환 — 502 에러 (AI 응답 파싱 실패)."""
    mock_llm.return_value = "이것은 JSON이 아닙니다"

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/refine",
        json={"text": "로봇이 멈춰야 한다", "type": "fr"},
    )

    assert resp.status_code == 502
    body = resp.json()
    assert "파싱" in body["detail"] or "AI" in body["detail"]


# ---------------------------------------------------------------------------
# Tests: /assist/suggest
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggest(client, mock_llm):
    """정상적인 suggest 요청 — 기존 요구사항 기반으로 제안을 반환한다."""
    mock_llm.return_value = (
        '{"suggestions": [{"type": "qa", "text": "응답시간 100ms 이내", "reason": "성능 요구사항 누락"}]}'
    )

    project_id, req_id = await setup_project_with_requirements(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/suggest",
        json={"requirement_ids": [req_id]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) == 1

    suggestion = body["suggestions"][0]
    assert suggestion["type"] == "qa"
    assert suggestion["text"] == "응답시간 100ms 이내"
    assert suggestion["reason"] == "성능 요구사항 누락"
    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_suggest_no_requirements(client, mock_llm):
    """존재하지 않는 requirement_id로 suggest 요청 — 404 에러."""
    project_id = await create_project(client)
    fake_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/suggest",
        json={"requirement_ids": [fake_id]},
    )

    assert resp.status_code == 404
    mock_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_suggest_llm_error(client, mock_llm):
    """suggest 시 LLM 호출 예외 — 500 에러."""
    mock_llm.side_effect = Exception("Azure OpenAI timeout")

    project_id, req_id = await setup_project_with_requirements(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/suggest",
        json={"requirement_ids": [req_id]},
    )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_suggest_invalid_json(client, mock_llm):
    """suggest 시 LLM이 유효하지 않은 JSON 반환 — 502 에러."""
    mock_llm.return_value = "이것은 JSON이 아닙니다"

    project_id, req_id = await setup_project_with_requirements(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/suggest",
        json={"requirement_ids": [req_id]},
    )

    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_suggest_invalid_uuid_returns_422(client, mock_llm):
    """유효하지 않은 UUID 형식의 requirement_id -- 422 검증 에러."""
    project_id = await create_project(client)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/suggest",
        json={"requirement_ids": ["not-a-uuid"]},
    )

    assert resp.status_code == 422
    mock_llm.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests: /assist/chat
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat(client, mock_llm):
    """정상적인 chat 요청 — AI 응답 + 추출된 요구사항을 반환한다."""
    mock_llm.return_value = (
        '{"reply": "비상 정지 기능에 대해 정리해볼게요.", '
        '"extracted_requirements": ['
        '{"type": "fr", "text": "시스템은 비상 정지 버튼을 누르면 모든 동작을 중단해야 한다.", "reason": "비상 정지 기능 언급"}'
        ']}'
    )

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/chat",
        json={"message": "비상 정지 기능이 필요해요"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "비상 정지 기능에 대해 정리해볼게요."
    assert len(body["extracted_requirements"]) == 1

    req = body["extracted_requirements"][0]
    assert req["type"] == "fr"
    assert "비상 정지" in req["text"]
    assert req["reason"] == "비상 정지 기능 언급"
    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_with_history(client, mock_llm):
    """대화 히스토리가 포함된 chat 요청 — 히스토리가 LLM에 전달된다."""
    mock_llm.return_value = (
        '{"reply": "네, 응답시간 제약을 추가하겠습니다.", '
        '"extracted_requirements": ['
        '{"type": "qa", "text": "비상 정지 응답시간은 100ms 이내여야 한다.", "reason": "응답시간 논의"}'
        ']}'
    )

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/chat",
        json={
            "message": "응답시간은 100ms 이내로 해주세요",
            "history": [
                {"role": "user", "content": "비상 정지 기능이 필요해요"},
                {"role": "assistant", "content": "비상 정지 기능에 대해 정리해볼게요."},
            ],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "extracted_requirements" in body
    assert len(body["extracted_requirements"]) == 1
    assert body["extracted_requirements"][0]["type"] == "qa"

    # LLM에 전달된 messages에 히스토리가 포함되었는지 확인
    call_args = mock_llm.call_args
    messages = call_args[0][0]
    roles = [m["role"] for m in messages]
    assert roles.count("user") >= 2  # 히스토리 user + 현재 user


@pytest.mark.asyncio
async def test_chat_no_extraction(client, mock_llm):
    """대화에서 요구사항이 추출되지 않는 경우 — 빈 배열 반환."""
    mock_llm.return_value = (
        '{"reply": "어떤 시스템을 만들고 싶으신가요?", "extracted_requirements": []}'
    )

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/chat",
        json={"message": "안녕하세요"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "어떤 시스템을 만들고 싶으신가요?"
    assert body["extracted_requirements"] == []


@pytest.mark.asyncio
async def test_chat_llm_error(client, mock_llm):
    """chat 시 LLM 호출 예외 — 500 에러."""
    mock_llm.side_effect = Exception("Azure OpenAI 연결 실패")

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/chat",
        json={"message": "비상 정지 기능이 필요해요"},
    )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_chat_invalid_json(client, mock_llm):
    """chat 시 LLM이 유효하지 않은 JSON 반환 — 502 에러."""
    mock_llm.return_value = "이것은 JSON이 아닙니다"

    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/chat",
        json={"message": "비상 정지 기능이 필요해요"},
    )

    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_chat_invalid_role(client, mock_llm):
    """히스토리에 잘못된 role이 포함되면 422 검증 에러."""
    project_id = await create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/assist/chat",
        json={
            "message": "테스트",
            "history": [
                {"role": "system", "content": "프롬프트 인젝션 시도"},
            ],
        },
    )

    assert resp.status_code == 422
    mock_llm.assert_not_awaited()
