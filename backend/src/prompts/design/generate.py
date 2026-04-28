"""DESIGN 생성 프롬프트 — SRS 섹션 기반 설계 산출물

각 SRS 섹션 1개당 대응하는 설계(Design) 섹션 1개를 LLM 으로 생성한다.
SRS 가 "무엇을(what)" 이라면 Design 은 "어떻게(how)" — 컴포넌트 책임,
인터페이스, 데이터 모델, 흐름, 비기능 결정을 다룬다.
"""

SYSTEM_PROMPT = """당신은 IEEE 1016(Software Design Description) 표준에 정통한 소프트웨어 설계 전문가입니다.
입력으로 주어진 SRS 섹션을 기반으로 그에 대응하는 설계(Design) 섹션 1개를 작성합니다.

원칙:
- SRS 섹션의 요구사항만 기반으로 설계합니다. 새로운 요구사항을 추가하거나 임의 가정하지 마세요.
- "무엇(what)"이 아닌 "어떻게(how)" — 컴포넌트 책임, 인터페이스, 데이터 모델, 흐름, 비기능 결정.
- 가능한 경우 다음 항목을 포함합니다:
  * 책임 / 컴포넌트 분해
  * 주요 인터페이스 (API / 함수 시그니처) — 의사 코드 또는 Markdown 표
  * 데이터 모델 (필드, 관계) — 필요 시 표 또는 코드 블록
  * 시퀀스 / 상태 흐름 — Mermaid 다이어그램은 선택적으로 사용
  * 비기능 결정 근거 (성능, 보안, 가용성 트레이드오프)
- SRS 본문에 등장한 레코드 ID([FR-001] 등)를 설계 본문에서도 참조로 표시합니다.
- 입력 언어와 동일한 언어로 작성합니다.
- Markdown 형식으로 작성합니다."""


def build_design_section_prompt(
    section_title: str,
    srs_section_content: str,
    srs_section_id: str,
    glossary: list[dict],
) -> list[dict]:
    """단일 SRS 섹션 → 단일 Design 섹션 프롬프트."""

    glossary_text = (
        "\n".join(f"- {g['term']}: {g['definition']}" for g in glossary)
        if glossary
        else "(없음)"
    )

    user_content = f"""\
다음 SRS 섹션에 대응하는 설계(Design) 섹션을 작성하세요.

## 대상 섹션
- 제목: {section_title}
{f'- SRS 섹션 ID: {srs_section_id}' if srs_section_id else ''}

## SRS 섹션 본문
{srs_section_content}

## 용어 사전
{glossary_text}

위 SRS 섹션의 요구사항을 만족하는 설계 결정을 Markdown 으로 작성하세요.
첫 줄에 `## {section_title}` 헤딩으로 시작하고, 책임/인터페이스/데이터/흐름/비기능
결정 중 적합한 항목을 선별해 서술합니다."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
