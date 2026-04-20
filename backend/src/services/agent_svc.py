"""Agent Chat 서비스 -- SSE 스트리밍 + Function Calling 기반 대화"""

import json
import re
import uuid
from collections.abc import AsyncGenerator
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session
from src.models.glossary import GlossaryItem
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.project import Project
from src.models.requirement import Requirement
from src.models.session import Session
from src.prompts.agent.chat import build_agent_chat_prompt
from src.schemas.api.record import RecordCreate, RecordUpdate, RecordStatusUpdate
from src.services import embedding_svc, session_svc, record_svc
from src.services.llm_svc import get_client, _get_default_model
from src.services.rag_svc import search_similar_chunks

# 프론트에서 실행하는 도구 (백엔드는 SSE 이벤트만 전달)
FRONTEND_TOOLS = {"extract_records", "generate_srs"}

# 백엔드에서 직접 실행하는 도구 (결과를 LLM에 다시 전달)
BACKEND_TOOLS = {
    "create_record", "update_record", "delete_record",
    "update_record_status", "search_records",
}

# Function Calling 도구 정의
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_records",
            "description": (
                "지식 문서에서 섹션별 요구사항 레코드를 추출하여 후보 목록을 생성합니다. "
                "사용자가 '레코드 추출해줘', '요구사항을 뽑아줘', '레코드 생성' 등 "
                "레코드 추출을 **명시적으로** 요청할 때만 호출합니다. "
                "단순 문서 질의(내용 요약, 검색, 설명 요청)에는 호출하지 않습니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section_id": {
                        "type": "string",
                        "description": "특정 섹션만 추출할 경우 섹션 ID. 전체 추출 시 생략.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_srs",
            "description": "승인된 레코드를 기반으로 SRS 문서를 생성합니다. 사용자가 SRS 생성, 문서 작성 등을 요청할 때 호출합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_record",
            "description": (
                "새 요구사항 레코드를 생성합니다. "
                "사용자가 '요구사항 추가해줘', 'FR 하나 만들어줘' 등 개별 레코드 생성을 요청할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "레코드 본문 (요구사항 내용)",
                    },
                    "section_name": {
                        "type": "string",
                        "description": "섹션 이름 (예: 'Functional Requirements', 'Quality Attributes'). 미지정 시 기본 섹션에 배치.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_record",
            "description": (
                "기존 레코드의 내용을 수정합니다. "
                "사용자가 'FR-001 수정해줘', '이 요구사항 내용을 바꿔줘' 등 수정을 요청할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "display_id": {
                        "type": "string",
                        "description": "수정할 레코드의 display_id (예: FR-001, QA-003)",
                    },
                    "content": {
                        "type": "string",
                        "description": "수정할 새 내용",
                    },
                },
                "required": ["display_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_record",
            "description": (
                "레코드를 삭제합니다. "
                "사용자가 'FR-003 삭제해줘', '이 요구사항 제거' 등 삭제를 요청할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "display_id": {
                        "type": "string",
                        "description": "삭제할 레코드의 display_id (예: FR-001)",
                    },
                },
                "required": ["display_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_record_status",
            "description": (
                "레코드의 상태를 변경합니다 (draft, approved, excluded). "
                "사용자가 'FR-001 승인해줘', 'FR-002 제외해줘' 등 상태 변경을 요청할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "display_id": {
                        "type": "string",
                        "description": "상태를 변경할 레코드의 display_id",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "approved", "excluded"],
                        "description": "변경할 상태",
                    },
                },
                "required": ["display_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_records",
            "description": (
                "프로젝트의 레코드를 검색합니다. "
                "사용자가 '보안 관련 요구사항 찾아줘', 'FR 목록 보여줘' 등 검색을 요청할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 키워드 (display_id 또는 내용)",
                    },
                    "section_name": {
                        "type": "string",
                        "description": "특정 섹션 내에서만 검색할 경우 섹션 이름",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


async def stream_chat(
    session_id: uuid.UUID,
    message: str,
) -> AsyncGenerator[str, None]:
    """Agent Chat SSE 스트리밍 응답 생성 (Function Calling 지원)

    자체 DB 세션을 생성하여 StreamingResponse 수명 동안 유지.
    (FastAPI Depends의 DB 세션은 라우터 함수 반환 시 닫히므로 사용 불가)

    Yields SSE events:
    - data: {"type": "token", "content": "..."} -- 텍스트 토큰
    - data: {"type": "tool_call", "name": "...", "arguments": {...}} -- 도구 호출
    - data: {"type": "done"} -- 스트리밍 완료
    - data: {"type": "error", "content": "..."} -- 에러
    """
    async with async_session() as db:
        try:
            # 1. 세션 조회
            session = await db.get(Session, session_id)
            if not session:
                yield _sse_event({"type": "error", "content": "세션을 찾을 수 없습니다."})
                return

            project_id = session.project_id

            # 2. user 메시지 저장
            await session_svc.add_message(db, session_id, "user", message)
            await session_svc.update_session_title_if_first(db, session_id, message)
            await db.commit()

            # 3. DB에서 history 로드
            history = await session_svc.get_history(db, session_id, limit=50)

            # 4. 프로젝트 조회
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                yield _sse_event({"type": "error", "content": "프로젝트를 찾을 수 없습니다."})
                return

            # 5. Knowledge 검색 (RAG)
            knowledge_chunks = await _fetch_knowledge_chunks(project_id, message, db)

            # 6. Glossary 조회
            glossary = await _fetch_glossary(project_id, db)

            # 7. 기존 요구사항 조회
            requirements = await _fetch_requirements(project_id, db)

            # 7-1. 레코드 조회 (에이전트 컨텍스트용)
            records = await _fetch_records(project_id, db)

            # 8. 시스템 프롬프트 빌드
            system_prompt = build_agent_chat_prompt(
                project_name=project.name,
                project_description=project.description,
                project_domain=project.domain,
                knowledge_context=knowledge_chunks,
                glossary=glossary,
                requirements=requirements,
                records=records,
            )

            # 9. 메시지 구성 (DB에서 로드한 history 사용 — 마지막 user 메시지 포함)
            messages = [{"role": "system", "content": system_prompt}]
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})

            logger.info(
                f"Agent Chat 스트리밍 시작: session_id={session_id}, project_id={project_id}, "
                f"messages={len(messages)}개, knowledge={len(knowledge_chunks)}개"
            )

            # 10. LLM 스트리밍 호출 (Function Calling 포함 + 백엔드 도구 루프)
            client = get_client()
            all_tool_calls_data: list[dict] = []
            full_content = ""

            # 도구 루프: 백엔드 도구가 호출되면 결과를 LLM에 돌려주고 재호출
            while True:
                stream = await client.chat.completions.create(
                    model=_get_default_model(),
                    messages=messages,
                    tools=TOOLS,
                    temperature=0.3,
                    max_completion_tokens=4096,
                    stream=True,
                )

                # 스트리밍 청크 처리 — tool_call과 텍스트를 분리
                tool_call_chunks: dict[int, dict] = {}  # index → {id, name, arguments}
                round_content = ""

                async for chunk in stream:
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    # 텍스트 토큰
                    if delta.content:
                        round_content += delta.content
                        full_content += delta.content
                        yield _sse_event({"type": "token", "content": delta.content})

                    # Tool call 청크 누적
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_call_chunks:
                                tool_call_chunks[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_call_chunks[idx]["id"] = tc.id
                            if tc.function and tc.function.name:
                                tool_call_chunks[idx]["name"] = tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_call_chunks[idx]["arguments"] += tc.function.arguments

                # 도구 호출이 없으면 루프 종료
                if not tool_call_chunks:
                    break

                # 도구 호출 처리
                has_backend_tools = False
                parsed_tool_calls = []

                for idx in sorted(tool_call_chunks.keys()):
                    tc = tool_call_chunks[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    parsed_tool_calls.append({
                        "id": tc["id"],
                        "name": tc["name"],
                        "arguments": args,
                    })

                # assistant 메시지(tool_calls 포함)를 messages에 추가
                assistant_tool_msg: dict = {"role": "assistant", "content": round_content or None}
                assistant_tool_msg["tool_calls"] = [
                    {
                        "id": ptc["id"],
                        "type": "function",
                        "function": {
                            "name": ptc["name"],
                            "arguments": json.dumps(ptc["arguments"], ensure_ascii=False),
                        },
                    }
                    for ptc in parsed_tool_calls
                ]
                messages.append(assistant_tool_msg)

                for ptc in parsed_tool_calls:
                    tc_name = ptc["name"]
                    tc_args = ptc["arguments"]
                    tc_id = ptc["id"]

                    logger.info(f"Tool call 감지: name={tc_name}, args={tc_args}")

                    if tc_name in BACKEND_TOOLS:
                        # 백엔드에서 직접 실행
                        has_backend_tools = True
                        result = await _execute_backend_tool(
                            db, project_id, tc_name, tc_args,
                        )
                        # SSE로 결과 전송 (프론트 레코드 갱신용)
                        yield _sse_event({
                            "type": "tool_result",
                            "name": tc_name,
                            "arguments": tc_args,
                            "result": result,
                        })
                        all_tool_calls_data.append({
                            "name": tc_name,
                            "arguments": tc_args,
                        })
                        # tool result를 messages에 추가하여 LLM이 사용자에게 요약 가능
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                    else:
                        # 프론트에서 실행할 도구 — SSE 이벤트만 전송
                        yield _sse_event({
                            "type": "tool_call",
                            "name": tc_name,
                            "arguments": tc_args,
                        })
                        all_tool_calls_data.append({
                            "name": tc_name,
                            "arguments": tc_args,
                        })
                        # 프론트 도구는 LLM 재호출 불필요 — 더미 결과 추가
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": json.dumps({"status": "delegated_to_frontend"}, ensure_ascii=False),
                        })

                if not has_backend_tools:
                    # 프론트 전용 도구만 호출된 경우 루프 종료
                    break

                # 백엔드 도구 결과가 있으면 LLM 재호출하여 사용자에게 요약 생성

            # 10-1. [SOURCES] 블록 보완 (LLM이 누락하거나 불완전한 경우)
            # 프론트엔드 파서는 복수 [SOURCES] 블록을 모두 수집하므로 추가 블록만 append
            if knowledge_chunks:
                text_refs = set()
                for m in re.finditer(r"\[(\d+)\]", full_content):
                    ref_num = int(m.group(1))
                    if 1 <= ref_num <= len(knowledge_chunks):
                        text_refs.add(ref_num)

                if text_refs:
                    existing_refs: set[int] = set()
                    for sm in re.finditer(r"\[SOURCES\]\s*([\s\S]*?)\s*\[/SOURCES\]", full_content):
                        try:
                            existing_refs.update(s["ref"] for s in json.loads(sm.group(1)))
                        except (json.JSONDecodeError, KeyError):
                            pass

                    missing_refs = text_refs - existing_refs
                    if missing_refs:
                        sources = [
                            {
                                "ref": ref,
                                "document_id": knowledge_chunks[ref - 1]["document_id"],
                                "document_name": knowledge_chunks[ref - 1]["document_name"],
                                "chunk_index": knowledge_chunks[ref - 1]["chunk_index"],
                                "file_type": knowledge_chunks[ref - 1].get("file_type", "txt"),
                            }
                            for ref in sorted(missing_refs)
                        ]
                        extra_block = f"\n\n[SOURCES]\n{json.dumps(sources, ensure_ascii=False)}\n[/SOURCES]"
                        full_content += extra_block
                        yield _sse_event({"type": "token", "content": extra_block})

            # 11. assistant 메시지 저장
            await session_svc.add_message(
                db, session_id, "assistant", full_content,
                tool_calls=all_tool_calls_data if all_tool_calls_data else None,
            )
            await db.commit()

            yield _sse_event({"type": "done"})
            logger.info(f"Agent Chat 스트리밍 완료: session_id={session_id}")

        except Exception as e:
            logger.error(f"Agent Chat 스트리밍 실패: {e}")
            yield _sse_event({"type": "error", "content": f"AI 응답 생성에 실패했습니다: {str(e)}"})


async def _execute_backend_tool(
    db: AsyncSession,
    project_id: uuid.UUID,
    tool_name: str,
    args: dict,
) -> dict:
    """백엔드 도구 실행 → 결과 딕셔너리 반환"""
    try:
        if tool_name == "create_record":
            content = args.get("content", "")
            section_name = args.get("section_name")
            section_id = None
            if section_name:
                section = await record_svc.get_section_by_name(db, project_id, section_name)
                if section:
                    section_id = str(section.id)

            data = RecordCreate(content=content, section_id=section_id)
            result = await record_svc.create_record(db, project_id, data)
            return {
                "success": True,
                "record_id": result.record_id,
                "display_id": result.display_id,
                "section_name": result.section_name,
                "content": result.content,
                "status": result.status,
            }

        elif tool_name == "update_record":
            display_id = args.get("display_id", "")
            content = args.get("content", "")
            record = await record_svc.get_record_by_display_id(db, project_id, display_id)
            if not record:
                return {"success": False, "error": f"레코드 '{display_id}'를 찾을 수 없습니다."}

            data = RecordUpdate(content=content)
            result = await record_svc.update_record(db, project_id, record.id, data)
            return {
                "success": True,
                "record_id": result.record_id,
                "display_id": result.display_id,
                "content": result.content,
                "status": result.status,
            }

        elif tool_name == "delete_record":
            display_id = args.get("display_id", "")
            record = await record_svc.get_record_by_display_id(db, project_id, display_id)
            if not record:
                return {"success": False, "error": f"레코드 '{display_id}'를 찾을 수 없습니다."}

            await record_svc.delete_record(db, project_id, record.id)
            return {"success": True, "deleted": True, "display_id": display_id}

        elif tool_name == "update_record_status":
            display_id = args.get("display_id", "")
            status = args.get("status", "draft")
            record = await record_svc.get_record_by_display_id(db, project_id, display_id)
            if not record:
                return {"success": False, "error": f"레코드 '{display_id}'를 찾을 수 없습니다."}

            old_status = record.status
            data = RecordStatusUpdate(status=status)
            result = await record_svc.update_record_status(db, project_id, record.id, data)
            return {
                "success": True,
                "display_id": result.display_id,
                "old_status": old_status,
                "new_status": result.status,
            }

        elif tool_name == "search_records":
            query = args.get("query", "")
            section_name = args.get("section_name")
            results = await record_svc.search_records(
                db, project_id, query, section_name=section_name,
            )
            return {
                "success": True,
                "count": len(results),
                "records": [
                    {
                        "display_id": r.display_id,
                        "section_name": r.section_name,
                        "content": r.content,
                        "status": r.status,
                    }
                    for r in results
                ],
            }

        else:
            return {"success": False, "error": f"알 수 없는 도구: {tool_name}"}

    except Exception as e:
        logger.error(f"백엔드 도구 실행 실패: {tool_name} - {e}")
        return {"success": False, "error": str(e)}


async def _fetch_records(project_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    """현재 프로젝트의 레코드 목록 조회 (에이전트 컨텍스트용)"""
    try:
        result = await record_svc.list_records(db, project_id)
        return [
            {
                "display_id": r.display_id,
                "section_name": r.section_name,
                "content": r.content,
                "status": r.status,
            }
            for r in result.records
        ]
    except Exception as e:
        logger.warning(f"레코드 조회 실패 (계속 진행): {e}")
        return []


async def _fetch_knowledge_chunks(
    project_id: uuid.UUID,
    message: str,
    db: AsyncSession,
) -> list[dict]:
    try:
        chunks_with_scores = await search_similar_chunks(project_id, message, 5, db)
        doc_ids = {c.document_id for c, _ in chunks_with_scores}
        doc_info_map: dict[uuid.UUID, tuple[str, str]] = {}
        if doc_ids:
            doc_result = await db.execute(
                select(KnowledgeDocument.id, KnowledgeDocument.name, KnowledgeDocument.file_type)
                .where(KnowledgeDocument.id.in_(doc_ids))
            )
            for did, dname, ftype in doc_result.all():
                doc_info_map[did] = (dname, ftype)

        # 문서 내 순서(chunk_index)로 정렬하여 ref 번호가 직관적이도록 함
        results = [
            {
                "document_id": str(chunk.document_id),
                "document_name": doc_info_map.get(chunk.document_id, ("Unknown", "txt"))[0],
                "file_type": doc_info_map.get(chunk.document_id, ("Unknown", "txt"))[1],
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
            }
            for chunk, score in chunks_with_scores
        ]
        results.sort(key=lambda c: (c["document_name"], c["chunk_index"]))
        return results
    except Exception as e:
        logger.warning(f"Knowledge 검색 실패 (계속 진행): {e}")
        return []


async def _fetch_glossary(project_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    try:
        g_result = await db.execute(
            select(GlossaryItem)
            .where(GlossaryItem.project_id == project_id)
            .order_by(GlossaryItem.term)
        )
        return [{"term": g.term, "definition": g.definition} for g in g_result.scalars().all()]
    except Exception as e:
        logger.warning(f"Glossary 조회 실패 (계속 진행): {e}")
        return []


async def _fetch_requirements(project_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    try:
        r_result = await db.execute(
            select(Requirement)
            .where(Requirement.project_id == project_id, Requirement.is_selected == True)  # noqa: E712
            .order_by(Requirement.order_index)
        )
        return [
            {
                "display_id": r.display_id,
                "type": r.type,
                "original_text": r.original_text,
                "refined_text": r.refined_text,
            }
            for r in r_result.scalars().all()
        ]
    except Exception as e:
        logger.warning(f"요구사항 조회 실패 (계속 진행): {e}")
        return []


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
