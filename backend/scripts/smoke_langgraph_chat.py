"""Phase 1 USE_LANGGRAPH=true smoke test.

Hits POST /api/v1/agent/chat against a real seeded project+session in the
dev DB using the in-process ASGI transport (no uvicorn needed). Confirms
the LangGraph path produces the contract SSE sequence with real LLM
+ real embeddings + real RAG retrieval.

Usage (from backend/):
    USE_LANGGRAPH=true uv run python scripts/smoke_langgraph_chat.py \
        --session-id <uuid> --message "질문"

Override defaults via flags if the seeded data changes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx


DEFAULT_SESSION = "bfe68d29-a990-4a34-a2db-3a3be3303455"
DEFAULT_MESSAGE = "이 프로젝트의 주요 기능을 한 문장으로 요약해줘."


def _parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    for line in text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[len("data: "):]))
            except json.JSONDecodeError as exc:
                print(f"[warn] non-JSON data line: {line!r} ({exc})")
    return events


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", default=DEFAULT_SESSION)
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    args = parser.parse_args()

    if os.getenv("USE_LANGGRAPH", "false").lower() not in {"1", "true", "yes", "on"}:
        print("ERROR: USE_LANGGRAPH must be true for this smoke. Re-run with:")
        print('  USE_LANGGRAPH=true uv run python scripts/smoke_langgraph_chat.py ...')
        return 2

    # Import after env is set so any module-level reads see it.
    from src.main import app  # noqa: E402

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://smoke", timeout=60) as c:
        print(f"POST /api/v1/agent/chat  session={args.session_id}  message={args.message!r}")
        resp = await c.post(
            "/api/v1/agent/chat",
            json={"session_id": args.session_id, "message": args.message},
        )
        print(f"status={resp.status_code}  content-type={resp.headers.get('content-type')}")
        events = _parse_sse(resp.text)

    print(f"--- {len(events)} events ---")
    for ev in events:
        t = ev.get("type", "?")
        data = ev.get("data", {})
        if t == "token":
            txt = data.get("text", "")
            preview = txt[:80] + ("…" if len(txt) > 80 else "")
            print(f"  token  text={preview!r}")
        elif t == "tool_call":
            print(f"  tool_call  name={data.get('name')!r}  id={data.get('tool_call_id')!r}")
        elif t == "tool_result":
            print(
                f"  tool_result  name={data.get('name')!r}  status={data.get('status')!r}  "
                f"duration_ms={data.get('duration_ms')}  result={data.get('result')}"
            )
        elif t == "done":
            print(f"  done  finish_reason={data.get('finish_reason')!r}")
        elif t == "error":
            print(f"  error  code={data.get('code')!r}  message={data.get('message')!r}")
        else:
            print(f"  {t}  {data}")

    types = [ev.get("type") for ev in events]
    # Accept either single (tool_call/tool_result/token/done) or plan
    # (plan_update*/tool_call/tool_result × N/token/done) flows.
    has_agent_pair = "tool_call" in types and "tool_result" in types
    ok = (
        types
        and types[-1] == "done"
        and "error" not in types
        and has_agent_pair
    )
    print("\n" + ("PASS ✅" if ok else "FAIL ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
