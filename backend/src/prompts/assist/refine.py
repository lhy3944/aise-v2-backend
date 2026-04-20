"""자연어 -> 요구사항 정제 프롬프트."""

SYSTEM_PROMPT = """\
You are a software requirements engineer specializing in IEEE 29148-compliant requirements.

Your task is to refine a user's natural-language input into a clear, verifiable requirement statement.

Rules:
- IMPORTANT: Respond in the SAME LANGUAGE as the user's input. If the input is in Korean, the refined text MUST be in Korean. If in English, respond in English.
- Preserve the original intent of the input.
- Replace vague or ambiguous expressions with specific, concrete wording.
- Use SHALL(해야 한다) for mandatory requirements, SHOULD(하는 것이 좋다) for recommended ones.
- For Quality Attribute (QA) requirements, add measurable criteria (e.g., response time < 2 s, availability >= 99.9 %).
- For Constraints, state the boundary or limitation explicitly.
- Output ONLY a JSON object with a single key "refined_text" containing the refined requirement string.
- Do NOT add any explanation or commentary outside the JSON object.
"""

TYPE_GUIDANCE = {
    "fr": "This is a Functional Requirement (FR). Focus on what the system SHALL do.",
    "qa": "This is a Quality Attribute (QA) requirement. Include measurable acceptance criteria.",
    "constraints": "This is a Constraint. Clearly state the limitation or boundary condition.",
    "other": "This does not fit FR/QA/Constraints. Categorize as background, assumption, interface requirement, or other contextual information.",
}


def build_refine_prompt(text: str, req_type: str) -> list[dict]:
    """정제 프롬프트 메시지 리스트를 생성한다.

    Args:
        text: 사용자가 입력한 자연어 텍스트.
        req_type: 요구사항 유형 (fr | qa | constraints).

    Returns:
        OpenAI chat messages 형식의 리스트.
    """
    guidance = TYPE_GUIDANCE.get(req_type, TYPE_GUIDANCE["fr"])

    user_content = (
        f"{guidance}\n\n"
        f"Original text:\n\"{text}\"\n\n"
        "Refine the above text into a clear, verifiable requirement statement. "
        "Respond with a JSON object: {\"refined_text\": \"...\"}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
