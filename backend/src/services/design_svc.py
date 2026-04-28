"""Design 생성/조회 서비스 — SRS 의 clean version 을 입력으로 설계 산출물 생성.

설계 모델: srs_svc 와 동일 패턴.
- DESIGN = `Artifact(artifact_type='design')` 1 row + 다수 `ArtifactVersion`
- 프로젝트당 1개의 DESIGN Artifact (display_id='DSG-001')
- design_id (응답 외부 식별자) = `ArtifactVersion.id`
- 사용자 수동 편집은 staging-store -> PR -> merge 흐름 (별도 라우터 없음)

content payload schema:
{
  "sections": [
    {"section_id": "uuid|null", "title": "...", "content": "...", "order_index": 0}
  ],
  "based_on_srs": {"version_id": "uuid", "version_number": int},
  "status": "completed|failed",
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
from src.prompts.design.generate import build_design_section_prompt
from src.schemas.api.design import (
    DesignDocumentResponse,
    DesignListResponse,
    DesignSectionResponse,
)
from src.services.llm_svc import chat_completion


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _payload_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("sections")
    if not isinstance(raw, list):
        return []
    out = [s for s in raw if isinstance(s, dict)]
    return sorted(out, key=lambda s: int(s.get("order_index") or 0))


def _to_response(
    artifact: Artifact, version: ArtifactVersion
) -> DesignDocumentResponse:
    snapshot = _coerce_dict(version.snapshot)
    sections = _payload_sections(snapshot)
    return DesignDocumentResponse(
        design_id=str(version.id),
        artifact_id=str(artifact.id),
        project_id=str(artifact.project_id),
        version=version.version_number,
        status=str(snapshot.get("status") or "completed"),
        error_message=snapshot.get("error_message"),
        sections=[
            DesignSectionResponse(
                section_id=s.get("section_id"),
                title=str(s.get("title") or ""),
                content=str(s.get("content") or ""),
                order_index=int(s.get("order_index") or 0),
            )
            for s in sections
        ],
        based_on_srs=snapshot.get("based_on_srs"),
        source_artifact_versions=version.source_artifact_versions,
        created_at=version.committed_at,
    )


async def _get_design_artifact(
    db: AsyncSession, project_id: uuid.UUID
) -> Artifact | None:
    return (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "design",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalar_one_or_none()


async def _get_srs_clean_version(
    db: AsyncSession, project_id: uuid.UUID
) -> ArtifactVersion:
    """프로젝트의 SRS Artifact 의 current(clean) version 을 반환. 없으면 400."""
    srs_artifact = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "srs",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalar_one_or_none()
    if srs_artifact is None or srs_artifact.current_version_id is None:
        raise AppException(
            400,
            "완료된 SRS 문서가 없습니다. 먼저 SRS 를 생성하세요.",
        )
    version = await db.get(ArtifactVersion, srs_artifact.current_version_id)
    if version is None:
        raise AppException(500, "SRS current version 이 유실되었습니다.")
    return version


async def _next_version_number(db: AsyncSession, artifact_id: uuid.UUID) -> int:
    max_n = (
        await db.execute(
            select(func.max(ArtifactVersion.version_number)).where(
                ArtifactVersion.artifact_id == artifact_id,
            )
        )
    ).scalar() or 0
    return int(max_n) + 1


async def generate_design(
    db: AsyncSession, project_id: uuid.UUID
) -> DesignDocumentResponse:
    """SRS clean version 기반으로 설계 산출물 새 버전 생성.

    각 SRS 섹션 1개당 대응하는 Design 섹션 1개를 LLM 으로 생성한다.
    """
    logger.info(f"DESIGN 생성 시작: project_id={project_id}")

    # 1. SRS clean version 입력 확보
    srs_version = await _get_srs_clean_version(db, project_id)
    snapshot: dict[str, Any] = (
        srs_version.snapshot if isinstance(srs_version.snapshot, dict) else {}
    )
    raw_sections = snapshot.get("sections")
    srs_sections: list[dict[str, Any]] = (
        sorted(
            [s for s in raw_sections if isinstance(s, dict)],
            key=lambda s: int(s.get("order_index") or 0),
        )
        if isinstance(raw_sections, list)
        else []
    )
    if not srs_sections:
        raise AppException(400, "SRS 문서에 섹션이 없습니다.")

    # 2. 용어 사전
    glossary = (
        await db.execute(
            select(GlossaryItem).where(
                GlossaryItem.project_id == project_id,
                GlossaryItem.is_approved == True,  # noqa: E712
            )
        )
    ).scalars().all()
    glossary_dicts = [{"term": g.term, "definition": g.definition} for g in glossary]

    # 3. 섹션별 LLM 생성
    out_sections: list[dict[str, Any]] = []
    any_failed = False
    last_error: str | None = None
    for i, srs_section in enumerate(srs_sections):
        section_title = str(srs_section.get("title") or f"Section {i + 1}")
        srs_content = str(srs_section.get("content") or "")
        srs_section_id = str(srs_section.get("section_id") or "")

        if not srs_content.strip():
            out_sections.append({
                "section_id": srs_section.get("section_id"),
                "title": section_title,
                "content": "*대응하는 SRS 섹션 내용이 없어 설계를 생성하지 않았습니다.*",
                "order_index": i,
            })
            continue

        try:
            messages = build_design_section_prompt(
                section_title=section_title,
                srs_section_content=srs_content,
                srs_section_id=srs_section_id,
                glossary=glossary_dicts,
            )
            design_content = await chat_completion(
                messages, temperature=0.2, max_completion_tokens=4096
            )
        except Exception as e:
            logger.error(f"DESIGN 섹션 생성 실패: {section_title}, error={e}")
            design_content = f"*생성 실패: {str(e)[:200]}*"
            any_failed = True
            last_error = str(e)[:500]

        out_sections.append({
            "section_id": srs_section.get("section_id"),
            "title": section_title,
            "content": design_content,
            "order_index": i,
        })

    # 4. content payload 구성
    payload: dict[str, Any] = {
        "sections": out_sections,
        "based_on_srs": {
            "version_id": str(srs_version.id),
            "version_number": srs_version.version_number,
        },
        "status": "failed" if any_failed and not any(
            s["content"] and not s["content"].startswith("*생성 실패")
            for s in out_sections
        ) else "completed",
        "error_message": last_error if any_failed else None,
    }

    # 5. DESIGN Artifact 조회/생성
    artifact = await _get_design_artifact(db, project_id)
    if artifact is None:
        artifact = Artifact(
            project_id=project_id,
            artifact_type="design",
            display_id="DSG-001",
            title="Design",
            content=payload,
            working_status="dirty",
            lifecycle_status="active",
        )
        db.add(artifact)
        await db.flush()
    else:
        artifact.content = payload
        artifact.updated_at = datetime.now(timezone.utc)

    # 6. 새 ArtifactVersion 추가 (Phase E: source = SRS clean version)
    version_number = await _next_version_number(db, artifact.id)
    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=version_number,
        parent_version_id=artifact.current_version_id,
        snapshot=payload,
        content_hash=_content_hash(payload),
        commit_message=f"DESIGN v{version_number} generated",
        author_id="design_generator",
        source_artifact_versions={
            "srs": [
                {
                    "artifact_id": str(srs_version.artifact_id),
                    "version_id": str(srs_version.id),
                    "version_number": srs_version.version_number,
                }
            ]
        },
    )
    db.add(version)
    await db.flush()

    artifact.current_version_id = version.id
    artifact.working_status = "clean"
    artifact.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(version)
    await db.refresh(artifact)

    logger.info(
        f"DESIGN 생성 완료: artifact_id={artifact.id}, version={version_number}"
    )
    return _to_response(artifact, version)


async def list_design(
    db: AsyncSession, project_id: uuid.UUID
) -> DesignListResponse:
    artifact = await _get_design_artifact(db, project_id)
    if artifact is None:
        return DesignListResponse(documents=[])

    versions = (
        await db.execute(
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact.id)
            .order_by(ArtifactVersion.version_number.desc())
        )
    ).scalars().all()

    return DesignListResponse(
        documents=[_to_response(artifact, v) for v in versions]
    )


async def get_design(
    db: AsyncSession, project_id: uuid.UUID, design_id: uuid.UUID
) -> DesignDocumentResponse:
    """design_id = ArtifactVersion.id 로 조회."""
    version = await db.get(ArtifactVersion, design_id)
    if version is None:
        raise AppException(404, "Design 문서를 찾을 수 없습니다.")
    artifact = await db.get(Artifact, version.artifact_id)
    if (
        artifact is None
        or artifact.project_id != project_id
        or artifact.artifact_type != "design"
    ):
        raise AppException(404, "Design 문서를 찾을 수 없습니다.")
    return _to_response(artifact, version)
