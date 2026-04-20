"""SRS 생성 프롬프트 — 섹션별 레코드 기반"""

SYSTEM_PROMPT = """당신은 IEEE 830 / ISO 29148 표준에 정통한 소프트웨어 요구공학 전문가입니다.
제공된 레코드와 용어 사전을 기반으로 SRS(Software Requirements Specification) 문서의 특정 섹션을 작성합니다.

규칙:
- 레코드에 있는 내용만 기반으로 작성합니다. 추가 내용을 임의로 생성하지 마세요.
- 각 레코드의 ID를 본문에 참조로 표시합니다 (예: [FR-001])
- 도메인 용어는 용어 사전의 정의를 따릅니다
- 명확하고 검증 가능한 표현을 사용합니다
- 입력 언어와 동일한 언어로 작성합니다
- Markdown 형식으로 작성합니다"""


def build_srs_section_prompt(
    section_name: str,
    section_description: str | None,
    output_format_hint: str | None,
    records: list[dict],
    glossary: list[dict],
) -> list[dict]:
    """SRS 섹션 하나를 생성하는 프롬프트를 빌드한다."""

    records_text = "\n".join(
        f"- [{r['display_id']}] {r['content']}"
        for r in records
    ) if records else "(레코드 없음)"

    glossary_text = "\n".join(
        f"- {g['term']}: {g['definition']}"
        for g in glossary
    ) if glossary else "(없음)"

    user_content = f"""\
다음 섹션의 SRS 문서 내용을 작성하세요.

## 섹션 정보
- 이름: {section_name}
{f'- 설명: {section_description}' if section_description else ''}
{f'- 출력 형식 힌트: {output_format_hint}' if output_format_hint else ''}

## 이 섹션에 포함된 레코드
{records_text}

## 용어 사전
{glossary_text}

위 레코드를 기반으로 "{section_name}" 섹션의 SRS 내용을 Markdown으로 작성하세요.
각 레코드 ID를 본문에 참조로 포함하세요."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_srs_generate_prompt(
    sections_with_records: list[dict],
    glossary: list[dict],
) -> str:
    """전체 SRS 생성 개요 프롬프트 (사용하지 않지만 export용)"""
    return SYSTEM_PROMPT
