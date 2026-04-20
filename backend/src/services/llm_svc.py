"""LLM service — LiteLLM-backed chat completion with provider abstraction.

`chat_completion()` is the public API. Internally it routes through LiteLLM
(`litellm.acompletion`) so new providers can be added by env alone.

Provider selection
------------------
- LLM_PROVIDER=openai → `model` is used as-is (e.g. "gpt-4o"), uses
  OPENAI_API_KEY.
- LLM_PROVIDER=azure  → `model` is prefixed with "azure/" and LiteLLM
  receives the per-client-type (srs|tc) API key, endpoint, and
  api_version. Two separate Azure deployments are supported
  (SRS_API_KEY/SRS_ENDPOINT vs TC_API_KEY/TC_ENDPOINT).

Legacy surface
--------------
`get_client`, `get_srs_client`, `get_tc_client`, `get_openai_client`,
`_get_provider`, `_get_default_model` are retained for backward
compatibility — they still return the raw OpenAI SDK client objects
used by `services.embedding_svc` and `services.agent_svc`. Those will
migrate to LiteLLM in a later phase.
"""

from __future__ import annotations

import os
from typing import Any

import litellm
from litellm.exceptions import BadRequestError as LiteLLMBadRequestError
from loguru import logger
from openai import AsyncAzureOpenAI, AsyncOpenAI, BadRequestError

from src.core.exceptions import AppException

AZURE_API_VERSION = "2025-03-01-preview"


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "azure").lower()


# Singleton OpenAI SDK clients (legacy, used by embeddings + legacy agent_svc)
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
    """Return the singleton OpenAI SDK client (legacy surface)."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AppException(500, "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


def get_srs_client() -> AsyncAzureOpenAI:
    """Return the singleton Azure OpenAI SRS client (legacy surface)."""
    global _srs_client
    if _srs_client is None:
        api_key = os.getenv("SRS_API_KEY")
        endpoint = os.getenv("SRS_ENDPOINT")
        if not api_key or not endpoint:
            raise AppException(500, "SRS_API_KEY / SRS_ENDPOINT 환경변수가 설정되지 않았습니다.")
        _srs_client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=AZURE_API_VERSION,
        )
    return _srs_client


def get_tc_client() -> AsyncAzureOpenAI:
    """Return the singleton Azure OpenAI TC client (legacy surface)."""
    global _tc_client
    if _tc_client is None:
        api_key = os.getenv("TC_API_KEY")
        endpoint = os.getenv("TC_ENDPOINT")
        if not api_key or not endpoint:
            raise AppException(500, "TC_API_KEY / TC_ENDPOINT 환경변수가 설정되지 않았습니다.")
        _tc_client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=AZURE_API_VERSION,
        )
    return _tc_client


def get_client(client_type: str = "srs") -> AsyncOpenAI | AsyncAzureOpenAI:
    """Return a raw SDK client chosen by LLM_PROVIDER (legacy surface)."""
    if _get_provider() == "openai":
        return get_openai_client()
    return get_srs_client() if client_type == "srs" else get_tc_client()


# ---------- LiteLLM-backed chat_completion ----------


def _litellm_kwargs(client_type: str, model: str | None) -> dict[str, Any]:
    """Build the provider-specific kwargs for litellm.acompletion."""
    provider = _get_provider()
    resolved = model or _get_default_model(client_type)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AppException(500, "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return {"model": resolved, "api_key": api_key}

    # Azure
    if client_type == "tc":
        api_key = os.getenv("TC_API_KEY")
        api_base = os.getenv("TC_ENDPOINT")
    else:
        api_key = os.getenv("SRS_API_KEY")
        api_base = os.getenv("SRS_ENDPOINT")
    if not api_key or not api_base:
        raise AppException(
            500,
            f"Azure {client_type.upper()}_API_KEY / {client_type.upper()}_ENDPOINT 환경변수가 설정되지 않았습니다.",
        )
    return {
        "model": f"azure/{resolved}",
        "api_key": api_key,
        "api_base": api_base,
        "api_version": AZURE_API_VERSION,
    }


def _is_azure_content_filter(exc: Exception) -> bool:
    """Detect Azure's Responsible AI content-filter rejection.

    LiteLLM often wraps provider errors; fall back to stringification.
    """
    body = getattr(exc, "body", None) or getattr(exc, "response", None)
    if isinstance(body, dict):
        inner = body.get("innererror") or {}
        if isinstance(inner, dict) and inner.get("code") == "ResponsibleAIPolicyViolation":
            return True
    return "ResponsibleAIPolicyViolation" in str(exc)


async def chat_completion(
    messages: list[dict],
    *,
    model: str | None = None,
    client_type: str = "srs",
    temperature: float = 0.3,
    max_completion_tokens: int = 4096,
) -> str:
    """Chat completion via LiteLLM (preserves legacy signature)."""
    kwargs = _litellm_kwargs(client_type, model)
    provider = _get_provider()

    logger.debug(
        f"LLM 호출(LiteLLM): provider={provider}, model={kwargs['model']}, messages={len(messages)}개"
    )

    try:
        response = await litellm.acompletion(
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            **kwargs,
        )
    except (BadRequestError, LiteLLMBadRequestError) as e:
        if provider == "azure" and _is_azure_content_filter(e):
            logger.warning("Azure content filter rejected the request")
            raise AppException(
                status_code=422,
                detail="콘텐츠 필터에 의해 요청이 차단되었습니다. 입력 내용을 수정 후 다시 시도해주세요.",
            ) from e
        raise

    # LiteLLM's response mirrors OpenAI's: .choices[0].message.content
    content = response.choices[0].message.content or ""
    logger.debug(f"LLM 응답: {len(content)}자")
    return content
