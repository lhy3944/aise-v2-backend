"""Project 비즈니스 로직 서비스"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from sqlalchemy import func

from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeDocument
from src.models.project import Project, ProjectSettings
from src.models.requirement import RequirementSection
from src.schemas.api.project import (
    ProjectCreate,
    ProjectReadiness,
    ProjectUpdate,
    ProjectSettingsUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectSettingsResponse,
)
from src.utils.db import get_or_404


def _to_project_response(project: Project) -> ProjectResponse:
    """Project 모델 -> ProjectResponse 스키마 변환"""
    return ProjectResponse(
        project_id=str(project.id),
        name=project.name,
        description=project.description,
        domain=project.domain,
        product_type=project.product_type,
        modules=project.modules or [],
        member_count=0,  # MVP: 멤버 기능은 Phase 6
        status=project.status,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


def _to_settings_response(settings: ProjectSettings) -> ProjectSettingsResponse:
    """ProjectSettings 모델 -> ProjectSettingsResponse 스키마 변환"""
    return ProjectSettingsResponse(
        llm_model=settings.llm_model,
        language=settings.language,
        export_format=settings.export_format,
        diagram_tool=settings.diagram_tool,
        polarion_pat=settings.polarion_pat,
    )


async def _get_readiness(db: AsyncSession, project_id: uuid.UUID) -> ProjectReadiness:
    """프로젝트 준비도 요약 조회"""
    knowledge = (await db.execute(
        select(func.count()).where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.is_active == True, KnowledgeDocument.status == "completed",  # noqa: E712
        )
    )).scalar() or 0

    glossary = (await db.execute(
        select(func.count()).where(
            GlossaryItem.project_id == project_id,
            GlossaryItem.is_approved == True,  # noqa: E712
        )
    )).scalar() or 0

    sections = (await db.execute(
        select(func.count()).where(
            RequirementSection.project_id == project_id,
            RequirementSection.is_active == True,  # noqa: E712
        )
    )).scalar() or 0

    return ProjectReadiness(
        knowledge=knowledge, glossary=glossary, sections=sections,
        is_ready=knowledge >= 1 and sections >= 1,
    )


async def list_projects(db: AsyncSession) -> ProjectListResponse:
    """프로젝트 목록 조회 (준비도 포함)"""
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    responses = []
    for p in projects:
        responses.append(await _to_project_response_with_readiness(db, p))

    logger.debug(f"프로젝트 목록 조회: {len(projects)}건")
    return ProjectListResponse(projects=responses)


async def _get_project_model(db: AsyncSession, project_id: uuid.UUID) -> Project:
    """프로젝트 DB 모델 조회 (내부용)"""
    return await get_or_404(
        db, Project, Project.id == project_id,
        error_msg="프로젝트를 찾을 수 없습니다.",
    )


async def _to_project_response_with_readiness(
    db: AsyncSession, project: Project,
) -> ProjectResponse:
    """ProjectResponse + readiness 포함"""
    resp = _to_project_response(project)
    resp.readiness = await _get_readiness(db, project.id)
    return resp


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> ProjectResponse:
    """프로젝트 상세 조회"""
    project = await _get_project_model(db, project_id)
    return await _to_project_response_with_readiness(db, project)


async def create_project(db: AsyncSession, data: ProjectCreate) -> ProjectResponse:
    """프로젝트 생성 (설정도 기본값으로 함께 생성)"""
    project = Project(
        name=data.name,
        description=data.description,
        domain=data.domain,
        product_type=data.product_type,
        modules=[m.value for m in data.modules],
    )
    db.add(project)
    await db.flush()

    settings = ProjectSettings(project_id=project.id)
    db.add(settings)

    # 기본 섹션 5종 자동 생성
    from src.models.requirement import RequirementSection, DEFAULT_SECTIONS
    for sec_def in DEFAULT_SECTIONS:
        section = RequirementSection(project_id=project.id, **sec_def)
        db.add(section)

    await db.commit()
    await db.refresh(project)
    logger.info(f"프로젝트 생성: id={project.id}, name={project.name}")
    return await _to_project_response_with_readiness(db, project)


async def update_project(
    db: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate
) -> ProjectResponse:
    """프로젝트 수정"""
    project = await _get_project_model(db, project_id)

    update_data = data.model_dump(exclude_unset=True)
    if "modules" in update_data and update_data["modules"] is not None:
        update_data["modules"] = [m.value for m in data.modules]

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    logger.info(f"프로젝트 수정: id={project_id}")
    return await _to_project_response_with_readiness(db, project)


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    """프로젝트 삭제"""
    project = await _get_project_model(db, project_id)
    await db.delete(project)
    await db.commit()
    logger.info(f"프로젝트 삭제: id={project_id}")


async def get_project_settings(
    db: AsyncSession, project_id: uuid.UUID
) -> ProjectSettingsResponse:
    """프로젝트 설정 조회"""
    # 프로젝트 존재 확인
    await _get_project_model(db, project_id)

    settings = await get_or_404(
        db, ProjectSettings, ProjectSettings.project_id == project_id,
        error_msg="프로젝트 설정을 찾을 수 없습니다.",
    )
    return _to_settings_response(settings)


async def update_project_settings(
    db: AsyncSession, project_id: uuid.UUID, data: ProjectSettingsUpdate
) -> ProjectSettingsResponse:
    """프로젝트 설정 수정"""
    # 프로젝트 존재 확인
    await _get_project_model(db, project_id)

    settings = await get_or_404(
        db, ProjectSettings, ProjectSettings.project_id == project_id,
        error_msg="프로젝트 설정을 찾을 수 없습니다.",
    )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    logger.info(f"프로젝트 설정 수정: project_id={project_id}")
    return _to_settings_response(settings)
