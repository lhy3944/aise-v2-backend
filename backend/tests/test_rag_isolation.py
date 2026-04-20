"""RAG 검색의 프로젝트 격리 + 문서 상태 필터 테스트 (P0).

`rag_svc.search_similar_chunks`는 다음 보장이 필수:
1. project_id 필수 (None 시 400)
2. 다른 프로젝트의 청크는 절대 반환 안 됨 (보안)
3. is_active=False 문서의 청크는 반환 안 됨
4. status != 'completed' 문서의 청크는 반환 안 됨

REFECTORING.md P0 항목 + DESIGN.md §7.1 + MIGRATION_PLAN R5.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from src.core.exceptions import AppException
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.services import embedding_svc, rag_svc


def _vec(value: float) -> list[float]:
    """1536차원 동일값 벡터 (cosine similarity 결정적)."""
    return [value] * 1536


@pytest.fixture
def stub_embedding(monkeypatch):
    """embedding_svc.get_embeddings를 결정적 stub으로 교체.

    호출 시 첫 텍스트가 'A'로 시작하면 [0.1]*1536, 'B'로 시작하면 [0.2]*1536 반환.
    어떤 입력이든 임베딩 1개 반환.
    """

    async def fake(texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        first = texts[0].strip()
        if first.startswith("A"):
            return [_vec(0.1)]
        if first.startswith("B"):
            return [_vec(0.2)]
        return [_vec(0.05)]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake)


async def _make_project(db, name: str) -> Project:
    project = Project(name=name, description=f"{name} desc")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def _make_document(
    db,
    project_id: uuid.UUID,
    *,
    name: str,
    is_active: bool = True,
    status: str = "completed",
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        project_id=project_id,
        name=name,
        file_type="md",
        size_bytes=100,
        storage_key=f"{uuid.uuid4()}.md",
        status=status,
        chunk_count=1,
        is_active=is_active,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def _make_chunk(
    db,
    document_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    embedding: list[float],
    content: str = "chunk content",
) -> KnowledgeChunk:
    chunk = KnowledgeChunk(
        document_id=document_id,
        project_id=project_id,
        chunk_index=0,
        content=content,
        token_count=10,
        embedding=embedding,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    return chunk


async def test_search_requires_project_id(stub_embedding, db):
    with pytest.raises(AppException) as excinfo:
        await rag_svc.search_similar_chunks(
            project_id=None,  # type: ignore[arg-type]
            query="anything",
            top_k=5,
            db=db,
        )
    assert excinfo.value.status_code == 400


async def test_search_isolates_by_project(stub_embedding, db):
    """프로젝트 A로 검색 시 프로젝트 B의 청크가 절대 섞이지 않아야 한다."""
    project_a = await _make_project(db, "Project A")
    project_b = await _make_project(db, "Project B")

    doc_a = await _make_document(db, project_a.id, name="doc_a")
    doc_b = await _make_document(db, project_b.id, name="doc_b")

    # 동일 임베딩 — project_id 필터가 작동하지 않으면 양쪽 모두 반환됨
    await _make_chunk(db, doc_a.id, project_a.id, embedding=_vec(0.1), content="A-chunk")
    await _make_chunk(db, doc_b.id, project_b.id, embedding=_vec(0.1), content="B-chunk")

    results = await rag_svc.search_similar_chunks(
        project_id=project_a.id,
        query="A query",
        top_k=10,
        db=db,
    )

    assert len(results) == 1
    chunk, _score = results[0]
    assert chunk.project_id == project_a.id
    assert chunk.content == "A-chunk"


async def test_search_excludes_inactive_documents(stub_embedding, db):
    project = await _make_project(db, "P")
    active = await _make_document(db, project.id, name="active", is_active=True)
    inactive = await _make_document(db, project.id, name="inactive", is_active=False)

    await _make_chunk(db, active.id, project.id, embedding=_vec(0.1), content="active-chunk")
    await _make_chunk(db, inactive.id, project.id, embedding=_vec(0.1), content="inactive-chunk")

    results = await rag_svc.search_similar_chunks(
        project_id=project.id,
        query="A query",
        top_k=10,
        db=db,
    )

    contents = {chunk.content for chunk, _ in results}
    assert contents == {"active-chunk"}


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
async def test_search_excludes_non_completed_documents(stub_embedding, db, status):
    project = await _make_project(db, "P")
    completed = await _make_document(db, project.id, name="completed", status="completed")
    pending = await _make_document(db, project.id, name="other", status=status)

    await _make_chunk(db, completed.id, project.id, embedding=_vec(0.1), content="completed-chunk")
    await _make_chunk(db, pending.id, project.id, embedding=_vec(0.1), content=f"{status}-chunk")

    results = await rag_svc.search_similar_chunks(
        project_id=project.id,
        query="A query",
        top_k=10,
        db=db,
    )

    contents = {chunk.content for chunk, _ in results}
    assert contents == {"completed-chunk"}


async def test_search_returns_empty_when_no_matching_chunks(stub_embedding, db):
    """프로젝트는 있지만 활성/완료 문서가 하나도 없으면 빈 리스트."""
    project = await _make_project(db, "P")
    inactive = await _make_document(db, project.id, name="inactive", is_active=False)
    await _make_chunk(db, inactive.id, project.id, embedding=_vec(0.1))

    results = await rag_svc.search_similar_chunks(
        project_id=project.id,
        query="A query",
        top_k=10,
        db=db,
    )

    assert results == []
