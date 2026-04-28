"""Requirement record 추출 프롬프트.

`artifact_record_svc.extract_records` 가 호출하는 두 가지 추출 모드의
LLM messages 를 구성한다.

- `build_document_extract_messages`: 활성 지식 문서 청크에서 섹션별 후보를
  추출 (기존 동작).
- `build_user_text_extract_messages`: 사용자가 채팅에 직접 입력한 자유
  텍스트를 한 문장 = 한 후보로 분해 (Phase 3 PR-2 후 도입). 지식 문서가
  없는 신규 프로젝트에서도 동작.

두 모드 모두 동일한 출력 JSON 스키마 (`records: [{section_name, content,
source_document, source_location, confidence}]`) 를 사용해 후속 파싱
로직 (`parse_llm_json` + `ArtifactRecordExtractedItem` 매핑) 을 공유한다.
"""
from __future__ import annotations


_OUTPUT_FORMAT = """\
{"records": [
  {"section_name": "섹션명", "content": "레코드 내용", "source_document": "문서명", "source_location": "위치 정보", "confidence": 0.85}
]}\
"""


def build_document_extract_messages(
    *, sections_text: str, glossary_text: str, document_text: str,
) -> list[dict[str, str]]:
    """기존 문서 기반 추출 프롬프트 (인라인 → 외부화)."""
    user = f"""\
아래 지식 문서에서 섹션별 레코드를 추출하세요.

규칙:
- 각 레코드는 하나의 독립적인 요구사항/제약/속성/설명 단위여야 합니다
- 원문에 없는 내용을 생성하지 마세요
- 각 레코드에 출처(문서명, 위치)를 반드시 명시하세요
- 신뢰도 점수(0.0~1.0)를 부여하세요 (명확한 내용: 0.8+, 모호한 내용: 0.5 이하)
- 입력 언어와 동일한 언어로 응답하세요

출력 형식:
{_OUTPUT_FORMAT}

섹션 목록:
{sections_text}

용어 사전:
{glossary_text}

지식 문서:
{document_text}"""
    return [
        {"role": "system", "content": "JSON 형식으로만 응답하세요."},
        {"role": "user", "content": user},
    ]


def build_user_text_extract_messages(
    *, sections_text: str, glossary_text: str, user_text: str,
) -> list[dict[str, str]]:
    """채팅 자유 입력 기반 추출 프롬프트 (Phase 3 신규).

    `source_document` 는 항상 비우고 `source_location` 은 `"user_input"`
    으로 고정하도록 LLM 에 지시한다. 한 문장 = 한 후보 분해 원칙.
    """
    user = f"""\
사용자가 채팅으로 직접 입력한 텍스트입니다. 한 문장 = 한 레코드 후보로
섹션별로 분류해 추출하세요.

규칙:
- 각 레코드는 하나의 독립적인 요구사항/제약/속성/설명 단위여야 합니다
- source_document 필드는 빈 문자열 ""
- source_location 필드는 항상 "user_input" 고정
- 입력에 명시되지 않은 내용을 생성하지 마세요
- 신뢰도 점수(0.0~1.0): 명확한 진술문(0.85+), 모호한 표현(0.6 이하)
- 입력 언어와 동일한 언어로 응답하세요
- 추출할 만한 요구사항이 없으면 records 를 빈 배열로 반환하세요

출력 형식:
{_OUTPUT_FORMAT}

섹션 목록:
{sections_text}

용어 사전:
{glossary_text}

사용자 입력:
{user_text}"""
    return [
        {"role": "system", "content": "JSON 형식으로만 응답하세요."},
        {"role": "user", "content": user},
    ]


__all__ = [
    "build_document_extract_messages",
    "build_user_text_extract_messages",
]
