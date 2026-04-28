"""Project 비즈니스 로직 서비스"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from sqlalchemy import func

from src.models.artifact import Artifact, ArtifactVersion, PullRequest
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeDocument
from src.models.project import Project, ProjectSettings
from src.models.requirement import RequirementSection
from src.models.session import Session as ChatSession, SessionMessage
from src.schemas.api.project import (
    ProjectCreate,
    ProjectDeletePreview,
    ProjectReadiness,
    ProjectUpdate,
    ProjectSettingsUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectSettingsResponse,
)
from src.services import storage_svc
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


async def list_projects(
    db: AsyncSession, *, include_deleted: bool = False
) -> ProjectListResponse:
    """프로젝트 목록 조회 (준비도 포함). 기본은 status='active' 만 반환."""
    stmt = select(Project).order_by(Project.created_at.desc())
    if not include_deleted:
        stmt = stmt.where(Project.status != "deleted")
    result = await db.execute(stmt)
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


async def delete_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    confirm_name: str | None = None,
) -> None:
    """프로젝트 soft delete — status='deleted' 로 마킹.

    실제 row 삭제는 `hard_delete_project` 에서. 사용자는 30일 내 복원 가능 (휴지통).
    `confirm_name` 이 주어지면 프로젝트 이름과 일치해야 진행 (운영 안전망).
    """
    project = await _get_project_model(db, project_id)
    if confirm_name is not None and confirm_name.strip() != project.name:
        raise AppException(
            400,
            "프로젝트 이름이 일치하지 않습니다. 삭제를 확인하려면 정확한 이름을 입력하세요.",
        )
    if project.status == "deleted":
        # 이미 휴지통에 있는 경우 — 일관성 위해 200 처리.
        logger.info(f"프로젝트 이미 삭제됨(skip): id={project_id}")
        return
    project.status = "deleted"
    await db.commit()
    logger.info(f"프로젝트 soft delete: id={project_id}, name={project.name}")


async def restore_project(
    db: AsyncSession, project_id: uuid.UUID
) -> ProjectResponse:
    """soft-deleted 프로젝트를 복원 (status='active')."""
    project = await _get_project_model(db, project_id)
    if project.status != "deleted":
        raise AppException(409, "삭제 상태가 아닌 프로젝트는 복원할 수 없습니다.")
    project.status = "active"
    await db.commit()
    await db.refresh(project)
    logger.info(f"프로젝트 복원: id={project_id}, name={project.name}")
    return await _to_project_response_with_readiness(db, project)


async def get_delete_preview(
    db: AsyncSession, project_id: uuid.UUID
) -> ProjectDeletePreview:
    """프로젝트 hard delete 시 영향받을 데이터 카운트.

    UI 의 삭제 확인 모달에서 보여주는 데이터. 카운트만 집계 — 실제 삭제 X.
    """
    project = await _get_project_model(db, project_id)

    async def _count(model, *conds) -> int:
        stmt = select(func.count()).select_from(model).where(*conds)
        return (await db.execute(stmt)).scalar() or 0

    knowledge_docs = await _count(
        KnowledgeDocument, KnowledgeDocument.project_id == project_id
    )
    # MinIO 누적 바이트 — KnowledgeDocument.file_size_bytes 컬럼이 있으면 합계,
    # 없으면 0 으로 두고 UI 에서 "(파일)" 정도만 표시.
    file_size_total = 0
    if hasattr(KnowledgeDocument, "file_size_bytes"):
        file_size_total = (
            await db.execute(
                select(func.coalesce(func.sum(KnowledgeDocument.file_size_bytes), 0))
                .where(KnowledgeDocument.project_id == project_id)
            )
        ).scalar() or 0
    sessions_count = await _count(
        ChatSession, ChatSession.project_id == project_id
    )
    msgs_count = (
        await db.execute(
            select(func.count())
            .select_from(SessionMessage)
            .join(ChatSession, SessionMessage.session_id == ChatSession.id)
            .where(ChatSession.project_id == project_id)
        )
    ).scalar() or 0
    artifacts_count = await _count(
        Artifact, Artifact.project_id == project_id
    )
    versions_count = (
        await db.execute(
            select(func.count())
            .select_from(ArtifactVersion)
            .join(Artifact, ArtifactVersion.artifact_id == Artifact.id)
            .where(Artifact.project_id == project_id)
        )
    ).scalar() or 0
    prs_count = (
        await db.execute(
            select(func.count())
            .select_from(PullRequest)
            .join(Artifact, PullRequest.artifact_id == Artifact.id)
            .where(Artifact.project_id == project_id)
        )
    ).scalar() or 0
    glossary_count = await _count(
        GlossaryItem, GlossaryItem.project_id == project_id
    )
    sections_count = await _count(
        RequirementSection, RequirementSection.project_id == project_id
    )

    return ProjectDeletePreview(
        project_id=str(project.id),
        project_name=project.name,
        knowledge_documents=int(knowledge_docs),
        knowledge_files_bytes=int(file_size_total),
        sessions=int(sessions_count),
        session_messages=int(msgs_count),
        artifacts=int(artifacts_count),
        artifact_versions=int(versions_count),
        pull_requests=int(prs_count),
        glossary_items=int(glossary_count),
        requirement_sections=int(sections_count),
    )


async def hard_delete_project(
    db: AsyncSession, project_id: uuid.UUID
) -> int:
    """완전 삭제 (DB CASCADE + MinIO prefix 정리). 삭제된 MinIO 객체 수 반환.

    호출 경로:
    - 사용자가 휴지통에서 즉시 영구 삭제 선택
    - 30 일 retention cron (별도 구현)

    DB CASCADE 가 모든 자식 row 를 정리하지만 MinIO 객체는 별도 정리 필요.
    """
    project = await _get_project_model(db, project_id)

    # 1. MinIO prefix 정리 (DB 삭제 전에 시도 — 실패해도 DB 는 진행)
    minio_deleted = 0
    try:
        bucket = storage_svc.get_default_bucket()
        prefix = f"{project_id}/"
        minio_deleted = await storage_svc.delete_prefix(bucket, prefix)
    except AppException as exc:
        logger.error(
            f"프로젝트 hard delete - MinIO 정리 실패 (DB 삭제는 진행): "
            f"id={project_id}, err={exc.detail}"
        )

    # 2. DB CASCADE 로 모든 관련 row 삭제
    await db.delete(project)
    await db.commit()
    logger.info(
        f"프로젝트 hard delete 완료: id={project_id}, name={project.name}, "
        f"minio_objects_deleted={minio_deleted}"
    )
    return minio_deleted


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
