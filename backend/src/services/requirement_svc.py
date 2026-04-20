"""Requirement 비즈니스 로직 서비스"""

import json
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, func, cast, Integer as SAInteger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.project import Project
from src.models.requirement import Requirement, RequirementVersion, RequirementSection
from src.schemas.api.common import RequirementType
from src.schemas.api.requirement import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    RequirementSelectionUpdate,
    RequirementReorderRequest,
)
from src.utils.db import get_or_404
from src.utils.reorder import build_reordered_ids

# 타입별 display_id 접두사
_TYPE_PREFIX = {
    "fr": "FR",
    "qa": "QA",
    "constraints": "CON",
    "other": "OTH",
}


def _to_response(req: Requirement) -> RequirementResponse:
    """Requirement 모델을 응답 스키마로 변환"""
    return RequirementResponse(
        requirement_id=str(req.id),
        display_id=req.display_id,
        order_index=req.order_index,
        type=req.type,
        original_text=req.original_text,
        refined_text=req.refined_text,
        is_selected=req.is_selected,
        status=req.status,
        section_id=str(req.section_id) if req.section_id else None,
        created_at=req.created_at.isoformat(),
        updated_at=req.updated_at.isoformat(),
    )


async def _next_display_id(db: AsyncSession, project_id: uuid.UUID, req_type: str) -> str:
    """프로젝트+타입 내 다음 display_id를 생성 (예: FR-001, FR-002).
    삭제된 번호를 재사용하지 않도록 기존 최대 번호 + 1을 사용한다."""
    prefix = _TYPE_PREFIX.get(req_type, "REQ")
    # display_id에서 숫자 부분(하이픈 뒤)을 추출하여 최대값 조회
    # display_id 형식: "FR-001", "QA-012" 등
    numeric_part = cast(
        func.substring(Requirement.display_id, func.length(prefix) + 2),
        SAInteger,
    )
    stmt = (
        select(func.max(numeric_part))
        .where(Requirement.project_id == project_id, Requirement.type == req_type)
    )
    result = await db.execute(stmt)
    max_num = result.scalar() or 0
    return f"{prefix}-{max_num + 1:03d}"


async def _validate_section(
    db: AsyncSession, project_id: uuid.UUID, section_id: uuid.UUID, req_type: str,
) -> None:
    """섹션 존재 여부 + 프로젝트 소속 + 타입 일치 검증"""
    section = await get_or_404(
        db, RequirementSection,
        RequirementSection.id == section_id,
        RequirementSection.project_id == project_id,
        error_msg="섹션을 찾을 수 없습니다.",
    )
    if section.type != req_type:
        raise AppException(
            status_code=400,
            detail=f"요구사항 타입({req_type})과 섹션 타입({section.type})이 일치하지 않습니다.",
        )


async def _next_order_index(db: AsyncSession, project_id: uuid.UUID) -> int:
    """프로젝트 내 다음 order_index 반환"""
    stmt = (
        select(func.max(Requirement.order_index))
        .where(Requirement.project_id == project_id)
    )
    result = await db.execute(stmt)
    max_idx = result.scalar()
    return (max_idx + 1) if max_idx is not None else 0


async def create_requirement_from_review(
    project_id: uuid.UUID,
    req_type: str,
    text: str,
    db: AsyncSession,
) -> Requirement:
    """Review 제안 수락으로 새 요구사항을 생성한다."""
    display_id = await _next_display_id(db, project_id, req_type)
    order_index = await _next_order_index(db, project_id)

    new_req = Requirement(
        project_id=project_id,
        type=req_type,
        original_text=text,
        refined_text=text,
        display_id=display_id,
        order_index=order_index,
        is_selected=True,
    )
    db.add(new_req)
    await db.flush()
    return new_req


async def get_requirements(
    db: AsyncSession,
    project_id: uuid.UUID,
    type_filter: RequirementType | None = None,
) -> list[RequirementResponse]:
    """프로젝트의 요구사항 목록 조회 (type 필터링 지원)"""
    stmt = select(Requirement).where(Requirement.project_id == project_id)
    if type_filter is not None:
        stmt = stmt.where(Requirement.type == type_filter.value)
    stmt = stmt.order_by(Requirement.order_index.asc())

    result = await db.execute(stmt)
    requirements = result.scalars().all()

    logger.info(f"요구사항 목록 조회: project_id={project_id}, type={type_filter}, count={len(requirements)}")
    return [_to_response(r) for r in requirements]


async def create_requirement(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: RequirementCreate,
) -> RequirementResponse:
    """요구사항 생성"""
    await get_or_404(
        db, Project, Project.id == project_id,
        error_msg="프로젝트를 찾을 수 없습니다.",
    )

    section_uuid = data.section_id
    if section_uuid:
        await _validate_section(db, project_id, section_uuid, data.type.value)

    display_id = await _next_display_id(db, project_id, data.type.value)
    order_index = await _next_order_index(db, project_id)

    requirement = Requirement(
        project_id=project_id,
        section_id=section_uuid,
        type=data.type.value,
        display_id=display_id,
        order_index=order_index,
        original_text=data.original_text,
    )
    db.add(requirement)
    await db.commit()
    await db.refresh(requirement)

    logger.info(f"요구사항 생성: id={requirement.id}, display_id={display_id}, project_id={project_id}")
    return _to_response(requirement)


async def update_requirement(
    db: AsyncSession,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    data: RequirementUpdate,
) -> RequirementResponse:
    """요구사항 수정"""
    requirement = await get_or_404(
        db, Requirement,
        Requirement.id == requirement_id,
        Requirement.project_id == project_id,
        error_msg="요구사항을 찾을 수 없습니다.",
    )

    update_fields = data.model_dump(exclude_unset=True)
    # section_id: None(미분류) 또는 UUID + 검증
    if "section_id" in update_fields:
        sid = update_fields.pop("section_id")
        if sid is not None:
            await _validate_section(db, project_id, sid, requirement.type)
            requirement.section_id = sid
        else:
            requirement.section_id = None
    for field, value in update_fields.items():
        setattr(requirement, field, value)

    requirement.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(requirement)

    logger.info(f"요구사항 수정: id={requirement_id}, fields={list(update_fields.keys())}")
    return _to_response(requirement)


async def delete_requirement(
    db: AsyncSession,
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
) -> None:
    """요구사항 삭제"""
    requirement = await get_or_404(
        db, Requirement,
        Requirement.id == requirement_id,
        Requirement.project_id == project_id,
        error_msg="요구사항을 찾을 수 없습니다.",
    )

    await db.delete(requirement)
    await db.commit()

    logger.info(f"요구사항 삭제: id={requirement_id}, project_id={project_id}")


async def update_selection(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: RequirementSelectionUpdate,
) -> int:
    """요구사항 일괄 선택/해제. 업데이트된 건수를 반환."""
    stmt = select(Requirement).where(
        Requirement.project_id == project_id,
        Requirement.id.in_(data.requirement_ids),
    )
    result = await db.execute(stmt)
    requirements = result.scalars().all()

    now = datetime.now(timezone.utc)
    for req in requirements:
        req.is_selected = data.is_selected
        req.updated_at = now

    await db.commit()

    logger.info(
        f"요구사항 선택 일괄 업데이트: project_id={project_id}, "
        f"count={len(requirements)}, is_selected={data.is_selected}"
    )
    return len(requirements)


async def reorder_requirements(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: RequirementReorderRequest,
) -> int:
    """요구사항 순서 변경. 실제 변경된 건수를 반환."""
    if not data.ordered_ids:
        return 0

    stmt = (
        select(Requirement)
        .where(Requirement.project_id == project_id)
        .order_by(Requirement.order_index.asc())
    )
    result = await db.execute(stmt)
    requirement_rows = result.scalars().all()
    requirements = {row.id: row for row in requirement_rows}
    current_ids = [row.id for row in requirement_rows]
    reordered_ids = build_reordered_ids(data.ordered_ids, current_ids)

    now = datetime.now(timezone.utc)
    updated = 0
    for idx, rid in enumerate(reordered_ids):
        req = requirements.get(rid)
        if req and req.order_index != idx:
            req.order_index = idx
            req.updated_at = now
            updated += 1

    await db.commit()

    logger.info(f"요구사항 순서 변경: project_id={project_id}, updated={updated}")
    return updated


async def save_version(
    db: AsyncSession,
    project_id: uuid.UUID,
    created_by: str | None = None,
) -> dict:
    """현재 프로젝트의 모든 요구사항을 버전으로 저장"""
    stmt = select(Requirement).where(Requirement.project_id == project_id).order_by(Requirement.order_index.asc())
    result = await db.execute(stmt)
    requirements = result.scalars().all()

    max_version_stmt = select(func.max(RequirementVersion.version)).where(
        RequirementVersion.project_id == project_id
    )
    max_version_result = await db.execute(max_version_stmt)
    max_version = max_version_result.scalar() or 0
    new_version = max_version + 1

    snapshot_data = [
        {
            "id": str(r.id),
            "display_id": r.display_id,
            "order_index": r.order_index,
            "type": r.type,
            "original_text": r.original_text,
            "refined_text": r.refined_text,
            "is_selected": r.is_selected,
            "status": r.status,
            "section_id": str(r.section_id) if r.section_id else None,
        }
        for r in requirements
    ]
    snapshot_json = json.dumps(snapshot_data, ensure_ascii=False)

    version = RequirementVersion(
        project_id=project_id,
        version=new_version,
        snapshot=snapshot_json,
        saved_count=len(requirements),
        created_by=created_by,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    logger.info(
        f"요구사항 버전 저장: project_id={project_id}, "
        f"version={new_version}, saved_count={len(requirements)}"
    )
    return {
        "version": new_version,
        "saved_count": len(requirements),
        "saved_at": version.created_at.isoformat(),
    }
