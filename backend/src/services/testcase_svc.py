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

import json
import uuid
from datetime import timezone

from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from src.models.artifact import Artifact
from src.models.glossary import GlossaryItem
from src.models.srs import SrsDocument
from src.prompts.testcase.generate import build_testcase_section_prompt
from src.schemas.api.artifact_testcase import (
    TestCaseArtifactResponse,
    TestCaseContent,
    TestCaseGenerateResponse,
)
from src.services.llm_svc import chat_completion


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
    logger.info(f"TestCase 생성 시작: project_id={project_id}")

    # 1. 최신 완료 SRS 선택
    srs_row = (
        await db.execute(
            select(SrsDocument)
            .where(
                SrsDocument.project_id == project_id,
                SrsDocument.status == "completed",
            )
            .options(selectinload(SrsDocument.sections))
            .order_by(SrsDocument.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if srs_row is None:
        raise AppException(400, "완료된 SRS 문서가 없습니다. 먼저 SRS를 생성하세요.")

    sections = sorted(srs_row.sections, key=lambda s: s.order_index)
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
        section_key = section.title or (
            str(section.section_id) if section.section_id else "미제목"
        )

        if not section.content or not section.content.strip():
            skipped.append(f"{section_key} (내용 없음)")
            continue

        messages = build_testcase_section_prompt(
            section_title=section.title,
            section_content=section.content,
            srs_section_id=str(section.section_id) if section.section_id else "",
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
            artifact = Artifact(
                project_id=project_id,
                artifact_type="testcase",
                display_id=display_id,
                content=content.model_dump(),
                working_status="dirty",
                lifecycle_status="active",
            )
            db.add(artifact)
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
        based_on_srs_id=str(srs_row.id),
        srs_version=srs_row.version,
        testcases=[_to_response(a) for a in testcases],
        section_coverage=section_coverage,
        skipped_sections=skipped,
    )


__all__ = ["generate_testcases"]
