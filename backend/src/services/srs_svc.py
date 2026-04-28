"""SRS 생성/조회/편집 서비스 — Artifact governance 통합 버전.

Phase C 변경 사항:
- 기존 srs_documents/srs_sections 테이블 의존 제거
- SRS = `Artifact(artifact_type='srs')` 1 row + 다수 `ArtifactVersion` 체인
- 프로젝트당 1개의 SRS Artifact (display_id='SRS-001'), version 증가
- 사용자 수동 편집은 staging-store → PR → merge 흐름으로 통일 (별도 라우터 제거)
- `srs_id` (응답 외부 식별자) = `ArtifactVersion.id`
  * 각 version 이 frontend 의 "SRS 문서" 개념과 1:1 매핑되도록
  * 기존 `SrsDocumentResponse` 스키마 호환 유지

content payload schema (Artifact.content / ArtifactVersion.snapshot):
{
  "sections": [
    {"section_id": "uuid|null", "title": "...", "content": "...", "order_index": 0}
  ],
  "based_on_records": {"artifact_ids": ["uuid", ...]},
  "based_on_documents": {"documents": [{"id": "uuid", "name": "..."}]},
  "status": "completed|generating|failed",
  "error_message": null
}
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.artifact import Artifact, ArtifactVersion
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeDocument
from src.models.requirement import RequirementSection
from src.prompts.srs.generate import build_srs_section_prompt
from src.schemas.api.srs import (
    SrsDocumentResponse,
    SrsListResponse,
    SrsSectionResponse,
)
from src.services.llm_svc import chat_completion


# ── 직렬화 헬퍼 ─────────────────────────────────────────────────────────────


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _payload_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("sections")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for s in raw:
        if isinstance(s, dict):
            out.append(s)
    return sorted(out, key=lambda s: int(s.get("order_index") or 0))


def _to_response(
    artifact: Artifact,
    version: ArtifactVersion,
) -> SrsDocumentResponse:
    """ArtifactVersion 1개를 frontend 가 알고 있는 SrsDocumentResponse 로 변환.

    - srs_id = ArtifactVersion.id (frontend 의 'SRS 문서' 단위)
    - version = ArtifactVersion.version_number (단조 증가)
    """
    snapshot = _coerce_dict(version.snapshot)
    sections = _payload_sections(snapshot)
    return SrsDocumentResponse(
        srs_id=str(version.id),
        artifact_id=str(artifact.id),
        project_id=str(artifact.project_id),
        version=version.version_number,
        status=str(snapshot.get("status") or "completed"),
        error_message=snapshot.get("error_message"),
        sections=[
            SrsSectionResponse(
                section_id=s.get("section_id"),
                title=str(s.get("title") or ""),
                content=str(s.get("content") or ""),
                order_index=int(s.get("order_index") or 0),
            )
            for s in sections
        ],
        based_on_records=snapshot.get("based_on_records"),
        based_on_documents=snapshot.get("based_on_documents"),
        source_artifact_versions=version.source_artifact_versions,
        created_at=version.committed_at,
    )


# ── Internal: SRS Artifact lookup / version ────────────────────────────────


async def _get_srs_artifact(
    db: AsyncSession, project_id: uuid.UUID
) -> Artifact | None:
    """프로젝트의 SRS Artifact (1개) 조회. 없으면 None."""
    return (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "srs",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalar_one_or_none()


async def _next_version_number(db: AsyncSession, artifact_id: uuid.UUID) -> int:
    max_n = (
        await db.execute(
            select(func.max(ArtifactVersion.version_number)).where(
                ArtifactVersion.artifact_id == artifact_id,
            )
        )
    ).scalar() or 0
    return int(max_n) + 1


# ── generate ───────────────────────────────────────────────────────────────


async def generate_srs(
    db: AsyncSession, project_id: uuid.UUID,
) -> SrsDocumentResponse:
    """승인된 레코드 기반 SRS 새 버전 생성.

    Artifact governance 통합:
    - 프로젝트의 SRS Artifact 가 없으면 새로 생성 (display_id='SRS-001').
    - 새 ArtifactVersion 1개를 INSERT 하고 current_version_id 로 연결.
    - working_status='clean' (LLM 직접 생성은 PR 워크플로우 우회 — 빠른 iteration).
    """
    logger.info(f"SRS 생성 시작: project_id={project_id}")

    # 1. 활성 섹션 조회 (순서대로)
    sections = (await db.execute(
        select(RequirementSection)
        .where(RequirementSection.project_id == project_id, RequirementSection.is_active == True)  # noqa: E712
        .order_by(RequirementSection.order_index)
    )).scalars().all()

    if not sections:
        raise AppException(400, "활성 섹션이 없습니다.")

    # 2. 레코드 Artifact 조회
    records = (await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.artifact_type == "record",
            Artifact.lifecycle_status == "active",
        )
        .order_by(Artifact.created_at.asc())
    )).scalars().all()

    if not records:
        raise AppException(400, "레코드가 없습니다. 먼저 레코드를 추출하세요.")

    # Phase E lineage — 각 record 의 current_version_id 의 version_number 일괄 조회.
    record_version_ids = [
        r.current_version_id for r in records if r.current_version_id is not None
    ]
    record_version_map: dict[uuid.UUID, int] = {}
    if record_version_ids:
        rows = (
            await db.execute(
                select(ArtifactVersion.id, ArtifactVersion.version_number).where(
                    ArtifactVersion.id.in_(record_version_ids)
                )
            )
        ).all()
        record_version_map = {vid: vn for vid, vn in rows}

    # 3. 용어 사전
    glossary = (await db.execute(
        select(GlossaryItem)
        .where(GlossaryItem.project_id == project_id, GlossaryItem.is_approved == True)  # noqa: E712
    )).scalars().all()
    glossary_dicts = [{"term": g.term, "definition": g.definition} for g in glossary]

    # 4. 기반 문서 목록
    doc_ids = {
        r.content["source_document_id"]
        for r in records
        if isinstance(r.content, dict) and r.content.get("source_document_id")
    }
    doc_names: list[dict[str, str]] = []
    if doc_ids:
        docs = (await db.execute(
            select(KnowledgeDocument.id, KnowledgeDocument.name)
            .where(KnowledgeDocument.id.in_([uuid.UUID(d) for d in doc_ids]))
        )).all()
        doc_names = [{"id": str(d), "name": n} for d, n in docs]

    # 5. 섹션별 LLM 생성
    record_map: dict[str, list[dict]] = {}
    for r in records:
        payload = r.content if isinstance(r.content, dict) else {}
        section_id = payload.get("section_id")
        key = str(section_id) if section_id else "none"
        record_map.setdefault(key, []).append(
            {"display_id": r.display_id, "content": payload.get("text", "")}
        )

    out_sections: list[dict[str, Any]] = []
    any_failed = False
    last_error: str | None = None
    for i, section in enumerate(sections):
        sec_records = record_map.get(str(section.id), [])

        if not sec_records:
            section_content = "*이 섹션에 해당하는 레코드가 없습니다.*"
        else:
            try:
                messages = build_srs_section_prompt(
                    section_name=section.name,
                    section_description=section.description,
                    output_format_hint=section.output_format_hint,
                    records=sec_records,
                    glossary=glossary_dicts,
                )
                section_content = await chat_completion(
                    messages, temperature=0.2, max_completion_tokens=4096
                )
            except Exception as e:
                logger.error(f"SRS 섹션 생성 실패: {section.name}, error={e}")
                section_content = f"*생성 실패: {str(e)[:200]}*"
                any_failed = True
                last_error = str(e)[:500]

        out_sections.append({
            "section_id": str(section.id) if section.id else None,
            "title": section.name,
            "content": section_content,
            "order_index": i,
        })

    # 6. content payload 구성
    payload: dict[str, Any] = {
        "sections": out_sections,
        "based_on_records": {"artifact_ids": [str(r.id) for r in records]},
        "based_on_documents": {"documents": doc_names},
        "status": "failed" if any_failed and not any(
            s["content"] and not s["content"].startswith("*생성 실패") for s in out_sections
        ) else "completed",
        "error_message": last_error if any_failed else None,
    }

    # 7. SRS Artifact 조회/생성
    artifact = await _get_srs_artifact(db, project_id)
    if artifact is None:
        artifact = Artifact(
            project_id=project_id,
            artifact_type="srs",
            display_id="SRS-001",
            title="SRS",
            content=payload,
            working_status="dirty",  # version 생성 후 clean 으로 전환
            lifecycle_status="active",
        )
        db.add(artifact)
        await db.flush()
    else:
        # 기존 artifact 의 working copy 도 최신 payload 로 갱신
        artifact.content = payload
        artifact.updated_at = datetime.now(timezone.utc)

    # 8. 새 ArtifactVersion 추가 (Phase E: source_artifact_versions 로 lineage 기록)
    record_lineage: list[dict[str, Any]] = []
    for r in records:
        entry: dict[str, Any] = {"artifact_id": str(r.id)}
        if (
            r.current_version_id is not None
            and r.current_version_id in record_version_map
        ):
            entry["version_number"] = record_version_map[r.current_version_id]
        record_lineage.append(entry)

    version_number = await _next_version_number(db, artifact.id)
    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=version_number,
        parent_version_id=artifact.current_version_id,
        snapshot=payload,
        content_hash=_content_hash(payload),
        commit_message=f"SRS v{version_number} generated",
        author_id="srs_generator",
        source_artifact_versions={"record": record_lineage},
    )
    db.add(version)
    await db.flush()

    # 9. current_version_id 갱신 + clean 전환 (CHECK 제약: clean 은 version 필요)
    artifact.current_version_id = version.id
    artifact.working_status = "clean"
    artifact.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(version)
    await db.refresh(artifact)

    logger.info(
        f"SRS 생성 완료: artifact_id={artifact.id}, version={version_number}, "
        f"version_id={version.id}"
    )
    return _to_response(artifact, version)


# ── list / get ─────────────────────────────────────────────────────────────


async def list_srs(
    db: AsyncSession, project_id: uuid.UUID,
) -> SrsListResponse:
    """프로젝트의 모든 SRS 버전을 SrsDocumentResponse 리스트로 반환.

    각 ArtifactVersion 이 응답의 1개 row 가 됨 — frontend 는 기존과 동일하게
    version 별 select dropdown 을 그릴 수 있다.
    """
    artifact = await _get_srs_artifact(db, project_id)
    if artifact is None:
        return SrsListResponse(documents=[])

    versions = (
        await db.execute(
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact.id)
            .order_by(ArtifactVersion.version_number.desc())
        )
    ).scalars().all()

    return SrsListResponse(
        documents=[_to_response(artifact, v) for v in versions]
    )


async def get_srs(
    db: AsyncSession, project_id: uuid.UUID, srs_id: uuid.UUID,
) -> SrsDocumentResponse:
    """srs_id = ArtifactVersion.id 로 조회."""
    version = await db.get(ArtifactVersion, srs_id)
    if version is None:
        raise AppException(404, "SRS 문서를 찾을 수 없습니다.")
    artifact = await db.get(Artifact, version.artifact_id)
    if (
        artifact is None
        or artifact.project_id != project_id
        or artifact.artifact_type != "srs"
    ):
        raise AppException(404, "SRS 문서를 찾을 수 없습니다.")
    return _to_response(artifact, version)
