"""Conversational query rewriter 단위 테스트."""

from __future__ import annotations

import pytest

from src.services import llm_svc, query_rewriter


async def test_rewrite_returns_raw_when_history_empty(monkeypatch):
    """history가 비어 있으면 LLM 호출 없이 원문을 그대로 돌려준다."""
    called: list[list[dict]] = []

    async def should_not_be_called(**_):  # pragma: no cover - asserted via called list
        called.append(_)
        return ""

    monkeypatch.setattr(llm_svc, "chat_completion", should_not_be_called)
    out = await query_rewriter.rewrite_query("글로벌 기업 AI 에이전트 사례", [])
    assert out == "글로벌 기업 AI 에이전트 사례"
    assert called == []


async def test_rewrite_returns_raw_when_user_input_empty():
    assert await query_rewriter.rewrite_query("", []) == ""
    assert await query_rewriter.rewrite_query("   ", []) == ""


async def test_rewrite_folds_in_history_via_llm(monkeypatch):
    """history가 있으면 LLM 호출로 standalone query를 얻어 정리한다."""

    async def fake(messages, **kwargs):
        # Returns a wrapped rewrite to exercise strip/cleanup code.
        return '  "글로벌 기업들의 AI 에이전트 적용 사례"  \n extra line ignored'

    monkeypatch.setattr(llm_svc, "chat_completion", fake)
    history = [
        {"role": "user", "content": "글로벌 기업들의 AI 에이전트 적용 사례를 알려줘"},
        {"role": "assistant", "content": "실시간 검색 없이..."},
    ]
    out = await query_rewriter.rewrite_query("프로젝트 문서 기반으로 대답해", history)
    assert out == "글로벌 기업들의 AI 에이전트 적용 사례"


async def test_rewrite_falls_back_to_raw_on_llm_failure(monkeypatch):
    """LLM이 예외를 던지면 원문으로 폴백해 검색 자체는 계속 진행시킨다."""

    async def boom(messages, **kwargs):
        raise RuntimeError("llm down")

    monkeypatch.setattr(llm_svc, "chat_completion", boom)
    history = [{"role": "user", "content": "이전 질문"}]
    out = await query_rewriter.rewrite_query("이 문서 기반으로", history)
    assert out == "이 문서 기반으로"


async def test_rewrite_rejects_abnormally_long_llm_output(monkeypatch):
    """비정상적으로 긴 응답은 신뢰하지 않고 원문으로 폴백."""

    async def fake(messages, **kwargs):
        return "x" * 2000

    monkeypatch.setattr(llm_svc, "chat_completion", fake)
    out = await query_rewriter.rewrite_query(
        "정상 질문", [{"role": "user", "content": "이전"}]
    )
    assert out == "정상 질문"
