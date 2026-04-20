"""요구사항 Review 프롬프트 -- 충돌(conflict) + 중복(duplicate) 검출 + 해결 힌트(1줄)."""

SYSTEM_PROMPT = """\
You are a requirements engineer. Review the given requirements and detect conflicts and duplicates.

Issue types:
- "conflict": Two or more requirements contradict each other or impose incompatible constraints.
- "duplicate": Two or more requirements express the same intent with different or identical wording.

For each issue:
- "type": "conflict" | "duplicate"
- "description": Clear explanation of the issue (1-2 sentences).
- "related_requirements": The display_ids of the related requirements.
- "hint": A brief resolution suggestion (1 sentence).

Rules:
- Output ONLY a JSON object with "issues" and "summary".
- Do NOT detect ambiguities or missing requirements.
- "ready_for_next" is always true (issues are warnings, not blockers).
- Respond in the SAME LANGUAGE as the user's input requirements.

Output format:
{
  "issues": [
    {
      "type": "conflict" | "duplicate",
      "description": "...",
      "related_requirements": ["FR-001", "FR-003"],
      "hint": "..."
    }
  ],
  "summary": {
    "total_issues": 0,
    "conflicts": 0,
    "duplicates": 0,
    "ready_for_next": true,
    "feedback": "..."
  }
}
"""


def build_requirements_review_prompt(requirements_data: list[dict]) -> list[dict]:
    """요구사항 Review 프롬프트 메시지 리스트를 생성한다.

    Args:
        requirements_data: 요구사항 목록. 각 dict에는 "req_id", "display_id", "type", "text" 키가 포함된다.

    Returns:
        OpenAI chat messages 형식의 리스트.
    """
    if not requirements_data:
        req_block = "(No requirements provided.)"
    else:
        lines = []
        for req in requirements_data:
            display_id = req.get("display_id", "unknown")
            req_type = req.get("type", "fr").upper()
            text = req.get("text", "")
            lines.append(f"- [{display_id}] [{req_type}] {text}")
        req_block = "\n".join(lines)

    user_content = (
        "Review the following requirements for conflicts and duplicates.\n\n"
        f"Requirements:\n{req_block}\n\n"
        "Respond with a JSON object containing \"issues\" and \"summary\"."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
