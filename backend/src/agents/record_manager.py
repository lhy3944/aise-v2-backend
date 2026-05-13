"""RecordManagerAgent — 개별 요구사항 레코드 CRUD.

전체 문서 추출이 아닌 개별 레코드 조작(append/delete/update/status_change)을 담당.
전체 문서 추출은 RequirementAgent가 담당.

Preflight 규칙:
- append: 내용이 충분하면 후보 생성 후 confirm, 섹션 모호하면 질문
- delete/update/status_change: display_id 조회, 없거나 여러 후보면 clarify
- staged/open PR이면 lock 상태 설명하고 실행 안 함
- 승인 전에는 DB를 변경하지 않음 — confirm payload에 미리보기만 저장
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.orchestration.state import AgentContext, AgentState
from src.schemas.events import ConfirmActions, ConfirmData
from src.services import artifact_record_svc


_ACTION_LABELS: dict[str, str] = {
    "append": "추가",
    "delete": "삭제",
    "update": "수정",
    "status_change": "상태 변경",
}

_STATUS_LABELS: dict[str, str] = {
    "draft": "초안",
    "approved": "승인",
    "excluded": "제외",
}


def _resolve_action(routing: dict[str, Any]) -> str:
    params = routing.get("action_params") or {}
    action = params.get("action", "")
    if action in ("append", "delete", "update", "status_change"):
        return action
    return "append"


def _resolve_params(routing: dict[str, Any]) -> dict[str, Any]:
    return routing.get("action_params") or {}


@register_agent
class RecordManagerAgent(BaseAgent):
    capability = AgentCapability(
        name="record_manager",
        description=(
            "개별 요구사항 레코드를 추가/수정/삭제/상태변경한다. "
            "전체 문서 추출은 requirement 에이전트. "
            "사용자가 특정 레코드 ID(OVR-002, FR-003 등)와 함께 추가/수정/삭제/승인/제외를 "
            "요청하면 반드시 이 에이전트를 사용한다. "
            "'승인해줘'는 status_change(target_status=approved)를 의미한다. "
            "충분한 정보가 없으면 질문한다: 대상 display_id, 섹션, 내용 등. "
            "승인 전에는 DB를 변경하지 않는다."
        ),
        triggers=[
            "레코드 추가해줘",
            "FR-003 삭제해줘",
            "FR-001 승인해줘",
            "이 레코드 수정해줘",
            "OVR-002 승인해줘",
        ],
        tool_parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["append", "delete", "update", "status_change"],
                    "description": "CRUD action. '승인' = status_change, '추가' = append, '수정' = update, '삭제' = delete.",
                },
                "display_id": {
                    "type": "string",
                    "description": "Target record display ID (e.g. FR-003, OVR-002). For single record operations.",
                },
                "display_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiple record display IDs for batch operations (e.g. ['OVR-002','OVR-003','OVR-004','OVR-005']). Use for range or multi-record requests like 'OVR-002 ~ OVR-005'.",
                },
                "filter_status": {
                    "type": "string",
                    "enum": ["draft", "approved", "excluded"],
                    "description": "Batch: change ALL records with this status. Use instead of display_id for bulk operations like '초안을 모두 승인해줘'.",
                },
                "content": {
                    "type": "string",
                    "description": "Record text content. Required for append and update.",
                },
                "target_status": {
                    "type": "string",
                    "enum": ["draft", "approved", "excluded"],
                    "description": "Target status for status_change action. '승인' → approved, '초안' → draft, '제외' → excluded.",
                },
            },
            "required": ["action"],
        },
        input_schema={
            "action": "str",
            "display_id": "str",
            "display_ids": "list[str]",
            "filter_status": "str",
            "content": "str",
            "target_status": "str",
        },
        output_schema={"final_answer": "str"},
        tags=["records", "crud"],
        estimated_tokens=600,
        requires_hitl=True,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        result: dict[str, Any] = {}
        async for ev in self.run_stream(state, ctx):
            if ev.get("kind") == "final":
                result = ev.get("update", {}) or {}
        return result

    async def run_stream(
        self, state: AgentState, ctx: AgentContext
    ):  # noqa: C901 — intentional branching by CRUD mode
        routing = state.get("routing") or {}
        action = _resolve_action(routing)
        params = _resolve_params(routing)

        # ── resume 경로: 승인된 CRUD 실행 ──────────────────────────
        hitl_response = state.get("hitl_response")
        if hitl_response is not None:
            is_approved = (
                hitl_response.get("approved") is True
                or hitl_response.get("action") == "approve"
            )
            if not is_approved:
                yield {"kind": "token", "text": "작업이 취소되었습니다."}
                yield {"kind": "final", "update": {"final_answer": "작업 취소"}}
                return

            # resume 시 action_params는 accumulated_state에서 복원
            acc = state.get("records_extracted") or []
            saved_action = None
            saved_params = {}
            # interrupt 전에 partial로 저장한 action 정보 복원
            for item in acc:
                if isinstance(item, dict) and item.get("_type") == "action_params":
                    saved_action = item.get("action")
                    saved_params = item
                    break

            resume_action = saved_action or action
            resume_params = saved_params or params

            async for ev in self._execute_crud(resume_action, resume_params, ctx):
                yield ev
            return

        # ── 첫 호출 경로: preflight → confirm interrupt ────────────
        display_id = params.get("display_id")
        display_ids = params.get("display_ids") or []
        filter_status = params.get("filter_status")
        content = params.get("content")
        target_status = params.get("target_status")

        # 배치 모드 판별
        is_batch_status = action == "status_change" and filter_status and not display_id
        is_multi_id = bool(display_ids) and not display_id

        # Preflight: append 시 내용 확인
        if action == "append" and not content:
            msg = "추가할 레코드의 내용을 알려주세요. 예: '사용자는 MFA를 설정할 수 있어야 한다'"
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg}}
            return

        # Preflight: delete/update/status_change 시 display_id, display_ids, 또는 filter_status 필수
        if action in ("delete", "update", "status_change") and not display_id and not display_ids and not filter_status:
            msg = f"{_ACTION_LABELS.get(action, action)}할 레코드의 ID를 알려주세요. 예: 'FR-003'"
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg}}
            return

        # Preflight: 대상 레코드 조회 (단일 ID 모드만)
        target_record = None
        if action in ("delete", "update", "status_change") and display_id and not is_batch_status and not is_multi_id:
            target_record = await artifact_record_svc.get_record_by_display_id(
                ctx.db, ctx.project_id, display_id
            )
            if target_record is None:
                msg = f"'{display_id}' 레코드를 찾을 수 없습니다. 올바른 ID인지 확인해주세요."
                yield {"kind": "token", "text": msg}
                yield {"kind": "final", "update": {"final_answer": msg}}
                return

        # Preflight: status_change 시 target_status 필수
        if action == "status_change" and not target_status:
            msg = "변경할 상태를 알려주세요. 선택: draft, approved, excluded"
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg}}
            return

        # ── ConfirmData 구성 ───────────────────────────────────────
        interrupt_id = f"itp_rm_{uuid.uuid4().hex[:12]}"

        if is_batch_status:
            # 배치 상태변경: 대상 레코드 수 조회
            all_records = await artifact_record_svc.list_records(ctx.db, ctx.project_id)
            matching = [r for r in all_records.records if r.status == filter_status]
            count = len(matching)
            if count == 0:
                msg = f"{_STATUS_LABELS.get(filter_status, filter_status)} 상태의 레코드가 없습니다."
                yield {"kind": "token", "text": msg}
                yield {"kind": "final", "update": {"final_answer": msg}}
                return
            title = f"{_STATUS_LABELS.get(filter_status, filter_status)} 레코드 {count}개를 {_STATUS_LABELS.get(target_status, target_status)}(으)로 변경하시겠습니까?"
            description = f"현재 {_STATUS_LABELS.get(filter_status, filter_status)} {count}개 → {_STATUS_LABELS.get(target_status, target_status)} {count}개"
            severity = "warning"
        elif is_multi_id:
            # 복수 ID 상태변경/삭제
            id_list = ", ".join(display_ids)
            count = len(display_ids)
            if action == "status_change":
                title = f"{count}개 레코드({id_list})의 상태를 {_STATUS_LABELS.get(target_status, target_status)}(으)로 변경하시겠습니까?"
                description = f"대상: {id_list} ({count}개)"
            elif action == "delete":
                title = f"{count}개 레코드({id_list})를 삭제하시겠습니까?"
                description = f"이 작업은 되돌리기 어렵습니다."
            else:
                title = f"{count}개 레코드에 작업을 실행하시겠습니까?"
                description = f"대상: {id_list}"
            severity = "warning"
        elif action == "append":
            title = "다음 레코드를 추가하시겠습니까?"
            description = f"내용: {content}"
            severity = "info"
        elif action == "delete":
            payload = artifact_record_svc._payload(target_record)
            preview = payload.get("text", "")[:80]
            title = f"'{display_id}' 레코드를 삭제하시겠습니까?"
            description = f"내용: {preview}{'...' if len(preview) < len(payload.get('text', '')) else ''}\n이 작업은 되돌리기 어렵습니다."
            severity = "danger"
        elif action == "update":
            title = f"'{display_id}' 레코드를 수정하시겠습니까?"
            description = f"새 내용: {content}"
            severity = "warning"
        elif action == "status_change":
            payload = artifact_record_svc._payload(target_record)
            current = payload.get("metadata", {}).get("status", "draft")
            title = f"'{display_id}' 레코드의 상태를 변경하시겠습니까?"
            description = (
                f"현재 상태: {_STATUS_LABELS.get(current, current)} → "
                f"변경 상태: {_STATUS_LABELS.get(target_status, target_status)}"
            )
            severity = "info"
        else:
            title = "작업을 실행하시겠습니까?"
            description = ""
            severity = "info"

        # action_params를 partial로 누적 — resume 시 복원
        action_data = {"_type": "action_params", "action": action}
        action_data.update(params)

        yield {"kind": "partial", "update": {"records_extracted": [action_data]}}

        yield {
            "kind": "interrupt",
            "data": ConfirmData(
                interrupt_id=interrupt_id,
                title=title,
                description=description,
                severity=severity,
                actions=ConfirmActions(approve="확인", reject="취소"),
                context={"action": action, "display_id": display_id, "content": content, "target_status": target_status},
            ),
        }

    async def _execute_crud(
        self, action: str, params: dict[str, Any], ctx: AgentContext
    ):
        """승인된 CRUD 작업을 실행한다."""
        display_id = params.get("display_id")
        display_ids = params.get("display_ids") or []
        filter_status = params.get("filter_status")
        content = params.get("content")
        target_status = params.get("target_status")

        # 배치 모드 판별
        is_batch_status = action == "status_change" and filter_status and not display_id
        is_multi_id = bool(display_ids) and not display_id

        try:
            if is_batch_status:
                from src.schemas.api.artifact_record import ArtifactRecordStatusUpdate

                all_records = await artifact_record_svc.list_records(ctx.db, ctx.project_id)
                matching = [r for r in all_records.records if r.status == filter_status]
                changed = 0
                for rec in matching:
                    try:
                        aid = uuid.UUID(str(rec.artifact_id))
                        status_data = ArtifactRecordStatusUpdate(status=target_status)
                        await artifact_record_svc.update_record_status(
                            ctx.db, ctx.project_id, aid, status_data
                        )
                        changed += 1
                    except Exception:
                        logger.warning(f"batch status_change failed for {rec.display_id}")
                msg = f"{_STATUS_LABELS.get(filter_status, filter_status)} 레코드 {changed}개를 {_STATUS_LABELS.get(target_status, target_status)}(으)로 변경했습니다."

            elif is_multi_id:
                from src.schemas.api.artifact_record import ArtifactRecordStatusUpdate

                succeeded: list[str] = []
                failed: list[str] = []
                for did in display_ids:
                    target = await artifact_record_svc.get_record_by_display_id(
                        ctx.db, ctx.project_id, did
                    )
                    if target is None:
                        failed.append(did)
                        continue
                    try:
                        if action == "status_change":
                            status_data = ArtifactRecordStatusUpdate(status=target_status)
                            await artifact_record_svc.update_record_status(
                                ctx.db, ctx.project_id, target.id, status_data
                            )
                        elif action == "delete":
                            await artifact_record_svc.delete_record(
                                ctx.db, ctx.project_id, target.id
                            )
                        elif action == "update":
                            from src.schemas.api.artifact_record import ArtifactRecordUpdate

                            update_data = ArtifactRecordUpdate(content=content)
                            await artifact_record_svc.update_record(
                                ctx.db, ctx.project_id, target.id, update_data
                            )
                        else:
                            failed.append(did)
                            continue
                        succeeded.append(did)
                    except Exception:
                        logger.warning(f"multi-id {action} failed for {did}")
                        failed.append(did)

                parts = [f"{len(succeeded)}개 완료"]
                if failed:
                    parts.append(f"{len(failed)}개 실패({', '.join(failed)})")
                action_label = _ACTION_LABELS.get(action, action)
                msg = f"레코드 {action_label} — {', '.join(parts)}"

            elif action == "append":
                from src.schemas.api.artifact_record import ArtifactRecordCreate

                section_id = params.get("section_id")
                parsed_section = None
                if section_id:
                    try:
                        parsed_section = uuid.UUID(str(section_id))
                    except (ValueError, TypeError):
                        parsed_section = None

                create_data = ArtifactRecordCreate(
                    content=content or "",
                    section_id=parsed_section,
                )
                result = await artifact_record_svc.create_record(
                    ctx.db, ctx.project_id, create_data
                )
                msg = f"레코드를 추가했습니다. (ID: {result.display_id})"

            elif action == "delete":
                target = await artifact_record_svc.get_record_by_display_id(
                    ctx.db, ctx.project_id, display_id
                )
                if target is None:
                    msg = f"'{display_id}' 레코드를 찾을 수 없습니다."
                else:
                    await artifact_record_svc.delete_record(
                        ctx.db, ctx.project_id, target.id
                    )
                    msg = f"'{display_id}' 레코드를 삭제했습니다."

            elif action == "update":
                target = await artifact_record_svc.get_record_by_display_id(
                    ctx.db, ctx.project_id, display_id
                )
                if target is None:
                    msg = f"'{display_id}' 레코드를 찾을 수 없습니다."
                else:
                    from src.schemas.api.artifact_record import ArtifactRecordUpdate

                    update_data = ArtifactRecordUpdate(content=content)
                    await artifact_record_svc.update_record(
                        ctx.db, ctx.project_id, target.id, update_data
                    )
                    msg = f"'{display_id}' 레코드를 수정했습니다."

            elif action == "status_change":
                target = await artifact_record_svc.get_record_by_display_id(
                    ctx.db, ctx.project_id, display_id
                )
                if target is None:
                    msg = f"'{display_id}' 레코드를 찾을 수 없습니다."
                else:
                    from src.schemas.api.artifact_record import ArtifactRecordStatusUpdate

                    status_data = ArtifactRecordStatusUpdate(
                        status=target_status
                    )
                    await artifact_record_svc.update_record_status(
                        ctx.db, ctx.project_id, target.id, status_data
                    )
                    msg = f"'{display_id}' 레코드 상태를 {_STATUS_LABELS.get(target_status, target_status)}(으)로 변경했습니다."
            else:
                msg = f"알 수 없는 작업: {action}"

        except Exception as exc:
            logger.exception(f"RecordManager CRUD failed: action={action}")
            msg = f"작업 실행 중 오류가 발생했습니다: {exc}"

        yield {"kind": "token", "text": msg}
        yield {"kind": "final", "update": {"final_answer": msg}}


__all__ = ["RecordManagerAgent"]
