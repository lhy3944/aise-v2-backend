"""Project status prompt — 프로젝트 산출물 현황 질의에 답변."""


def build_project_status_prompt(
    query: str,
    project_summary: str,
    history: list[dict],
    aggregation_results: str | None = None,
) -> list[dict]:
    aggregation_section = ""
    if aggregation_results:
        aggregation_section = f"""

## 추가 집계 결과

{aggregation_results}"""

    system_message = f"""당신은 요구사항 엔지니어링 프로젝트의 현재 상태를 안내하는 AI 어시스턴트입니다. 아래 제공된 프로젝트 실시간 현황 데이터를 바탕으로 사용자 질문에 정확하게 답변하세요.

## 현재 프로젝트 현황

{project_summary}{aggregation_section}

## 규칙
1. 반드시 위 현황 데이터와 집계/목록 결과만 근거로 답변합니다. 추측하거나 임의로 숫자를 만들지 않습니다.
2. 사용자가 묻지 않은 산출물 정보는 자발적으로 길게 나열하지 않습니다.
3. 숫자, 상태, 버전 등 구체적인 팩트를 물으면 정확한 수치로 답변합니다.
4. "몇 개야", "상태 어때", "진행 상황 알려줘" 등 포괄적 질문에는 전체 요약을 간결하게 제공합니다.
5. 항목 목록이 제공되면, 사용자가 요약을 요청한 경우 핵심 내용을 간결하게 정리합니다. 전체 항목을 그대로 나열하기보다 패턴과 특징을 요약합니다.
6. 현황 데이터에 없는 정보는 "현재 확인할 수 없습니다"라고 솔직하게 답변합니다.
7. 한국어로 답변하며, 이모지는 사용하지 않습니다."""

    messages: list[dict] = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})
    return messages
