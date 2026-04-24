"""TestCase 생성 프롬프트 — SRS 섹션 기반으로 TC JSON 배열 생성"""

SYSTEM_PROMPT = """당신은 ISTQB 공인 테스트 설계 전문가입니다.
제공된 SRS 섹션 내용을 기반으로 검증 가능한 테스트 케이스를 JSON 배열로 생성합니다.

규칙:
- 반드시 순수 JSON 배열만 반환합니다. 설명 문장/코드펜스 금지.
- SRS 섹션에 명시된 요구사항만 다룹니다. 추측 금지.
- 각 TC 는 positive 1개 + negative 1개 이상을 권장하되 섹션의 복잡도에 맞춰 조절합니다.
- 섹션당 최대 5개, 최소 1개.
- 입력 언어와 동일한 언어로 작성합니다.

각 TC 객체 스키마:
{
  "title": str,              // "TC-FR-001 다크모드 토글" 과 같은 한 줄 제목
  "precondition": str,       // 테스트 수행 전 전제 (없으면 "없음")
  "steps": list[str],        // 순서대로 수행할 단계들
  "expected_result": str,    // 기대 결과
  "priority": str,           // "high" | "medium" | "low"
  "type": str,               // "functional" | "non_functional" | "boundary" | "negative"
  "related_srs_section_id": str  // 입력으로 받은 섹션 id 그대로 포함
}
"""


def build_testcase_section_prompt(
    *,
    section_title: str,
    section_content: str,
    srs_section_id: str,
    glossary: list[dict],
) -> list[dict]:
    """하나의 SRS 섹션에서 테스트 케이스 JSON 배열을 생성하는 프롬프트."""

    glossary_text = (
        "\n".join(f"- {g['term']}: {g['definition']}" for g in glossary)
        if glossary
        else "(없음)"
    )

    user_content = f"""\
다음 SRS 섹션을 읽고 테스트 케이스를 생성하세요.

## SRS 섹션 id
{srs_section_id}

## 섹션 제목
{section_title}

## 섹션 내용
{section_content}

## 용어 사전
{glossary_text}

위 섹션을 검증하기 위한 테스트 케이스 JSON 배열을 반환하세요.
각 객체는 위의 스키마(title / precondition / steps / expected_result / priority / type /
related_srs_section_id)를 따라야 하며, related_srs_section_id 는 반드시 "{srs_section_id}" 를 그대로 복사하세요."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


__all__ = ["SYSTEM_PROMPT", "build_testcase_section_prompt"]
