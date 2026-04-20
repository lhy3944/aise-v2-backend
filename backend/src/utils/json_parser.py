"""JSON 파싱 공통 유틸리티 -- LLM 응답 파싱에 사용"""

import json

from loguru import logger

from src.core.exceptions import AppException


def parse_llm_json(raw: str, *, error_msg: str = "AI 응답을 파싱할 수 없습니다.") -> dict:
    """LLM 응답 문자열에서 JSON 객체를 추출한다.

    마크다운 코드 펜스(```json ... ```)로 감싸진 경우도 처리한다.

    Args:
        raw: LLM이 반환한 원본 문자열.
        error_msg: 파싱 실패 시 AppException에 사용할 메시지.

    Returns:
        파싱된 dict 객체.

    Raises:
        AppException(502): JSON 파싱에 실패한 경우.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"LLM 응답 JSON 파싱 실패: {exc}\n원본: {raw[:500]}")
        raise AppException(status_code=502, detail=error_msg)
