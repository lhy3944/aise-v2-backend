"""프로젝트 요구사항 기반 Glossary 자동 생성 프롬프트."""

SYSTEM_PROMPT = "JSON 형식으로만 응답하세요."

USER_PROMPT_TEMPLATE = """\
당신은 소프트웨어 요구사항 분석 전문가입니다.
아래 요구사항 목록에서 프로젝트 Glossary(용어집)에 포함되어야 할 \
도메인 용어, 약어, 기술 용어를 추출하고 정의를 작성하세요.

규칙:
- 일반적인 프로그래밍 용어(API, DB 등)는 제외하고, 프로젝트 도메인에 특화된 용어만 추출
- 각 용어에 대해 명확하고 간결한 정의를 작성
- product_group이 식별 가능하면 포함, 아니면 null
- 반드시 아래 JSON 형식으로만 응답

출력 형식:
{{"glossary": [{{"term": "용어", "definition": "정의", "product_group": "제품군 또는 null"}}]}}

요구사항 목록:
{requirements_block}"""


def build_glossary_generate_prompt(requirements_block: str) -> list[dict]:
    """Glossary 자동 생성용 프롬프트 메시지 리스트를 생성한다.

    Args:
        requirements_block: 줄바꿈으로 구분된 요구사항 텍스트 블록.

    Returns:
        OpenAI chat messages 형식의 리스트.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                requirements_block=requirements_block,
            ),
        },
    ]
