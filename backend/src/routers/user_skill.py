import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import AppException
from src.schemas.api.user_skill import (
    SkillCreateRequest,
    SkillDraft,
    SkillListResponse,
    SkillPreviewGithubRequest,
    SkillPreviewTextRequest,
    SkillResponse,
    SkillUpdateRequest,
)
from src.services import user_skill_svc


router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.post("/preview/github", response_model=SkillDraft)
async def preview_github_skill(body: SkillPreviewGithubRequest):
    return await user_skill_svc.preview_github_skill(
        body.url,
        fallback_name=body.name,
        fallback_description=body.description,
    )


@router.post("/preview/text", response_model=SkillDraft)
async def preview_text_skill(body: SkillPreviewTextRequest):
    return user_skill_svc.parse_markdown_skill(
        body.body,
        source_type="text",
        fallback_name=body.name,
        fallback_description=body.description,
    )


@router.post("/preview/upload", response_model=SkillDraft)
async def preview_uploaded_skill(
    file: UploadFile = File(...),
):
    filename = file.filename or ""
    if not filename.lower().endswith(".md"):
        raise AppException(400, "Markdown(.md) 파일만 업로드할 수 있습니다.")
    raw = await file.read(user_skill_svc.MAX_SKILL_CHARS + 1)
    if len(raw) > user_skill_svc.MAX_SKILL_CHARS:
        raise AppException(400, f"스킬 본문은 {user_skill_svc.MAX_SKILL_CHARS}자를 넘을 수 없습니다.")
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppException(400, "Markdown 파일은 UTF-8 인코딩이어야 합니다.") from exc
    return user_skill_svc.parse_markdown_skill(
        markdown,
        source_type="upload",
        fallback_name=filename.rsplit(".", 1)[0],
        source_ref=filename,
    )


@router.get("", response_model=SkillListResponse)
async def list_skills(db: AsyncSession = Depends(get_db)):
    return SkillListResponse(skills=await user_skill_svc.list_skills(db))


@router.post("", response_model=SkillResponse, status_code=201)
async def create_skill(
    body: SkillCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await user_skill_svc.save_skill(db, body)


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: uuid.UUID,
    body: SkillUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await user_skill_svc.update_skill(
        db,
        skill_id,
        name=body.name,
        description=body.description,
        body=body.body,
        enabled=body.enabled,
    )


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await user_skill_svc.delete_skill(db, skill_id)
