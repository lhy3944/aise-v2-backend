"""Knowledge Repository 서비스 -- 문서 업로드/조회/삭제/토글/미리보기"""

import uuid

from fastapi import BackgroundTasks, UploadFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.models.knowledge import KnowledgeDocument, KnowledgeChunk
from src.schemas.api.knowledge import (
    KnowledgeDocumentListResponse,
    KnowledgeDocumentPreviewResponse,
    KnowledgeDocumentResponse,
)
from src.services import storage_svc
from src.services.document_processor import process_document

ALLOWED_FILE_TYPES = {"pdf", "txt", "md"}

# Content-Type 매핑
CONTENT_TYPE_MAP = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
}

PREVIEW_MAX_CHARS = 3000  # 미리보기 최대 문자 수


def _safe_truncate_md(text: str, max_chars: int) -> str:
    """마크다운 블록 경계에서 안전하게 자른다.

    - max_chars 이전의 마지막 \\n\\n 위치에서 자름
    - 열린 코드블록(```)이 있으면 닫기
    """
    if len(text) <= max_chars:
        return text

    cut = text.rfind("\n\n", 0, max_chars)
    if cut == -1:
        cut = max_chars
    truncated = text[:cut]

    # 열린 코드블록 닫기
    if truncated.count("```") % 2 == 1:
        truncated += "\n```"

    return truncated


def _to_response(doc: KnowledgeDocument) -> KnowledgeDocumentResponse:
    """DB 모델 -> 응답 스키마 변환"""
    return KnowledgeDocumentResponse(
        document_id=str(doc.id),
        project_id=str(doc.project_id),
        name=doc.name,
        file_type=doc.file_type,
        size_bytes=doc.size_bytes,
        status=doc.status,
        is_active=doc.is_active,
        error_message=doc.error_message,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _get_file_type(filename: str) -> str:
    """파일 확장자에서 타입 추출"""
    if not filename or "." not in filename:
        raise AppException(400, "파일 확장자를 확인할 수 없습니다.")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise AppException(
            400,
            f"지원하지 않는 파일 형식입니다: .{ext} (지원: {', '.join(sorted(ALLOWED_FILE_TYPES))})",
        )
    return ext


async def _find_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession,
) -> KnowledgeDocument:
    """프로젝트 내 문서 조회 (없으면 404)"""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.project_id == project_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise AppException(404, "문서를 찾을 수 없습니다.")
    return doc


async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    overwrite: bool = False,
) -> KnowledgeDocumentResponse:
    """문서 업로드 + 비동기 처리 시작"""
    logger.info(f"문서 업로드: project_id={project_id}, filename={file.filename}")

    # 1. 파일 타입 검증
    file_type = _get_file_type(file.filename or "")

    # 2. 파일 읽기
    file_bytes = await file.read()
    if not file_bytes:
        raise AppException(400, "빈 파일은 업로드할 수 없습니다.")

    # 3. 중복 파일 감지 (동일 프로젝트 + 동일 파일명)
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.name == (file.filename or "unknown"),
        )
    )
    existing_doc = result.scalar_one_or_none()

    if existing_doc and not overwrite:
        raise AppException(409, f"동일한 이름의 문서가 이미 존재합니다: {file.filename}")

    # 덮어쓰기: 기존 문서 삭제 후 재업로드
    if existing_doc and overwrite:
        logger.info(f"덮어쓰기 모드: 기존 문서 삭제 document_id={existing_doc.id}")
        bucket = storage_svc.get_default_bucket()
        try:
            await storage_svc.delete_file(bucket, existing_doc.storage_key)
        except Exception as e:
            logger.warning(f"MinIO 기존 파일 삭제 실패 (계속 진행): {e}")
        await db.delete(existing_doc)
        await db.flush()

    # 4. 스토리지 키 생성 및 업로드
    document_id = uuid.uuid4()
    storage_key = f"{project_id}/{document_id}/{file.filename}"
    bucket = storage_svc.get_default_bucket()
    content_type = CONTENT_TYPE_MAP.get(file_type, "application/octet-stream")

    await storage_svc.upload_file(bucket, storage_key, file_bytes, content_type)

    # 5. DB 레코드 생성
    doc = KnowledgeDocument(
        id=document_id,
        project_id=project_id,
        name=file.filename or "unknown",
        file_type=file_type,
        size_bytes=len(file_bytes),
        storage_key=storage_key,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 6. 백그라운드에서 문서 처리 시작 (독립 세션 사용)
    background_tasks.add_task(process_document, document_id)

    logger.info(f"문서 업로드 완료: document_id={document_id}, status=processing")
    return _to_response(doc)


async def list_documents(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> KnowledgeDocumentListResponse:
    """프로젝트의 문서 목록 조회"""
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.project_id == project_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()

    return KnowledgeDocumentListResponse(
        documents=[_to_response(doc) for doc in docs],
        total=len(docs),
    )


async def get_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession,
) -> KnowledgeDocumentResponse:
    """문서 상세 조회"""
    doc = await _find_document(project_id, document_id, db)
    return _to_response(doc)


async def toggle_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    is_active: bool,
    db: AsyncSession,
) -> KnowledgeDocumentResponse:
    """문서 활성화/비활성화 토글"""
    doc = await _find_document(project_id, document_id, db)
    doc.is_active = is_active
    await db.commit()
    await db.refresh(doc)
    logger.info(f"문서 토글: document_id={document_id}, is_active={is_active}")
    return _to_response(doc)


async def get_document_preview(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession,
) -> KnowledgeDocumentPreviewResponse:
    """문서 미리보기 (청크 텍스트 결합)"""
    doc = await _find_document(project_id, document_id, db)

    if doc.status != "completed":
        raise AppException(400, f"문서가 아직 처리되지 않았습니다. (상태: {doc.status})")

    # 청크를 순서대로 조회하여 결합
    result = await db.execute(
        select(KnowledgeChunk.content)
        .where(KnowledgeChunk.document_id == document_id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    chunks = result.scalars().all()
    full_text = "\n\n".join(chunks)
    preview_text = _safe_truncate_md(full_text, PREVIEW_MAX_CHARS)

    return KnowledgeDocumentPreviewResponse(
        document_id=str(doc.id),
        name=doc.name,
        file_type=doc.file_type,
        preview_text=preview_text,
        total_characters=len(full_text),
    )


async def reprocess_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> KnowledgeDocumentResponse:
    """실패한 문서 재처리"""
    doc = await _find_document(project_id, document_id, db)

    if doc.status not in ("failed", "completed"):
        raise AppException(400, f"재처리할 수 없는 상태입니다: {doc.status}")

    # 기존 청크 삭제
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
    )

    # 상태 초기화
    doc.status = "processing"
    doc.error_message = None
    doc.chunk_count = 0
    await db.commit()
    await db.refresh(doc)

    # 백그라운드에서 재처리
    background_tasks.add_task(process_document, document_id)

    logger.info(f"문서 재처리 시작: document_id={document_id}")
    return _to_response(doc)


async def delete_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """문서 삭제 (DB + MinIO)"""
    doc = await _find_document(project_id, document_id, db)

    # MinIO에서 파일 삭제
    bucket = storage_svc.get_default_bucket()
    try:
        await storage_svc.delete_file(bucket, doc.storage_key)
    except Exception as e:
        logger.warning(f"MinIO 파일 삭제 실패 (계속 진행): {e}")

    # DB에서 삭제 (cascade로 chunks도 삭제)
    await db.delete(doc)
    await db.commit()

    logger.info(f"문서 삭제 완료: document_id={document_id}")


async def get_chunk_with_context(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    chunk_index: int,
    context: int,
    db: AsyncSession,
) -> dict:
    """특정 청크 + 전후 context 청크 반환"""
    doc = await _find_document(project_id, document_id, db)

    min_index = max(0, chunk_index - context)
    max_index = chunk_index + context

    result = await db.execute(
        select(KnowledgeChunk.chunk_index, KnowledgeChunk.content)
        .where(
            KnowledgeChunk.document_id == document_id,
            KnowledgeChunk.chunk_index >= min_index,
            KnowledgeChunk.chunk_index <= max_index,
        )
        .order_by(KnowledgeChunk.chunk_index)
    )
    rows = result.all()

    before = []
    after = []
    target = None

    for idx, content in rows:
        entry = {"index": idx, "content": content}
        if idx < chunk_index:
            before.append(entry)
        elif idx == chunk_index:
            target = entry
        else:
            after.append(entry)

    if target is None:
        raise AppException(404, f"청크 {chunk_index}를 찾을 수 없습니다.")

    return {
        "document_id": str(document_id),
        "document_name": doc.name,
        "file_type": doc.file_type,
        "target": target,
        "before": before,
        "after": after,
    }
