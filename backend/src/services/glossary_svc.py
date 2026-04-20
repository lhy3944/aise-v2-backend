"""Glossary 비즈니스 로직 서비스"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.models.requirement import Requirement
from src.schemas.api.glossary import (
    GlossaryApproveRequest,
    GlossaryCreate,
    GlossaryExtractedItem,
    GlossaryExtractResponse,
    GlossaryGenerateResponse,
    GlossaryListResponse,
    GlossaryResponse,
    GlossaryUpdate,
)
from src.prompts.glossary import build_glossary_generate_prompt, build_glossary_extract_prompt
from src.services.llm_svc import chat_completion
from src.utils.db import get_or_404
from src.utils.json_parser import parse_llm_json


def _to_response(item: GlossaryItem) -> GlossaryResponse:
    """DB 모델 -> 응답 스키마 변환"""
    source_doc_name = None
    if hasattr(item, "source_document") and item.source_document:
        source_doc_name = item.source_document.name

    return GlossaryResponse(
        glossary_id=str(item.id),
        term=item.term,
        definition=item.definition,
        product_group=item.product_group,
        synonyms=item.synonyms or [],
        abbreviations=item.abbreviations or [],
        section_tags=item.section_tags or [],
        source_document_id=str(item.source_document_id) if item.source_document_id else None,
        source_document_name=source_doc_name,
        is_auto_extracted=item.is_auto_extracted,
        is_approved=item.is_approved,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _load_documents_by_ids(
    db: AsyncSession,
    project_id: uuid.UUID,
    document_ids: set[uuid.UUID],
) -> dict[uuid.UUID, KnowledgeDocument]:
    if not document_ids:
        return {}

    stmt = select(KnowledgeDocument).where(
        KnowledgeDocument.project_id == project_id,
        KnowledgeDocument.id.in_(document_ids),
    )
    result = await db.execute(stmt)
    documents = {doc.id: doc for doc in result.scalars().all()}
    missing_ids = document_ids - set(documents.keys())
    if missing_ids:
        raise AppException(400, "유효하지 않은 지식 문서 ID가 포함되어 있습니다.")

    return documents


async def list_glossary(db: AsyncSession, project_id: uuid.UUID) -> GlossaryListResponse:
    """프로젝트의 용어 목록 조회"""
    result = await db.execute(
        select(GlossaryItem)
        .options(selectinload(GlossaryItem.source_document))
        .where(GlossaryItem.project_id == project_id)
        .order_by(GlossaryItem.term)
    )
    items = result.scalars().all()

    return GlossaryListResponse(glossary=[_to_response(item) for item in items])


async def create_glossary(
    db: AsyncSession, project_id: uuid.UUID, data: GlossaryCreate
) -> GlossaryResponse:
    """용어 추가"""
    await get_or_404(
        db, Project, Project.id == project_id,
        error_msg="프로젝트를 찾을 수 없습니다.",
    )

    if data.source_document_id:
        await _load_documents_by_ids(db, project_id, {data.source_document_id})

    item = GlossaryItem(
        project_id=project_id,
        term=data.term,
        definition=data.definition,
        product_group=data.product_group,
        synonyms=data.synonyms or [],
        abbreviations=data.abbreviations or [],
        section_tags=data.section_tags or [],
        source_document_id=data.source_document_id,
        is_approved=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return _to_response(item)


async def update_glossary(
    db: AsyncSession,
    project_id: uuid.UUID,
    glossary_id: uuid.UUID,
    data: GlossaryUpdate,
) -> GlossaryResponse:
    """용어 수정"""
    item = await get_or_404(
        db, GlossaryItem,
        GlossaryItem.id == glossary_id,
        GlossaryItem.project_id == project_id,
        error_msg="용어를 찾을 수 없습니다.",
    )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)

    return _to_response(item)


async def delete_glossary(
    db: AsyncSession, project_id: uuid.UUID, glossary_id: uuid.UUID
) -> None:
    """용어 삭제"""
    item = await get_or_404(
        db, GlossaryItem,
        GlossaryItem.id == glossary_id,
        GlossaryItem.project_id == project_id,
        error_msg="용어를 찾을 수 없습니다.",
    )
    await db.delete(item)
    await db.commit()


async def generate_glossary(
    db: AsyncSession, project_id: uuid.UUID
) -> GlossaryGenerateResponse:
    """프로젝트 요구사항 기반 Glossary 초안 자동 생성 (LLM) — 레거시"""
    result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id)
    )
    requirements = result.scalars().all()

    if not requirements:
        raise AppException(400, "용어를 생성할 요구사항이 없습니다.")

    req_texts = []
    for req in requirements:
        text = req.refined_text or req.original_text
        req_texts.append(f"[{req.type.upper()}] {text}")

    requirements_block = "\n".join(req_texts)
    messages = build_glossary_generate_prompt(requirements_block)
    raw = await chat_completion(messages, temperature=0.3, max_completion_tokens=4096)

    parsed = parse_llm_json(raw, error_msg="LLM 응답을 파싱할 수 없습니다.")
    items = parsed.get("glossary", [])

    generated = [
        GlossaryCreate(
            term=item["term"],
            definition=item["definition"],
            product_group=item.get("product_group"),
        )
        for item in items
    ]

    return GlossaryGenerateResponse(generated_glossary=generated)


async def extract_glossary(
    db: AsyncSession, project_id: uuid.UUID
) -> GlossaryExtractResponse:
    """지식 문서 기반 용어 후보 추출 (LLM)"""
    logger.info(f"Glossary 추출 시작: project_id={project_id}")

    # 1. 활성 + 완료된 지식 문서의 청크 수집
    result = await db.execute(
        select(KnowledgeChunk.content, KnowledgeDocument.id, KnowledgeDocument.name)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.is_active == True,  # noqa: E712
            KnowledgeDocument.status == "completed",
        )
        .order_by(KnowledgeDocument.id, KnowledgeChunk.chunk_index)
    )
    rows = result.all()

    if not rows:
        raise AppException(400, "추출할 활성 지식 문서가 없습니다.")

    # 문서별로 텍스트 그룹핑
    doc_texts: dict[str, dict] = {}
    for content, doc_id, doc_name in rows:
        doc_id_str = str(doc_id)
        if doc_id_str not in doc_texts:
            doc_texts[doc_id_str] = {"name": doc_name, "chunks": []}
        doc_texts[doc_id_str]["chunks"].append(content)

    # 2. 기존 용어 목록 (중복 방지)
    existing_result = await db.execute(
        select(GlossaryItem.term).where(GlossaryItem.project_id == project_id)
    )
    existing_terms = [row[0] for row in existing_result.all()]

    # 3. 문서별로 LLM 추출
    all_candidates: list[GlossaryExtractedItem] = []

    for doc_id_str, doc_info in doc_texts.items():
        document_text = "\n".join(doc_info["chunks"][:20])  # 최대 20개 청크
        messages = build_glossary_extract_prompt(document_text, existing_terms)

        try:
            raw = await chat_completion(messages, temperature=0.3, max_completion_tokens=4096)
            parsed = parse_llm_json(raw, error_msg="LLM 응답 파싱 실패")
            items = parsed.get("glossary", [])

            for item in items:
                all_candidates.append(GlossaryExtractedItem(
                    term=item.get("term", ""),
                    definition=item.get("definition", ""),
                    synonyms=item.get("synonyms", []),
                    abbreviations=item.get("abbreviations", []),
                    source_document_id=doc_id_str,
                    source_document_name=doc_info["name"],
                ))
                # 추출된 용어도 중복 체크 목록에 추가
                existing_terms.append(item.get("term", ""))

        except Exception as e:
            logger.warning(f"문서 {doc_id_str} 용어 추출 실패: {e}")

    logger.info(f"Glossary 추출 완료: {len(all_candidates)}개 후보")
    return GlossaryExtractResponse(candidates=all_candidates)


async def approve_glossary(
    db: AsyncSession, project_id: uuid.UUID, data: GlossaryApproveRequest
) -> GlossaryListResponse:
    """추출된 용어 후보 일괄 승인 저장"""
    logger.info(f"Glossary 승인: project_id={project_id}, count={len(data.items)}")

    source_document_ids = {
        item.source_document_id for item in data.items if item.source_document_id is not None
    }
    await _load_documents_by_ids(db, project_id, source_document_ids)

    created_items = []
    for item_data in data.items:
        item = GlossaryItem(
            project_id=project_id,
            term=item_data.term,
            definition=item_data.definition,
            product_group=item_data.product_group,
            synonyms=item_data.synonyms or [],
            abbreviations=item_data.abbreviations or [],
            section_tags=item_data.section_tags or [],
            source_document_id=item_data.source_document_id,
            is_auto_extracted=True,
            is_approved=True,
        )
        db.add(item)
        created_items.append(item)

    await db.commit()
    for item in created_items:
        await db.refresh(item)

    return GlossaryListResponse(glossary=[_to_response(item) for item in created_items])
