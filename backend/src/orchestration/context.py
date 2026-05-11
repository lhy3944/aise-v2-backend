"""Project context snapshot for supervisor routing.

The supervisor should decide from current project state, not only keywords.
This module builds a compact, JSON-serializable snapshot that can be placed
in prompts and persisted in AgentState.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.artifact import Artifact, ArtifactVersion
from src.models.knowledge import KnowledgeDocument
from src.models.project import Project
from src.models.requirement import RequirementSection


class SectionSnapshot(BaseModel):
    section_id: str
    name: str
    type: str


class ArtifactTypeSnapshot(BaseModel):
    count: int = 0
    latest_version: int | None = None
    working_status_counts: dict[str, int] = Field(default_factory=dict)


class LockedArtifactSnapshot(BaseModel):
    artifact_id: str
    artifact_type: str
    display_id: str
    open_pr_id: str | None = None


class ProjectContextSnapshot(BaseModel):
    project_id: str
    project_name: str | None = None
    active_document_count: int = 0
    active_section_count: int = 0
    active_sections: list[SectionSnapshot] = Field(default_factory=list)
    active_record_count: int = 0
    record_status_counts: dict[str, int] = Field(default_factory=dict)
    artifacts: dict[str, ArtifactTypeSnapshot] = Field(default_factory=dict)
    locked_artifacts: list[LockedArtifactSnapshot] = Field(default_factory=list)
    readiness: dict[str, bool] = Field(default_factory=dict)
    recent_conversation: str = ""


def _payload(artifact: Artifact) -> dict[str, Any]:
    return artifact.content if isinstance(artifact.content, dict) else {}


def _recent_conversation(history: list[dict[str, Any]] | None) -> str:
    if not history:
        return "(no prior turns)"
    lines: list[str] = []
    for turn in history[-6:]:
        role = str(turn.get("role") or "user")
        content = str(turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content[:240]}")
    return "\n".join(lines) if lines else "(no prior turns)"


async def build_project_context_snapshot(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    history: list[dict[str, Any]] | None = None,
) -> ProjectContextSnapshot:
    project = await db.get(Project, project_id)

    sections = (
        await db.execute(
            select(RequirementSection)
            .where(
                RequirementSection.project_id == project_id,
                RequirementSection.is_active == True,  # noqa: E712
            )
            .order_by(RequirementSection.order_index.asc())
        )
    ).scalars().all()

    active_doc_count = (
        await db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.project_id == project_id,
                KnowledgeDocument.is_active == True,  # noqa: E712
                KnowledgeDocument.status == "completed",
            )
        )
    ).scalar() or 0

    artifact_rows = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalars().all()

    artifacts: dict[str, ArtifactTypeSnapshot] = {
        kind: ArtifactTypeSnapshot()
        for kind in ("record", "srs", "design", "testcase")
    }
    active_artifact_ids_by_type: dict[str, list[uuid.UUID]] = {}
    record_status_counts: dict[str, int] = {}
    locked_artifacts: list[LockedArtifactSnapshot] = []

    for artifact in artifact_rows:
        kind = artifact.artifact_type
        if kind not in artifacts:
            artifacts[kind] = ArtifactTypeSnapshot()
        stats = artifacts[kind]
        stats.count += 1
        stats.working_status_counts[artifact.working_status] = (
            stats.working_status_counts.get(artifact.working_status, 0) + 1
        )
        active_artifact_ids_by_type.setdefault(kind, []).append(artifact.id)

        if kind == "record":
            metadata = _payload(artifact).get("metadata") or {}
            status = str(metadata.get("status") or "draft")
            record_status_counts[status] = record_status_counts.get(status, 0) + 1

        if artifact.working_status == "staged" or artifact.open_pr_id is not None:
            locked_artifacts.append(
                LockedArtifactSnapshot(
                    artifact_id=str(artifact.id),
                    artifact_type=kind,
                    display_id=artifact.display_id,
                    open_pr_id=str(artifact.open_pr_id) if artifact.open_pr_id else None,
                )
            )

    for kind, artifact_ids in active_artifact_ids_by_type.items():
        if not artifact_ids:
            continue
        latest = (
            await db.execute(
                select(func.max(ArtifactVersion.version_number)).where(
                    ArtifactVersion.artifact_id.in_(artifact_ids)
                )
            )
        ).scalar()
        if latest is not None:
            artifacts[kind].latest_version = int(latest)

    record_count = artifacts.get("record", ArtifactTypeSnapshot()).count
    srs_count = artifacts.get("srs", ArtifactTypeSnapshot()).count
    design_count = artifacts.get("design", ArtifactTypeSnapshot()).count

    readiness = {
        "can_extract_records_from_documents": active_doc_count >= 1 and len(sections) >= 1,
        "can_add_user_text_record": len(sections) >= 1,
        "can_generate_srs": record_count >= 1 and len(sections) >= 1,
        "can_generate_design": srs_count >= 1,
        "can_generate_testcases": srs_count >= 1,
        "has_locks": bool(locked_artifacts),
        "has_design": design_count >= 1,
    }

    return ProjectContextSnapshot(
        project_id=str(project_id),
        project_name=project.name if project else None,
        active_document_count=int(active_doc_count),
        active_section_count=len(sections),
        active_sections=[
            SectionSnapshot(section_id=str(s.id), name=s.name, type=s.type)
            for s in sections
        ],
        active_record_count=record_count,
        record_status_counts=record_status_counts,
        artifacts=artifacts,
        locked_artifacts=locked_artifacts,
        readiness=readiness,
        recent_conversation=_recent_conversation(history),
    )


def format_snapshot_for_prompt(snapshot: ProjectContextSnapshot | dict[str, Any] | None) -> str:
    if snapshot is None:
        return "(snapshot unavailable)"
    if isinstance(snapshot, dict):
        snapshot = ProjectContextSnapshot.model_validate(snapshot)

    section_names = ", ".join(s.name for s in snapshot.active_sections) or "(none)"
    artifact_lines = []
    for kind in ("record", "srs", "design", "testcase"):
        stats = snapshot.artifacts.get(kind, ArtifactTypeSnapshot())
        version = f", latest v{stats.latest_version}" if stats.latest_version else ""
        statuses = ", ".join(
            f"{status}:{count}" for status, count in sorted(stats.working_status_counts.items())
        )
        artifact_lines.append(
            f"- {kind}: count={stats.count}{version}"
            + (f", working={statuses}" if statuses else "")
        )

    locks = (
        ", ".join(
            f"{l.artifact_type}/{l.display_id}(pr={l.open_pr_id or 'unknown'})"
            for l in snapshot.locked_artifacts
        )
        or "(none)"
    )
    readiness = ", ".join(
        f"{key}={value}" for key, value in sorted(snapshot.readiness.items())
    )
    record_status = ", ".join(
        f"{key}:{value}" for key, value in sorted(snapshot.record_status_counts.items())
    ) or "(none)"

    return "\n".join(
        [
            f"project: {snapshot.project_name or snapshot.project_id}",
            f"active_documents: {snapshot.active_document_count}",
            f"active_sections: {snapshot.active_section_count} ({section_names})",
            f"record_statuses: {record_status}",
            "artifacts:",
            *artifact_lines,
            f"locks: {locks}",
            f"readiness: {readiness}",
            "recent_conversation:",
            snapshot.recent_conversation or "(no prior turns)",
        ]
    )


__all__ = [
    "ArtifactTypeSnapshot",
    "LockedArtifactSnapshot",
    "ProjectContextSnapshot",
    "SectionSnapshot",
    "build_project_context_snapshot",
    "format_snapshot_for_prompt",
]
