"""CriticAgent — verifies the integrity of the previous agent's output.

Phase 2 minimum implementation:
    - checks that every `[N]` citation in `state["final_answer"]` maps to a
      valid `ref` number in `state["sources"]`.
    - produces a short audit summary so users (and plan executors) can see
      whether the prior answer is well-grounded.

Intended use inside a plan:
    knowledge_qa → critic
or:
    srs_generator → critic   (future: schema sanity, requirement coverage)

The agent purposely does **not** call an LLM. Citation integrity is a
deterministic check; adding an LLM here would just reintroduce
non-determinism that `retrieval_gate` and `query_rewriter` work to remove.

Output contract (partial state update):
    - `final_answer`: short human-readable audit summary (keeps streaming
      UX consistent with other agents).
    - `critic_report`: dict
        {
          "passed": bool,
          "issues": list[str],
          "checked_citations": int,
          "valid_citations": int,
        }
    - `error`: set only when prerequisites (a prior final_answer) are
      missing — surfaces as a clean AGENT_ERROR.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.orchestration.state import AgentContext, AgentState


CITATION_RE = re.compile(r"\[(\d+)\]")


def _collect_citations(text: str) -> list[int]:
    """Returns every `[N]` citation as int, preserving duplicates.

    Duplicates matter when reporting "N citations checked".
    """
    if not text:
        return []
    return [int(m.group(1)) for m in CITATION_RE.finditer(text)]


def _valid_refs(sources: list[dict[str, Any]] | None) -> set[int]:
    """Set of 1-based refs considered valid. Falls back to positional index
    when a source entry lacks an explicit `ref` field (tolerant parsing).
    """
    if not sources:
        return set()
    refs: set[int] = set()
    for i, src in enumerate(sources):
        ref = src.get("ref") if isinstance(src, dict) else None
        if isinstance(ref, int) and ref > 0:
            refs.add(ref)
        else:
            refs.add(i + 1)
    return refs


@register_agent
class CriticAgent(BaseAgent):
    capability = AgentCapability(
        name="critic",
        description=(
            "직전 에이전트의 답변 품질을 검증한다. 현재는 답변 본문의 "
            "[N] 인용이 실제 sources 목록의 유효 ref 를 가리키는지 "
            "결정론적으로 확인한다. 사용자가 '답변 검증', '인용 확인', "
            "'출처 맞는지 봐줘' 등 **명시적으로** 검증을 요청할 때 선택한다. "
            "또한 plan 실행기가 knowledge_qa 등 RAG 에이전트 뒤에 자동으로 "
            "덧붙이는 단계로도 사용된다."
        ),
        triggers=[
            "답변 검증해줘",
            "인용이 맞는지 확인해줘",
            "출처 올바른지 봐줘",
            "이 답변 신뢰할 수 있어?",
        ],
        input_schema={"final_answer": "str", "sources": "list"},
        output_schema={
            "final_answer": "str",
            "critic_report": "dict",
        },
        tags=["verification", "quality"],
        estimated_tokens=0,  # deterministic check — no LLM call
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        answer = state.get("final_answer") or ""
        sources = state.get("sources") or []

        if not answer:
            logger.info("CriticAgent: no prior answer to verify")
            return {
                "error": "검증할 직전 답변이 없습니다. RAG 에이전트 뒤에서 호출해야 합니다."
            }

        citations = _collect_citations(answer)
        valid_refs = _valid_refs(sources)

        issues: list[str] = []
        valid_count = 0
        unknown_refs: set[int] = set()
        for ref in citations:
            if ref in valid_refs:
                valid_count += 1
            else:
                unknown_refs.add(ref)

        if unknown_refs:
            refs_str = ", ".join(f"[{r}]" for r in sorted(unknown_refs))
            issues.append(
                f"{refs_str} 인용은 제공된 출처 목록에 없습니다."
            )

        if not sources and citations:
            # 이 경우는 위에서 이미 unknown으로 잡혔지만, 별도 메시지로 명확화.
            issues.append(
                "답변은 [N] 인용을 포함하지만 sources 가 비어 있습니다."
            )

        passed = not issues
        report = {
            "passed": passed,
            "issues": issues,
            "checked_citations": len(citations),
            "valid_citations": valid_count,
        }

        if passed:
            if citations:
                summary = (
                    f"검증 통과 — {len(citations)}개 인용이 모두 출처 "
                    f"{len(sources)}건과 일치합니다."
                )
            else:
                summary = (
                    "검증 통과 — 답변에 인용이 없으나 sources 불일치도 없습니다."
                )
        else:
            summary_lines = ["검증 실패 — 다음 문제가 발견되었습니다:"]
            summary_lines.extend(f"• {msg}" for msg in issues)
            summary = "\n".join(summary_lines)

        logger.info(
            "CriticAgent: passed=%s checked=%d valid=%d",
            passed,
            len(citations),
            valid_count,
        )
        return {
            "final_answer": summary,
            "critic_report": report,
        }


__all__ = ["CriticAgent"]
