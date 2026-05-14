"""Impact / Stale 분석 서비스.

알고리즘 (PLAN §F.1):
1. 프로젝트의 모든 active artifact 와 current_version_id 의 version_number 일괄 조회
   → snapshot_map: {artifact_id: (artifact_type, display_id, current_version_number)}
2. 각 artifact 의 current_version 의 source_artifact_versions 를 검사
3. lineage entry (source_artifact_id, referenced_version) 와
   snapshot_map[source_artifact_id].current_version_number 비교
4. referenced_version < current 면 stale, reason 누적
5. stale_reasons 가 1개 이상이면 ImpactedArtifact 로 응답

새 record/SRS 가 ArtifactDependency 그래프 외부에서 추가되어도, source_artifact_versions
JSONB 안에 들어 있는 모든 입력만 검사하므로 grand-parent 까지 자동 전파된다 (record 변경 →
SRS stale, SRS stale 자체는 별도 검출 — Design/TC 의 source 인 SRS 의 current_version_number
가 lineage 의 그것보다 크면 Design/TC 도 stale).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.artifact import Artifact, ArtifactDependency, ArtifactVersion
from src.schemas.api.impact import (
    ImpactApplyEntry,
    ImpactApplyResponse,
    ImpactedArtifact,
    ImpactResponse,
    StaleReason,
)


async def get_project_impact(
    db: AsyncSession, project_id: uuid.UUID
) -> ImpactResponse:
    # 1. 프로젝트의 모든 active artifact + current_version_id
    artifacts = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalars().all()

    if not artifacts:
        return ImpactResponse(stale=[])

    # 2. 모든 current_version 일괄 조회 → version_number, source_artifact_versions
    version_ids = [a.current_version_id for a in artifacts if a.current_version_id]
    versions: dict[uuid.UUID, ArtifactVersion] = {}
    if version_ids:
        rows = (
            await db.execute(
                select(ArtifactVersion).where(ArtifactVersion.id.in_(version_ids))
            )
        ).scalars().all()
        versions = {v.id: v for v in rows}

    # 3. snapshot_map for fast lookup
    snapshot_map: dict[
        str, dict[str, Any]
    ] = {}  # artifact_id_str -> {type, display_id, current_vn}
    for a in artifacts:
        current_vn: int | None = None
        if a.current_version_id and a.current_version_id in versions:
            current_vn = versions[a.current_version_id].version_number
        snapshot_map[str(a.id)] = {
            "type": a.artifact_type,
            "display_id": a.display_id,
            "current_vn": current_vn,
        }

    # 4. 각 artifact 검사
    stale_list: list[ImpactedArtifact] = []
    for a in artifacts:
        if a.current_version_id is None:
            continue
        v = versions.get(a.current_version_id)
        if v is None:
            continue
        lineage = v.source_artifact_versions
        if not isinstance(lineage, dict) or not lineage:
            # lineage 가 비어있으면 artifact_type 기반 fallback:
            # testcase/design → SRS, srs → record 를 자동 추론
            lineage = _infer_lineage(a.artifact_type, snapshot_map)
            if not lineage:
                continue

        reasons: list[StaleReason] = []
        for kind, entries in lineage.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                source_id = entry.get("artifact_id")
                if not isinstance(source_id, str):
                    continue
                ref_vn_raw = entry.get("version_number")
                ref_vn = (
                    int(ref_vn_raw) if isinstance(ref_vn_raw, (int, float)) else None
                )
                section_id = entry.get("section_id")

                snap = snapshot_map.get(source_id)
                if snap is None:
                    # source artifact 자체가 사라짐 → 구조적 stale
                    reasons.append(
                        StaleReason(
                            source_artifact_id=source_id,
                            source_artifact_type=str(kind),
                            source_display_id=None,
                            referenced_version=ref_vn,
                            current_version=None,
                            section_id=section_id,
                        )
                    )
                    continue

                current_vn = snap.get("current_vn")
                if current_vn is None:
                    # source 가 아직 첫 version 도 안 만들어짐 → 비교 보류
                    continue
                if ref_vn is None:
                    # 우리는 lineage 에 version 을 명시하지 않은 상태
                    # (record draft 시점) — current 와 다를 수 있으므로 stale 후보
                    reasons.append(
                        StaleReason(
                            source_artifact_id=source_id,
                            source_artifact_type=str(snap["type"]),
                            source_display_id=str(snap["display_id"]),
                            referenced_version=None,
                            current_version=int(current_vn),
                            section_id=section_id,
                        )
                    )
                    continue
                if int(current_vn) > ref_vn:
                    reasons.append(
                        StaleReason(
                            source_artifact_id=source_id,
                            source_artifact_type=str(snap["type"]),
                            source_display_id=str(snap["display_id"]),
                            referenced_version=ref_vn,
                            current_version=int(current_vn),
                            section_id=section_id,
                        )
                    )

        if reasons:
            stale_list.append(
                ImpactedArtifact(
                    artifact_id=str(a.id),
                    artifact_type=a.artifact_type,
                    display_id=a.display_id,
                    current_version_number=snapshot_map[str(a.id)]["current_vn"],
                    stale_reasons=reasons,
                )
            )

    # 5. ArtifactDependency 기반 역방향 cascade
    # 이미 stale로 감지된 artifact들의 downstream을 추가로 탐지
    stale_ids = {s.artifact_id for s in stale_list}
    visited = set(stale_ids)  # 무한 루프 방지
    frontier = list(stale_ids)

    while frontier:
        next_frontier: list[str] = []
        dep_rows = (
            await db.execute(
                select(ArtifactDependency).where(
                    ArtifactDependency.upstream_artifact_id.in_(
                        [uuid.UUID(fid) for fid in frontier]
                    )
                )
            )
        ).scalars().all()

        for dep in dep_rows:
            ds_id = str(dep.downstream_artifact_id)
            if ds_id in visited:
                continue
            visited.add(ds_id)
            ds_snap = snapshot_map.get(ds_id)
            if ds_snap is None:
                continue

            us_snap = snapshot_map.get(str(dep.upstream_artifact_id))
            stale_list.append(
                ImpactedArtifact(
                    artifact_id=ds_id,
                    artifact_type=ds_snap["type"],
                    display_id=ds_snap["display_id"],
                    current_version_number=ds_snap.get("current_vn"),
                    stale_reasons=[
                        StaleReason(
                            source_artifact_id=str(dep.upstream_artifact_id),
                            source_artifact_type=us_snap["type"] if us_snap else "unknown",
                            source_display_id=us_snap["display_id"] if us_snap else None,
                            referenced_version=None,
                            current_version=None,
                        )
                    ],
                )
            )
            next_frontier.append(ds_id)

        frontier = next_frontier

    return ImpactResponse(stale=stale_list)


def _infer_lineage(
    artifact_type: str,
    snapshot_map: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """source_artifact_versions 가 비어있을 때 artifact_type 기반으로 lineage 를 추론.

    testcase/design → 같은 프로젝트의 SRS artifact 를 upstream 으로 간주.
    현재 SRS 의 current_vn 을 referenced_version 으로 설정하여,
    이후 SRS 가 재생성되면 current_vn > ref_vn 이 되어 stale 로 감지됨.
    """
    UPSTREAM_MAP: dict[str, str] = {
        "testcase": "srs",
        "design": "srs",
    }
    upstream_type = UPSTREAM_MAP.get(artifact_type)
    if not upstream_type:
        return {}

    entries: list[dict[str, Any]] = []
    for aid_str, snap in snapshot_map.items():
        if snap["type"] == upstream_type:
            entries.append({
                "artifact_id": aid_str,
                "version_number": snap.get("current_vn"),
            })

    if not entries:
        return {}
    return {upstream_type: entries}


# ─── Phase G: 자동 재생성 ────────────────────────────────────────────────────


# 순환 import 회피 — 함수 내부에서 import.


async def apply_regeneration(
    session_factory: Any,
    project_id: uuid.UUID,
    artifact_ids: list[str] | None = None,
) -> ImpactApplyResponse:
    """선택된(또는 전체) stale artifact 를 일괄 재생성.

    session_factory 를 받아 각 재생성 작업마다 새로운 단명 DB 세션을
    사용한다. 긴 LLM 호출 후 커넥션이 닫히는 문제를 방지한다.

    동작:
    - artifact_ids 가 비어 있으면 get_project_impact() 결과의 stale 전체를 대상.
    - artifact_type 별 분기:
      * srs   → srs_svc.generate_srs (새 ArtifactVersion + clean)
      * design→ design_svc.generate_design
      * record → 자동 재생성 미지원 (skip)
      * testcase → regenerate_all_testcases (1회만 실행)
    - 각 항목 결과를 regenerated/skipped/failed 로 분류해 반환.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from src.services import design_svc, srs_svc  # 지연 import — 순환 회피

    sf: async_sessionmaker[AsyncSession] = session_factory

    # Phase 1: 대상 결정 (단명 세션)
    target_ids: list[uuid.UUID] = []
    artifact_map: dict[uuid.UUID, Artifact] = {}

    async with sf() as db:
        if artifact_ids:
            for s in artifact_ids:
                try:
                    target_ids.append(uuid.UUID(s))
                except (ValueError, AttributeError):
                    continue
        else:
            impact = await get_project_impact(db, project_id)
            target_ids = [uuid.UUID(item.artifact_id) for item in impact.stale]

        if not target_ids:
            return ImpactApplyResponse()

        rows = (
            await db.execute(
                select(Artifact).where(
                    Artifact.project_id == project_id,
                    Artifact.id.in_(target_ids),
                )
            )
        ).scalars().all()
        artifact_map = {a.id: a for a in rows}
        await db.commit()

    if not target_ids:
        return ImpactApplyResponse()

    response = ImpactApplyResponse()

    # Phase 2: 각 재생성 작업마다 독립 세션 사용
    for aid in target_ids:
        artifact = artifact_map.get(aid)
        if artifact is None:
            response.failed.append(
                ImpactApplyEntry(
                    artifact_id=str(aid),
                    artifact_type="unknown",
                    error="대상 산출물을 찾을 수 없습니다.",
                )
            )
            continue

        kind = artifact.artifact_type

        # 자동 재생성 미지원 타입은 skip
        if kind == "record":
            response.skipped.append(
                ImpactApplyEntry(
                    artifact_id=str(aid),
                    artifact_type=kind,
                    display_id=artifact.display_id,
                    skipped_reason=(
                        "record 는 자동 재생성을 지원하지 않습니다. "
                        "수동으로 편집 후 PR 머지하세요."
                    ),
                )
            )
            continue

        # TC는 전체 일괄 재생성 — 중복 실행 방지
        if kind == "testcase" and any(
            r.artifact_type == "testcase" for r in response.regenerated
        ):
            response.skipped.append(
                ImpactApplyEntry(
                    artifact_id=str(aid),
                    artifact_type=kind,
                    display_id=artifact.display_id,
                    skipped_reason="TC 일괄 재생성이 이미 실행됨",
                )
            )
            continue

        try:
            async with sf() as db:
                if kind == "srs":
                    doc = await srs_svc.generate_srs(db, project_id)
                    response.regenerated.append(
                        ImpactApplyEntry(
                            artifact_id=str(aid),
                            artifact_type=kind,
                            display_id=artifact.display_id,
                            new_version_id=doc.srs_id,
                            new_version_number=doc.version,
                        )
                    )
                elif kind == "design":
                    doc = await design_svc.generate_design(db, project_id)
                    response.regenerated.append(
                        ImpactApplyEntry(
                            artifact_id=str(aid),
                            artifact_type=kind,
                            display_id=artifact.display_id,
                            new_version_id=doc.design_id,
                            new_version_number=doc.version,
                        )
                    )
                elif kind == "testcase":
                    from src.services import testcase_svc  # 지연 import

                    tc_resp = await testcase_svc.regenerate_all_testcases(
                        db, project_id
                    )
                    response.regenerated.append(
                        ImpactApplyEntry(
                            artifact_id=str(aid),
                            artifact_type=kind,
                            display_id=f"TC {len(tc_resp.testcases)}건 재생성",
                            new_version_id=None,
                            new_version_number=None,
                        )
                    )
                else:
                    response.skipped.append(
                        ImpactApplyEntry(
                            artifact_id=str(aid),
                            artifact_type=kind,
                            display_id=artifact.display_id,
                            skipped_reason=f"지원되지 않는 artifact_type: {kind}",
                        )
                    )
        except AppException as exc:
            response.failed.append(
                ImpactApplyEntry(
                    artifact_id=str(aid),
                    artifact_type=kind,
                    display_id=artifact.display_id,
                    error=str(exc.detail),
                )
            )
        except Exception as exc:  # pragma: no cover — defensive
            response.failed.append(
                ImpactApplyEntry(
                    artifact_id=str(aid),
                    artifact_type=kind,
                    display_id=artifact.display_id,
                    error=str(exc)[:200],
                )
            )

    return response

