"""AI Assist 서비스 — 요구사항 정제(refine), 보완 제안(suggest), 대화 모드(chat)."""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.requirement import Requirement
from src.prompts.assist import build_chat_prompt, build_refine_prompt, build_suggest_prompt
from src.schemas.api.assist import (
    ChatResponse,
    ExtractedRequirement,
    RefineRequest,
    RefineResponse,
    Suggestion,
    SuggestResponse,
)
from src.services.llm_svc import chat_completion
from src.utils.json_parser import parse_llm_json


async def refine_requirement(request: RefineRequest) -> RefineResponse:
    """자연어 텍스트를 정제된 요구사항으로 변환한다."""
    logger.info(f"Refine 요청: type={request.type.value}, text_len={len(request.text)}")

    messages = build_refine_prompt(text=request.text, req_type=request.type.value)
    raw = await chat_completion(messages, client_type="srs", temperature=0.3)

    parsed = parse_llm_json(raw, error_msg="AI 응답을 파싱할 수 없습니다.")
    refined_text = parsed.get("refined_text")
    if not refined_text:
        logger.error(f"LLM 응답에 refined_text 키 없음: {parsed}")
        raise AppException(status_code=502, detail="AI 응답 형식이 올바르지 않습니다.")

    return RefineResponse(
        original_text=request.text,
        refined_text=refined_text,
        type=request.type,
    )


async def suggest_requirements(
    requirement_ids: list[uuid.UUID],
    project_id: uuid.UUID,
    db: AsyncSession,
) -> SuggestResponse:
    """기존 요구사항을 분석하여 누락된 요구사항을 제안한다."""
    logger.info(f"Suggest 요청: project_id={project_id}, ids={len(requirement_ids)}개")

    # DB에서 요구사항 조회
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
    missing = [rid for rid in requirement_ids if rid not in found_ids]
    if missing:
        logger.warning(f"조회되지 않은 requirement_id: {missing}")

    # 프롬프트용 데이터 구성 (정제된 텍스트가 있으면 우선 사용)
    requirements_data = [
        {
            "type": r.type,
            "text": r.refined_text or r.original_text,
        }
        for r in rows
    ]

    messages = build_suggest_prompt(requirements_data)
    raw = await chat_completion(messages, client_type="srs", temperature=0.5, max_completion_tokens=4096)

    parsed = parse_llm_json(raw, error_msg="AI 응답을 파싱할 수 없습니다.")
    raw_suggestions = parsed.get("suggestions", [])
    if not isinstance(raw_suggestions, list):
        logger.error(f"LLM 응답의 suggestions가 리스트가 아님: {type(raw_suggestions)}")
        raise AppException(status_code=502, detail="AI 응답 형식이 올바르지 않습니다.")

    suggestions = []
    for item in raw_suggestions:
        try:
            suggestions.append(
                Suggestion(
                    type=item["type"],
                    text=item["text"],
                    reason=item["reason"],
                )
            )
        except (KeyError, ValueError) as exc:
            logger.warning(f"제안 항목 파싱 스킵: {exc}, item={item}")
            continue

    logger.info(f"Suggest 완료: {len(suggestions)}개 제안 생성")
    return SuggestResponse(suggestions=suggestions)


async def chat_assist(
    message: str,
    history: list[dict],
    project_id: uuid.UUID,
    db: AsyncSession,
) -> ChatResponse:
    """대화 모드 — 자유 대화를 통해 요구사항을 탐색적으로 정의한다."""
    logger.info(f"Chat 요청: project_id={project_id}, history_len={len(history)}")

    # 기존 요구사항을 컨텍스트로 제공 (중복 추출 방지)
    stmt = (
        select(Requirement)
        .where(Requirement.project_id == project_id)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    existing_requirements = [
        {
            "type": r.type,
            "display_id": r.display_id,
            "text": r.refined_text or r.original_text,
        }
        for r in rows
    ] if rows else None

    messages = build_chat_prompt(
        message=message,
        history=history,
        existing_requirements=existing_requirements,
    )
    raw = await chat_completion(
        messages, client_type="srs", temperature=0.7, max_completion_tokens=4096,
    )

    parsed = parse_llm_json(raw, error_msg="AI 응답을 파싱할 수 없습니다.")

    reply = parsed.get("reply", "")
    if not reply:
        logger.error(f"LLM 응답에 reply 키 없음: {parsed}")
        raise AppException(status_code=502, detail="AI 응답 형식이 올바르지 않습니다.")

    raw_extracted = parsed.get("extracted_requirements", [])
    if not isinstance(raw_extracted, list):
        logger.warning(f"extracted_requirements가 리스트가 아님: {type(raw_extracted)}")
        raw_extracted = []

    extracted = []
    for item in raw_extracted:
        try:
            extracted.append(
                ExtractedRequirement(
                    type=item["type"],
                    text=item["text"],
                    reason=item["reason"],
                )
            )
        except (KeyError, ValueError) as exc:
            logger.warning(f"추출된 요구사항 파싱 스킵: {exc}, item={item}")
            continue

    logger.info(f"Chat 완료: reply_len={len(reply)}, extracted={len(extracted)}개")
    return ChatResponse(reply=reply, extracted_requirements=extracted)
