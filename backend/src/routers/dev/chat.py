"""
Dev용 Chat API — Azure OpenAI Responses API 멀티턴 테스트
Frontend에서 LLM 연동 확인용

사용법:
  POST /api/dev/chat          — 새 대화 시작 또는 멀티턴 이어가기
  POST /api/dev/chat/reset    — 대화 초기화 (previous_response_id 삭제)
"""

import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from openai import AzureOpenAI
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/dev", tags=["dev"])

# --- Azure OpenAI 클라이언트 ---
_client = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("SRS_API_KEY"),
            azure_endpoint=os.getenv("SRS_ENDPOINT"),
            api_version="2025-03-01-preview",
        )
    return _client


# --- 스키마 ---


class ChatRequest(BaseModel):
    message: str = Field(description="사용자 메시지")
    previous_response_id: str | None = Field(
        default=None, description="이전 응답 ID (멀티턴 시 사용)"
    )
    system_prompt: str | None = Field(
        default="You are a helpful assistant.", description="시스템 프롬프트"
    )
    stream: bool = Field(default=False, description="스트리밍 여부")


class ChatResponse(BaseModel):
    response_id: str = Field(description="응답 ID (다음 턴에 previous_response_id로 사용)")
    content: str = Field(description="AI 응답 내용")
    model: str = Field(description="사용된 모델")


# --- API ---


@router.post("/chat", response_model=ChatResponse)
async def dev_chat(req: ChatRequest):
    """
    Azure OpenAI Responses API를 이용한 채팅.
    - 첫 요청: previous_response_id 없이 보내면 새 대화 시작
    - 멀티턴: 응답의 response_id를 previous_response_id로 보내면 대화 이어감
    """
    logger.info(
        f"[DEV CHAT] message={req.message[:50]}, prev_id={req.previous_response_id}"
    )

    client = _get_client()

    # 입력 구성
    input_messages = [{"role": "user", "content": req.message}]

    # Responses API 호출
    kwargs = {
        "model": "gpt-5.2",
        "input": input_messages,
    }

    # 시스템 프롬프트 (첫 턴에만)
    if req.system_prompt and not req.previous_response_id:
        kwargs["instructions"] = req.system_prompt

    # 멀티턴: 이전 응답 ID 연결
    if req.previous_response_id:
        kwargs["previous_response_id"] = req.previous_response_id

    # 스트리밍
    if req.stream:
        kwargs["stream"] = True

        async def generate():
            response_id = ""
            stream = client.responses.create(**kwargs)
            for event in stream:
                if hasattr(event, "response") and event.response:
                    response_id = event.response.id
                if event.type == "response.output_text.delta":
                    yield event.delta
            # 마지막에 response_id 전달 (프론트에서 파싱)
            yield f"\n[RESPONSE_ID:{response_id}]"

        return StreamingResponse(generate(), media_type="text/plain")

    # 일반 응답
    response = client.responses.create(**kwargs)

    # 응답에서 텍스트 추출
    content = ""
    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if block.type == "output_text":
                    content += block.text

    logger.info(
        f"[DEV CHAT] response_id={response.id}, content_length={len(content)}"
    )

    return ChatResponse(
        response_id=response.id,
        content=content,
        model=response.model,
    )


@router.post("/chat/reset")
async def dev_chat_reset():
    """대화 초기화 — 프론트에서 previous_response_id를 버리면 됨"""
    return {"message": "previous_response_id를 null로 설정하면 새 대화가 시작됩니다."}
