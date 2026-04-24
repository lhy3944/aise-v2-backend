"""backfill_records_to_artifacts

기존 records 테이블의 모든 행을 artifacts + artifact_versions(v1)로 백필한다.
레거시 records 테이블은 그대로 유지되며, Phase 2의 record_svc 어댑터 리팩토링 이후
실질적으로 artifacts 테이블이 primary store 역할을 하게 된다.

SRS 백필은 Phase 2 후반(artifact_svc 연동 시)으로 이연 — srs_documents + srs_sections의
구조화된 스냅샷 생성 로직이 필요하므로 별도 마이그레이션으로 분리.

Revision ID: c6e3d4f50607
Revises: b5d2c3e4f506
Create Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "c6e3d4f50607"
down_revision: Union[str, Sequence[str], None] = "b5d2c3e4f506"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _canonical_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    # offline 모드(--sql)에서는 동적 백필을 생성할 수 없다.
    # 실제 DB에 upgrade를 실행할 때만 수행.
    if context.is_offline_mode():
        return

    bind = op.get_bind()

    # 멱등성: artifacts(type='record')가 이미 존재하면 스킵.
    existing = bind.execute(
        sa.text("SELECT COUNT(*) FROM artifacts WHERE artifact_type = 'record'")
    ).scalar()
    if existing and existing > 0:
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT
              id, project_id, section_id, content, display_id,
              source_document_id, source_location, confidence_score,
              status, is_auto_extracted, order_index, created_at, updated_at
            FROM records
            """
        )
    ).mappings().all()

    # CHECK(ck_artifacts_clean_requires_version) 때문에 current_version_id 가
    # NULL 인 상태로는 working_status='clean' 이 될 수 없다. 초기 INSERT 는
    # 'dirty' 로 하고, version 생성 후 UPDATE 에서 version_id + 'clean' 을
    # 동시에 세팅해 최종 상태로 옮긴다.
    artifacts_insert = sa.text(
        """
        INSERT INTO artifacts (
          id, project_id, artifact_type, display_id, title, content,
          working_status, lifecycle_status, current_version_id, open_pr_id,
          created_at, updated_at
        ) VALUES (
          :id, :project_id, 'record', :display_id, NULL, CAST(:content AS jsonb),
          'dirty', 'active', NULL, NULL,
          :created_at, :updated_at
        )
        """
    )
    versions_insert = sa.text(
        """
        INSERT INTO artifact_versions (
          id, artifact_id, version_number, parent_version_id,
          snapshot, content_hash, commit_message, author_id, committed_at,
          merged_from_pr_id
        ) VALUES (
          :id, :artifact_id, 1, NULL,
          CAST(:snapshot AS jsonb), :content_hash,
          'initial backfill from legacy records table', 'system', :committed_at,
          NULL
        )
        """
    )
    set_current = sa.text(
        "UPDATE artifacts "
        "SET current_version_id = :version_id, working_status = 'clean' "
        "WHERE id = :artifact_id"
    )

    for row in rows:
        content_payload = {
            "text": row["content"],
            "section_id": str(row["section_id"]) if row["section_id"] else None,
            "source_document_id": (
                str(row["source_document_id"]) if row["source_document_id"] else None
            ),
            "source_location": row["source_location"],
            "confidence_score": row["confidence_score"],
            "is_auto_extracted": bool(row["is_auto_extracted"]),
            "order_index": row["order_index"],
            "metadata": {"legacy_status": row["status"]},
        }
        content_json = json.dumps(content_payload, ensure_ascii=False, default=str)
        content_hash = _canonical_hash(content_payload)

        # 기존 Record.id를 그대로 Artifact.id로 재사용 → 양쪽 키 매핑이 자연스러움
        artifact_id = row["id"]
        display_id = row["display_id"] or f"REC-{str(artifact_id)[:8]}"

        bind.execute(
            artifacts_insert,
            {
                "id": artifact_id,
                "project_id": row["project_id"],
                "display_id": display_id,
                "content": content_json,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        )

        version_id = uuid.uuid4()
        bind.execute(
            versions_insert,
            {
                "id": version_id,
                "artifact_id": artifact_id,
                "snapshot": content_json,
                "content_hash": content_hash,
                "committed_at": row["created_at"],
            },
        )
        bind.execute(
            set_current,
            {"version_id": version_id, "artifact_id": artifact_id},
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    # 데이터 보존 원칙 — 백필 롤백은 artifacts(type='record') 행만 삭제하고,
    # 레거시 records 테이블은 건드리지 않는다.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM artifact_versions
             WHERE artifact_id IN (
               SELECT id FROM artifacts WHERE artifact_type = 'record'
             )
            """
        )
    )
    bind.execute(
        sa.text("DELETE FROM artifacts WHERE artifact_type = 'record'")
    )
