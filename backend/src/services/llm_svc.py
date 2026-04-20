import os

from loguru import logger
from openai import AsyncAzureOpenAI, AsyncOpenAI, BadRequestError

from src.core.exceptions import AppException


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "azure").lower()


# 싱글톤 클라이언트
_openai_client: AsyncOpenAI | None = None
_srs_client: AsyncAzureOpenAI | None = None
_tc_client: AsyncAzureOpenAI | None = None


def _get_default_model(client_type: str = "srs") -> str:
    if _get_provider() == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o")
    if client_type == "tc":
        return os.getenv("TC_MODEL", "gpt-5.2")
    return os.getenv("SRS_MODEL", "gpt-5.2")


def get_openai_client() -> AsyncOpenAI:
    """개인용 OpenAI 클라이언트"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AppException(500, "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


def get_srs_client() -> AsyncAzureOpenAI:
    """회사용 Azure OpenAI 클라이언트 (SRS)"""
    global _srs_client
    if _srs_client is None:
        api_key = os.getenv("SRS_API_KEY")
        endpoint = os.getenv("SRS_ENDPOINT")
        if not api_key or not endpoint:
            raise AppException(500, "SRS_API_KEY / SRS_ENDPOINT 환경변수가 설정되지 않았습니다.")
        _srs_client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2025-03-01-preview",
        )
    return _srs_client


def get_tc_client() -> AsyncAzureOpenAI:
    """회사용 Azure OpenAI 클라이언트 (TC)"""
    global _tc_client
    if _tc_client is None:
        api_key = os.getenv("TC_API_KEY")
        endpoint = os.getenv("TC_ENDPOINT")
        if not api_key or not endpoint:
            raise AppException(500, "TC_API_KEY / TC_ENDPOINT 환경변수가 설정되지 않았습니다.")
        _tc_client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2025-03-01-preview",
        )
    return _tc_client


def get_client(client_type: str = "srs") -> AsyncOpenAI | AsyncAzureOpenAI:
    """LLM_PROVIDER에 따라 적절한 클라이언트 반환"""
    if _get_provider() == "openai":
        return get_openai_client()
    return get_srs_client() if client_type == "srs" else get_tc_client()


async def chat_completion(
    messages: list[dict],
    *,
    model: str | None = None,
    client_type: str = "srs",
    temperature: float = 0.3,
    max_completion_tokens: int = 4096,
) -> str:
    """Chat Completion 호출 (OpenAI / Azure OpenAI 자동 전환)"""
    resolved_model = model or _get_default_model(client_type)
    client = get_client(client_type)
    provider = _get_provider()

    logger.debug(f"LLM 호출: provider={provider}, model={resolved_model}, messages={len(messages)}개")

    try:
        response = await client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
    except BadRequestError as e:
        # Azure 콘텐츠 필터 처리
        if provider == "azure":
            body = e.body or {}
            inner = body.get("innererror", {}) if isinstance(body, dict) else {}
            if inner.get("code") == "ResponsibleAIPolicyViolation":
                filters = inner.get("content_filter_result", {})
                triggered = [
                    k for k, v in filters.items()
                    if isinstance(v, dict) and v.get("filtered")
                ]
                logger.warning(f"Azure 콘텐츠 필터 차단: categories={triggered}")
                raise AppException(
                    status_code=422,
                    detail="콘텐츠 필터에 의해 요청이 차단되었습니다. 입력 내용을 수정 후 다시 시도해주세요.",
                ) from e
        raise

    content = response.choices[0].message.content or ""
    logger.debug(f"LLM 응답: {len(content)}자")
    return content
