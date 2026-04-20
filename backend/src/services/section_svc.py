"""RequirementSection 비즈니스 로직 서비스"""

import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.models.requirement import RequirementSection
from src.schemas.api.requirement import (
    SectionCreate,
    SectionUpdate,
    SectionReorderRequest,
    SectionResponse,
)
from src.services.llm_svc import chat_completion
from src.utils.db import get_or_404
from src.utils.json_parser import parse_llm_json
from src.utils.reorder import build_reordered_ids


def _to_response(section: RequirementSection) -> SectionResponse:
    return SectionResponse(
        section_id=str(section.id),
        name=section.name,
        type=section.type,
        description=section.description,
        output_format_hint=section.output_format_hint,
        is_default=section.is_default,
        is_active=section.is_active,
        order_index=section.order_index,
        created_at=section.created_at.isoformat(),
        updated_at=section.updated_at.isoformat(),
    )


async def _next_order_index(db: AsyncSession, project_id: uuid.UUID) -> int:
    stmt = select(func.max(RequirementSection.order_index)).where(
        RequirementSection.project_id == project_id,
    )
    result = await db.execute(stmt)
    max_idx = result.scalar()
    return (max_idx + 1) if max_idx is not None else 0


async def _ensure_default_sections(db: AsyncSession, project_id: uuid.UUID) -> None:
    """기본 섹션이 없으면 자동 생성 (기존 프로젝트 호환)"""
    from src.models.requirement import DEFAULT_SECTIONS

    result = await db.execute(
        select(RequirementSection.type).where(
            RequirementSection.project_id == project_id,
            RequirementSection.is_default == True,  # noqa: E712
        )
    )
    existing_default_types = {row[0] for row in result.all()}
    missing_defaults = [
        section_def
        for section_def in DEFAULT_SECTIONS
        if section_def["type"] not in existing_default_types
    ]

    if not missing_defaults:
        return

    for sec_def in missing_defaults:
        section = RequirementSection(project_id=project_id, **sec_def)
        db.add(section)
    await db.commit()
    logger.info(
        f"기본 섹션 자동 보강: project_id={project_id}, added={len(missing_defaults)}"
    )


async def get_sections(
    db: AsyncSession,
    project_id: uuid.UUID,
    type_filter: str | None = None,
) -> list[SectionResponse]:
    await _ensure_default_sections(db, project_id)

    stmt = select(RequirementSection).where(RequirementSection.project_id == project_id)
    if type_filter is not None:
        stmt = stmt.where(RequirementSection.type == type_filter)
    stmt = stmt.order_by(RequirementSection.order_index.asc())

    result = await db.execute(stmt)
    sections = result.scalars().all()

    return [_to_response(s) for s in sections]


async def create_section(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: SectionCreate,
) -> SectionResponse:
    await get_or_404(
        db, Project, Project.id == project_id,
        error_msg="프로젝트를 찾을 수 없습니다.",
    )

    order_index = await _next_order_index(db, project_id)

    section = RequirementSection(
        project_id=project_id,
        type=data.type,
        name=data.name,
        description=data.description,
        output_format_hint=data.output_format_hint,
        order_index=order_index,
    )
    db.add(section)
    await db.commit()
    await db.refresh(section)

    logger.info(f"섹션 생성: id={section.id}, name={data.name}, project_id={project_id}")
    return _to_response(section)


async def update_section(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    data: SectionUpdate,
) -> SectionResponse:
    section = await get_or_404(
        db, RequirementSection,
        RequirementSection.id == section_id,
        RequirementSection.project_id == project_id,
        error_msg="섹션을 찾을 수 없습니다.",
    )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(section, key, value)

    section.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(section)

    logger.info(f"섹션 수정: id={section_id}")
    return _to_response(section)


async def toggle_section(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    is_active: bool,
) -> SectionResponse:
    """섹션 활성화/비활성화 토글"""
    section = await get_or_404(
        db, RequirementSection,
        RequirementSection.id == section_id,
        RequirementSection.project_id == project_id,
        error_msg="섹션을 찾을 수 없습니다.",
    )

    section.is_active = is_active
    section.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(section)

    logger.info(f"섹션 토글: id={section_id}, is_active={is_active}")
    return _to_response(section)


async def delete_section(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> None:
    """섹션 삭제 — 기본 섹션(is_default=True)은 삭제 불가"""
    section = await get_or_404(
        db, RequirementSection,
        RequirementSection.id == section_id,
        RequirementSection.project_id == project_id,
        error_msg="섹션을 찾을 수 없습니다.",
    )

    if section.is_default:
        raise AppException(400, "기본 제공 섹션은 삭제할 수 없습니다. 비활성화만 가능합니다.")

    await db.delete(section)
    await db.commit()

    logger.info(f"섹션 삭제: id={section_id}, project_id={project_id}")


async def reorder_sections(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: SectionReorderRequest,
) -> int:
    if not data.ordered_ids:
        return 0

    stmt = (
        select(RequirementSection)
        .where(RequirementSection.project_id == project_id)
        .order_by(RequirementSection.order_index.asc())
    )
    result = await db.execute(stmt)
    section_rows = result.scalars().all()
    sections = {section.id: section for section in section_rows}
    current_ids = [section.id for section in section_rows]
    reordered_ids = build_reordered_ids(data.ordered_ids, current_ids)

    now = datetime.now(timezone.utc)
    updated = 0
    for idx, sid in enumerate(reordered_ids):
        section = sections.get(sid)
        if section and section.order_index != idx:
            section.order_index = idx
            section.updated_at = now
            updated += 1

    await db.commit()

    logger.info(f"섹션 순서 변경: project_id={project_id}, updated={updated}")
    return updated


async def extract_sections(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[SectionResponse]:
    """지식 문서 기반 섹션 후보 AI 추출 (DB 저장 없이 후보 반환)"""
    logger.info(f"섹션 추출 시작: project_id={project_id}")

    # 활성 지식 문서 청크 수집
    result = await db.execute(
        select(KnowledgeChunk.content)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.is_active == True,  # noqa: E712
            KnowledgeDocument.status == "completed",
        )
        .order_by(KnowledgeChunk.chunk_index)
        .limit(30)
    )
    chunks = [row[0] for row in result.all()]

    if not chunks:
        raise AppException(400, "추출할 활성 지식 문서가 없습니다.")

    # 기존 섹션 이름 목록
    existing_result = await db.execute(
        select(RequirementSection.name).where(RequirementSection.project_id == project_id)
    )
    existing_names = [row[0] for row in existing_result.all()]

    document_text = "\n".join(chunks[:30])
    existing_str = ", ".join(existing_names) if existing_names else "(없음)"

    messages = [
        {"role": "system", "content": "JSON 형식으로만 응답하세요."},
        {"role": "user", "content": f"""\
아래 지식 문서 내용을 분석하여 SRS 문서에 포함되어야 할 추가 섹션을 제안하세요.

규칙:
- 기존 섹션과 중복되지 않는 섹션만 제안
- 각 섹션에 이름, 설명, 출력 형식 힌트를 포함
- 입력 언어와 동일한 언어로 응답
- 반드시 아래 JSON 형식으로만 응답

출력 형식:
{{"sections": [{{"name": "섹션명", "type": "소문자_영문_키", "description": "설명", "output_format_hint": "출력 형식 힌트"}}]}}

기존 섹션: {existing_str}

지식 문서 내용:
{document_text}"""},
    ]

    raw = await chat_completion(messages, temperature=0.3, max_completion_tokens=2048)
    parsed = parse_llm_json(raw, error_msg="LLM 응답 파싱 실패")
    items = parsed.get("sections", [])

    # SectionResponse 형태로 반환 (임시 ID, 저장 안 됨)
    candidates = []
    for i, item in enumerate(items):
        candidates.append(SectionResponse(
            section_id=f"candidate-{i}",
            name=item.get("name", ""),
            type=item.get("type", "other"),
            description=item.get("description"),
            output_format_hint=item.get("output_format_hint"),
            is_default=False,
            is_active=True,
            order_index=100 + i,
            created_at="",
            updated_at="",
        ))

    logger.info(f"섹션 추출 완료: {len(candidates)}개 후보")
    return candidates
