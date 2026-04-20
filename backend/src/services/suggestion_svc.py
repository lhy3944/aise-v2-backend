"""동적 프롬프트 제안 서비스 — 프로젝트 메타데이터 기반 맞춤형 질문 생성"""

import hashlib
import json
import time
import uuid

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeDocument
from src.models.project import Project
from src.models.record import Record
from src.models.requirement import RequirementSection
from src.services.llm_svc import chat_completion
from src.utils.json_parser import parse_llm_json


# 프로젝트별 TTL 캐시 (10분)
_CACHE_TTL = 600  # seconds
_suggestion_cache: dict[str, tuple[float, str, list[dict]]] = {}  # key → (expires_at, fingerprint, data)


def _make_fingerprint(context: dict) -> str:
    """프로젝트 메타데이터 컨텍스트의 해시 fingerprint 생성"""
    raw = json.dumps(context, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


async def get_fingerprint(db: AsyncSession, project_id: uuid.UUID) -> str:
    """프로젝트의 현재 메타데이터 fingerprint만 조회 (캐시 비교용)"""
    context = await _gather_project_context(db, project_id)
    return _make_fingerprint(context)


async def generate_prompt_suggestions(
    db: AsyncSession,
    project_id: uuid.UUID,
    project_name: str,
    project_description: str | None = None,
    project_domain: str | None = None,
) -> dict:
    """프로젝트 메타데이터 기반 맞춤형 프롬프트 제안 생성

    Returns:
        dict: {"fingerprint": "...", "suggestions": [...]}
    """
    cache_key = str(project_id)

    # 프로젝트 컨텍스트 수집 + fingerprint
    context = await _gather_project_context(db, project_id)
    fingerprint = _make_fingerprint(context)

    # 캐시 히트 (TTL 유효 + fingerprint 일치)
    cached = _suggestion_cache.get(cache_key)
    if cached and cached[0] > time.monotonic() and cached[1] == fingerprint:
        logger.debug(f"프롬프트 제안 캐시 히트: project_id={project_id}")
        return {"fingerprint": fingerprint, "suggestions": cached[2]}

    # LLM 호출
    suggestions = await _generate_with_llm(
        project_name=project_name,
        project_description=project_description,
        project_domain=project_domain,
        context=context,
    )

    # 캐시에 저장
    _suggestion_cache[cache_key] = (time.monotonic() + _CACHE_TTL, fingerprint, suggestions)
    return {"fingerprint": fingerprint, "suggestions": suggestions}


def invalidate_cache(project_id: uuid.UUID) -> None:
    """프로젝트 캐시 무효화 (레코드/문서/섹션 변경 시 호출)"""
    _suggestion_cache.pop(str(project_id), None)


async def _gather_project_context(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict:
    """프로젝트 현황 요약 (fingerprint 재료 포함)"""
    # 프로젝트 메타데이터 — name/description/domain 변경 시 fingerprint 변경
    project_result = await db.execute(
        select(Project.name, Project.description, Project.domain).where(
            Project.id == project_id,
        )
    )
    project_row = project_result.one_or_none()
    project_name = project_row[0] if project_row else ""
    project_description = project_row[1] if project_row else ""
    project_domain = project_row[2] if project_row else ""

    # 문서 수 + 최신 변경 시점
    doc_result = await db.execute(
        select(
            func.count(KnowledgeDocument.id),
            func.max(KnowledgeDocument.updated_at),
        ).where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.status == "completed",
        )
    )
    doc_row = doc_result.one()
    doc_count = doc_row[0] or 0
    doc_latest = str(doc_row[1]) if doc_row[1] else ""

    # 문서 이름 목록
    doc_names_result = await db.execute(
        select(KnowledgeDocument.name).where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.status == "completed",
        ).limit(10)
    )
    doc_names = [n for (n,) in doc_names_result.all()]

    # 섹션 목록
    section_result = await db.execute(
        select(RequirementSection.name, RequirementSection.type).where(
            RequirementSection.project_id == project_id,
            RequirementSection.is_active == True,  # noqa: E712
        ).order_by(RequirementSection.order_index)
    )
    sections = [{"name": n, "type": t} for n, t in section_result.all()]

    # 레코드 현황 + 최신 변경 시점
    record_result = await db.execute(
        select(Record.status, func.count(Record.id)).where(
            Record.project_id == project_id,
        ).group_by(Record.status)
    )
    record_stats = {status: count for status, count in record_result.all()}

    record_latest_result = await db.execute(
        select(func.max(Record.updated_at)).where(
            Record.project_id == project_id,
        )
    )
    record_latest = str(record_latest_result.scalar() or "")

    # 용어 수 + 최신 변경 시점
    glossary_result = await db.execute(
        select(
            func.count(GlossaryItem.id),
            func.max(GlossaryItem.updated_at),
        ).where(
            GlossaryItem.project_id == project_id,
        )
    )
    glossary_row = glossary_result.one()
    glossary_count = glossary_row[0] or 0
    glossary_latest = str(glossary_row[1]) if glossary_row[1] else ""

    return {
        "project_name": project_name,
        "project_description": project_description or "",
        "project_domain": project_domain or "",
        "document_count": doc_count,
        "document_names": doc_names,
        "document_latest": doc_latest,
        "sections": sections,
        "record_stats": record_stats,
        "record_latest": record_latest,
        "glossary_count": glossary_count,
        "glossary_latest": glossary_latest,
    }


async def _generate_with_llm(
    project_name: str,
    project_description: str | None,
    project_domain: str | None,
    context: dict,
) -> list[dict]:
    """LLM을 사용하여 맞춤형 프롬프트 제안 생성"""
    doc_names = context.get("document_names", [])
    sections = context.get("sections", [])
    record_stats = context.get("record_stats", {})
    total_records = sum(record_stats.values())

    context_parts = [f"프로젝트: {project_name}"]
    if project_description:
        context_parts.append(f"설명: {project_description}")
    if project_domain:
        context_parts.append(f"도메인: {project_domain}")
    context_parts.append(f"지식 문서: {context['document_count']}개")
    if doc_names:
        context_parts.append(f"문서 목록: {', '.join(doc_names[:5])}")
    if sections:
        context_parts.append(f"섹션: {', '.join(s['name'] for s in sections)}")
    context_parts.append(f"레코드: 총 {total_records}개 ({', '.join(f'{k}: {v}개' for k, v in record_stats.items()) or '없음'})")
    context_parts.append(f"용어: {context['glossary_count']}개")

    messages = [
        {"role": "system", "content": "JSON 형식으로만 응답하세요."},
        {"role": "user", "content": f"""\
아래 프로젝트 현황을 보고, 사용자가 AI 어시스턴트에게 물어볼 만한 질문 5~6개를 생성하세요.

규칙:
- 프로젝트 상태에 맞는 실용적인 질문을 생성합니다
- 문서가 있으면 문서 분석/요약/비교 관련 질문 포함
- 레코드가 없거나 적으면 레코드 추출/생성 관련 질문 포함
- 레코드가 있으면 검토/수정/승인 관련 질문 포함
- 각 질문은 title(짧은 제목)과 description(구체적 질문)으로 구성
- 사용자의 언어(한국어)로 생성

프로젝트 현황:
{chr(10).join(context_parts)}

출력 형식:
{{"suggestions": [
  {{"title": "짧은 제목", "description": "구체적인 질문 내용"}},
  ...
]}}"""},
    ]

    try:
        raw = await chat_completion(messages, temperature=0.5, max_completion_tokens=2048)
        parsed = parse_llm_json(raw, error_msg="프롬프트 제안 파싱 실패")
        suggestions = parsed.get("suggestions", [])
        return [
            {"title": s.get("title", ""), "description": s.get("description", "")}
            for s in suggestions
            if s.get("title") and s.get("description")
        ]
    except Exception as e:
        logger.error(f"프롬프트 제안 생성 실패: {e}")
        return _get_fallback_suggestions()


def _get_fallback_suggestions() -> list[dict]:
    """API 실패 시 기본 프롬프트 카드"""
    return [
        {"title": "문서 분석", "description": "업로드된 문서의 주요 내용을 요약해주세요"},
        {"title": "요구사항 추출", "description": "지식 문서에서 요구사항 레코드를 추출해주세요"},
        {"title": "프로젝트 현황", "description": "현재 프로젝트의 요구사항 정의 상태를 분석해주세요"},
    ]
