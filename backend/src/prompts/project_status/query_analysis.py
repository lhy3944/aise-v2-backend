"""Project status query analysis — 사용자 질문에서 필요한 집계를 식별."""

ANALYSIS_SYSTEM_PROMPT = """당신은 사용자의 프로젝트 현황 질문을 분석하여 필요한 추가 데이터를 식별합니다.

## 현재 알려진 현황

{base_summary}

## 사용 가능한 artifact 타입과 content 필드

- record: text, section_id, source_document_id, confidence_score, is_auto_extracted, order_index, metadata.status
- testcase: title, precondition, steps, expected_result, priority(high/medium/low), type(functional/non_functional/boundary/negative), related_srs_section_id
- srs: sections(배열), based_on_records, based_on_documents, status
- design: srs와 유사한 sections 구조

## 규칙

1. 기본 현황 데이터로 답변 가능하면 answerable=true로 응답
2. 추가 집계가 필요하면 answerable=false이고 queries에 필요한 집계를 나열
3. 반드시 순수 JSON만 반환 (코드펜스 금지)
4. 여러 필드 집계가 필요하면 queries에 여러 항목 추가

## 응답 형식

기본 현황으로 답변 가능:
{{"answerable": true, "response": "답변 내용"}}

추가 집계 필요:
{{"answerable": false, "queries": [{{"artifact_type": "testcase", "field": "priority"}}]}}"""


def build_query_analysis_prompt(
    *,
    base_summary: str,
    query: str,
) -> list[dict]:
    system = ANALYSIS_SYSTEM_PROMPT.format(base_summary=base_summary)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]


__all__ = ["build_query_analysis_prompt"]
