"""RecordManagerAgent — individual record CRUD/status changes with HITL.

`requirement` owns extraction from documents/user text. This agent owns
single-record mutations and never writes before a ConfirmData approval.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import register_agent
from src.core.exceptions import AppException
from src.models.artifact import Artifact
from src.models.requirement import RequirementSection
from src.orchestration.state import AgentContext, AgentState
from src.schemas.api.artifact_record import (
    ArtifactRecordCreate,
    ArtifactRecordStatusUpdate,
    ArtifactRecordUpdate,
)
from src.schemas.events import (
    ClarifyData,
    ClarifyOption,
    ConfirmActions,
    ConfirmData,
    ConfirmImpact,
)
from src.services import artifact_record_svc


_DISPLAY_ID_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,5}\b", re.IGNORECASE)


def _routing_params(state: AgentState) -> dict[str, Any]:
    routing = state.get("routing") or {}
    params = routing.get("action_params")
    return dict(params) if isinstance(params, dict) else {}


def _is_approved(response: dict[str, Any] | None) -> bool:
    if not response:
        return False
    return response.get("approved") is True or response.get("action") == "approve"


def _infer_display_id(text: str, params: dict[str, Any]) -> str | None:
    explicit = params.get("display_id") or params.get("target_display_id")
    if explicit:
        return str(explicit).upper()
    match = _DISPLAY_ID_RE.search(text or "")
    return match.group(0).upper() if match else None


def _infer_status(text: str, params: dict[str, Any]) -> str | None:
    raw = params.get("status")
    if raw in ("draft", "approved", "excluded"):
        return raw
    lowered = (text or "").lower()
    if "approved" in lowered or "승인" in lowered:
        return "approved"
    if "excluded" in lowered or "제외" in lowered:
        return "excluded"
    if "draft" in lowered or "초안" in lowered:
        return "draft"
    return None


def _infer_action(text: str, params: dict[str, Any]) -> str:
    raw = params.get("action")
    aliases = {
        "create": "create",
        "append": "create",
        "add": "create",
        "update": "update",
        "edit": "update",
        "delete": "delete",
        "remove": "delete",
        "status": "status_change",
        "status_change": "status_change",
    }
    if isinstance(raw, str) and raw in aliases:
        return aliases[raw]

    lowered = (text or "").lower()
    has_target = _DISPLAY_ID_RE.search(text or "") is not None
    if has_target and any(term in lowered for term in ("삭제", "delete", "remove")):
        return "delete"
    if has_target and any(term in lowered for term in ("상태", "status", "승인", "제외", "초안")):
        return "status_change"
    if has_target and any(term in lowered for term in ("수정", "바꿔", "변경", "update", "edit")):
        return "update"
    return "create"


def _infer_content(text: str, params: dict[str, Any]) -> str | None:
    for key in ("content", "text", "requirement", "record_content"):
        value = params.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    patterns = [
        r"레코드에\s*(.+?)\s*(?:추가|넣어|등록|생성|만들)",
        r"(.+?)\s*(?:을|를)?\s*레코드(?:로)?\s*(?:추가|등록|생성|만들)",
        r"(?:추가|등록|생성|만들).*?:\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if match:
            content = match.group(1).strip(" .。\"'")
            if content:
                return content

    if any(term in (text or "") for term in ("해야 한다", "가능해야", "필요하다", "지원해야")):
        return (text or "").strip()
    return None


async def _active_sections(ctx: AgentContext) -> list[RequirementSection]:
    return (
        await ctx.db.execute(
            select(RequirementSection)
            .where(
                RequirementSection.project_id == ctx.project_id,
                RequirementSection.is_active == True,  # noqa: E712
            )
            .order_by(RequirementSection.order_index.asc())
        )
    ).scalars().all()


async def _resolve_section_id(ctx: AgentContext, params: dict[str, Any]) -> uuid.UUID | None:
    raw_id = params.get("section_id")
    if raw_id:
        try:
            section_id = uuid.UUID(str(raw_id))
        except ValueError as exc:
            raise AppException(400, "유효하지 않은 섹션 ID입니다.") from exc
        section = await ctx.db.get(RequirementSection, section_id)
        if section is None or section.project_id != ctx.project_id or not section.is_active:
            raise AppException(400, "활성 섹션을 찾을 수 없습니다.")
        return section_id

    section_name = params.get("section_name")
    if isinstance(section_name, str) and section_name.strip():
        section = await artifact_record_svc.get_section_by_name(
            ctx.db, ctx.project_id, section_name.strip()
        )
        if section is None:
            raise AppException(400, "요청한 섹션을 찾을 수 없습니다.")
        return section.id

    return None


def _artifact_preview(artifact: Artifact | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    payload = artifact.content if isinstance(artifact.content, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return {
        "artifact_id": str(artifact.id),
        "display_id": artifact.display_id,
        "content": payload.get("text", ""),
        "status": metadata.get("status", "draft"),
        "working_status": artifact.working_status,
        "open_pr_id": str(artifact.open_pr_id) if artifact.open_pr_id else None,
    }


async def _load_target(ctx: AgentContext, display_id: str | None) -> Artifact | None:
    if not display_id:
        return None
    return await artifact_record_svc.get_record_by_display_id(
        ctx.db, ctx.project_id, display_id.upper()
    )


def _clarify(question: str, *, options: list[ClarifyOption] | None = None) -> dict[str, Any]:
    return {
        "kind": "interrupt",
        "data": ClarifyData(
            interrupt_id=f"itp_rec_clarify_{uuid.uuid4().hex[:12]}",
            question=question,
            options=options,
            allow_custom=True,
        ),
    }


@register_agent
class RecordManagerAgent(BaseAgent):
    capability = AgentCapability(
        name="record_manager",
        description=(
            "개별 요구사항 레코드의 추가, 수정, 삭제, 상태 변경을 담당한다. "
            "충분한 입력은 action(create/update/delete/status_change), 대상 display_id(수정/삭제/상태변경), "
            "content(추가/수정), status(상태변경), 선택적 section_id/section_name 이다. "
            "대상이 없거나 섹션/내용이 불충분하면 실행하지 말고 질문해야 한다."
        ),
        triggers=[
            "레코드에 MFA 추가해줘",
            "FR-003 수정해줘",
            "FR-001 삭제해줘",
            "FR-002 상태를 approved로 바꿔줘",
        ],
        input_schema={"project_id": "str", "user_input": "str"},
        output_schema={"final_answer": "str", "record_mutation": "dict"},
        tool_parameters={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "append", "update", "delete", "status_change"],
                },
                "display_id": {"type": "string"},
                "content": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "approved", "excluded"],
                },
                "section_id": {"type": "string"},
                "section_name": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string"},
            },
        },
        tags=["records", "mutation"],
        estimated_tokens=800,
        requires_hitl=True,
    )

    async def run(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        final: dict[str, Any] = {}
        async for ev in self.run_stream(state, ctx):
            if ev.get("kind") == "final":
                final = ev.get("update", {}) or {}
        return final

    async def run_stream(self, state: AgentState, ctx: AgentContext):
        hitl_response = state.get("hitl_response")
        if hitl_response is not None:
            proposal = state.get("record_manager_proposal") or {}
            if not _is_approved(hitl_response):
                msg = "레코드 변경을 취소했습니다."
                yield {"kind": "token", "text": msg}
                yield {
                    "kind": "final",
                    "update": {"final_answer": msg, "record_mutation": {"status": "rejected"}},
                }
                return

            try:
                result = await self._execute_proposal(ctx, proposal)
            except AppException as exc:
                yield {"kind": "token", "text": exc.detail}
                yield {"kind": "final", "update": {"final_answer": exc.detail}}
                return

            msg = result["message"]
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg, "record_mutation": result}}
            return

        try:
            proposal_or_interrupt = await self._build_proposal(state, ctx)
        except AppException as exc:
            yield {"kind": "token", "text": exc.detail}
            yield {"kind": "final", "update": {"final_answer": exc.detail}}
            return

        if proposal_or_interrupt.get("kind") == "interrupt":
            yield proposal_or_interrupt
            return

        proposal = proposal_or_interrupt
        if proposal.get("action") == "locked":
            msg = proposal.get("message") or "레코드가 잠겨 있어 변경하지 않았습니다."
            yield {"kind": "token", "text": msg}
            yield {"kind": "final", "update": {"final_answer": msg, "record_mutation": proposal}}
            return

        yield {"kind": "partial", "update": {"record_manager_proposal": proposal}}
        preview = proposal.get("preview") or {}
        action = proposal["action"]
        labels = {
            "create": "레코드 추가",
            "update": "레코드 수정",
            "delete": "레코드 삭제",
            "status_change": "레코드 상태 변경",
        }
        impacts = [
            ConfirmImpact(label="대상", detail=preview.get("display_id") or "새 레코드"),
            ConfirmImpact(label="작업", detail=labels.get(action, action)),
        ]
        content = preview.get("new_content")
        if content:
            impacts.append(ConfirmImpact(label="미리보기", detail=str(content)[:160]))

        yield {
            "kind": "interrupt",
            "data": ConfirmData(
                interrupt_id=f"itp_rec_{uuid.uuid4().hex[:12]}",
                title=f"{labels.get(action, action)}을(를) 진행할까요?",
                description="승인 전에는 데이터베이스를 변경하지 않습니다.",
                impact=impacts,
                context={"proposal": proposal},
                severity="danger" if action == "delete" else "warning",
                actions=ConfirmActions(approve="승인", reject="취소"),
            ),
        }

    async def _build_proposal(self, state: AgentState, ctx: AgentContext) -> dict[str, Any]:
        params = _routing_params(state)
        text = state.get("user_input") or ""
        action = _infer_action(text, params)
        display_id = _infer_display_id(text, params)
        target = await _load_target(ctx, display_id)

        if action in ("update", "delete", "status_change"):
            if display_id is None:
                return _clarify("어떤 레코드(display_id)를 변경할까요?")
            if target is None:
                return _clarify(f"{display_id} 레코드를 찾지 못했습니다. display_id를 다시 확인해주세요.")
            if target.working_status == "staged" or target.open_pr_id is not None:
                msg = (
                    f"{target.display_id}는 열린 PR에 의해 잠겨 있어 변경할 수 없습니다 "
                    f"(open_pr_id={target.open_pr_id})."
                )
                return {"action": "locked", "preview": _artifact_preview(target), "message": msg}

        if action == "create":
            content = _infer_content(text, params)
            if not content:
                sections = await _active_sections(ctx)
                options = [
                    ClarifyOption(value=str(s.id), label=s.name, description=s.type)
                    for s in sections[:6]
                ] or None
                return _clarify("새 레코드에 넣을 요구사항 문장을 알려주세요.", options=options)
            section_id = await _resolve_section_id(ctx, params)
            return {
                "action": "create",
                "content": content,
                "section_id": str(section_id) if section_id else None,
                "preview": {"display_id": None, "new_content": content},
            }

        if action == "update":
            content = _infer_content(text, params)
            if not content:
                return _clarify(f"{display_id} 레코드를 어떤 내용으로 수정할까요?")
            section_id = await _resolve_section_id(ctx, params)
            return {
                "action": "update",
                "artifact_id": str(target.id),
                "display_id": target.display_id,
                "content": content,
                "section_id": str(section_id) if section_id else None,
                "preview": {
                    **(_artifact_preview(target) or {}),
                    "new_content": content,
                },
            }

        if action == "delete":
            return {
                "action": "delete",
                "artifact_id": str(target.id),
                "display_id": target.display_id,
                "preview": _artifact_preview(target),
            }

        status = _infer_status(text, params)
        if status is None:
            return _clarify(f"{display_id} 레코드 상태를 draft, approved, excluded 중 무엇으로 바꿀까요?")
        return {
            "action": "status_change",
            "artifact_id": str(target.id),
            "display_id": target.display_id,
            "status": status,
            "preview": {**(_artifact_preview(target) or {}), "new_status": status},
        }

    async def _execute_proposal(self, ctx: AgentContext, proposal: dict[str, Any]) -> dict[str, Any]:
        action = proposal.get("action")
        if action == "locked":
            return {
                "status": "locked",
                "message": proposal.get("message") or "레코드가 잠겨 있어 변경하지 않았습니다.",
            }

        if action == "create":
            section_id = proposal.get("section_id")
            response = await artifact_record_svc.create_record(
                ctx.db,
                ctx.project_id,
                ArtifactRecordCreate(
                    content=str(proposal.get("content") or ""),
                    section_id=uuid.UUID(section_id) if section_id else None,
                ),
            )
            return {
                "status": "created",
                "display_id": response.display_id,
                "artifact_id": response.artifact_id,
                "message": f"{response.display_id} 레코드를 추가했습니다.",
            }

        artifact_id = uuid.UUID(str(proposal.get("artifact_id")))
        if action == "update":
            section_id = proposal.get("section_id")
            update = ArtifactRecordUpdate(content=str(proposal.get("content") or ""))
            if section_id:
                update.section_id = uuid.UUID(section_id)
            response = await artifact_record_svc.update_record(
                ctx.db,
                ctx.project_id,
                artifact_id,
                update,
            )
            return {
                "status": "updated",
                "display_id": response.display_id,
                "artifact_id": response.artifact_id,
                "message": f"{response.display_id} 레코드를 수정했습니다.",
            }

        if action == "delete":
            await artifact_record_svc.delete_record(ctx.db, ctx.project_id, artifact_id)
            display_id = str(proposal.get("display_id") or "")
            return {
                "status": "deleted",
                "display_id": display_id,
                "artifact_id": str(artifact_id),
                "message": f"{display_id} 레코드를 삭제했습니다.",
            }

        if action == "status_change":
            status = proposal.get("status")
            if status not in ("draft", "approved", "excluded"):
                raise AppException(400, "유효하지 않은 레코드 상태입니다.")
            response = await artifact_record_svc.update_record_status(
                ctx.db,
                ctx.project_id,
                artifact_id,
                ArtifactRecordStatusUpdate(status=status),
            )
            return {
                "status": "status_changed",
                "display_id": response.display_id,
                "artifact_id": response.artifact_id,
                "record_status": response.status,
                "message": f"{response.display_id} 상태를 {response.status}(으)로 변경했습니다.",
            }

        raise AppException(400, "지원하지 않는 레코드 작업입니다.")


__all__ = ["RecordManagerAgent"]
