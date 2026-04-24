"""Retrieval-first routing gate.

Supervisor LLM 앞단에서 **결정적**으로 동작하는 라우팅 게이트.
임베딩 유사도 기반으로 "이 질의는 knowledge 문서로 답할 수 있나?"를
먼저 판정한다.

동작 흐름:
1. Skip guards — 초단문 인사/감사말, 문서 0개 프로젝트면 즉시 None 반환
   (= Supervisor LLM에 그대로 넘김)
2. Query rewrite — history가 있으면 standalone query로 재작성
3. Embedding + pgvector 검색 — top-k 청크의 최대 score 확인
4. Threshold 판정 — `max_score >= τ`면 knowledge_qa로 직결하고,
   임베딩·청크 결과를 `rag_cache`에 담아 KnowledgeQAAgent가 재활용

Returns `GateResult | None`:
- None = gate가 결정하지 않음. Supervisor LLM이 판단.
- `GateResult(routing=..., rag_cache=...)` = 게이트가 결정. run_chat은
  supervisor_node를 건너뛰고 바로 agent 경로로 진입한다.

환경변수(선택):
- `RAG_GATE_ENABLED` (default "true")
- `RAG_GATE_THRESHOLD` (default 0.35) — cosine similarity 임계값
- `RAG_GATE_TOP_K` (default 5) — 검색 top-k
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.knowledge import KnowledgeDocument
from src.services import embedding_svc, rag_svc
from src.services.query_rewriter import rewrite_query


# 인사말·감사 표현: 지식 질의일 가능성 거의 0. embedding 호출 자체 skip.
_SMALL_TALK_TOKENS = frozenset(
    {
        "안녕",
        "안녕하세요",
        "하이",
        "반가워",
        "반갑습니다",
        "고마워",
        "감사",
        "감사합니다",
        "잘가",
        "수고",
        "수고했어",
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "bye",
    }
)

# 짧은 인사로 판단할 최대 문자 길이(구두점·공백 제거 기준).
_SMALL_TALK_MAX_LEN = 8


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"{name}={raw!r}를 float으로 변환 실패, 기본값 {default} 사용")
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(f"{name}={raw!r}를 int으로 변환 실패, 기본값 {default} 사용")
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _is_small_talk(text: str) -> bool:
    """아주 짧은 인사/감사 입력이면 True. 판단 실패 시 False(안전).

    임베딩은 어차피 값싸지만, 명백한 케이스는 미리 거르는 편이 결과의
    노이즈/지연을 줄인다.
    """
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch.isspace()).strip().lower()
    if not cleaned:
        return True
    if len(cleaned) <= _SMALL_TALK_MAX_LEN and cleaned in _SMALL_TALK_TOKENS:
        return True
    return False


@dataclass
class GateResult:
    """Gate가 내린 최종 결정과 KnowledgeQAAgent가 재활용할 캐시."""

    # 통과 시 routing dict (supervisor 산출물과 동일한 shape).
    routing: dict[str, Any]
    # state['rag_cache']에 저장될 값. 통과 시에만 의미가 있다.
    rag_cache: dict[str, Any]


async def _project_has_documents(project_id: uuid.UUID, db: AsyncSession) -> bool:
    """프로젝트에 RAG 검색 대상 문서가 하나라도 있는지 확인."""
    stmt = (
        select(func.count(KnowledgeDocument.id))
        .where(KnowledgeDocument.project_id == project_id)
        .where(KnowledgeDocument.is_active.is_(True))
        .where(KnowledgeDocument.status == "completed")
    )
    result = await db.execute(stmt)
    return (result.scalar() or 0) > 0


async def evaluate_gate(
    *,
    user_input: str,
    history: list[dict],
    project_id: uuid.UUID,
    db: AsyncSession,
) -> GateResult | None:
    """Retrieval-first gate 판정.

    None 반환 시 호출자(run_chat)는 기존 supervisor LLM 경로로 fallback.
    """
    if not _env_bool("RAG_GATE_ENABLED", True):
        return None

    text = (user_input or "").strip()
    if not text:
        return None

    # 1) Skip guards.
    if _is_small_talk(text):
        logger.debug(f"retrieval_gate: small-talk skip ({text!r})")
        return None

    if not await _project_has_documents(project_id, db):
        logger.debug(f"retrieval_gate: no documents in project {project_id}, skip")
        return None

    # 2) Query rewrite — history가 비면 no-op.
    rewritten = await rewrite_query(text, history or [])

    # 3) Embedding + pgvector 검색.
    top_k = _env_int("RAG_GATE_TOP_K", 5)
    try:
        embeddings = await embedding_svc.get_embeddings([rewritten])
    except Exception as exc:
        logger.warning(f"retrieval_gate: embedding failed ({exc!r}), supervisor fallback")
        return None
    if not embeddings:
        return None
    query_embedding = embeddings[0]

    chunks_with_scores = await rag_svc.search_similar_chunks(
        project_id=project_id,
        query=rewritten,
        top_k=top_k,
        db=db,
        query_embedding=query_embedding,
    )
    if not chunks_with_scores:
        logger.debug("retrieval_gate: zero chunks returned, supervisor fallback")
        return None

    max_score = max(score for _, score in chunks_with_scores)
    threshold = _env_float("RAG_GATE_THRESHOLD", 0.35)
    logger.info(
        f"retrieval_gate: max_score={max_score:.4f} threshold={threshold:.2f} "
        f"rewritten={rewritten!r}"
    )
    if max_score < threshold:
        return None

    # 4) Pass — KnowledgeQA로 직결하고 캐시엔 state-safe primitive만 담는다.
    # ORM 객체는 담지 않는다(LangGraph checkpoint 직렬화 고려). KnowledgeQA는
    # `query_embedding`만 재사용해 비싼 임베딩 API call을 건너뛰고, 값싼
    # pgvector 검색 한 번만 다시 수행한다.
    rag_cache = {
        "rewritten_query": rewritten,
        "query_embedding": query_embedding,
        "max_score": max_score,
    }
    routing = {
        "action": "single",
        "agent": "knowledge_qa",
        "plan": None,
        "clarification": None,
        "reasoning": (
            f"retrieval-first gate: max_score={max_score:.4f} >= {threshold:.2f}"
        ),
    }
    return GateResult(routing=routing, rag_cache=rag_cache)


__all__ = ["GateResult", "evaluate_gate"]
