"""Agent API 테스트"""

import pytest


@pytest.mark.asyncio
async def test_agent_chat_invalid_session_id_returns_422(client):
    resp = await client.post(
        "/api/v1/agent/chat",
        json={"session_id": "not-a-uuid", "message": "안녕하세요"},
    )

    assert resp.status_code == 422
