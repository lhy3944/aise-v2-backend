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
5. 도메인 용어가 있으면 해당 정의에 맞게 사용합니다."""

    messages = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})
    return messages
