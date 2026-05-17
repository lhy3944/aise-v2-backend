"""TestCaseGeneratorAgent — produces TestCase artifacts from the latest
completed SRS document.

Thin wrapper around `services.testcase_svc.generate_testcases`; LLM calls,
JSON parsing, artifact persistence all live there so HTTP endpoints can
reuse the same path later.

Output contract (partial state update):
    - `final_answer`: short human-readable summary (count + SRS version)
    - `testcases_generated`: dict
        {
          "based_on_srs_id": str,
          "srs_version": int,
          "testcase_count": int,
          "skipped_section_count": int,
        }
      Consumed by the UI (N5 TestCaseList) and plan chaining.
    - `error`: set when SRS / sections are missing.
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.orchestration.state import AgentContext, AgentState
from src.services import testcase_svc


@register_agent
class TestCaseGeneratorAgent(BaseAgent):
    capability = AgentCapability(
        name="testcase_generator",
        description=(
            "프로젝트의 최신 SRS 문서를 기반으로 테스트케이스를 생성해 "
            "artifact_type='testcase' Artifact 로 저장한다. 사용자가 "
            "'테스트케이스 생성', 'TC 만들어줘', '검증 시나리오 뽑아줘' 등 "
            "**명시적으로** TC 생성을 요청할 때만 선택한다. "
            "테스트케이스 삭제/제거 요청도 이 에이전트가 처리한다."
        ),
        triggers=[
            "테스트케이스 생성해줘",
            "TC 만들어줘",
            "검증 시나리오 뽑아줘",
            "테스트 시나리오 작성",
            "테스트케이스 삭제해줘",
            "TC 전부 제거해줘",
        ],
        tool_parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["generate", "delete_all"],
                    "description": "TC action. '생성' = generate, '삭제/제거' = delete_all.",
                },
            },
            "required": ["action"],
        },
        input_schema={"project_id": "str", "action": "str"},
        output_schema={
            "final_answer": "str",
            "testcases_generated": "dict",
        },
        tags=["generation", "testcase", "artifact"],
        estimated_tokens=12000,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        logger.info(f"TestCaseGeneratorAgent run: project={ctx.project_id}")

        # HITL resume: 승인/거부 후 실행
        hitl_response = state.get("hitl_response")
        if hitl_response is not None:
            is_approved = (
                hitl_response.get("approved") is True
                or hitl_response.get("action") == "approve"
            )
            if not is_approved:
                return {"final_answer": "테스트케이스 삭제가 취소되었습니다."}

            saved_action = (state.get("records_extracted") or [])
            action = "generate"
            for item in saved_action:
                if isinstance(item, dict) and item.get("_type") == "tc_action":
                    action = item.get("action", "generate")
                    break

            if action == "delete_all":
                count = await testcase_svc.delete_all_testcases(ctx.db, ctx.project_id)
                return {"final_answer": f"테스트케이스 {count}개를 삭제했습니다."}
            # generate 는 아래 로직으로 폴스루

        # 라우팅에서 action 추출
        routing = state.get("routing") or {}
        action_params = routing.get("action_params") or {}
        action = action_params.get("action", "generate")

        if action == "delete_all":
            count = await testcase_svc.delete_all_testcases(ctx.db, ctx.project_id)
            return {"final_answer": f"테스트케이스 {count}개를 삭제했습니다."}

        # 기본: TC 생성
        try:
            response = await testcase_svc.generate_testcases(
                ctx.db,
                ctx.project_id,
                personal_skill_instructions=state.get("personal_skill_instructions"),
            )
        except AppException as exc:
            logger.warning(
                f"TestCaseGeneratorAgent: testcase_svc rejected: {exc.detail}"
            )
            return {"error": exc.detail}

        count = len(response.testcases)
        skipped = response.skipped_sections
        summary_parts = [
            f"SRS v{response.srs_version} 기반으로 "
            f"테스트케이스 {count}개 생성."
        ]
        if skipped:
            summary_parts.append(f"생략된 섹션: {len(skipped)}건.")
        summary = " ".join(summary_parts)

        return {
            "final_answer": summary,
            "testcases_generated": {
                "based_on_srs_id": response.based_on_srs_id,
                "srs_version": response.srs_version,
                "testcase_count": count,
                "skipped_section_count": len(skipped),
            },
        }


__all__ = ["TestCaseGeneratorAgent"]
