"""Agent Chat API 라우터"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.schemas.api.agent import AgentChatRequest
from src.services import agent_svc

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/chat")
async def agent_chat(body: AgentChatRequest):
    """Agent Chat SSE 스트리밍 엔드포인트

    session_id 기반: 백엔드가 DB에서 history 로드 + 메시지 자동 저장
    (DB 세션은 stream_chat 내부에서 자체 관리 — StreamingResponse 수명 이슈 방지)

    SSE 이벤트 형식:
    - data: {"type": "token", "content": "..."} -- 텍스트 토큰
    - data: {"type": "tool_call", "name": "...", "arguments": {...}} -- 도구 호출
    - data: {"type": "done"} -- 스트리밍 완료
    - data: {"type": "error", "content": "..."} -- 에러
    """
    return StreamingResponse(
        agent_svc.stream_chat(body.session_id, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
