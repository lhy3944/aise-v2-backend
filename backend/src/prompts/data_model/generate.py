"""데이터 모델 생성 프롬프트 — SRS + 시스템 모델 기반 Conceptual/Logical/Physical Data Model

SRS와 시스템 모델을 입력으로 받아 3개 섹션을 생성한다:
1. Conceptual Data Model (PlantUML ERD)
2. Logical Data Model
3. Physical Data Model
"""

SYSTEM_PROMPT = """당신은 데이터 모델링 전문가입니다.
입력으로 주어진 SRS 문서와 시스템 모델을 기반으로 데이터 모델을 작성합니다.

원칙:
- SRS의 요구사항과 시스템 모델의 엔티티만 기반으로 작성합니다. 임의 가정하지 마세요.
- SRS 본문에 등장한 레코드 ID([FR-001] 등)를 본문에서 참조로 표시합니다.
- 입력 언어와 동일한 언어로 작성합니다.

각 섹션 작성 규칙:

## 1. Conceptual Data Model
- PlantUML 형식으로 ERD를 작성합니다.
- 반드시 ```plantuml 코드 블록으로 감쌉니다.
- @startuml / @enduml 을 사용합니다.
- entity 키워드로 엔티티를 정의합니다.
- 식별자(기본키) 속성은 **굵게** 표시합니다.
- 관계는 IDEF1X 표기법으로 작성 (예: ||--o{, ||--||, }o--o{).
- 관계 라벨에 동사구를 명시 (예: "주문한다", "포함한다").
- 다대다 관계는 연결 엔티티로 분해합니다.

## 2. Logical Data Model
- Conceptual 모델을 논리 수준으로 상세화합니다.
- 각 엔티티(테이블)의 전체 속성을 Markdown 표로 작성:
  * 컬럼명, 데이터 타입, NULL 허용, 기본값, 설명
- 정규화 수준(1NF/2NF/3NF)을 명시하고 정규화 근거를 서술.
- 외래키 관계를 명시적으로 표시.
- 도메인 제약조건(CHECK, UNIQUE 등)이 있으면 명시.

## 3. Physical Data Model
- Logical 모델을 물리 수준으로 구체화합니다.
- 각 테이블에 대해 다음을 작성:
  * 테이블명 (실제 DB 테이블명 컨벤션 적용)
  * 인덱스 전략 (인덱스명, 컬럼, 유형: B-tree/Hash/Composite)
  * 파티셔닝 전략 (필요 시)
  * 스토리지 예상 크기 및 성능 고려사항
- 데이터베이스 종류(PostgreSQL/MySQL 등)별 특화 사항이 있으면 명시.
- 대용량 테이블에 대한 샤딩/파티셔닝 권고사항."""


def build_data_model_prompt(
    srs_sections: list[dict],
    system_model_sections: list[dict] | None,
    glossary: list[dict],
) -> list[dict]:
    """SRS + 시스템 모델 → 데이터 모델 3섹션 프롬프트."""

    srs_text = "\n\n".join(
        f"### {s.get('title', f'Section {i+1}')}\n{s.get('content', '')}"
        for i, s in enumerate(srs_sections)
    )

    sm_text = ""
    if system_model_sections:
        sm_text = "\n\n".join(
            f"### {s.get('title', f'Section {i+1}')}\n{s.get('content', '')}"
            for i, s in enumerate(system_model_sections)
        )

    glossary_text = (
        "\n".join(f"- {g['term']}: {g['definition']}" for g in glossary)
        if glossary
        else "(없음)"
    )

    system_model_block = ""
    if sm_text:
        system_model_block = f"""
## 시스템 모델 (참고)
{sm_text}
"""

    user_content = f"""\
다음 SRS 문서와 시스템 모델을 기반으로 데이터 모델을 작성하세요.

## SRS 문서
{srs_text}
{system_model_block}
## 용어 사전
{glossary_text}

위 문서를 기반으로 다음 3개 섹션을 작성하세요:

## Conceptual Data Model
엔티티, 관계, 식별자를 PlantUML ERD로 작성하세요.

## Logical Data Model
각 엔티티의 전체 속성, 데이터 타입, 제약조건을 Markdown 표로 작성하세요.

## Physical Data Model
인덱스 전략, 파티셔닝, 스토리지 결정을 작성하세요."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
