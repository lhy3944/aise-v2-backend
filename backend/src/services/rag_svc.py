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

    Returns:
        (KnowledgeChunk, score) 튜플 리스트. score는 1 - cosine_distance.
    """
    logger.debug(f"유사 청크 검색: project_id={project_id}, top_k={top_k}")

    # 쿼리 임베딩 생성
    embeddings = await embedding_svc.get_embeddings([query])
    if not embeddings:
        return []
    query_embedding = embeddings[0]

    # pgvector cosine distance 검색
    stmt = (
        select(
            KnowledgeChunk,
            KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(KnowledgeChunk.project_id == project_id)
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


async def chat(
    project_id: uuid.UUID,
    message: str,
    history: list[dict],
    top_k: int,
    db: AsyncSession,
) -> KnowledgeChatResponse:
    """Knowledge Repository 기반 RAG 채팅"""
    logger.info(f"Knowledge 채팅: project_id={project_id}, message={message[:50]}...")

    # 1. 유사 청크 검색
    chunks_with_scores = await search_similar_chunks(project_id, message, top_k, db)

    # 2. 문서 이름 조회 (청크에서 document_id로 조회)
    doc_ids = {chunk.document_id for chunk, _ in chunks_with_scores}
    doc_name_map: dict[uuid.UUID, str] = {}
    if doc_ids:
        doc_result = await db.execute(
            select(KnowledgeDocument.id, KnowledgeDocument.name)
            .where(KnowledgeDocument.id.in_(doc_ids))
        )
        for doc_id, doc_name in doc_result.all():
            doc_name_map[doc_id] = doc_name

    # 3. 컨텍스트 청크 구성
    context_chunks = []
    for chunk, score in chunks_with_scores:
        context_chunks.append({
            "document_name": doc_name_map.get(chunk.document_id, "Unknown"),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
        })

    # 4. Glossary 조회 (도메인 컨텍스트)
    glossary_result = await db.execute(
        select(GlossaryItem)
        .where(GlossaryItem.project_id == project_id)
        .order_by(GlossaryItem.term)
    )
    glossary_items = glossary_result.scalars().all()
    glossary = [
        {"term": item.term, "definition": item.definition}
        for item in glossary_items
    ]

    # 5. RAG 프롬프트 빌드
    messages = build_knowledge_chat_prompt(
        query=message,
        context_chunks=context_chunks,
        glossary=glossary,
        history=history,
    )

    # 6. LLM 호출
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

    # 7. 소스 정보 구성
    sources = []
    for chunk, score in chunks_with_scores:
        sources.append(
            KnowledgeChatSource(
                document_id=str(chunk.document_id),
                document_name=doc_name_map.get(chunk.document_id, "Unknown"),
                chunk_index=chunk.chunk_index,
                content=chunk.content[:200],  # 미리보기용 200자
                score=round(score, 4),
            )
        )

    logger.info(f"Knowledge 채팅 완료: sources={len(sources)}개")
    return KnowledgeChatResponse(answer=answer, sources=sources)
