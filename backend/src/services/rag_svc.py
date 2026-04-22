"""RAG 서비스 -- Knowledge Repository 기반 검색 + 채팅"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.schemas.api.knowledge import KnowledgeChatResponse, KnowledgeChatSource
from src.services import embedding_svc
from src.services.llm_svc import chat_completion
from src.prompts.knowledge import build_knowledge_chat_prompt


async def search_similar_chunks(
    project_id: uuid.UUID,
    query: str,
    top_k: int,
    db: AsyncSession,
) -> list[tuple[KnowledgeChunk, float]]:
    """쿼리와 유사한 청크를 검색한다.

    프로젝트 격리(P0): `project_id`는 필수 필터이며, 임베딩이 완료된
    `is_active=True` + `status='completed'` 문서의 청크만 반환한다.
    필터 누락은 보안 사고로 간주(REFECTORING.md P0).

    Returns:
        (KnowledgeChunk, score) 튜플 리스트. score는 1 - cosine_distance.
    """
    if project_id is None:
        raise AppException(400, "project_id는 필수입니다.")

    logger.debug(f"유사 청크 검색: project_id={project_id}, top_k={top_k}")

    # 쿼리 임베딩 생성
    embeddings = await embedding_svc.get_embeddings([query])
    if not embeddings:
        return []
    query_embedding = embeddings[0]

    # pgvector cosine distance 검색.
    # KnowledgeDocument와 join하여 활성/완료된 문서의 청크만 검색.
    stmt = (
        select(
            KnowledgeChunk,
            KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeChunk.project_id == project_id)
        .where(KnowledgeDocument.project_id == project_id)  # 방어적 이중 필터
        .where(KnowledgeDocument.is_active.is_(True))
        .where(KnowledgeDocument.status == "completed")
        .where(KnowledgeChunk.embedding.isnot(None))
        .order_by("distance")
        .limit(top_k)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # score = 1 - distance (cosine similarity)
    chunks_with_scores = [(row[0], 1.0 - (row[1] or 0.0)) for row in rows]
    logger.debug(f"검색 결과: {len(chunks_with_scores)}개 청크")
    return chunks_with_scores


async def search_and_prepare(
    project_id: uuid.UUID,
    message: str,
    history: list[dict],
    top_k: int,
    db: AsyncSession,
) -> tuple[list[dict], list[KnowledgeChatSource]]:
    """Retrieval + glossary + prompt build + sources 반환 (LLM 호출 없음).

    스트리밍 호출자(`KnowledgeQAAgent.run_stream`)가 이 함수로 준비 단계만
    수행한 뒤 `llm_svc.chat_completion_stream`으로 토큰을 직접 받아 emit
    하기 위해 분리. `chat()`은 이 함수 + `chat_completion()`의 합성.
    """
    chunks_with_scores = await search_similar_chunks(project_id, message, top_k, db)

    # 문서 메타 조회
    doc_ids = {chunk.document_id for chunk, _ in chunks_with_scores}
    doc_name_map: dict[uuid.UUID, str] = {}
    doc_type_map: dict[uuid.UUID, str] = {}
    if doc_ids:
        doc_result = await db.execute(
            select(KnowledgeDocument.id, KnowledgeDocument.name, KnowledgeDocument.file_type)
            .where(KnowledgeDocument.id.in_(doc_ids))
        )
        for doc_id, doc_name, file_type in doc_result.all():
            doc_name_map[doc_id] = doc_name
            doc_type_map[doc_id] = file_type

    context_chunks = [
        {
            "document_name": doc_name_map.get(chunk.document_id, "Unknown"),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
        }
        for chunk, _ in chunks_with_scores
    ]

    # Glossary (도메인 컨텍스트)
    glossary_result = await db.execute(
        select(GlossaryItem)
        .where(GlossaryItem.project_id == project_id)
        .order_by(GlossaryItem.term)
    )
    glossary = [
        {"term": item.term, "definition": item.definition}
        for item in glossary_result.scalars().all()
    ]

    messages = build_knowledge_chat_prompt(
        query=message,
        context_chunks=context_chunks,
        glossary=glossary,
        history=history,
    )

    sources = [
        KnowledgeChatSource(
            document_id=str(chunk.document_id),
            document_name=doc_name_map.get(chunk.document_id, "Unknown"),
            chunk_index=chunk.chunk_index,
            content=chunk.content[:200],  # 미리보기용 200자
            score=round(score, 4),
            file_type=doc_type_map.get(chunk.document_id),
        )
        for chunk, score in chunks_with_scores
    ]
    return messages, sources


async def chat(
    project_id: uuid.UUID,
    message: str,
    history: list[dict],
    top_k: int,
    db: AsyncSession,
) -> KnowledgeChatResponse:
    """Knowledge Repository 기반 RAG 채팅 (non-streaming, HTTP API용)."""
    logger.info(f"Knowledge 채팅: project_id={project_id}, message={message[:50]}...")

    messages, sources = await search_and_prepare(project_id, message, history, top_k, db)

    try:
        answer = await chat_completion(
            messages,
            client_type="srs",
            temperature=0.3,
            max_completion_tokens=2048,
        )
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Knowledge 채팅 LLM 호출 실패: {e}")
        raise AppException(500, "AI 응답 생성에 실패했습니다.")

    logger.info(f"Knowledge 채팅 완료: sources={len(sources)}개")
    return KnowledgeChatResponse(answer=answer, sources=sources)
