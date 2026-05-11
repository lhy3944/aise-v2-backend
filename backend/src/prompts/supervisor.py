"""Supervisor prompt loader + formatter.

Separates the prompt text (markdown, under `prompts/supervisor.md`) from
the runtime wiring so the prompt can be iterated without redeploying —
and so tests can assert the expected shape without reading the file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.agents.base import AgentCapability


_PROMPT_PATH = Path(__file__).with_name("supervisor.md")
_TOOLUSE_PROMPT_PATH = Path(__file__).with_name("supervisor_tooluse.md")


def _load_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _load_tooluse_template() -> str:
    return _TOOLUSE_PROMPT_PATH.read_text(encoding="utf-8")


def _format_agents(capabilities: Iterable[AgentCapability]) -> str:
    lines: list[str] = []
    for cap in capabilities:
        triggers = ", ".join(cap.triggers) if cap.triggers else "(none)"
        tags = ", ".join(cap.tags) if cap.tags else "(none)"
        lines.append(
            f"- **{cap.name}** — {cap.description}\n"
            f"  triggers: {triggers}\n"
            f"  tags: {tags}"
        )
    return "\n".join(lines) if lines else "(no agents registered)"


def _format_history(history: list[dict]) -> str:
    if not history:
        return "(no prior turns)"
    rendered: list[str] = []
    for turn in history[-6:]:  # cap to keep token cost bounded
        role = turn.get("role", "user")
        content = str(turn.get("content", "")).strip()
        if not content:
            continue
        rendered.append(f"{role}: {content}")
    return "\n".join(rendered) if rendered else "(no prior turns)"


def build_supervisor_prompt(
    *,
    user_input: str,
    capabilities: Iterable[AgentCapability],
    history: list[dict] | None = None,
) -> str:
    """Assemble the routing prompt for one user turn."""
    template = _load_template()
    return template.format(
        agents=_format_agents(capabilities),
        history=_format_history(history or []),
        user_input=user_input.strip(),
    )


def build_supervisor_tooluse_messages(
    *,
    user_input: str,
    snapshot: str,
    rag_signal: dict | None = None,
) -> list[dict]:
    template = _load_tooluse_template()
    rag_text = "(none)"
    if rag_signal:
        rag_text = "\n".join(f"- {k}: {v}" for k, v in rag_signal.items())
    return [
        {
            "role": "system",
            "content": (
                "You are a routing supervisor. Use tool calls for agent routing. "
                "If clarification is needed, return content beginning with CLARIFY:."
            ),
        },
        {
            "role": "user",
            "content": template.format(
                snapshot=snapshot,
                rag_signal=rag_text,
                user_input=user_input.strip(),
            ),
        },
    ]


__all__ = ["build_supervisor_prompt", "build_supervisor_tooluse_messages"]
