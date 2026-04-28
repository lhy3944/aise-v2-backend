"""TestCase 생성 서비스 — SRS 섹션 기반 TC Artifact 생성

흐름
----
1. 프로젝트의 `status='completed'` 중 가장 최신 버전의 SrsDocument 선택
2. 각 섹션마다 `build_testcase_section_prompt` 로 LLM 호출
3. 응답 JSON 배열 파싱 → 스키마 검증 → artifact_type='testcase' Artifact
   로 append (working_status='dirty')
4. 생성된 TC Artifact 리스트와 섹션별 coverage 집계 반환

에러
----
- SRS 없음 → AppException(400)
- 모든 섹션 LLM 응답이 파싱 실패 → AppException(502)
- 단일 섹션 실패는 `skipped_sections` 에 담고 계속 진행
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.artifact import Artifact, ArtifactVersion
from src.models.glossary import GlossaryItem
from src.prompts.testcase.generate import build_testcase_section_prompt
from src.schemas.api.artifact_testcase import (
    TestCaseArtifactResponse,
    TestCaseContent,
    TestCaseGenerateResponse,
)
from src.services.llm_svc import chat_completion


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_tc_array(raw: str) -> list[dict]:
    """LLM 응답에서 TC 배열을 추출. 코드펜스 허용."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("TC payload must be a JSON array")
    return parsed


async def _next_tc_display_id(db: AsyncSession, project_id: uuid.UUID) -> int:
    """project 내 TC display_id 최대값 + 1 반환. 기본값 1."""
    rows = (
        await db.execute(
            select(Artifact.display_id).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "testcase",
            )
        )
    ).all()
    max_n = 0
    for (disp,) in rows:
        if not disp:
            continue
        # "TC-001" 형태 가정; 숫자 파트만 추출
        tail = disp.split("-")[-1]
        try:
            n = int(tail)
        except ValueError:
            continue
        if n > max_n:
            max_n = n
    return max_n + 1


def _to_response(artifact: Artifact) -> TestCaseArtifactResponse:
    payload = artifact.content if isinstance(artifact.content, dict) else {}
    created = artifact.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return TestCaseArtifactResponse(
        artifact_id=str(artifact.id),
        display_id=artifact.display_id,
        content=TestCaseContent(**payload),
        working_status=artifact.working_status,
        lifecycle_status=artifact.lifecycle_status,
        created_at=created.isoformat(),
    )


async def generate_testcases(
    db: AsyncSession, project_id: uuid.UUID
) -> TestCaseGenerateResponse:
    """프로젝트의 SRS Artifact 의 current(clean) version 을 입력으로 TC 생성.

    Phase C 변경:
    - 기존 SrsDocument 직접 조회 제거
    - artifact_type='srs' Artifact + current_version_id (clean version) 의
      ArtifactVersion.snapshot 에서 sections 추출
    - dirty/staged 상태의 SRS 는 입력으로 사용하지 않음 (검증 안 된 변경 차단)
    """
    logger.info(f"TestCase 생성 시작: project_id={project_id}")

    # 1. SRS Artifact + clean current version 조회
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
        raise AppException(400, "완료된 SRS 문서가 없습니다. 먼저 SRS를 생성하세요.")

    srs_version = await db.get(ArtifactVersion, srs_artifact.current_version_id)
    if srs_version is None:
        raise AppException(500, "SRS current version 이 유실되었습니다.")

    snapshot: dict[str, Any] = (
        srs_version.snapshot if isinstance(srs_version.snapshot, dict) else {}
    )
    raw_sections = snapshot.get("sections")
    sections: list[dict[str, Any]] = (
        sorted(
            [s for s in raw_sections if isinstance(s, dict)],
            key=lambda s: int(s.get("order_index") or 0),
        )
        if isinstance(raw_sections, list)
        else []
    )
    if not sections:
        raise AppException(400, "SRS 문서에 섹션이 없습니다.")

    # 2. 용어 사전
    glossary_rows = (
        await db.execute(
            select(GlossaryItem).where(
                GlossaryItem.project_id == project_id,
                GlossaryItem.is_approved == True,  # noqa: E712
            )
        )
    ).scalars().all()
    glossary_dicts = [
        {"term": g.term, "definition": g.definition} for g in glossary_rows
    ]

    # 3. 다음 display_id 시작점
    next_n = await _next_tc_display_id(db, project_id)

    testcases: list[Artifact] = []
    section_coverage: dict[str, int] = {}
    skipped: list[str] = []

    for section in sections:
        section_title = str(section.get("title") or "")
        section_content = str(section.get("content") or "")
        section_id_raw = section.get("section_id")
        section_id_str = str(section_id_raw) if section_id_raw else ""
        section_key = section_title or section_id_str or "미제목"

        if not section_content.strip():
            skipped.append(f"{section_key} (내용 없음)")
            continue

        messages = build_testcase_section_prompt(
            section_title=section_title,
            section_content=section_content,
            srs_section_id=section_id_str,
            glossary=glossary_dicts,
        )

        try:
            raw = await chat_completion(messages, client_type="tc", temperature=0.2)
            tc_dicts = _parse_tc_array(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(f"TC JSON 파싱 실패 — section={section_key}: {exc}")
            skipped.append(f"{section_key} (JSON 파싱 실패)")
            continue
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception(f"TC LLM 호출 실패 — section={section_key}: {exc}")
            skipped.append(f"{section_key} (LLM 오류)")
            continue

        count_in_section = 0
        for tc_dict in tc_dicts:
            if not isinstance(tc_dict, dict):
                continue
            try:
                content = TestCaseContent(**tc_dict)
            except ValidationError as exc:
                logger.warning(
                    f"TC 스키마 검증 실패 — section={section_key}: {exc}"
                )
                continue

            display_id = f"TC-{next_n:03d}"
            next_n += 1
            payload = content.model_dump()
            artifact = Artifact(
                project_id=project_id,
                artifact_type="testcase",
                display_id=display_id,
                content=payload,
                # Phase E: 생성 시 즉시 v1 ArtifactVersion 을 만들어 clean 으로 두면
                # SRS clean version 을 source 로 한 lineage 가 ArtifactVersion 에
                # 기록될 수 있다. 사용자 수동 편집 -> dirty -> staged -> merge 흐름은
                # 그대로 유지.
                working_status="clean",
                lifecycle_status="active",
            )
            db.add(artifact)
            await db.flush()  # artifact.id 확정

            v1 = ArtifactVersion(
                artifact_id=artifact.id,
                version_number=1,
                parent_version_id=None,
                snapshot=payload,
                content_hash=_content_hash(payload),
                commit_message="TC v1 generated",
                author_id="testcase_generator",
                source_artifact_versions={
                    "srs": [
                        {
                            "artifact_id": str(srs_version.artifact_id),
                            "version_id": str(srs_version.id),
                            "version_number": srs_version.version_number,
                            "section_id": section_id_str or None,
                        }
                    ]
                },
            )
            db.add(v1)
            await db.flush()
            artifact.current_version_id = v1.id

            testcases.append(artifact)
            count_in_section += 1

        section_coverage[section_key] = count_in_section

    if not testcases and skipped:
        raise AppException(
            502, f"테스트케이스를 생성하지 못했습니다. 실패 섹션: {', '.join(skipped)}"
        )

    await db.commit()
    for a in testcases:
        await db.refresh(a)

    return TestCaseGenerateResponse(
        based_on_srs_id=str(srs_version.id),
        srs_version=srs_version.version_number,
        testcases=[_to_response(a) for a in testcases],
        section_coverage=section_coverage,
        skipped_sections=skipped,
    )


__all__ = ["generate_testcases"]
