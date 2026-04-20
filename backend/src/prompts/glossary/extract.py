"""지식 문서 기반 Glossary 추출 프롬프트."""

SYSTEM_PROMPT = "JSON 형식으로만 응답하세요."

USER_PROMPT_TEMPLATE = """\
당신은 소프트웨어 요구사항 분석 전문가입니다.
아래 지식 문서 내용에서 프로젝트 용어집(Glossary)에 포함되어야 할 \
도메인 용어, 약어, 기술 용어를 추출하고 정의를 작성하세요.

규칙:
- 일반적인 프로그래밍 용어(API, DB, HTTP 등)는 제외하고, 프로젝트 도메인에 특화된 용어만 추출
- 각 용어에 대해 명확하고 간결한 정의를 작성
- 동의어(synonyms)가 있으면 함께 추출
- 약어(abbreviations)가 있으면 함께 추출
- 이미 등록된 용어와 중복되지 않도록 기존 용어 목록을 참고
- 입력 언어와 동일한 언어로 응답
- 반드시 아래 JSON 형식으로만 응답

출력 형식:
{{"glossary": [{{"term": "용어", "definition": "정의", "synonyms": ["동의어1"], "abbreviations": ["약어1"]}}]}}

기존 등록된 용어 (중복 제외용):
{existing_terms}

지식 문서 내용:
{document_text}"""


def build_glossary_extract_prompt(
    document_text: str,
    existing_terms: list[str],
) -> list[dict]:
    """지식 문서 기반 용어 추출 프롬프트를 생성한다."""
    terms_str = ", ".join(existing_terms) if existing_terms else "(없음)"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                document_text=document_text,
                existing_terms=terms_str,
            ),
        },
    ]
