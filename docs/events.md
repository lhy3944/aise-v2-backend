# docs/events.md — Agent SSE 이벤트 계약

> **단일 원천 규칙**: 이 문서 + `backend/src/schemas/events.py` + `frontend/src/types/agent-events.ts` 세 파일은 **항상 동기화**되어야 한다. 이벤트 스키마를 변경할 때는 세 파일을 같은 PR에서 수정한다.
>
> **대상 엔드포인트**: `POST /api/v1/agent/chat` (SSE), `POST /api/v1/chat/{session_id}/resume` (SSE, Phase 3+)
>
> **포맷**: `text/event-stream` — 한 이벤트는 `data: <json>\n\n` 한 줄. JSON은 `{ "type": "...", "data": {...} }` 구조.

---

## 1. 이벤트 타입 전체 목록

| type | 발생 조건 | Phase 도입 |
|---|---|---|
| `token` | LLM 텍스트 토큰 스트리밍 | Phase 1 |
| `tool_call` | 에이전트가 도구(또는 하위 에이전트)를 호출 시작 | Phase 1 |
| `tool_result` | 도구 실행 완료 (성공 또는 실패) | Phase 1 |
| `plan_update` | Supervisor가 plan을 수립/갱신하거나 step 상태 변화 | Phase 2 |
| `sources` | 에이전트가 참조한 RAG chunk 목록 (본문 `[N]` 인용 앵커) | Phase 2 |
| `interrupt` | HITL — 사용자 응답 대기 (`interrupt()` 호출) | Phase 3 |
| `artifact_created` | SRS/Design/TC/Requirement 등 산출물 저장 완료 | Phase 2 |
| `done` | 스트리밍 종료 (정상/이유 포함) | Phase 1 |
| `error` | 복구 불가 오류 → 연결 종료 | Phase 1 |

**주의**: `interrupt` 이벤트가 나오면 `done`도 함께(직후) 나온다. `done.data.finish_reason === 'interrupt'`.

---

## 2. 이벤트 상세

### 2.1 `token` (Phase 1)

```json
{ "type": "token", "data": { "text": "안녕" } }
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.text` | string | ✅ | 토큰 텍스트 조각 (UTF-8 안전 청크) |

### 2.2 `tool_call` (Phase 1)

```json
{
  "type": "tool_call",
  "data": {
    "tool_call_id": "call_abc123",
    "name": "extract_records",
    "arguments": { "section_id": "uuid-..." },
    "agent": "requirement"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.tool_call_id` | string | ✅ | 이 호출의 고유 ID (이어지는 `tool_result`와 매칭) |
| `data.name` | string | ✅ | 도구 또는 에이전트 노드 이름 |
| `data.arguments` | object | ✅ | 구조화된 인자 (빈 객체 허용) |
| `data.agent` | string | 선택 | LangGraph 노드명. 멀티 에이전트 plan에서만 의미 |

### 2.3 `tool_result` (Phase 1)

```json
{
  "type": "tool_result",
  "data": {
    "tool_call_id": "call_abc123",
    "name": "extract_records",
    "status": "success",
    "duration_ms": 2340,
    "result": { "candidates_count": 12 }
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.tool_call_id` | string | ✅ | 호응되는 `tool_call`의 id |
| `data.name` | string | ✅ | 도구 이름 (로그/디버그용, 중복 OK) |
| `data.status` | `"success"` \| `"error"` | ✅ | |
| `data.duration_ms` | number | 선택 | 실행 소요 ms |
| `data.result` | any | 선택 | 도구 반환값. 실패 시 에러 요약 |

### 2.4 `plan_update` (Phase 2)

```json
{
  "type": "plan_update",
  "data": {
    "plan": [
      { "agent": "knowledge_qa", "status": "completed", "started_at": "...", "completed_at": "...", "result_summary": "문서 3건 참조" },
      { "agent": "requirement", "status": "running", "started_at": "..." },
      { "agent": "critic", "status": "pending" }
    ],
    "current_step": 1
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.plan` | `PlanStep[]` | ✅ | 전체 plan 스냅샷 (매 업데이트마다 전체 전송) |
| `data.current_step` | number | 선택 | 현재 진행 중 step의 0-based 인덱스 |

**PlanStep**:
| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `agent` | string | ✅ | 에이전트/노드 이름 |
| `status` | `"pending" \| "running" \| "completed" \| "failed" \| "skipped"` | ✅ | |
| `started_at` | ISO 8601 | 선택 | |
| `completed_at` | ISO 8601 | 선택 | |
| `result_summary` | string | 선택 | 사용자에게 보여줄 요약 |

### 2.5 `interrupt` (Phase 3)

HITL 3종(Clarify/Confirm/Decision)을 `data.kind`로 구분.

#### 2.5.1 `clarify` — 선택형 명확화

```json
{
  "type": "interrupt",
  "data": {
    "kind": "clarify",
    "interrupt_id": "int_xxx",
    "question": "인증 방식을 명확히 해주세요",
    "options": [
      { "value": "jwt", "label": "JWT 기반" },
      { "value": "oauth2", "label": "OAuth2 (Google/GitHub)" },
      { "value": "session", "label": "세션 기반" }
    ],
    "allow_custom": true,
    "context": { "request": "..." }
  }
}
```

#### 2.5.2 `confirm` — 승인형 확인

```json
{
  "type": "interrupt",
  "data": {
    "kind": "confirm",
    "interrupt_id": "int_yyy",
    "title": "REQ-003~007을 삭제하고 교체합니다",
    "description": "영향받는 항목이 있습니다",
    "impact": [
      { "label": "TC-012, TC-013, TC-017", "detail": "TestCase 3개 재생성 필요" },
      { "label": "SRS §3.2", "detail": "Functional Requirements 섹션" }
    ],
    "severity": "warning",
    "actions": { "approve": "승인", "reject": "거부", "modify": "수정 후 진행" }
  }
}
```

#### 2.5.3 `decision` — 다중 선택

```json
{
  "type": "interrupt",
  "data": {
    "kind": "decision",
    "interrupt_id": "int_zzz",
    "question": "포함할 비기능 요구사항 카테고리를 선택하세요",
    "options": [
      { "id": "perf", "label": "성능", "default": true },
      { "id": "sec", "label": "보안", "default": true },
      { "id": "a11y", "label": "접근성" }
    ],
    "min_selection": 1
  }
}
```

공통 필수: `interrupt_id` (resume body의 `interrupt_id`와 매칭), `kind`.

### 2.6 `sources` (Phase 2)

```json
{
  "type": "sources",
  "data": {
    "agent": "knowledge_qa",
    "sources": [
      {
        "ref": 1,
        "document_id": "uuid-...",
        "document_name": "요구사항_v3.pdf",
        "chunk_index": 4,
        "file_type": "pdf",
        "content_preview": "…",
        "score": 0.8712
      }
    ]
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.sources[].ref` | int (1-based) | ✅ | 본문의 `[N]` 인용 앵커와 매칭 |
| `data.sources[].document_id` | UUID str | ✅ | |
| `data.sources[].document_name` | string | ✅ | |
| `data.sources[].chunk_index` | int | ✅ | |
| `data.sources[].file_type` | string | 선택 | `pdf` / `md` / `txt` |
| `data.sources[].content_preview` | string | 선택 | 청크 본문 앞 200자 |
| `data.sources[].score` | float | 선택 | 1 − cosine distance |
| `data.agent` | string | 선택 | 산출 에이전트 (plan 실행 시 step 매칭용) |

**발행 타이밍**: single 경로는 `tool_result` 뒤, `token`(답변) 앞에서 1회. plan 경로는 sources를 산출한 step의 `tool_result` 직후에 emit.

### 2.7 `artifact_created` (Phase 2)

```json
{
  "type": "artifact_created",
  "data": {
    "artifact_id": "uuid-...",
    "artifact_type": "srs",
    "title": "SRS v1.0",
    "project_id": "uuid-...",
    "version": "1.0"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.artifact_id` | UUID | ✅ | |
| `data.artifact_type` | `"srs" \| "design" \| "testcase" \| "requirement_list" \| "records"` | ✅ | |
| `data.title` | string | ✅ | |
| `data.project_id` | UUID | ✅ | |
| `data.version` | string | 선택 | `"1.0"` 등 |

### 2.8 `done` (Phase 1)

```json
{ "type": "done", "data": { "finish_reason": "stop" } }
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.finish_reason` | `"stop" \| "tool_calls" \| "length" \| "content_filter" \| "interrupt" \| "error"` | ✅ | 종료 사유 |

### 2.9 `error` (Phase 1)

```json
{
  "type": "error",
  "data": { "message": "LLM timeout", "code": "LLM_TIMEOUT", "recoverable": false }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `data.message` | string | ✅ | 사용자에게 보일 수 있는 메시지 |
| `data.code` | string | 선택 | 기계 판독용 (예: `RATE_LIMIT`, `LLM_TIMEOUT`, `VALIDATION_ERROR`) |
| `data.recoverable` | boolean | 선택 | 재시도 권장 여부 |

---

## 3. 시퀀스 규약

### 3.1 단일 RAG 질의 (Phase 2)
```
tool_call → tool_result → sources → token × N → done(stop)
```
`sources`가 앞서 오므로 프론트는 답변 본문의 `[N]` 인용을 바로 링크로 매핑할 수 있다.

### 3.2 도구 호출 포함
```
token × N → tool_call → tool_result → token × M → done(stop)
```

### 3.3 Plan 기반 멀티 에이전트 (Phase 2)
```
plan_update(current_step=0, status=pending) →
plan_update(current_step=0, status=running) →
  tool_call → tool_result → [sources if any] →
plan_update(current_step=0, status=completed; current_step=1, status=running) →
  ...
plan_update(all completed) →
artifact_created →
done(stop)
```

### 3.4 HITL 개입 (Phase 3)
```
token × N → interrupt(clarify) → done(interrupt)
```
**프론트 응답 후** (`POST /chat/{session_id}/resume`):
```
token × M → done(stop)
```

### 3.5 에러
```
... → error(recoverable=false) → (연결 종료)
```
`error` 후 `done`은 나오지 않는다.

---

## 4. 동기화 규칙

| 변경 유형 | 필수 조치 |
|---|---|
| 신규 이벤트 추가 | `docs/events.md` + Pydantic + TS 3개 동시 수정, 버전 주석 업데이트 |
| 기존 이벤트 필드 추가 (선택) | 하위 호환. 3개 파일 동시 수정, 변경 로그 |
| 기존 이벤트 필드 삭제/타입 변경 | **Breaking** — 별도 논의. 가능하면 새 이벤트 타입 추가로 대체 |
| 이벤트 네이밍 변경 | Breaking — 절대 피한다. 폐기 시 새 이름 도입 후 Phase 간격 두고 제거 |

**검증**: CI에서 Pydantic `model_json_schema()` → JSON Schema 생성 → `agent-events.ts`와 대조하는 체크를 추가할 예정 (Phase 4).

---

## 5. 버전

| 버전 | 날짜 | 변경 |
|---|---|---|
| 1.0 | 2026-04-21 | 초기 계약: token/tool_call/tool_result/done/error (Phase 1 구현), plan_update/interrupt/artifact_created (Phase 2~3 도입 예정) |
| 1.1 | 2026-04-22 | `sources` 이벤트 추가 — 본문 `[N]` 인용의 백엔드 소유 메타데이터 채널 (ref/document_id/name/chunk_index + optional file_type/content_preview/score). legacy `[SOURCES]` 블록 프롬프트 의존 제거를 위함. |
