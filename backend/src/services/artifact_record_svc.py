"""Record-flavoured artifact 서비스 — `artifacts(artifact_type='record')` 전용.

공통 PR 라이프사이클은 `artifact_svc` 에, 도메인 관심사(섹션/지식문서 enrich,
추출 SSE, 일괄 승인, status 메타)는 이 파일에 둔다. Plan §2.1 의 타입별
어댑터 구조를 그대로 따른다 — SRS/Design/TestCase 어댑터는 동일 패턴으로
추후 추가 예정.

Artifact.content JSONB 페이로드:
  {
    "text": str,
    "section_id": str | None,
    "source_document_id": str | None,
    "source_location": str | None,
    "confidence_score": float | None,
    "is_auto_extracted": bool,
    "order_index": int,
    "metadata": {"status": "draft" | "approved" | "excluded"}
  }
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session
from src.core.exceptions import AppException
from src.models.artifact import Artifact
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.requirement import RequirementSection
from src.schemas.api.artifact_record import (
    ArtifactRecordApproveRequest,
    ArtifactRecordCreate,
    ArtifactRecordExtractedItem,
    ArtifactRecordExtractResponse,
    ArtifactRecordListResponse,
    ArtifactRecordReorderRequest,
    ArtifactRecordResponse,
    ArtifactRecordStatusUpdate,
    ArtifactRecordUpdate,
    RecordStatus,
)
from src.prompts.extraction import (
    build_document_extract_messages,
    build_user_text_extract_messages,
)
from src.services.llm_svc import chat_completion
from src.utils.json_parser import parse_llm_json
from src.utils.reorder import build_reordered_ids

DISPLAY_ID_PREFIX_MAP = {
    "overview": "OVR",
    "fr": "FR",
    "qa": "QA",
    "constraints": "CON",
    "interfaces": "IF",
    "other": "OTH",
}


# ── content 헬퍼 ────────────────────────────────────────────────────────────


def _payload(artifact: Artifact) -> dict[str, Any]:
    return artifact.content if isinstance(artifact.content, dict) else {}


def _build_content(
    *,
    text: str,
    section_id: uuid.UUID | None,
    source_document_id: uuid.UUID | None,
    source_location: str | None,
    confidence_score: float | None,
    is_auto_extracted: bool,
    order_index: int,
    status: RecordStatus,
) -> dict[str, Any]:
    return {
        "text": text,
        "section_id": str(section_id) if section_id else None,
        "source_document_id": str(source_document_id) if source_document_id else None,
        "source_location": source_location,
        "confidence_score": confidence_score,
        "is_auto_extracted": is_auto_extracted,
        "order_index": order_index,
        "metadata": {"status": status},
    }


def _uuid_or_none(raw: Any) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (ValueError, AttributeError):
        return None


def _status_of(artifact: Artifact) -> RecordStatus:
    meta = _payload(artifact).get("metadata") or {}
    status = meta.get("status")
    if status in ("draft", "approved", "excluded"):
        return status  # type: ignore[return-value]
    legacy = meta.get("legacy_status")
    if legacy in ("draft", "approved", "excluded"):
        return legacy  # type: ignore[return-value]
    return "approved"


def _order_index_expr():
    return cast(Artifact.content["order_index"].astext, Integer)


def _to_response(
    artifact: Artifact,
    *,
    section_name: str | None = None,
    source_document_name: str | None = None,
    current_version_number: int | None = None,
) -> ArtifactRecordResponse:
    c = _payload(artifact)
    return ArtifactRecordResponse(
        artifact_id=str(artifact.id),
        project_id=str(artifact.project_id),
        section_id=c.get("section_id"),
        section_name=section_name,
        content=c.get("text", ""),
        display_id=artifact.display_id,
        source_document_id=c.get("source_document_id"),
        source_document_name=source_document_name,
        source_location=c.get("source_location"),
        confidence_score=c.get("confidence_score"),
        status=_status_of(artifact),
        is_auto_extracted=bool(c.get("is_auto_extracted", False)),
        order_index=int(c.get("order_index") or 0),
        current_version_number=current_version_number,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


async def _enrich_names(
    db: AsyncSession, artifacts: list[Artifact]
) -> tuple[dict[str, str], dict[str, str]]:
    section_ids = {
        _payload(a).get("section_id") for a in artifacts if _payload(a).get("section_id")
    }
    doc_ids = {
        _payload(a).get("source_document_id")
        for a in artifacts
        if _payload(a).get("source_document_id")
    }

    section_map: dict[str, str] = {}
    if section_ids:
        rows = (
            await db.execute(
                select(RequirementSection.id, RequirementSection.name).where(
                    RequirementSection.id.in_(
                        [uuid.UUID(s) for s in section_ids if _uuid_or_none(s)]
                    )
                )
            )
        ).all()
        section_map = {str(sid): name for sid, name in rows}

    doc_map: dict[str, str] = {}
    if doc_ids:
        rows = (
            await db.execute(
                select(KnowledgeDocument.id, KnowledgeDocument.name).where(
                    KnowledgeDocument.id.in_(
                        [uuid.UUID(d) for d in doc_ids if _uuid_or_none(d)]
                    )
                )
            )
        ).all()
        doc_map = {str(did): name for did, name in rows}

    return section_map, doc_map


# ── display_id / order_index ───────────────────────────────────────────────


def _display_prefix(section_type: str) -> str:
    return DISPLAY_ID_PREFIX_MAP.get(section_type, section_type[:3].upper())


def _build_display_counters(display_ids: list[str]) -> dict[str, int]:
    counters: dict[str, int] = {}
    for did in display_ids:
        prefix, sep, tail = did.rpartition("-")
        if not sep or not prefix:
            continue
        try:
            seq = int(tail)
        except ValueError:
            continue
        counters[prefix] = max(counters.get(prefix, 0), seq)
    return counters


def _reserve_display_id(counters: dict[str, int], section_type: str) -> str:
    prefix = _display_prefix(section_type)
    next_seq = counters.get(prefix, 0) + 1
    counters[prefix] = next_seq
    return f"{prefix}-{next_seq:03d}"


async def _next_display_id(
    db: AsyncSession, project_id: uuid.UUID, section_type: str
) -> str:
    prefix = _display_prefix(section_type)
    stmt = select(Artifact.display_id).where(
        Artifact.project_id == project_id,
        Artifact.artifact_type == "record",
        Artifact.display_id.like(f"{prefix}-%"),
    )
    existing = (await db.execute(stmt)).scalars().all()
    counters = _build_display_counters(existing)
    return _reserve_display_id(counters, section_type)


async def _next_order_index(db: AsyncSession, project_id: uuid.UUID) -> int:
    max_idx = (
        await db.execute(
            select(func.max(_order_index_expr())).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "record",
            )
        )
    ).scalar()
    return (max_idx + 1) if max_idx is not None else 0


# ── 조회 ───────────────────────────────────────────────────────────────────


def _base_query(project_id: uuid.UUID, section_id: uuid.UUID | None = None):
    stmt = (
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.artifact_type == "record",
            Artifact.lifecycle_status != "deleted",
        )
        .order_by(_order_index_expr().asc().nullslast(), Artifact.created_at.asc())
    )
    if section_id:
        stmt = stmt.where(Artifact.content["section_id"].astext == str(section_id))
    return stmt


async def _load_sections_by_ids(
    db: AsyncSession, project_id: uuid.UUID, section_ids: set[uuid.UUID]
) -> dict[uuid.UUID, RequirementSection]:
    if not section_ids:
        return {}
    rows = (
        await db.execute(
            select(RequirementSection).where(
                RequirementSection.project_id == project_id,
                RequirementSection.id.in_(section_ids),
            )
        )
    ).scalars().all()
    sections = {s.id: s for s in rows}
    missing = section_ids - set(sections.keys())
    if missing:
        raise AppException(400, "유효하지 않은 섹션 ID가 포함되어 있습니다.")
    return sections


async def _load_documents_by_ids(
    db: AsyncSession, project_id: uuid.UUID, document_ids: set[uuid.UUID]
) -> dict[uuid.UUID, KnowledgeDocument]:
    if not document_ids:
        return {}
    rows = (
        await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.project_id == project_id,
                KnowledgeDocument.id.in_(document_ids),
            )
        )
    ).scalars().all()
    documents = {d.id: d for d in rows}
    missing = document_ids - set(documents.keys())
    if missing:
        raise AppException(400, "유효하지 않은 지식 문서 ID가 포함되어 있습니다.")
    return documents


async def _require_record(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> Artifact:
    artifact = await db.get(Artifact, artifact_id)
    if (
        artifact is None
        or artifact.project_id != project_id
        or artifact.artifact_type != "record"
        or artifact.lifecycle_status == "deleted"
    ):
        raise AppException(404, "레코드를 찾을 수 없습니다.")
    return artifact


# ── CRUD ───────────────────────────────────────────────────────────────────


async def list_records(
    db: AsyncSession, project_id: uuid.UUID, section_id: uuid.UUID | None = None,
) -> ArtifactRecordListResponse:
    rows = (await db.execute(_base_query(project_id, section_id))).scalars().all()
    section_map, doc_map = await _enrich_names(db, list(rows))

    # current_version_number 일괄 조회 — N+1 회피.
    from src.models.artifact import ArtifactVersion as _AV
    version_ids = [a.current_version_id for a in rows if a.current_version_id]
    version_map: dict = {}
    if version_ids:
        v_rows = (
            await db.execute(
                select(_AV.id, _AV.version_number).where(_AV.id.in_(version_ids))
            )
        ).all()
        version_map = {vid: vn for vid, vn in v_rows}

    records = [
        _to_response(
            a,
            section_name=section_map.get(_payload(a).get("section_id") or ""),
            source_document_name=doc_map.get(_payload(a).get("source_document_id") or ""),
            current_version_number=(
                version_map.get(a.current_version_id) if a.current_version_id else None
            ),
        )
        for a in rows
    ]
    return ArtifactRecordListResponse(records=records, total=len(records))


async def create_record(
    db: AsyncSession, project_id: uuid.UUID, data: ArtifactRecordCreate,
) -> ArtifactRecordResponse:
    section_type = "other"
    section_name: str | None = None
    if data.section_id:
        sections = await _load_sections_by_ids(db, project_id, {data.section_id})
        section_type = sections[data.section_id].type
        section_name = sections[data.section_id].name
    doc_name: str | None = None
    if data.source_document_id:
        docs = await _load_documents_by_ids(db, project_id, {data.source_document_id})
        doc_name = docs[data.source_document_id].name

    display_id = await _next_display_id(db, project_id, section_type)
    order_index = await _next_order_index(db, project_id)

    artifact = Artifact(
        project_id=project_id,
        artifact_type="record",
        display_id=display_id,
        content=_build_content(
            text=data.content,
            section_id=data.section_id,
            source_document_id=data.source_document_id,
            source_location=data.source_location,
            # 수동 입력은 사용자가 직접 신뢰도를 적은 경우만 보존 (보통 None).
            confidence_score=data.confidence_score,
            is_auto_extracted=False,
            order_index=order_index,
            status="draft",
        ),
        working_status="dirty",
        lifecycle_status="active",
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return _to_response(artifact, section_name=section_name, source_document_name=doc_name)


async def update_record(
    db: AsyncSession,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    data: ArtifactRecordUpdate,
) -> ArtifactRecordResponse:
    artifact = await _require_record(db, project_id, artifact_id)

    update_data = data.model_dump(exclude_unset=True)
    payload = dict(_payload(artifact))

    if "content" in update_data and update_data["content"] is not None:
        payload["text"] = update_data["content"]

    if "section_id" in update_data:
        new_section = update_data["section_id"]
        if new_section is not None:
            await _load_sections_by_ids(db, project_id, {new_section})
            payload["section_id"] = str(new_section)
        else:
            payload["section_id"] = None

    artifact.content = payload
    artifact.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(artifact)

    section_map, doc_map = await _enrich_names(db, [artifact])
    return _to_response(
        artifact,
        section_name=section_map.get(_payload(artifact).get("section_id") or ""),
        source_document_name=doc_map.get(
            _payload(artifact).get("source_document_id") or ""
        ),
    )


async def update_record_status(
    db: AsyncSession,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    data: ArtifactRecordStatusUpdate,
) -> ArtifactRecordResponse:
    artifact = await _require_record(db, project_id, artifact_id)
    payload = dict(_payload(artifact))
    meta = dict(payload.get("metadata") or {})
    meta["status"] = data.status
    payload["metadata"] = meta
    artifact.content = payload
    artifact.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(artifact)

    section_map, doc_map = await _enrich_names(db, [artifact])
    return _to_response(
        artifact,
        section_name=section_map.get(_payload(artifact).get("section_id") or ""),
        source_document_name=doc_map.get(
            _payload(artifact).get("source_document_id") or ""
        ),
    )


async def delete_record(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID,
) -> None:
    artifact = await _require_record(db, project_id, artifact_id)
    artifact.lifecycle_status = "deleted"
    artifact.updated_at = datetime.now(timezone.utc)
    await db.commit()


async def reorder_records(
    db: AsyncSession, project_id: uuid.UUID, data: ArtifactRecordReorderRequest,
) -> int:
    if not data.ordered_ids:
        return 0

    rows = (await db.execute(_base_query(project_id))).scalars().all()
    by_id = {a.id: a for a in rows}
    current_ids = [a.id for a in rows]
    reordered_ids = build_reordered_ids(data.ordered_ids, current_ids)

    now = datetime.now(timezone.utc)
    updated = 0
    for idx, aid in enumerate(reordered_ids):
        a = by_id.get(aid)
        if not a:
            continue
        current_idx = int(_payload(a).get("order_index") or 0)
        if current_idx != idx:
            payload = dict(_payload(a))
            payload["order_index"] = idx
            a.content = payload
            a.updated_at = now
            updated += 1

    await db.commit()
    return updated


# ── 추출 / 승인 ────────────────────────────────────────────────────────────


async def extract_records(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_id: uuid.UUID | None = None,
    *,
    user_text: str | None = None,
) -> ArtifactRecordExtractResponse:
    """프로젝트 record 후보를 LLM 으로 추출.

    두 가지 모드:
      - **document** (`user_text=None`, default): 활성 지식 문서 청크에서
        섹션별 후보를 추출. 활성 섹션 + 활성 지식 문서 모두 필요.
      - **user_text** (`user_text=<자유 입력>`): 사용자가 채팅에 직접 적은
        텍스트를 한 문장 = 한 후보로 분해. 활성 섹션만 필요 (지식 문서 불요).
        `source_document_id` 는 None, `source_location` 은 "user_input".
    """
    mode = "user_text" if user_text else "document"
    logger.info(
        f"레코드 추출 시작: project_id={project_id}, section_id={section_id}, mode={mode}"
    )

    sect_stmt = (
        select(RequirementSection)
        .where(
            RequirementSection.project_id == project_id,
            RequirementSection.is_active == True,  # noqa: E712
        )
        .order_by(RequirementSection.order_index)
    )
    if section_id:
        sect_stmt = sect_stmt.where(RequirementSection.id == section_id)

    sections = (await db.execute(sect_stmt)).scalars().all()
    if not sections:
        raise AppException(400, "활성 섹션이 없습니다.")

    glossary_result = await db.execute(
        select(GlossaryItem.term, GlossaryItem.definition).where(
            GlossaryItem.project_id == project_id,
            GlossaryItem.is_approved == True,  # noqa: E712
        )
    )
    glossary_items = glossary_result.all()
    glossary_text = (
        "\n".join(f"- {t}: {d}" for t, d in glossary_items) if glossary_items else "(없음)"
    )

    sections_text = "\n".join(
        f"- {s.name} (type: {s.type}): {s.description or '설명 없음'}"
        + (f" [출력 형식: {s.output_format_hint}]" if s.output_format_hint else "")
        for s in sections
    )

    section_ids_map = {s.name: {"id": str(s.id), "type": s.type} for s in sections}

    if mode == "user_text":
        assert user_text is not None
        doc_map: dict[str, dict] = {}
        messages = build_user_text_extract_messages(
            sections_text=sections_text,
            glossary_text=glossary_text,
            user_text=user_text,
        )
        max_tokens = 2048
    else:
        chunk_stmt = (
            select(KnowledgeChunk.content, KnowledgeDocument.id, KnowledgeDocument.name)
            .join(
                KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
            )
            .where(
                KnowledgeDocument.project_id == project_id,
                KnowledgeDocument.is_active == True,  # noqa: E712
                KnowledgeDocument.status == "completed",
            )
            .order_by(KnowledgeDocument.id, KnowledgeChunk.chunk_index)
        )
        rows = (await db.execute(chunk_stmt)).all()
        if not rows:
            raise AppException(400, "활성 지식 문서가 없습니다.")

        doc_map = {}
        for content, doc_id, doc_name in rows:
            did = str(doc_id)
            if did not in doc_map:
                doc_map[did] = {"name": doc_name, "chunks": []}
            doc_map[did]["chunks"].append(content)

        document_text = "\n\n".join(
            f"[문서: {info['name']}]\n" + "\n".join(info["chunks"][:20])
            for info in doc_map.values()
        )

        messages = build_document_extract_messages(
            sections_text=sections_text,
            glossary_text=glossary_text,
            document_text=document_text,
        )
        max_tokens = 8192

    raw = await chat_completion(messages, temperature=0.2, max_completion_tokens=max_tokens)
    parsed = parse_llm_json(raw, error_msg="LLM 응답 파싱 실패")
    items = parsed.get("records", [])

    candidates = []
    for item in items:
        sec_name = item.get("section_name", "")
        sec_info = section_ids_map.get(sec_name, {})
        src_doc_name = item.get("source_document", "")
        src_doc_id: str | None = None
        for did, info in doc_map.items():
            if info["name"] == src_doc_name:
                src_doc_id = did
                break

        candidates.append(
            ArtifactRecordExtractedItem(
                content=item.get("content", ""),
                section_id=sec_info.get("id"),
                section_name=sec_name,
                source_document_id=src_doc_id,
                source_document_name=src_doc_name or None,
                source_location=item.get("source_location"),
                confidence_score=item.get("confidence"),
            )
        )

    logger.info(f"레코드 추출 완료: {len(candidates)}개 후보 (mode={mode})")
    return ArtifactRecordExtractResponse(candidates=candidates)


def _sse(event_type: str, payload: dict | None = None) -> str:
    data = {"type": event_type}
    if payload:
        data.update(payload)
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_extract_records(
    project_id: uuid.UUID,
    section_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """추출 SSE 스트리밍 — heartbeat 로 프록시 keep-alive 유지."""
    HEARTBEAT_INTERVAL = 2.0

    try:
        yield _sse("progress", {"stage": "start", "message": "레코드 추출을 시작합니다"})

        async with async_session() as db:
            extract_task = asyncio.create_task(extract_records(db, project_id, section_id))
            try:
                while not extract_task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(extract_task), timeout=HEARTBEAT_INTERVAL
                        )
                    except asyncio.TimeoutError:
                        yield _sse(
                            "progress",
                            {"stage": "llm", "message": "LLM이 응답을 생성하고 있습니다"},
                        )
                result: ArtifactRecordExtractResponse = extract_task.result()
            finally:
                if not extract_task.done():
                    extract_task.cancel()
                    with suppress(asyncio.CancelledError, Exception):
                        await extract_task

        yield _sse(
            "done",
            {"candidates": [c.model_dump(mode="json") for c in result.candidates]},
        )
    except AppException as e:
        yield _sse("error", {"message": e.detail, "status": e.status_code})
    except Exception as e:  # noqa: BLE001
        logger.exception("레코드 추출 스트리밍 실패")
        yield _sse("error", {"message": str(e) or "레코드 추출에 실패했습니다"})


async def approve_records(
    db: AsyncSession, project_id: uuid.UUID, data: ArtifactRecordApproveRequest,
) -> ArtifactRecordListResponse:
    """추출된 candidate 를 일괄 Artifact 로 등록 (status='approved')."""
    logger.info(f"레코드 승인: project_id={project_id}, count={len(data.items)}")

    if not data.items:
        return ArtifactRecordListResponse(records=[], total=0)

    section_ids = {item.section_id for item in data.items if item.section_id is not None}
    sections = await _load_sections_by_ids(db, project_id, section_ids)
    source_document_ids = {
        item.source_document_id
        for item in data.items
        if item.source_document_id is not None
    }
    await _load_documents_by_ids(db, project_id, source_document_ids)

    existing_display_ids = (
        await db.execute(
            select(Artifact.display_id).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "record",
            )
        )
    ).scalars().all()
    display_counters = _build_display_counters(existing_display_ids)

    order_index = await _next_order_index(db, project_id)
    created: list[Artifact] = []
    for item_data in data.items:
        section_type = (
            sections[item_data.section_id].type
            if item_data.section_id is not None
            else "other"
        )
        display_id = _reserve_display_id(display_counters, section_type)
        artifact = Artifact(
            project_id=project_id,
            artifact_type="record",
            display_id=display_id,
            content=_build_content(
                text=item_data.content,
                section_id=item_data.section_id,
                source_document_id=item_data.source_document_id,
                source_location=item_data.source_location,
                confidence_score=item_data.confidence_score,
                is_auto_extracted=True,
                order_index=order_index,
                status="approved",
            ),
            working_status="dirty",
            lifecycle_status="active",
        )
        db.add(artifact)
        created.append(artifact)
        order_index += 1

    await db.commit()
    for a in created:
        await db.refresh(a)

    section_map, doc_map = await _enrich_names(db, created)
    records = [
        _to_response(
            a,
            section_name=section_map.get(_payload(a).get("section_id") or ""),
            source_document_name=doc_map.get(_payload(a).get("source_document_id") or ""),
        )
        for a in created
    ]
    return ArtifactRecordListResponse(records=records, total=len(records))


# ── agent tool / search ────────────────────────────────────────────────────


async def get_record_by_display_id(
    db: AsyncSession, project_id: uuid.UUID, display_id: str,
) -> Artifact | None:
    stmt = select(Artifact).where(
        Artifact.project_id == project_id,
        Artifact.artifact_type == "record",
        Artifact.lifecycle_status != "deleted",
        Artifact.display_id == display_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def search_records(
    db: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    section_name: str | None = None,
    limit: int = 10,
) -> list[ArtifactRecordResponse]:
    stmt = (
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.artifact_type == "record",
            Artifact.lifecycle_status != "deleted",
        )
        .order_by(_order_index_expr().asc().nullslast(), Artifact.created_at.asc())
        .limit(limit)
    )

    if section_name:
        sec_stmt = select(RequirementSection.id).where(
            RequirementSection.project_id == project_id,
            RequirementSection.name.ilike(f"%{section_name}%"),
        )
        section_ids = [str(sid) for sid, in (await db.execute(sec_stmt)).all()]
        if not section_ids:
            return []
        stmt = stmt.where(Artifact.content["section_id"].astext.in_(section_ids))

    stmt = stmt.where(
        Artifact.display_id.ilike(f"%{query}%")
        | Artifact.content["text"].astext.ilike(f"%{query}%")
    )

    rows = (await db.execute(stmt)).scalars().all()
    section_map, doc_map = await _enrich_names(db, list(rows))
    return [
        _to_response(
            a,
            section_name=section_map.get(_payload(a).get("section_id") or ""),
            source_document_name=doc_map.get(_payload(a).get("source_document_id") or ""),
        )
        for a in rows
    ]


async def get_section_by_name(
    db: AsyncSession, project_id: uuid.UUID, section_name: str,
) -> RequirementSection | None:
    stmt = select(RequirementSection).where(
        RequirementSection.project_id == project_id,
        RequirementSection.name.ilike(f"%{section_name}%"),
        RequirementSection.is_active == True,  # noqa: E712
    )
    return (await db.execute(stmt)).scalars().first()
