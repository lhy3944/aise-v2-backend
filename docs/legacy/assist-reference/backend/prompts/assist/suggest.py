"""기존 요구사항 기반 누락 요구사항 보완 제안 프롬프트."""

SYSTEM_PROMPT = """\
You are a requirements analysis expert. Given an existing set of software requirements, \
identify gaps and suggest additional requirements that are missing.

Rules:
- Do NOT duplicate or rephrase existing requirements.
- Each suggestion must cover a genuinely missing aspect (e.g., error handling, edge cases, \
non-functional qualities, security, accessibility, performance, etc.).
- Provide a concise reason explaining why each suggestion is needed.
- Classify each suggestion as one of: "fr" (Functional Requirement), "qa" (Quality Attribute), \
"constraints" (Constraint), or "other" (background, assumption, interface, etc.).
- Output ONLY a JSON object with a single key "suggestions" containing an array of objects, \
each with keys: "type", "text", "reason".
- Do NOT add any explanation or commentary outside the JSON object.
"""


def build_suggest_prompt(requirements: list[dict]) -> list[dict]:
    """보완 제안 프롬프트 메시지 리스트를 생성한다.

    Args:
        requirements: 기존 요구사항 목록. 각 dict에는 "type"과 "text" 키가 포함된다.

    Returns:
        OpenAI chat messages 형식의 리스트.
    """
    if not requirements:
        req_block = "(No existing requirements provided.)"
    else:
        lines = []
        for i, req in enumerate(requirements, 1):
            req_type = req.get("type", "fr").upper()
            text = req.get("text", "")
            lines.append(f"{i}. [{req_type}] {text}")
        req_block = "\n".join(lines)

    user_content = (
        "Existing requirements:\n"
        f"{req_block}\n\n"
        "Analyze the above requirements and suggest missing ones. "
        "Respond with a JSON object: {\"suggestions\": [{\"type\": \"...\", \"text\": \"...\", \"reason\": \"...\"}]}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
