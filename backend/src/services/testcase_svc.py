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
from src.services.artifact_messages import MISSING_SRS_MESSAGE
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


def _normalize(text: str) -> str:
    """TC title 비교용 정규화 — 소문자 + 다중 공백 축약."""
    import re
    return re.sub(r"\s+", " ", text.lower().strip())


def _is_similar(a: str, b: str, threshold: float = 0.85) -> bool:
    """SequenceMatcher 기반 유사도 비교."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() >= threshold


def _deduplicate_testcases(items: list[TestCaseContent]) -> list[TestCaseContent]:
    """title 유사도로 중복 TC 제거."""
    seen: list[str] = []
    unique: list[TestCaseContent] = []
    for item in items:
        normalized = _normalize(item.title)
        if any(_is_similar(normalized, s) for s in seen):
            continue
        seen.append(normalized)
        unique.append(item)
    return unique


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
        raise AppException(400, MISSING_SRS_MESSAGE)

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
        # 1차: 스키마 검증
        validated: list[TestCaseContent] = []
        for tc_dict in tc_dicts:
            if not isinstance(tc_dict, dict):
                continue
            try:
                validated.append(TestCaseContent(**tc_dict))
            except ValidationError as exc:
                logger.warning(
                    f"TC 스키마 검증 실패 — section={section_key}: {exc}"
                )

        # 2차: 중복 제거
        validated = _deduplicate_testcases(validated)

        for content in validated:

            display_id = f"TC-{next_n:03d}"
            next_n += 1
            payload = content.model_dump()
            artifact = Artifact(
                project_id=project_id,
                artifact_type="testcase",
                display_id=display_id,
                content=payload,
                working_status="dirty",
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
            artifact.working_status = "clean"

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


async def regenerate_testcase(
    db: AsyncSession, project_id: uuid.UUID, artifact_id: uuid.UUID
) -> TestCaseArtifactResponse:
    """기존 TC artifact 에 새 ArtifactVersion 을 append (최신 SRS 기반 재생성).

    기존 display_id, artifact 레코드는 유지하고 content 만 교체 + 새 version 추가.
    """
    # 1. 대상 TC artifact 확인
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None or str(artifact.project_id) != str(project_id):
        raise AppException(404, "대상 테스트케이스를 찾을 수 없습니다.")
    if artifact.artifact_type != "testcase":
        raise AppException(400, "testcase 타입만 재생성할 수 있습니다.")

    # 2. 현재 TC 가 참조하던 SRS section_id 확보
    current_v = None
    if artifact.current_version_id:
        current_v = await db.get(ArtifactVersion, artifact.current_version_id)

    section_id: str | None = None
    if current_v and isinstance(current_v.source_artifact_versions, dict):
        srs_entries = current_v.source_artifact_versions.get("srs", [])
        if isinstance(srs_entries, list) and len(srs_entries) > 0:
            section_id = srs_entries[0].get("section_id")

    # 3. 최신 SRS 조회
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

    srs_version = await db.get(ArtifactVersion, srs_artifact.current_version_id)
    if srs_version is None:
        raise AppException(500, "SRS current version 이 유실되었습니다.")

    snapshot: dict[str, Any] = (
        srs_version.snapshot if isinstance(srs_version.snapshot, dict) else {}
    )
    raw_sections = snapshot.get("sections", [])
    sections: list[dict[str, Any]] = (
        [s for s in raw_sections if isinstance(s, dict)] if isinstance(raw_sections, list) else []
    )

    # 4. 해당 section 찾기
    target_section: dict[str, Any] | None = None
    if section_id:
        for s in sections:
            if str(s.get("section_id", "")) == str(section_id):
                target_section = s
                break

    # section_id 가 없거나 찾지 못한 경우 첫 번째 섹션 사용
    if target_section is None and sections:
        target_section = sections[0]

    if target_section is None:
        raise AppException(400, "재생성할 SRS 섹션을 찾을 수 없습니다.")

    section_title = str(target_section.get("title") or "")
    section_content = str(target_section.get("content") or "")
    section_id_str = str(target_section.get("section_id") or "")

    if not section_content.strip():
        raise AppException(400, f"SRS 섹션 '{section_title}'에 내용이 없습니다.")

    # 5. 용어 사전
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

    # 6. LLM 호출 — 기존 TC 제목/구조를 힌트로 전달
    existing_content = artifact.content if isinstance(artifact.content, dict) else {}
    existing_title = existing_content.get("title", "")

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
        raise AppException(502, f"TC 재생성 JSON 파싱 실패: {exc}")
    except Exception as exc:
        raise AppException(502, f"TC 재생성 LLM 오류: {exc}")

    # 기존 TC 제목과 가장 유사한 결과 선택, 없으면 첫 번째
    best = None
    if existing_title:
        for d in tc_dicts:
            if isinstance(d, dict) and existing_title.lower() in str(d.get("title", "")).lower():
                best = d
                break
    if best is None and tc_dicts:
        best = tc_dicts[0]

    if not isinstance(best, dict):
        raise AppException(502, "재생성할 TC를 선택하지 못했습니다.")

    try:
        content = TestCaseContent(**best)
    except ValidationError as exc:
        raise AppException(502, f"TC 스키마 검증 실패: {exc}")

    # 7. 새 ArtifactVersion append
    payload = content.model_dump()
    version_number = await _next_version_number(db, artifact.id)
    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=version_number,
        parent_version_id=artifact.current_version_id,
        snapshot=payload,
        content_hash=_content_hash(payload),
        commit_message=f"TC v{version_number} regenerated (SRS v{srs_version.version_number})",
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
    db.add(version)
    await db.flush()

    artifact.current_version_id = version.id
    artifact.content = payload
    artifact.working_status = "clean"
    artifact.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(artifact)

    return _to_response(artifact)


async def _next_version_number(db: AsyncSession, artifact_id: uuid.UUID) -> int:
    """artifact 의 다음 version_number 반환."""
    result = await db.execute(
        select(ArtifactVersion.version_number)
        .where(ArtifactVersion.artifact_id == artifact_id)
        .order_by(ArtifactVersion.version_number.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return (row or 0) + 1


async def delete_all_testcases(
    db: AsyncSession, project_id: uuid.UUID
) -> int:
    """프로젝트의 모든 TC 를 soft-delete (lifecycle_status='deleted'). 삭제된 개수 반환."""
    rows = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "testcase",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalars().all()

    now = datetime.now(timezone.utc)
    for a in rows:
        a.lifecycle_status = "deleted"
        a.updated_at = now

    await db.commit()
    return len(rows)


async def regenerate_all_testcases(
    db: AsyncSession, project_id: uuid.UUID
) -> TestCaseGenerateResponse:
    """최신 SRS 기반으로 전체 TC 재생성.

    SRS 섹션 단위로 LLM 호출 → 중복 제거 → 기존 TC와 title 매칭:
    - 매칭 성공: 기존 artifact에 새 ArtifactVersion append
    - 매칭 실패: 새 artifact 생성
    """
    # 1. 최신 SRS 조회
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

    # 2. 기존 TC artifact 목록
    existing_rows = (
        await db.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "testcase",
                Artifact.lifecycle_status == "active",
            )
        )
    ).scalars().all()
    matched_artifact_ids: set[uuid.UUID] = set()

    # 3. 용어 사전
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

    # 4. 다음 display_id 시작점
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

        # 스키마 검증 + 중복 제거
        validated: list[TestCaseContent] = []
        for tc_dict in tc_dicts:
            if not isinstance(tc_dict, dict):
                continue
            try:
                validated.append(TestCaseContent(**tc_dict))
            except ValidationError:
                continue
        validated = _deduplicate_testcases(validated)

        count_in_section = 0
        for content in validated:
            # 기존 TC와 title 매칭
            matched_artifact = _match_tc(content, existing_rows, matched_artifact_ids)

            if matched_artifact is not None:
                # 기존 artifact에 새 버전 append
                matched_artifact_ids.add(matched_artifact.id)
                payload = content.model_dump()
                version_number = await _next_version_number(db, matched_artifact.id)
                version = ArtifactVersion(
                    artifact_id=matched_artifact.id,
                    version_number=version_number,
                    parent_version_id=matched_artifact.current_version_id,
                    snapshot=payload,
                    content_hash=_content_hash(payload),
                    commit_message=f"TC v{version_number} regenerated (SRS v{srs_version.version_number})",
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
                db.add(version)
                await db.flush()

                matched_artifact.current_version_id = version.id
                matched_artifact.content = payload
                matched_artifact.working_status = "clean"
                matched_artifact.updated_at = datetime.now(timezone.utc)

                testcases.append(matched_artifact)
            else:
                # 새 artifact 생성
                display_id = f"TC-{next_n:03d}"
                next_n += 1
                payload = content.model_dump()
                artifact = Artifact(
                    project_id=project_id,
                    artifact_type="testcase",
                    display_id=display_id,
                    content=payload,
                    working_status="dirty",
                    lifecycle_status="active",
                )
                db.add(artifact)
                await db.flush()

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
                artifact.working_status = "clean"

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


def _match_tc(
    new_tc: TestCaseContent,
    existing_artifacts: list[Artifact],
    already_matched: set[uuid.UUID],
) -> Artifact | None:
    """title 유사도로 기존 TC와 매칭. 이미 매칭된 artifact는 제외."""
    from difflib import SequenceMatcher

    normalized_new = _normalize(new_tc.title)
    best_match: Artifact | None = None
    best_ratio = 0.0

    for a in existing_artifacts:
        if a.id in already_matched:
            continue
        content = a.content if isinstance(a.content, dict) else {}
        title = str(content.get("title", ""))
        ratio = SequenceMatcher(None, normalized_new, _normalize(title)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = a

    if best_ratio >= 0.7 and best_match is not None:
        return best_match
    return None
