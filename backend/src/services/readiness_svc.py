"""프로젝트 준비도 서비스"""

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeDocument
from src.models.requirement import RequirementSection
from src.schemas.api.readiness import ReadinessItem, ReadinessResponse


async def get_readiness(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> ReadinessResponse:
    """프로젝트 준비도 조회"""

    # 1. 활성 + completed 지식 문서 수
    knowledge_count = (await db.execute(
        select(func.count()).where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.is_active == True,  # noqa: E712
            KnowledgeDocument.status == "completed",
        )
    )).scalar() or 0

    # 2. 승인된 용어 수
    glossary_count = (await db.execute(
        select(func.count()).where(
            GlossaryItem.project_id == project_id,
            GlossaryItem.is_approved == True,  # noqa: E712
        )
    )).scalar() or 0

    # 3. 활성 섹션 수
    section_count = (await db.execute(
        select(func.count()).where(
            RequirementSection.project_id == project_id,
            RequirementSection.is_active == True,  # noqa: E712
        )
    )).scalar() or 0

    knowledge = ReadinessItem(label="지식 문서", count=knowledge_count, sufficient=knowledge_count >= 1)
    glossary = ReadinessItem(label="승인 용어", count=glossary_count, sufficient=glossary_count >= 1)
    sections = ReadinessItem(label="활성 섹션", count=section_count, sufficient=section_count >= 1)

    is_ready = knowledge.sufficient and sections.sufficient

    return ReadinessResponse(
        knowledge=knowledge,
        glossary=glossary,
        sections=sections,
        is_ready=is_ready,
    )
