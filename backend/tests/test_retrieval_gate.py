"""Retrieval-first routing gate 단위 테스트.

Gate가 supervisor LLM 없이 결정적으로 knowledge_qa로 라우팅하는지,
skip 케이스(인사말, 문서 없음, threshold 미달)에서 None을 반환하는지,
그리고 캐시에 임베딩·rewritten query가 저장되는지를 검증한다.

LLM/embedding 호출은 모두 stub.
"""

from __future__ import annotations

import uuid

import pytest

from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.orchestration import retrieval_gate
from src.orchestration.retrieval_gate import evaluate_gate
from src.services import embedding_svc, query_rewriter


def _vec(value: float) -> list[float]:
    return [value] * 1536


@pytest.fixture(autouse=True)
def _enable_gate(monkeypatch):
    """Gate는 기본 활성 — 다른 테스트 세션이 꺼두었더라도 여기선 켠다."""
    monkeypatch.setenv("RAG_GATE_ENABLED", "true")
    # 결정적 threshold — 아래 테스트들이 이 값에 맞춰 설계됨.
    monkeypatch.setenv("RAG_GATE_THRESHOLD", "0.5")


@pytest.fixture
def stub_rewriter_passthrough(monkeypatch):
    """query_rewriter가 LLM을 건드리지 않도록 input을 그대로 반환."""

    async def passthrough(user_input: str, history):
        return user_input

    monkeypatch.setattr(query_rewriter, "rewrite_query", passthrough)
    # retrieval_gate는 query_rewriter 모듈에서 rewrite_query를 직접 import 하므로
    # 그 레퍼런스도 동일하게 교체한다.
    monkeypatch.setattr(retrieval_gate, "rewrite_query", passthrough)


async def _seed(db, *, chunk_vector: list[float] | None = None) -> Project:
    """문서 1개 + 청크 1개를 심어 둔 프로젝트를 리턴."""
    project = Project(name="gate-test", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    doc = KnowledgeDocument(
        project_id=project.id,
        name="doc.md",
        file_type="md",
        size_bytes=10,
        storage_key=f"{uuid.uuid4()}.md",
        status="completed",
        chunk_count=1,
        is_active=True,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    chunk = KnowledgeChunk(
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="hello",
        token_count=1,
        embedding=chunk_vector or _vec(0.1),
    )
    db.add(chunk)
    await db.commit()
    return project


async def test_skip_when_small_talk(monkeypatch, db):
    """인사말은 embedding·DB 접근 없이 즉시 skip."""
    called = {"embeddings": 0}

    async def fake_embeddings(texts):  # pragma: no cover - asserted via counter
        called["embeddings"] += 1
        return [_vec(0.1)]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    project = await _seed(db)

    result = await evaluate_gate(
        user_input="안녕",
        history=[],
        project_id=project.id,
        db=db,
    )
    assert result is None
    assert called["embeddings"] == 0


async def test_skip_when_no_documents(monkeypatch, db):
    """문서가 없는 프로젝트에서는 embedding도 호출하지 않고 skip."""
    called = {"embeddings": 0}

    async def fake_embeddings(texts):  # pragma: no cover
        called["embeddings"] += 1
        return [_vec(0.1)]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)

    project = Project(name="empty", description="x")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    result = await evaluate_gate(
        user_input="글로벌 기업 AI 에이전트 사례",
        history=[],
        project_id=project.id,
        db=db,
    )
    assert result is None
    assert called["embeddings"] == 0


async def test_pass_when_score_above_threshold(
    monkeypatch, stub_rewriter_passthrough, db
):
    """Top-k score가 threshold 이상이면 knowledge_qa로 라우팅 + 캐시 구성."""

    async def fake_embeddings(texts):
        # Chunk와 동일 벡터 → cosine distance = 0 → score = 1.0 ≥ 0.5
        return [_vec(0.1)]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    project = await _seed(db, chunk_vector=_vec(0.1))

    result = await evaluate_gate(
        user_input="이 문서 내용 요약해줘",
        history=[],
        project_id=project.id,
        db=db,
    )
    assert result is not None
    assert result.routing["action"] == "single"
    assert result.routing["agent"] == "knowledge_qa"
    assert result.rag_cache["rewritten_query"] == "이 문서 내용 요약해줘"
    assert result.rag_cache["query_embedding"] == _vec(0.1)
    assert result.rag_cache["max_score"] >= 0.5


async def test_skip_when_score_below_threshold(
    monkeypatch, stub_rewriter_passthrough, db
):
    """Score가 threshold 미만이면 supervisor로 폴백(None)."""

    async def fake_embeddings(texts):
        # Query 벡터는 chunk와 크게 다른 방향 → cosine similarity 낮음.
        return [[1.0, -1.0] + [0.0] * 1534]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    # chunk는 전혀 다른 방향의 벡터로 심어 cosine distance > 0.5.
    project = await _seed(db, chunk_vector=[0.0, 1.0] + [0.0] * 1534)

    result = await evaluate_gate(
        user_input="완전 무관한 질문",
        history=[],
        project_id=project.id,
        db=db,
    )
    assert result is None


async def test_disabled_by_env(monkeypatch, db):
    """RAG_GATE_ENABLED=false면 embedding·DB 접근 없이 None."""
    monkeypatch.setenv("RAG_GATE_ENABLED", "false")
    called = {"embeddings": 0}

    async def fake_embeddings(texts):  # pragma: no cover
        called["embeddings"] += 1
        return [_vec(0.1)]

    monkeypatch.setattr(embedding_svc, "get_embeddings", fake_embeddings)
    project = await _seed(db)

    result = await evaluate_gate(
        user_input="이 문서 내용 요약해줘",
        history=[],
        project_id=project.id,
        db=db,
    )
    assert result is None
    assert called["embeddings"] == 0
