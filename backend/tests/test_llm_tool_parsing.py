"""LLM tool-call parsing tests."""

from __future__ import annotations

import pytest

from src.services import llm_svc


@pytest.fixture
def _fake_provider(monkeypatch):
    monkeypatch.setattr(llm_svc, "_litellm_kwargs", lambda client_type, model: {"model": "fake"})


async def _call(monkeypatch, response):
    async def fake_acompletion(**kwargs):
        assert kwargs["tools"] == [{"type": "function", "function": {"name": "x"}}]
        assert kwargs["tool_choice"] == "auto"
        return response

    monkeypatch.setattr(llm_svc.litellm, "acompletion", fake_acompletion)
    return await llm_svc.chat_completion_with_tools(
        [{"role": "user", "content": "route"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
    )


@pytest.mark.asyncio
async def test_tool_call_parses_arguments(monkeypatch, _fake_provider):
    response = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "record_manager",
                                "arguments": '{"action":"create","content":"MFA"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }

    parsed = await _call(monkeypatch, response)

    assert parsed.finish_reason == "tool_calls"
    assert parsed.content == ""
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0].name == "record_manager"
    assert parsed.tool_calls[0].arguments == {"action": "create", "content": "MFA"}
    assert parsed.tool_calls[0].arguments_error is None


@pytest.mark.asyncio
async def test_multiple_tool_calls(monkeypatch, _fake_provider):
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "a", "function": {"name": "knowledge_qa", "arguments": "{}"}},
                        {"id": "b", "function": {"name": "requirement", "arguments": '{"extract_mode":"document"}'}},
                    ]
                },
                "finish_reason": "tool_calls",
            }
        ]
    }

    parsed = await _call(monkeypatch, response)

    assert [c.name for c in parsed.tool_calls] == ["knowledge_qa", "requirement"]
    assert parsed.tool_calls[1].arguments["extract_mode"] == "document"


@pytest.mark.asyncio
async def test_content_only_response(monkeypatch, _fake_provider):
    response = {
        "choices": [
            {
                "message": {"content": "CLARIFY: 어떤 산출물인가요?"},
                "finish_reason": "stop",
            }
        ]
    }

    parsed = await _call(monkeypatch, response)

    assert parsed.content == "CLARIFY: 어떤 산출물인가요?"
    assert parsed.tool_calls == []
    assert parsed.finish_reason == "stop"


@pytest.mark.asyncio
async def test_invalid_tool_arguments_do_not_raise(monkeypatch, _fake_provider):
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "bad",
                            "function": {
                                "name": "record_manager",
                                "arguments": '{"action":',
                            },
                        }
                    ]
                },
                "finish_reason": "tool_calls",
            }
        ]
    }

    parsed = await _call(monkeypatch, response)

    assert parsed.tool_calls[0].arguments == {}
    assert parsed.tool_calls[0].raw_arguments == '{"action":'
    assert parsed.tool_calls[0].arguments_error
