"""요구사항 Review 서비스 -- 요구사항 충돌(conflict) + 중복(duplicate) 검출 + 해결 힌트 제공."""

# --- v2 예정: 수정 제안 수락/거절 ---

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.requirement import Requirement
from src.models.review import RequirementReview
from src.prompts.review import build_requirements_review_prompt
from src.schemas.api.review import (
    LatestReviewResponse,
    ReviewIssue,
    ReviewResponse,
    ReviewSummary,
)
from src.services.llm_svc import chat_completion
# from src.services.requirement_svc import create_requirement_from_review  # v2 예정
from src.utils.json_parser import parse_llm_json


def _parse_review_response(parsed: dict, review_id: str) -> ReviewResponse:
    """LLM 응답 JSON을 ReviewResponse로 변환한다."""
    # issues 파싱
    raw_issues = parsed.get("issues", [])
    if not isinstance(raw_issues, list):
        logger.error(f"LLM 응답의 issues가 리스트가 아님: {type(raw_issues)}")
        raise AppException(status_code=502, detail="AI 응답 형식이 올바르지 않습니다.")

    issues: list[ReviewIssue] = []
    for item in raw_issues:
        try:
            issue_type = item.get("type", "conflict")
            if issue_type not in ("conflict", "duplicate"):
                logger.warning(f"알 수 없는 이슈 타입 '{issue_type}' → conflict로 fallback")
                issue_type = "conflict"
            issues.append(
                ReviewIssue(
                    issue_id=uuid.uuid4().hex[:8],
                    type=issue_type,
                    description=item.get("description", ""),
                    related_requirements=item.get("related_requirements", []),
                    hint=item.get("hint", ""),
                )
            )
        except (KeyError, ValueError) as exc:
            logger.warning(f"이슈 항목 파싱 스킵: {exc}, item={item}")
            continue

    # summary 파싱
    raw_summary = parsed.get("summary", {})
    if not isinstance(raw_summary, dict):
        logger.error(f"LLM 응답의 summary가 dict가 아님: {type(raw_summary)}")
        raise AppException(status_code=502, detail="AI 응답 형식이 올바르지 않습니다.")

    duplicate_count = sum(1 for i in issues if i.type == "duplicate")
    summary = ReviewSummary(
        total_issues=len(issues),
        conflicts=len(issues) - duplicate_count,
        duplicates=duplicate_count,
        ready_for_next=True,  # v1: 항상 true (경고만)
        feedback=raw_summary.get("feedback", ""),
    )

    return ReviewResponse(review_id=review_id, issues=issues, summary=summary)


async def review_requirements(
    requirement_ids: list[uuid.UUID],
    project_id: uuid.UUID,
    db: AsyncSession,
) -> ReviewResponse:
    """요구사항을 분석하여 충돌(conflict) 이슈를 검출하고 해결 힌트를 제공한다."""
    logger.info(f"Review 요청: project_id={project_id}, ids={len(requirement_ids)}개")

    # 전체 리뷰 분기: requirement_ids가 비어있으면 프로젝트 전체 조회
    if requirement_ids:
        stmt = (
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .where(Requirement.id.in_(requirement_ids))
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            raise AppException(status_code=404, detail="해당하는 요구사항을 찾을 수 없습니다.")

        found_ids = {r.id for r in rows}
        not_found = [rid for rid in requirement_ids if rid not in found_ids]
        if not_found:
            logger.warning(f"조회되지 않은 requirement_id: {not_found}")
    else:
        # 빈 리스트 → 프로젝트 전체 Include된 요구사항
        logger.info(f"전체 리뷰 모드: project_id={project_id}")
        stmt = (
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .where(Requirement.is_selected.is_(True))
            .order_by(Requirement.order_index.asc())
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            raise AppException(status_code=404, detail="Include된 요구사항이 없습니다.")

    # 프롬프트용 데이터 구성 (display_id 포함하여 토큰 절약)
    requirements_data = [
        {
            "req_id": str(r.id),
            "display_id": r.display_id or str(r.id)[:8],
            "type": r.type,
            "text": r.refined_text or r.original_text,
        }
        for r in rows
    ]

    messages = build_requirements_review_prompt(requirements_data)
    raw = await chat_completion(messages, client_type="srs", temperature=0.3, max_completion_tokens=2048)

    parsed = parse_llm_json(raw, error_msg="AI 응답을 파싱할 수 없습니다.")

    review_id = uuid.uuid4().hex[:12]
    response = _parse_review_response(parsed, review_id)

    # DB 저장: 프로젝트당 최신 1건 (delete + insert)
    # TODO: 다중 사용자 환경에서 INSERT ... ON CONFLICT ... DO UPDATE로 개선
    existing = await db.execute(
        select(RequirementReview).where(RequirementReview.project_id == project_id)
    )
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)
        await db.flush()

    new_review = RequirementReview(
        project_id=project_id,
        review_data=response.model_dump(mode="json"),
        reviewed_requirement_ids=[str(r.id) for r in rows],
    )
    db.add(new_review)
    await db.commit()

    logger.info(
        f"Review 완료: review_id={review_id}, {len(response.issues)}개 이슈 검출, "
        f"ready_for_next={response.summary.ready_for_next}"
    )
    return response


# --- v2 예정: 수정 제안 수락/거절 ---
# async def accept_suggestion(
#     project_id: uuid.UUID,
#     issue_id: str,
#     db: AsyncSession,
# ) -> AcceptSuggestionResponse:
#     """제안 수락 -- 즉시 DB 반영."""
#     logger.info(f"제안 수락: project_id={project_id}, issue_id={issue_id}")
#
#     # 1. RequirementReview에서 현재 리뷰 결과 조회
#     result = await db.execute(
#         select(RequirementReview).where(RequirementReview.project_id == project_id)
#     )
#     review = result.scalar_one_or_none()
#     if not review:
#         raise AppException(status_code=404, detail="리뷰 이력이 없습니다.")
#
#     review_data = review.review_data
#     issues = review_data.get("issues", [])
#
#     # 2. issue_id에 해당하는 이슈 찾기
#     target_issue = None
#     target_idx = None
#     for idx, issue in enumerate(issues):
#         if issue.get("issue_id") == issue_id:
#             target_issue = issue
#             target_idx = idx
#             break
#
#     if target_issue is None:
#         raise AppException(status_code=404, detail="해당 이슈를 찾을 수 없습니다.")
#
#     if target_issue.get("status") == "accepted":
#         raise AppException(status_code=400, detail="이미 수락된 제안입니다.")
#
#     issue_type = target_issue.get("type")
#     suggestion = target_issue.get("suggestion")
#
#     if not suggestion:
#         raise AppException(status_code=400, detail="수정 제안이 없는 이슈는 수락할 수 없습니다.")
#
#     suggested_text = suggestion.get("suggested_text", "")
#
#     # 3. type에 따라 처리
#     if issue_type == "missing":
#         # missing: 새 Requirement 생성 (requirement_svc에 위임)
#         req_type = suggestion.get("type", "fr")
#         if req_type not in ("fr", "qa", "constraints", "other"):
#             req_type = "fr"
#
#         new_req = await create_requirement_from_review(
#             project_id=project_id,
#             req_type=req_type,
#             text=suggested_text,
#             db=db,
#         )
#         requirement_id = str(new_req.id)
#         action = "created"
#         logger.info(f"missing 제안 수락 -> 새 요구사항 생성: {new_req.id}, display_id={new_req.display_id}")
#
#     else:
#         # conflict/duplicate/ambiguity: target_id로 Requirement 찾아 refined_text 업데이트
#         target_id = suggestion.get("target_id")
#         if not target_id:
#             raise AppException(status_code=400, detail="수정 대상 ID가 없습니다.")
#
#         try:
#             target_uuid = uuid.UUID(target_id)
#         except ValueError:
#             raise AppException(status_code=400, detail="유효하지 않은 수정 대상 ID입니다.")
#
#         stmt = select(Requirement).where(
#             Requirement.id == target_uuid,
#             Requirement.project_id == project_id,
#         )
#         req_result = await db.execute(stmt)
#         req = req_result.scalar_one_or_none()
#         if not req:
#             raise AppException(status_code=404, detail="수정 대상 요구사항을 찾을 수 없습니다.")
#
#         req.refined_text = suggested_text
#         req.updated_at = datetime.now(timezone.utc)
#         requirement_id = str(req.id)
#         action = "updated"
#         logger.info(f"{issue_type} 제안 수락 -> 요구사항 업데이트: {req.id}")
#
#     # 4. 해당 이슈의 status를 "accepted"로 업데이트 (review_data JSON 내부)
#     updated_data = copy.deepcopy(review_data)
#     updated_data["issues"][target_idx]["status"] = "accepted"
#     review.review_data = updated_data
#     flag_modified(review, "review_data")
#
#     await db.commit()
#     return AcceptSuggestionResponse(
#         success=True,
#         action=action,
#         requirement_id=requirement_id,
#         updated_text=suggested_text,
#     )
#
#
# async def reject_suggestion(
#     project_id: uuid.UUID,
#     issue_id: str,
#     db: AsyncSession,
# ) -> RejectSuggestionResponse:
#     """제안 거절."""
#     logger.info(f"제안 거절: project_id={project_id}, issue_id={issue_id}")
#
#     # 1. RequirementReview에서 현재 리뷰 결과 조회
#     result = await db.execute(
#         select(RequirementReview).where(RequirementReview.project_id == project_id)
#     )
#     review = result.scalar_one_or_none()
#     if not review:
#         raise AppException(status_code=404, detail="리뷰 이력이 없습니다.")
#
#     review_data = review.review_data
#     issues = review_data.get("issues", [])
#
#     # 2. issue_id에 해당하는 이슈 찾기
#     target_idx = None
#     for idx, issue in enumerate(issues):
#         if issue.get("issue_id") == issue_id:
#             target_idx = idx
#             break
#
#     if target_idx is None:
#         raise AppException(status_code=404, detail="해당 이슈를 찾을 수 없습니다.")
#
#     if issues[target_idx].get("status") == "rejected":
#         raise AppException(status_code=400, detail="이미 거절된 제안입니다.")
#
#     if issues[target_idx].get("status") == "accepted":
#         raise AppException(status_code=400, detail="이미 수락된 제안은 거절할 수 없습니다.")
#
#     # 3. status를 "rejected"로 업데이트
#     updated_data = copy.deepcopy(review_data)
#     updated_data["issues"][target_idx]["status"] = "rejected"
#     review.review_data = updated_data
#     flag_modified(review, "review_data")
#
#     await db.commit()
#     logger.info(f"제안 거절 완료: issue_id={issue_id}")
#     return RejectSuggestionResponse(success=True)


async def get_latest_review(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> LatestReviewResponse | None:
    """마지막 리뷰 결과 조회."""
    logger.info(f"최근 리뷰 조회: project_id={project_id}")

    result = await db.execute(
        select(RequirementReview).where(RequirementReview.project_id == project_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        return None

    review_data = review.review_data

    # issues를 ReviewIssue 모델로 변환
    raw_issues = review_data.get("issues", [])
    issues = [ReviewIssue(**item) for item in raw_issues]

    # summary를 ReviewSummary 모델로 변환
    raw_summary = review_data.get("summary", {})
    summary = ReviewSummary(**raw_summary)

    return LatestReviewResponse(
        review_id=review_data.get("review_id", ""),
        created_at=review.created_at,
        reviewed_requirement_ids=[str(rid) for rid in review.reviewed_requirement_ids],
        issues=issues,
        summary=summary,
    )
