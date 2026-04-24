"""Artifact Governance 서비스 — Git-like 워크플로우.

상태 머신 (plan §1.2):

    [new] --POST--> dirty --stage+create_pr--> staged
                      ^                          |
                      |----- reject/close -------|
                      |
                merge |
                      v
                    clean --PATCH--> dirty

diff / propagate_changes 는 현재 최소 구현. step 7(DiffViewer) · step 9(Impact)
에서 확장 예정.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.artifact import (
    Artifact,
    ArtifactDependency,
    ArtifactVersion,
    ChangeEvent,
    PullRequest,
)
from src.models.project import Project
from src.schemas.api.artifact import (
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactType,
    ArtifactVersionListResponse,
    ArtifactVersionResponse,
    ChangeEventResponse,
    DiffFieldEntry,
    DiffResult,
    ImpactResponse,
    ImpactedArtifactRef,
    PullRequestListResponse,
    PullRequestResponse,
    WorkingStatus,
)

# display_id prefix — 새 artifact 생성 시 자동 번호용 기본값.
# record 타입은 artifact_record_svc 가 섹션 타입 기반 prefix(FR/QA/...)를
# 직접 계산하며, 이 매핑은 SRS/Design/TC 등 PR 워크플로우 직접 진입 타입용.
DISPLAY_PREFIX_BY_TYPE: dict[str, str] = {
    "record": "REC",
    "srs": "SRS",
    "design": "DSG",
    "testcase": "TC",
}


# ── 직렬화 헬퍼 ─────────────────────────────────────────────────────────────


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _uuid(value: uuid.UUID | None) -> str | None:
    return str(value) if value else None


def _to_artifact_response(
    artifact: Artifact,
    current_version_number: int | None = None,
) -> ArtifactResponse:
    return ArtifactResponse(
        artifact_id=str(artifact.id),
        project_id=str(artifact.project_id),
        artifact_type=artifact.artifact_type,  # type: ignore[arg-type]
        display_id=artifact.display_id,
        title=artifact.title,
        content=artifact.content,
        working_status=artifact.working_status,  # type: ignore[arg-type]
        lifecycle_status=artifact.lifecycle_status,  # type: ignore[arg-type]
        current_version_id=_uuid(artifact.current_version_id),
        current_version_number=current_version_number,
        open_pr_id=_uuid(artifact.open_pr_id),
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def _to_version_response(
    version: ArtifactVersion, artifact_type: str
) -> ArtifactVersionResponse:
    return ArtifactVersionResponse(
        version_id=str(version.id),
        artifact_id=str(version.artifact_id),
        artifact_type=artifact_type,  # type: ignore[arg-type]
        version_number=version.version_number,
        parent_version_id=_uuid(version.parent_version_id),
        snapshot=version.snapshot,
        content_hash=version.content_hash,
        commit_message=version.commit_message,
        author_id=version.author_id,
        committed_at=version.committed_at,
        merged_from_pr_id=_uuid(version.merged_from_pr_id),
    )


def _to_pr_response(pr: PullRequest, artifact_type: str, project_id: str) -> PullRequestResponse:
    return PullRequestResponse(
        pr_id=str(pr.id),
        project_id=project_id,
        artifact_id=str(pr.artifact_id),
        artifact_type=artifact_type,  # type: ignore[arg-type]
        base_version_id=_uuid(pr.base_version_id),
        head_version_id=str(pr.head_version_id),
        status=pr.status,  # type: ignore[arg-type]
        title=pr.title,
        description=pr.description,
        author_id=pr.author_id,
        reviewer_id=pr.reviewer_id,
        created_at=pr.created_at,
        reviewed_at=pr.reviewed_at,
        merged_at=pr.merged_at,
    )


# ── 내부 조회 유틸 ──────────────────────────────────────────────────────────


async def _require_artifact(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> Artifact:
    artifact = await db.get(Artifact, artifact_id)
    if not artifact or artifact.project_id != project_id:
        raise AppException(404, "산출물을 찾을 수 없습니다.")
    return artifact


async def _require_pr(db: AsyncSession, pr_id: uuid.UUID) -> PullRequest:
    pr = await db.get(PullRequest, pr_id)
    if not pr:
        raise AppException(404, "PR을 찾을 수 없습니다.")
    return pr


async def _assert_project_exists(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await db.get(Project, project_id)
    if not project:
        raise AppException(404, "프로젝트를 찾을 수 없습니다.")


async def _next_display_id(
    db: AsyncSession, project_id: uuid.UUID, artifact_type: str
) -> str:
    prefix = DISPLAY_PREFIX_BY_TYPE.get(artifact_type, artifact_type[:3].upper())
    stmt = select(Artifact.display_id).where(
        Artifact.project_id == project_id,
        Artifact.artifact_type == artifact_type,
        Artifact.display_id.like(f"{prefix}-%"),
    )
    existing = (await db.execute(stmt)).scalars().all()
    max_seq = 0
    for did in existing:
        try:
            seq = int(did.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            continue
        max_seq = max(max_seq, seq)
    return f"{prefix}-{max_seq + 1:03d}"


async def _version_number(db: AsyncSession, version_id: uuid.UUID | None) -> int | None:
    if version_id is None:
        return None
    version = await db.get(ArtifactVersion, version_id)
    return version.version_number if version else None


async def _next_version_number(db: AsyncSession, artifact_id: uuid.UUID) -> int:
    stmt = select(ArtifactVersion.version_number).where(
        ArtifactVersion.artifact_id == artifact_id
    )
    existing = (await db.execute(stmt)).scalars().all()
    return (max(existing) + 1) if existing else 1


async def _log_event(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID | None,
    action: str,
    actor: str,
    pr_id: uuid.UUID | None = None,
    version_id: uuid.UUID | None = None,
    diff_summary: dict | None = None,
    impact_summary: dict | None = None,
) -> ChangeEvent:
    event = ChangeEvent(
        project_id=project_id,
        artifact_id=artifact_id,
        pr_id=pr_id,
        version_id=version_id,
        action=action,
        actor=actor,
        diff_summary=diff_summary,
        impact_summary=impact_summary,
    )
    db.add(event)
    return event


# ── Artifact CRUD ──────────────────────────────────────────────────────────


async def list_artifacts(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    artifact_type: ArtifactType | None = None,
    working_status: WorkingStatus | None = None,
) -> ArtifactListResponse:
    stmt = (
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.lifecycle_status == "active",
        )
        .order_by(Artifact.created_at.asc())
    )
    if artifact_type:
        stmt = stmt.where(Artifact.artifact_type == artifact_type)
    if working_status:
        stmt = stmt.where(Artifact.working_status == working_status)

    artifacts = (await db.execute(stmt)).scalars().all()

    # 각 artifact 의 current_version_number 조회 — N+1 회피 위해 일괄 로드
    version_ids = [a.current_version_id for a in artifacts if a.current_version_id]
    version_map: dict[uuid.UUID, int] = {}
    if version_ids:
        v_stmt = select(ArtifactVersion.id, ArtifactVersion.version_number).where(
            ArtifactVersion.id.in_(version_ids)
        )
        version_map = {vid: vn for vid, vn in (await db.execute(v_stmt)).all()}

    items = [
        _to_artifact_response(
            a,
            current_version_number=version_map.get(a.current_version_id)
            if a.current_version_id
            else None,
        )
        for a in artifacts
    ]
    return ArtifactListResponse(artifacts=items, total=len(items))


async def get_artifact(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> ArtifactResponse:
    artifact = await _require_artifact(db, project_id, artifact_id)
    vn = await _version_number(db, artifact.current_version_id)
    return _to_artifact_response(artifact, current_version_number=vn)


async def create_draft(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    artifact_type: str,
    content: dict[str, Any],
    title: str | None = None,
    display_id: str | None = None,
    author_id: str = "system",
) -> ArtifactResponse:
    """새 artifact를 dirty 상태로 생성한다.

    생성 시점에는 아직 version 이 없으며, `current_version_id` 는 NULL.
    첫 merge 에서 version_number=1 스냅샷이 생성된다.
    """
    if artifact_type not in ("record", "srs", "design", "testcase"):
        raise AppException(400, f"지원하지 않는 artifact_type: {artifact_type}")

    await _assert_project_exists(db, project_id)

    resolved_display_id = display_id or await _next_display_id(db, project_id, artifact_type)

    artifact = Artifact(
        project_id=project_id,
        artifact_type=artifact_type,
        display_id=resolved_display_id,
        title=title,
        content=content,
        working_status="dirty",
        lifecycle_status="active",
    )
    db.add(artifact)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(409, "display_id 충돌") from exc

    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="created",
        actor=author_id,
    )
    await db.commit()
    await db.refresh(artifact)
    return _to_artifact_response(artifact, current_version_number=None)


async def update_working_copy(
    db: AsyncSession,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    *,
    content: dict[str, Any] | None = None,
    title: str | None = None,
    author_id: str = "system",
) -> ArtifactResponse:
    """working copy 편집 — staged 상태면 409."""
    artifact = await _require_artifact(db, project_id, artifact_id)

    if artifact.working_status == "staged":
        raise AppException(
            409,
            f"산출물이 PR에 의해 lock 중입니다 (open_pr_id={artifact.open_pr_id}).",
        )

    if content is not None:
        artifact.content = content
    if title is not None:
        artifact.title = title

    artifact.working_status = "dirty"
    artifact.updated_at = datetime.now(timezone.utc)

    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="edited",
        actor=author_id,
    )
    await db.commit()
    await db.refresh(artifact)
    vn = await _version_number(db, artifact.current_version_id)
    return _to_artifact_response(artifact, current_version_number=vn)


# ── PullRequest 라이프사이클 ────────────────────────────────────────────────


async def create_pr(
    db: AsyncSession,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    *,
    title: str,
    description: str | None = None,
    author_id: str = "system",
) -> PullRequestResponse:
    """dirty → staged 전환. 현재 content를 head_version 으로 스냅샷."""
    artifact = await _require_artifact(db, project_id, artifact_id)

    if artifact.working_status == "staged":
        raise AppException(
            409,
            f"이미 PR이 열려 있습니다 (open_pr_id={artifact.open_pr_id}).",
        )

    # head snapshot 기록
    version_number = await _next_version_number(db, artifact.id)
    head_version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=version_number,
        parent_version_id=artifact.current_version_id,
        snapshot=artifact.content,
        content_hash=_content_hash(artifact.content),
        commit_message=title,
        author_id=author_id,
    )
    db.add(head_version)
    await db.flush()

    pr = PullRequest(
        artifact_id=artifact.id,
        base_version_id=artifact.current_version_id,
        head_version_id=head_version.id,
        status="open",
        title=title,
        description=description,
        author_id=author_id,
    )
    db.add(pr)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(
            409, "해당 산출물에 이미 열린 PR이 존재합니다."
        ) from exc

    artifact.working_status = "staged"
    artifact.open_pr_id = pr.id
    artifact.updated_at = datetime.now(timezone.utc)

    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="pr_opened",
        actor=author_id,
        pr_id=pr.id,
        version_id=head_version.id,
    )
    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="staged",
        actor=author_id,
        pr_id=pr.id,
        version_id=head_version.id,
    )

    await db.commit()
    await db.refresh(pr)
    return _to_pr_response(pr, artifact.artifact_type, str(project_id))


async def approve_pr(
    db: AsyncSession,
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
    *,
    reviewer_id: str = "system",
) -> PullRequestResponse:
    pr = await _require_pr(db, pr_id)
    artifact = await _require_artifact(db, project_id, pr.artifact_id)

    if pr.status != "open":
        raise AppException(409, f"open 상태가 아닙니다 (status={pr.status}).")

    pr.status = "approved"
    pr.reviewer_id = reviewer_id
    pr.reviewed_at = datetime.now(timezone.utc)

    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="pr_approved",
        actor=reviewer_id,
        pr_id=pr.id,
        version_id=pr.head_version_id,
    )
    await db.commit()
    await db.refresh(pr)
    return _to_pr_response(pr, artifact.artifact_type, str(project_id))


async def reject_pr(
    db: AsyncSession,
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
    *,
    reviewer_id: str = "system",
    reason: str | None = None,
) -> PullRequestResponse:
    """reject: head_version 보존, working_status → dirty 복귀, open_pr_id 해제."""
    pr = await _require_pr(db, pr_id)
    artifact = await _require_artifact(db, project_id, pr.artifact_id)

    if pr.status not in ("open", "approved"):
        raise AppException(409, f"reject 불가 상태: {pr.status}")

    pr.status = "rejected"
    pr.reviewer_id = reviewer_id
    pr.reviewed_at = datetime.now(timezone.utc)

    artifact.working_status = "dirty"
    artifact.open_pr_id = None
    artifact.updated_at = datetime.now(timezone.utc)

    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="pr_rejected",
        actor=reviewer_id,
        pr_id=pr.id,
        version_id=pr.head_version_id,
        diff_summary={"reason": reason} if reason else None,
    )
    await db.commit()
    await db.refresh(pr)
    return _to_pr_response(pr, artifact.artifact_type, str(project_id))


async def merge_pr(
    db: AsyncSession,
    project_id: uuid.UUID,
    pr_id: uuid.UUID,
    *,
    merger_id: str = "system",
) -> PullRequestResponse:
    """merge: artifact.current_version_id → head_version_id, clean 복귀."""
    await _assert_project_exists(db, project_id)

    pr = await _require_pr(db, pr_id)
    artifact = await _require_artifact(db, project_id, pr.artifact_id)

    if pr.status not in ("open", "approved"):
        raise AppException(409, f"merge 불가 상태: {pr.status}")

    head_version = await db.get(ArtifactVersion, pr.head_version_id)
    if head_version is None:
        raise AppException(500, "head_version 이 유실되었습니다.")
    head_version.merged_from_pr_id = pr.id

    pr.status = "merged"
    pr.reviewer_id = pr.reviewer_id or merger_id
    pr.merged_at = datetime.now(timezone.utc)

    artifact.current_version_id = pr.head_version_id
    artifact.working_status = "clean"
    artifact.open_pr_id = None
    artifact.updated_at = datetime.now(timezone.utc)

    await _log_event(
        db,
        project_id=project_id,
        artifact_id=artifact.id,
        action="pr_merged",
        actor=merger_id,
        pr_id=pr.id,
        version_id=pr.head_version_id,
    )
    await db.commit()
    await db.refresh(pr)
    return _to_pr_response(pr, artifact.artifact_type, str(project_id))


async def list_prs(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    status: str | None = None,
) -> PullRequestListResponse:
    stmt = (
        select(PullRequest, Artifact.artifact_type)
        .join(Artifact, PullRequest.artifact_id == Artifact.id)
        .where(Artifact.project_id == project_id)
        .order_by(PullRequest.created_at.desc())
    )
    if status:
        stmt = stmt.where(PullRequest.status == status)

    rows = (await db.execute(stmt)).all()
    items = [_to_pr_response(pr, atype, str(project_id)) for pr, atype in rows]
    return PullRequestListResponse(pull_requests=items, total=len(items))


# ── Version / Diff ─────────────────────────────────────────────────────────


async def list_versions(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> ArtifactVersionListResponse:
    artifact = await _require_artifact(db, project_id, artifact_id)
    stmt = (
        select(ArtifactVersion)
        .where(ArtifactVersion.artifact_id == artifact_id)
        .order_by(ArtifactVersion.version_number.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return ArtifactVersionListResponse(
        versions=[_to_version_response(v, artifact.artifact_type) for v in rows]
    )


async def get_diff(
    db: AsyncSession,
    *,
    head_version_id: uuid.UUID,
    base_version_id: uuid.UUID | None = None,
) -> DiffResult:
    """Phase 2 step 3 최소 구현 — top-level 필드별 단순 비교.

    정식 diff(unified/deepdiff) 는 step 7에서 확장. 여기서는 프론트가
    DiffViewer 와 계약을 맞출 수 있도록 최소 entries 만 반환한다.
    """
    head = await db.get(ArtifactVersion, head_version_id)
    if head is None:
        raise AppException(404, "head 버전을 찾을 수 없습니다.")
    base = await db.get(ArtifactVersion, base_version_id) if base_version_id else None

    head_snapshot: dict[str, Any] = head.snapshot or {}
    base_snapshot: dict[str, Any] = base.snapshot if base else {}

    entries: list[DiffFieldEntry] = []
    all_keys = sorted(set(head_snapshot.keys()) | set(base_snapshot.keys()))
    for key in all_keys:
        before = base_snapshot.get(key) if base else None
        after = head_snapshot.get(key)
        if base is None:
            kind = "added"
        elif key not in base_snapshot:
            kind = "added"
        elif key not in head_snapshot:
            kind = "removed"
        elif before != after:
            kind = "modified"
        else:
            kind = "unchanged"
        entries.append(
            DiffFieldEntry(
                field_path=key,
                kind=kind,  # type: ignore[arg-type]
                before=before,
                after=after,
            )
        )

    return DiffResult(
        format="deepdiff",
        base_version_id=_uuid(base_version_id),
        head_version_id=str(head_version_id),
        entries=entries,
    )


# ── Impact (Step 9에서 확장) ───────────────────────────────────────────────


async def propagate_changes(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> ImpactResponse:
    """downstream BFS 1-hop. depth=2 확장은 step 9 에서."""
    artifact = await _require_artifact(db, project_id, artifact_id)

    stmt = (
        select(ArtifactDependency, Artifact)
        .join(Artifact, ArtifactDependency.downstream_artifact_id == Artifact.id)
        .where(ArtifactDependency.upstream_artifact_id == artifact.id)
    )
    rows = (await db.execute(stmt)).all()
    impacted = [
        ImpactedArtifactRef(
            artifact_id=str(downstream.id),
            artifact_type=downstream.artifact_type,  # type: ignore[arg-type]
            display_id=downstream.display_id,
            reason="upstream_version_bumped",
            pinned_version_number=None,
        )
        for _, downstream in rows
    ]
    return ImpactResponse(source_artifact_id=str(artifact_id), impacted=impacted)


# ── ChangeEvent (감사 로그 조회) ────────────────────────────────────────────


async def list_change_events(
    db: AsyncSession, project_id: uuid.UUID, *, artifact_id: uuid.UUID | None = None
) -> list[ChangeEventResponse]:
    stmt = (
        select(ChangeEvent)
        .where(ChangeEvent.project_id == project_id)
        .order_by(ChangeEvent.occurred_at.desc())
        .limit(200)
    )
    if artifact_id:
        stmt = stmt.where(ChangeEvent.artifact_id == artifact_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        ChangeEventResponse(
            event_id=str(e.id),
            project_id=str(e.project_id),
            artifact_id=_uuid(e.artifact_id),
            pr_id=_uuid(e.pr_id),
            version_id=_uuid(e.version_id),
            action=e.action,  # type: ignore[arg-type]
            actor=e.actor,
            diff_summary=e.diff_summary,
            impact_summary=e.impact_summary,
            occurred_at=e.occurred_at,
        )
        for e in rows
    ]
