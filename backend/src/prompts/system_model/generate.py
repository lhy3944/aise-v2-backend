"""시스템 모델 생성 프롬프트 — SRS 기반 Use Case, Interaction, Conceptual Design

SRS 전체를 입력으로 받아 4개 섹션을 생성한다:
1. Use Case Diagram (PlantUML)
2. Use Case Specifications
3. Interaction Diagrams (PlantUML 시퀀스 다이어그램)
4. System Conceptual Design
"""

SYSTEM_PROMPT = """당신은 UML 및 시스템 모델링 전문가입니다.
입력으로 주어진 SRS 문서 전체를 기반으로 시스템 모델을 작성합니다.

원칙:
- SRS의 요구사항만 기반으로 작성합니다. 새로운 요구사항을 추가하거나 임의 가정하지 마세요.
- SRS 본문에 등장한 레코드 ID([FR-001] 등)를 본문에서 참조로 표시합니다.
- 입력 언어와 동일한 언어로 작성합니다.

각 섹션 작성 규칙:

## 1. Use Case Diagram
- PlantUML 형식으로 작성합니다.
- 반드시 ```plantuml 코드 블록으로 감쌉니다.
- @startuml / @enduml 을 사용합니다.
- left to right direction 지정.
- 액터(actor)는 사용자/외부시스템으로 구분.
- 유스케이스는 동사구로 명명 (예: "로그인 한다").
- include/extend 관계를 적절히 표현.
- 패키지로 기능 영역을 그룹화.

## 2. Use Case Specifications
- 각 주요 Use Case에 대해 다음 항목을 Markdown 표로 작성:
  * Use Case ID, 이름
  * 주 액터
  * 사전 조건 (Pre-condition)
  * 사후 조건 (Post-condition)
  * 주 흐름 (Main Flow) — 단계별 번호
  * 대안 흐름 (Alternative Flow)
  * 예외 흐름 (Exception Flow)

## 3. Interaction Diagrams
- 주요 시나리오별로 시퀀스 다이어그램을 PlantUML 형식으로 작성.
- 반드시 ```plantuml 코드 블록으로 감쌉니다.
- @startuml / @enduml 을 사용합니다.
- participant 선언 후 메시지 표기.
- alt/opt/loop 프래그먼트로 조건부 흐름 표현.
- 시나리오당 1개 다이어그램. 여러 시나리오가 있으면 여러 다이어그램을 작성.

## 4. System Conceptual Design
- 컴포넌트/서브시스템 분해를 Markdown으로 작성.
- 각 컴포넌트의 책임과 인터페이스를 명시.
- 컴포넌트 간 의존 관계를 표 또는 목록으로 정리.
- 배치 고려사항(동기/비동기, 캐시 전략 등)이 있으면 서술."""


def build_system_model_prompt(
    srs_sections: list[dict],
    glossary: list[dict],
) -> list[dict]:
    """SRS 전체 → 시스템 모델 4섹션 프롬프트."""

    srs_text = "\n\n".join(
        f"### {s.get('title', f'Section {i+1}')}\n{s.get('content', '')}"
        for i, s in enumerate(srs_sections)
    )

    glossary_text = (
        "\n".join(f"- {g['term']}: {g['definition']}" for g in glossary)
        if glossary
        else "(없음)"
    )

    user_content = f"""\
다음 SRS 문서를 기반으로 시스템 모델을 작성하세요.

## SRS 문서
{srs_text}

## 용어 사전
{glossary_text}

위 SRS 문서를 기반으로 다음 4개 섹션을 작성하세요:

## Use Case Diagram
SRS의 기능적 요구사항을 바탕으로 Use Case Diagram을 PlantUML로 작성하세요.

## Use Case Specifications
주요 Use Case 각각에 대해 사전/사후 조건, 주 흐름, 대안/예외 흐름을 작성하세요.

## Interaction Diagrams
핵심 시나리오별로 시퀀스 다이어그램을 PlantUML로 작성하세요.

## System Conceptual Design
시스템을 컴포넌트/서브시스템으로 분해하고, 각 책임과 인터페이스를 정의하세요."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
