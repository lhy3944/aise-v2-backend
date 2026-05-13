"""Data Model 생성/조회 서비스 — SRS + 시스템 모델 기반 데이터 모델 생성.

design_svc 와 동일 패턴:
- DATA_MODEL = `Artifact(artifact_type='data_model')` 1 row + 다수 `ArtifactVersion`
- 프로젝트당 1개의 DATA_MODEL Artifact (display_id='DM-001')
- data_model_id (응답 외부 식별자) = `ArtifactVersion.id`

content payload schema:
{
  "sections": [
    {"section_id": "uuid|null", "title": "...", "content": "...", "order_index": 0}
  ],
  "based_on_srs": {"version_id": "uuid", "version_number": int},
  "based_on_system_model": {"version_id": "uuid", "version_number": int} | null,
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
from src.prompts.data_model.generate import build_data_model_prompt
from src.schemas.api.data_model import (
    DataModelDocumentResponse,
    DataModelListResponse,
    DataModelSectionResponse,
)
from src.services.artifact_messages import MISSING_SRS_MESSAGE
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
) -> DataModelDocumentResponse:
    snapshot = _coerce_dict(version.snapshot)
    sections = _payload_sections(snapshot)
    return DataModelDocumentResponse(
        data_model_id=str(version.id),
        artifact_id=str(artifact.id),
        project_id=str(artifact.project_id),
        version=version.version_number,
        status=str(snapshot.get("status") or "completed"),
        error_message=snapshot.get("error_message"),
        sections=[
            DataModelSectionResponse(
                section_id=s.get("section_id"),
                title=str(s.get("title") or ""),
                content=str(s.get("content") or ""),
                order_index=int(s.get("order_index") or 0),
            )
            for s in sections
        ],
        based_on_srs=snapshot.get("based_on_srs"),
        based_on_system_model=snapshot.get("based_on_system_model"),
        source_artifact_versions=version.source_artifact_versions,
        created_at=version.committed_at,
    )


async def _get_data_model_artifact(
    db: AsyncSession, project_id: uuid.UUID
) -> Artifact | None:
    artifact = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "data_model",
                Artifact.lifecycle_status.in_(("active", "deleted")),
            ).order_by(
                Artifact.lifecycle_status.asc(),
            )
        )
    ).scalar_one_or_none()

    if artifact is not None and artifact.lifecycle_status != "active":
        artifact.lifecycle_status = "active"
        artifact.updated_at = datetime.now(timezone.utc)

    return artifact


async def _get_srs_clean_version(
    db: AsyncSession, project_id: uuid.UUID
) -> ArtifactVersion:
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
        raise AppException(400, MISSING_SRS_MESSAGE)
    version = await db.get(ArtifactVersion, srs_artifact.current_version_id)
    if version is None:
        raise AppException(500, "SRS current version 이 유실되었습니다.")
    return version


async def _get_system_model_version(
    db: AsyncSession, project_id: uuid.UUID
) -> ArtifactVersion | None:
    sm_artifact = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "system_model",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalar_one_or_none()
    if sm_artifact is None or sm_artifact.current_version_id is None:
        return None
    return await db.get(ArtifactVersion, sm_artifact.current_version_id)


async def _next_version_number(db: AsyncSession, artifact_id: uuid.UUID) -> int:
    max_n = (
        await db.execute(
            select(func.max(ArtifactVersion.version_number)).where(
                ArtifactVersion.artifact_id == artifact_id,
            )
        )
    ).scalar() or 0
    return int(max_n) + 1


async def generate_data_model(
    db: AsyncSession, project_id: uuid.UUID
) -> DataModelDocumentResponse:
    """SRS + 시스템 모델 기반으로 데이터 모델 새 버전 생성."""
    logger.info(f"DATA_MODEL 생성 시작: project_id={project_id}")

    srs_version = await _get_srs_clean_version(db, project_id)
    srs_snapshot: dict[str, Any] = (
        srs_version.snapshot if isinstance(srs_version.snapshot, dict) else {}
    )
    raw_sections = srs_snapshot.get("sections")
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

    sm_version = await _get_system_model_version(db, project_id)
    sm_sections: list[dict[str, Any]] | None = None
    if sm_version is not None:
        sm_snapshot = _coerce_dict(sm_version.snapshot)
        sm_sections = _payload_sections(sm_snapshot)

    glossary = (
        await db.execute(
            select(GlossaryItem).where(
                GlossaryItem.project_id == project_id,
                GlossaryItem.is_approved == True,  # noqa: E712
            )
        )
    ).scalars().all()
    glossary_dicts = [{"term": g.term, "definition": g.definition} for g in glossary]

    messages = build_data_model_prompt(
        srs_sections=srs_sections,
        system_model_sections=sm_sections,
        glossary=glossary_dicts,
    )

    any_failed = False
    last_error: str | None = None
    try:
        content = await chat_completion(
            messages, temperature=0.2, max_completion_tokens=8192
        )
    except Exception as e:
        logger.error(f"DATA_MODEL 생성 실패: error={e}")
        content = f"*생성 실패: {str(e)[:200]}*"
        any_failed = True
        last_error = str(e)[:500]

    section_titles = [
        "Conceptual Data Model",
        "Logical Data Model",
        "Physical Data Model",
    ]

    content_lines = content.split("\n")
    section_blocks: list[dict[str, Any]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in content_lines:
        is_section_header = False
        for title in section_titles:
            if line.strip().lstrip("#").strip().lower() == title.lower():
                if current_title is not None:
                    section_blocks.append({
                        "section_id": None,
                        "title": current_title,
                        "content": "\n".join(current_lines).strip(),
                        "order_index": len(section_blocks),
                    })
                current_title = title
                current_lines = []
                is_section_header = True
                break
        if not is_section_header:
            current_lines.append(line)

    if current_title is not None:
        section_blocks.append({
            "section_id": None,
            "title": current_title,
            "content": "\n".join(current_lines).strip(),
            "order_index": len(section_blocks),
        })

    if not section_blocks:
        section_blocks = [{
            "section_id": None,
            "title": "Data Model",
            "content": content,
            "order_index": 0,
        }]

    source_versions: dict[str, Any] = {
        "srs": [
            {
                "artifact_id": str(srs_version.artifact_id),
                "version_id": str(srs_version.id),
                "version_number": srs_version.version_number,
            }
        ]
    }

    based_on_sm: dict[str, Any] | None = None
    if sm_version is not None:
        based_on_sm = {
            "version_id": str(sm_version.id),
            "version_number": sm_version.version_number,
        }
        source_versions["system_model"] = [
            {
                "artifact_id": str(sm_version.artifact_id),
                "version_id": str(sm_version.id),
                "version_number": sm_version.version_number,
            }
        ]

    payload: dict[str, Any] = {
        "sections": section_blocks,
        "based_on_srs": {
            "version_id": str(srs_version.id),
            "version_number": srs_version.version_number,
        },
        "based_on_system_model": based_on_sm,
        "status": "failed" if any_failed else "completed",
        "error_message": last_error,
    }

    artifact = await _get_data_model_artifact(db, project_id)
    if artifact is None:
        artifact = Artifact(
            project_id=project_id,
            artifact_type="data_model",
            display_id="DM-001",
            title="Data Model",
            content=payload,
            working_status="dirty",
            lifecycle_status="active",
        )
        db.add(artifact)
        await db.flush()
    else:
        artifact.content = payload
        artifact.updated_at = datetime.now(timezone.utc)

    version_number = await _next_version_number(db, artifact.id)
    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=version_number,
        parent_version_id=artifact.current_version_id,
        snapshot=payload,
        content_hash=_content_hash(payload),
        commit_message=f"DATA_MODEL v{version_number} generated",
        author_id="data_model_generator",
        source_artifact_versions=source_versions,
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
        f"DATA_MODEL 생성 완료: artifact_id={artifact.id}, version={version_number}"
    )
    return _to_response(artifact, version)


async def list_data_model(
    db: AsyncSession, project_id: uuid.UUID
) -> DataModelListResponse:
    artifact = await _get_data_model_artifact(db, project_id)
    if artifact is None:
        return DataModelListResponse(documents=[])

    versions = (
        await db.execute(
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact.id)
            .order_by(ArtifactVersion.version_number.desc())
        )
    ).scalars().all()

    return DataModelListResponse(
        documents=[_to_response(artifact, v) for v in versions]
    )


async def get_data_model(
    db: AsyncSession, project_id: uuid.UUID, data_model_id: uuid.UUID
) -> DataModelDocumentResponse:
    version = await db.get(ArtifactVersion, data_model_id)
    if version is None:
        raise AppException(404, "Data Model 문서를 찾을 수 없습니다.")
    artifact = await db.get(Artifact, version.artifact_id)
    if (
        artifact is None
        or artifact.project_id != project_id
        or artifact.artifact_type != "data_model"
    ):
        raise AppException(404, "Data Model 문서를 찾을 수 없습니다.")
    return _to_response(artifact, version)
