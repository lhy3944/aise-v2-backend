"""SRS 생성 서비스"""

import uuid

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeDocument
from src.models.record import Record
from src.models.requirement import RequirementSection
from src.models.srs import SrsDocument, SrsSection
from src.prompts.srs.generate import build_srs_section_prompt
from src.schemas.api.srs import (
    SrsDocumentResponse,
    SrsListResponse,
    SrsSectionResponse,
    SrsSectionUpdate,
)
from src.services.llm_svc import chat_completion


def _to_response(doc: SrsDocument) -> SrsDocumentResponse:
    return SrsDocumentResponse(
        srs_id=str(doc.id),
        project_id=str(doc.project_id),
        version=doc.version,
        status=doc.status,
        error_message=doc.error_message,
        sections=[
            SrsSectionResponse(
                section_id=str(s.section_id) if s.section_id else None,
                title=s.title,
                content=s.content,
                order_index=s.order_index,
            )
            for s in sorted(doc.sections, key=lambda x: x.order_index)
        ],
        based_on_records=doc.based_on_records,
        based_on_documents=doc.based_on_documents,
        created_at=doc.created_at,
    )


async def generate_srs(
    db: AsyncSession, project_id: uuid.UUID,
) -> SrsDocumentResponse:
    """승인된 레코드 기반 SRS 생성"""
    logger.info(f"SRS 생성 시작: project_id={project_id}")

    # 1. 활성 섹션 조회 (순서대로)
    sections = (await db.execute(
        select(RequirementSection)
        .where(RequirementSection.project_id == project_id, RequirementSection.is_active == True)  # noqa: E712
        .order_by(RequirementSection.order_index)
    )).scalars().all()

    if not sections:
        raise AppException(400, "활성 섹션이 없습니다.")

    # 2. 승인된 레코드 조회
    records = (await db.execute(
        select(Record)
        .where(Record.project_id == project_id, Record.status == "approved")
        .order_by(Record.order_index)
    )).scalars().all()

    if not records:
        raise AppException(400, "승인된 레코드가 없습니다. 먼저 레코드를 추출하고 승인하세요.")

    # 3. 용어 사전
    glossary = (await db.execute(
        select(GlossaryItem)
        .where(GlossaryItem.project_id == project_id, GlossaryItem.is_approved == True)  # noqa: E712
    )).scalars().all()
    glossary_dicts = [{"term": g.term, "definition": g.definition} for g in glossary]

    # 4. 기반 문서 목록
    doc_ids = {str(r.source_document_id) for r in records if r.source_document_id}
    doc_names = []
    if doc_ids:
        docs = (await db.execute(
            select(KnowledgeDocument.id, KnowledgeDocument.name)
            .where(KnowledgeDocument.id.in_([uuid.UUID(d) for d in doc_ids]))
        )).all()
        doc_names = [{"id": str(d), "name": n} for d, n in docs]

    # 5. 다음 버전 번호
    max_version = (await db.execute(
        select(func.max(SrsDocument.version)).where(SrsDocument.project_id == project_id)
    )).scalar() or 0
    new_version = max_version + 1

    # 6. SrsDocument 생성
    srs_doc = SrsDocument(
        project_id=project_id,
        version=new_version,
        status="generating",
        based_on_records={"record_ids": [str(r.id) for r in records]},
        based_on_documents={"documents": doc_names},
    )
    db.add(srs_doc)
    await db.flush()

    # 7. 섹션별 LLM 생성
    record_map: dict[str, list[dict]] = {}
    for r in records:
        key = str(r.section_id) if r.section_id else "none"
        if key not in record_map:
            record_map[key] = []
        record_map[key].append({"display_id": r.display_id, "content": r.content})

    full_content_parts = []
    for i, section in enumerate(sections):
        sec_records = record_map.get(str(section.id), [])

        if not sec_records:
            # 레코드가 없는 섹션은 빈 내용
            section_content = f"*이 섹션에 해당하는 레코드가 없습니다.*"
        else:
            try:
                messages = build_srs_section_prompt(
                    section_name=section.name,
                    section_description=section.description,
                    output_format_hint=section.output_format_hint,
                    records=sec_records,
                    glossary=glossary_dicts,
                )
                section_content = await chat_completion(messages, temperature=0.2, max_completion_tokens=4096)
            except Exception as e:
                logger.error(f"SRS 섹션 생성 실패: {section.name}, error={e}")
                section_content = f"*생성 실패: {str(e)[:200]}*"

        srs_section = SrsSection(
            srs_document_id=srs_doc.id,
            section_id=section.id,
            title=section.name,
            content=section_content,
            order_index=i,
        )
        db.add(srs_section)
        full_content_parts.append(f"## {section.name}\n\n{section_content}")

    # 8. 전체 content 합침 + 상태 업데이트
    srs_doc.content = "\n\n---\n\n".join(full_content_parts)
    srs_doc.status = "completed"
    await db.commit()
    await db.refresh(srs_doc, ["sections"])

    logger.info(f"SRS 생성 완료: srs_id={srs_doc.id}, version={new_version}")
    return _to_response(srs_doc)


async def list_srs(
    db: AsyncSession, project_id: uuid.UUID,
) -> SrsListResponse:
    result = await db.execute(
        select(SrsDocument)
        .options(selectinload(SrsDocument.sections))
        .where(SrsDocument.project_id == project_id)
        .order_by(SrsDocument.version.desc())
    )
    docs = result.scalars().all()
    return SrsListResponse(documents=[_to_response(d) for d in docs])


async def get_srs(
    db: AsyncSession, project_id: uuid.UUID, srs_id: uuid.UUID,
) -> SrsDocumentResponse:
    result = await db.execute(
        select(SrsDocument)
        .options(selectinload(SrsDocument.sections))
        .where(SrsDocument.id == srs_id, SrsDocument.project_id == project_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise AppException(404, "SRS 문서를 찾을 수 없습니다.")
    return _to_response(doc)


async def update_srs_section(
    db: AsyncSession, project_id: uuid.UUID, srs_id: uuid.UUID,
    section_id: uuid.UUID, data: SrsSectionUpdate,
) -> SrsDocumentResponse:
    """SRS 섹션 인라인 편집"""
    # SRS 문서 확인
    result = await db.execute(
        select(SrsDocument)
        .options(selectinload(SrsDocument.sections))
        .where(SrsDocument.id == srs_id, SrsDocument.project_id == project_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise AppException(404, "SRS 문서를 찾을 수 없습니다.")

    # 섹션 찾기
    target = None
    for s in doc.sections:
        if s.section_id == section_id:
            target = s
            break

    if not target:
        raise AppException(404, "해당 섹션을 찾을 수 없습니다.")

    target.content = data.content

    # 전체 content도 업데이트
    doc.content = "\n\n---\n\n".join(
        f"## {s.title}\n\n{s.content}"
        for s in sorted(doc.sections, key=lambda x: x.order_index)
    )

    await db.commit()
    await db.refresh(doc, ["sections"])
    return _to_response(doc)
