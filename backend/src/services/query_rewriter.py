"""Conversational → standalone query rewriter.

후속 턴에서 "이 문서에도 없어?" / "프로젝트 문서 기반으로 대답해" 같은
지시문·대명사를 history 맥락과 합쳐 **독립적으로 검색 가능한 질의**로
변환한다. RAG 검색 직전에 호출되어 retrieval query로 사용된다.

동작 조건:
- history가 비어 있으면 원문 그대로 반환 (LLM 호출 없음)
- history가 있을 때만 짧은 LLM 호출 1회로 재작성
- 실패/타임아웃 시 원문 폴백 (검색 자체는 계속 진행되도록)

호출자(retrieval_gate, rag_svc)는 rewrite 결과를 state['rag_cache']에
저장해 KnowledgeQAAgent가 같은 임베딩을 재활용할 수 있게 한다.
"""

from __future__ import annotations

from loguru import logger

from src.services import llm_svc


_MAX_HISTORY_TURNS = 6  # 최근 N개 user/assistant 턴만 참고. 길어져도 비용 제한.
_REWRITER_MAX_TOKENS = 128


_SYSTEM = """You rewrite the user's latest message into a standalone search query.

Rules:
1. Output ONE line: the rewritten query, in the same language as the user.
2. Fold in any pronouns, demonstratives ("이 문서", "그거", "방금", "해당"),
   or follow-up instructions ("프로젝트 문서 기반으로 대답해") using the
   conversation history so the query makes sense on its own.
3. Keep it concise (under 30 words). Do NOT add explanations, quotes, or
   prefixes like "Query:".
4. If the latest message is already a standalone question, output it
   unchanged."""


def _format_history(history: list[dict]) -> str:
    """최근 history를 LLM 프롬프트용 텍스트로 포맷팅."""
    recent = history[-_MAX_HISTORY_TURNS * 2 :] if history else []
    lines: list[str] = []
    for turn in recent:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        speaker = "User" if role == "user" else "Assistant"
        # 너무 긴 assistant 응답은 축약 — retrieval 의도만 필요.
        if len(content) > 400:
            content = content[:400] + "..."
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


async def rewrite_query(user_input: str, history: list[dict]) -> str:
    """대화 맥락과 합쳐 standalone retrieval query를 반환한다.

    history가 없거나 LLM 호출이 실패하면 `user_input`을 그대로 돌려주어
    호출자가 동일 인터페이스로 계속 검색을 진행할 수 있다.
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return user_input

    history_text = _format_history(history or [])
    if not history_text:
        return user_input

    prompt = (
        f"## Conversation so far\n{history_text}\n\n"
        f"## Latest user message\n{user_input}\n\n"
        "## Standalone query"
    )

    try:
        rewritten = await llm_svc.chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            client_type="srs",
            temperature=0.0,
            max_completion_tokens=_REWRITER_MAX_TOKENS,
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(f"query rewrite failed, falling back to raw input: {exc!r}")
        return user_input

    cleaned = (rewritten or "").strip().splitlines()[0].strip().strip('"').strip("'")
    if not cleaned:
        return user_input
    if len(cleaned) > 500:  # 비정상 응답 방어
        return user_input
    logger.debug(f"query rewritten: {user_input!r} -> {cleaned!r}")
    return cleaned


__all__ = ["rewrite_query"]
