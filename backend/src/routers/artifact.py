"""Artifact Governance API — plan §1.4 의 엔드포인트 계약과 1:1 대응."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.api.artifact import (
    ArtifactCreate,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactType,
    ArtifactUpdate,
    ArtifactVersionListResponse,
    DiffResult,
    ImpactResponse,
    PRStatus,
    PullRequestCreate,
    PullRequestListResponse,
    PullRequestReject,
    PullRequestResponse,
    WorkingStatus,
)
from src.services import artifact_svc


project_router = APIRouter(
    prefix="/api/v1/projects/{project_id}",
    tags=["artifacts"],
)


@project_router.get("/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    project_id: uuid.UUID,
    artifact_type: ArtifactType | None = Query(default=None),
    working_status: WorkingStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.list_artifacts(
        db, project_id, artifact_type=artifact_type, working_status=working_status
    )


@project_router.post("/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    project_id: uuid.UUID,
    body: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.create_draft(
        db,
        project_id,
        artifact_type=body.artifact_type,
        content=body.content,
        title=body.title,
        display_id=body.display_id,
    )


@project_router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.get_artifact(db, project_id, artifact_id)


@project_router.patch("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    body: ArtifactUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.update_working_copy(
        db, project_id, artifact_id, content=body.content, title=body.title
    )


@project_router.post(
    "/artifacts/{artifact_id}/prs",
    response_model=PullRequestResponse,
    status_code=201,
)
async def create_artifact_pr(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    body: PullRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.create_pr(
        db, project_id, artifact_id, title=body.title, description=body.description
    )


@project_router.get(
    "/artifacts/{artifact_id}/versions",
    response_model=ArtifactVersionListResponse,
)
async def list_versions(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.list_versions(db, project_id, artifact_id)


@project_router.get(
    "/artifacts/{artifact_id}/impact",
    response_model=ImpactResponse,
)
async def get_impact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.propagate_changes(db, project_id, artifact_id)


@project_router.get("/prs", response_model=PullRequestListResponse)
async def list_prs(
    project_id: uuid.UUID,
    status: PRStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.list_prs(db, project_id, status=status)


# 프로젝트 스코프 밖에서 동작하는 라우터 (version diff / PR actions) ─────
global_router = APIRouter(prefix="/api/v1", tags=["artifacts"])


@global_router.get("/versions/{version_id}/diff", response_model=DiffResult)
async def get_version_diff(
    version_id: uuid.UUID,
    against: uuid.UUID | None = Query(default=None, description="비교 대상 base version"),
    db: AsyncSession = Depends(get_db),
):
    return await artifact_svc.get_diff(
        db, head_version_id=version_id, base_version_id=against
    )


# PR-centric 액션은 project_id 가 DB 조회로 결정되므로 프로젝트 경로 밖에 둔다.
# plan §1.4 와 동일. 프로젝트 소유 검증은 서비스 내부에서 수행.
@global_router.post("/prs/{pr_id}/approve", response_model=PullRequestResponse)
async def approve_pr(
    pr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # 라우터 레벨에서 project_id 를 조회하여 svc 에 전달
    from src.models.artifact import Artifact, PullRequest

    pr = await db.get(PullRequest, pr_id)
    if pr is None:
        from src.core.exceptions import AppException

        raise AppException(404, "PR을 찾을 수 없습니다.")
    artifact = await db.get(Artifact, pr.artifact_id)
    return await artifact_svc.approve_pr(db, artifact.project_id, pr_id)


@global_router.post("/prs/{pr_id}/reject", response_model=PullRequestResponse)
async def reject_pr(
    pr_id: uuid.UUID,
    body: PullRequestReject | None = None,
    db: AsyncSession = Depends(get_db),
):
    from src.models.artifact import Artifact, PullRequest

    pr = await db.get(PullRequest, pr_id)
    if pr is None:
        from src.core.exceptions import AppException

        raise AppException(404, "PR을 찾을 수 없습니다.")
    artifact = await db.get(Artifact, pr.artifact_id)
    reason = body.reason if body else None
    return await artifact_svc.reject_pr(db, artifact.project_id, pr_id, reason=reason)


@global_router.post("/prs/{pr_id}/merge", response_model=PullRequestResponse)
async def merge_pr(
    pr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from src.models.artifact import Artifact, PullRequest

    pr = await db.get(PullRequest, pr_id)
    if pr is None:
        from src.core.exceptions import AppException

        raise AppException(404, "PR을 찾을 수 없습니다.")
    artifact = await db.get(Artifact, pr.artifact_id)
    return await artifact_svc.merge_pr(db, artifact.project_id, pr_id)


# main.py 에서 단일 심볼로 include 하도록 모아준다.
routers = (project_router, global_router)
__all__ = ["project_router", "global_router", "routers"]
