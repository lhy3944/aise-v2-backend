"""Knowledge Repository RAG 채팅 프롬프트"""


def build_knowledge_chat_prompt(
    query: str,
    context_chunks: list[dict],  # [{"document_name": str, "chunk_index": int, "content": str}]
    glossary: list[dict],  # [{"term": str, "definition": str}]
    history: list[dict],  # [{"role": str, "content": str}]
) -> list[dict]:
    """RAG 채팅 프롬프트 빌드"""

    # Build context section
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        context_parts.append(f"[{i}] ({chunk['document_name']}) {chunk['content']}")
    context_text = "\n\n".join(context_parts) if context_parts else "관련 문서가 없습니다."

    # Build glossary section
    glossary_text = ""
    if glossary:
        glossary_lines = [f"- {g['term']}: {g['definition']}" for g in glossary]
        glossary_text = f"\n\n## 도메인 용어\n" + "\n".join(glossary_lines)

    system_message = f"""당신은 프로젝트의 Knowledge Repository를 기반으로 질문에 답변하는 AI 어시스턴트입니다.

## 참고 문서
{context_text}
{glossary_text}

## 규칙
1. 참고 문서의 내용을 기반으로 답변합니다.
2. 답변 시 관련 출처를 [번호] 형태로 인용합니다.
3. 참고 문서에 없는 내용은 "제공된 문서에서 관련 내용을 찾을 수 없습니다"라고 안내합니다.
4. 사용자의 질문 언어와 동일한 언어로 답변합니다.
5. 도메인 용어가 있으면 해당 정의에 맞게 사용합니다.

## 포맷 규칙
6. 아래 조건 중 하나라도 해당하면 **GitHub-Flavored Markdown 테이블**로 정리합니다.
   - 3개 이상의 항목이 **공통된 속성**을 가질 때 (예: 기업별 전략, 제품별 스펙, 단계별 산출물)
   - **비교·대조·매핑·카테고리 분류**가 핵심인 질문
   - 문서에 이미 표·리스트 형태로 정리된 데이터를 요약할 때
7. 다음 경우엔 테이블을 만들지 않습니다.
   - 항목이 2개 이하이거나 서술형 설명이 자연스러운 경우
   - 각 항목이 공통 속성을 공유하지 않아 빈 셀이 많아지는 경우
   - 단일 개념의 정의·원인·결론 같은 서사형 답변
8. 테이블 작성 규칙:
   - 열은 **2~5개**로 제한하고, 각 셀은 **한 줄로 요약**합니다 (긴 설명은 표 아래 문단에 둡니다).
   - 표 **바로 앞에 한 줄 요약 문장**을 두어 맥락을 제공합니다.
   - 표 셀 안에서도 출처 **[번호] 인용을 유지**합니다.
   - 항목이 8개를 초과하면 중요도 상위 항목만 표에 두고 나머지는 "그 외:"로 줄글 처리합니다."""

    messages = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})
    return messages
