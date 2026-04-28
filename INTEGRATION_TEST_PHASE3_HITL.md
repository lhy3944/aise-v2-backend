# Phase 3 HITL 통합 테스트 시나리오

> **대상**: PR-1 (백엔드 interrupt+resume 인프라) + PR-2 (RequirementAgent confirm 게이트) + PR-3 (프론트 HITLPromptModal) 통합 검증.
>
> **실행 환경**:
>
> ```bash
> ./start-dev.sh         # backend :9999, frontend :3009
> # 또는
> ./start-local.sh       # backend :8082, frontend :3009
> ```
>
> **사전 공통 조건** (모든 시나리오):
>
> 1. 프로젝트 1개 (`requirements` 모듈 활성)
> 2. 활성 섹션 ≥ 1 (FR/QA/Constraint 등)
> 3. 활성 지식 문서 ≥ 1 (status=`completed`, is_active=true)
> 4. 백엔드 LLM 키 설정 (extract_records 가 실제 LLM 호출)

---

## 시나리오 1: 추출 → 승인 (Happy Path)

**목적**: 정상 흐름 — interrupt 발행, 모달 응답, DB commit, UI 반영.

**단계**:

1. http://localhost:3009 → 프로젝트 진입
2. 채팅 입력란에 "요구사항 추출해줘" 입력 → 전송
3. 어시스턴트 카드에 `tool_call(requirement)` 표시
4. 잠시 후 **HITLPromptModal** 등장
5. 모달의 "승인" 버튼 클릭

**기대 SSE 시퀀스**:

| Step | 엔드포인트 | 이벤트 순서 |
|---|---|---|
| 2 | `POST /api/v1/agent/chat` | `tool_call(requirement)` → `interrupt(confirm)` → `done(interrupt)` |
| 5 | `POST /api/v1/agent/resume/{interrupt_id}` | `tool_call(requirement, resume_from=...)` → `token("N개 요구사항 후보를 승인했습니다.")` → `tool_result(success)` → `done(stop)` |

**기대 UI**:

- 모달 제목: `"{N}개 요구사항 후보를 승인하시겠습니까?"`
- 모달 본문: `"섹션 분포: FR(2), QA(1). 승인 시 모든 후보가 records 로 등록되며, 거부 시 폐기됩니다."`
- 승인 후 새 어시스턴트 메시지 turn 으로 "N개 요구사항 후보를 승인했습니다." 표시
- Records 탭이 자동 갱신되어 N건 신규 레코드 표시 (display_id 부여, status=`approved`)

**기대 DB**:

```sql
SELECT count(*) FROM artifacts
WHERE project_id = '<UUID>'
  AND artifact_type = 'record'
  AND content->>'is_auto_extracted' = 'true';
-- 시나리오 시작 전 카운트 + N
```

**기대 Records 카드 검증**:

- `confidence_score` 가 0 ~ 1 사이 값으로 노출 (PR-1 의 B 핫픽스 — null 아님)
- `source_document_id` 채워져 있음 (지식 문서 매칭 시)

---

## 시나리오 2: 추출 → 거부

**목적**: reject 분기에서 DB commit 이 발생하지 않는지 검증.

**단계**:

1. 시나리오 1 의 1~4 단계 동일
2. 모달의 "거부" 버튼 클릭

**기대 SSE 시퀀스**:

| Step | 엔드포인트 | 이벤트 |
|---|---|---|
| 2 | `POST /api/v1/agent/resume/{interrupt_id}` | `tool_call` → `token("요구사항 후보를 거부했습니다.")` → `tool_result(success, records_approved_count=0)` → `done(stop)` |

**기대 UI**:

- 새 어시스턴트 메시지: "요구사항 후보를 거부했습니다."

**기대 DB**:

```sql
SELECT count(*) FROM artifacts WHERE project_id = '<UUID>' AND artifact_type = 'record';
-- 시나리오 시작 전 카운트와 동일 (변화 없음)
```

---

## 시나리오 3: 후보 0개 — interrupt 미발행

**목적**: 추출 결과가 비어 있을 때 모달 띄우지 않고 즉시 정상 종료.

**사전 조건**: 활성 지식 문서가 비어 있거나 LLM 이 후보 0개를 반환할 만한 빈 문서로 교체.

**단계**:

1. 채팅에 "요구사항 추출해줘" 입력
2. 백엔드 응답 대기

**기대 SSE 시퀀스**:

- `tool_call(requirement)` → `token("추출된 요구사항 후보가 없습니다. ...")` → `tool_result(success, records_count=0)` → `done(stop)`

**기대 UI**:

- 모달 **등장하지 않음**
- 어시스턴트 메시지에 안내 텍스트만 표시

---

## 시나리오 4: 모달 dismiss — pendingHitl 폐기

**목적**: 사용자가 모달을 ESC / 배경 클릭으로 닫았을 때 동작 확인 (PR-3 한정 동작).

**단계**:

1. 시나리오 1 의 1~4 단계 동일
2. 모달 외부 영역 클릭 (또는 ESC 키)

**현재 동작** (PR-3 시점):

- 모달 닫힘 → 프론트 `pendingHitl` 클리어
- 백엔드 `hitl_state` 는 그대로 24h TTL 유지
- 사용자에게는 "재개" UI 가 없음 → resume 가 사실상 사용자 주도로 불가

**검증**:

```bash
# 백엔드에서 hitl_state 가 살아있는지 직접 호출 가능
curl -N -X POST http://localhost:9999/api/v1/agent/resume/<interrupt_id> \
  -H "Content-Type: application/json" \
  -d '{"interrupt_id":"<interrupt_id>","response":{"action":"approve"}}'
```

→ 정상 SSE 재개 (token + tool_result + done) 받아야 함.

**알려진 한계**: dismiss 후 UI 만으로는 재개 불가. PR-4 (ApprovalQueue) 에서 해결 예정.

---

## 시나리오 5: 만료된 thread_id로 resume

**목적**: TTL 만료 / 알 수 없는 thread_id 에 대한 에러 핸들링.

**단계**:

```bash
curl -N -X POST http://localhost:9999/api/v1/agent/resume/itp_does_not_exist \
  -H "Content-Type: application/json" \
  -d '{"interrupt_id":"itp_does_not_exist","response":{"action":"approve"}}'
```

**기대 SSE**:

```
data: {"type":"error","data":{"message":"hitl thread not found or expired","code":"HITL_THREAD_NOT_FOUND","recoverable":false}}
```

---

## 시나리오 6: interrupt_id 불일치 (라우터 검증)

**목적**: 경로의 thread_id 와 body 의 interrupt_id 가 다를 때 거부.

**단계**:

```bash
curl -N -X POST http://localhost:9999/api/v1/agent/resume/itp_a \
  -H "Content-Type: application/json" \
  -d '{"interrupt_id":"itp_b","response":{"action":"approve"}}'
```

**기대 SSE**:

```
data: {"type":"error","data":{"message":"interrupt_id mismatch","code":"HITL_ID_MISMATCH","recoverable":false}}
```

---

## 시나리오 7: 추출 두 번 연속 (각 thread 독립)

**목적**: 한 세션에서 추출을 두 번 요청했을 때 thread_id 가 독립적으로 관리되는지.

**단계**:

1. 채팅에 "요구사항 추출해줘" → 모달 A 등장 → "거부"
2. 다시 채팅에 "요구사항 다시 뽑아줘" → 모달 B 등장 → "승인"

**기대**:

- 모달 A 의 `interrupt_id` 와 모달 B 의 `interrupt_id` 가 다름
- A 거부 → DB 변경 없음
- B 승인 → DB 에 N건 추가
- session_messages 에 모든 turn 이 순서대로 저장됨 (user → assistant×2 → user → assistant×2)

**검증**:

```bash
# 세션 메시지 조회
curl http://localhost:9999/api/v1/sessions/<session_id> | jq '.messages | length'
# 기대: 6 (user, assistant(요청A), assistant(거부결과), user, assistant(요청B), assistant(승인결과))
```

---

## 시나리오 8: 라우팅 — 단순 질문은 HITL 안 거침

**목적**: requires_hitl 게이트가 RequirementAgent 에만 발동, 다른 에이전트 영향 없음.

**단계**:

1. 채팅에 "이 프로젝트의 핵심 기능 요약해줘" 입력 (knowledge_qa 라우팅)

**기대**:

- Supervisor 가 `single → knowledge_qa` 결정
- 모달 등장하지 않음
- 일반 token 스트리밍 + sources + done(stop)

---

## 시나리오 9: 빈 프로젝트 — 친절한 가이드 답변 (Records UX 개선)

**목적**: `extract_records` 가 raise 하는 AppException 이 빨간 ErrorEvent 가 아닌 채팅 가이드 답변으로 표시되는지.

**사전 조건**: 신규 프로젝트, **활성 지식 문서 0개** (업로드 안 함).

**단계**:

1. 프로젝트 진입 → 채팅에 "레코드 추출해줘" 입력

**기대 SSE 시퀀스**:

```
data: {"type":"tool_call","data":{...,"name":"requirement"}}
data: {"type":"token","data":{"text":"아직 분석할 지식 문서가 없습니다.\n좌측 사이드바의 ..."}}
data: {"type":"tool_result","data":{"status":"success",...}}
data: {"type":"done","data":{"finish_reason":"stop"}}
```

**기대 UI**:

- ❌ 빨간 에러 토스트 / `error` 카드 **표시되지 않음**
- ✅ 어시스턴트 메시지 말풍선에 가이드가 자연스럽게 표시:
  > 아직 분석할 지식 문서가 없습니다.
  > 좌측 사이드바의 '지식 문서' 메뉴에서 PDF·문서를 업로드하고 '활성' 토글을 켜주세요. ...
  > 또는 채팅창에 '우리 시스템은 ~~ 해야 한다' 같은 요구사항 문장을 직접 입력하셔도 좋고, 우측 'Records' 패널의 '직접 추가' 버튼으로 수동 등록도 가능합니다.

**검증 SQL**: 변경 없음 (artifacts 카운트 0 유지).

---

## 시나리오 10: 자유 입력 추출 (지식 문서 없이도 동작)

**목적**: Supervisor 가 진술문을 인식해 `extract_mode=user_text` 로 라우팅 → 지식 문서 없어도 추출 정상.

**사전 조건**: 신규 프로젝트, 지식 문서 0개, 활성 섹션 ≥ 1 (FR 등 기본 섹션).

**단계**:

1. 채팅에 "사용자는 OAuth 2.0 으로 로그인할 수 있어야 한다." 입력
2. 모달에 표시된 후보 검토 → "승인" 클릭

**기대 SSE 시퀀스**:

| Step | 이벤트 |
|---|---|
| 1 | `tool_call(requirement)` → `interrupt(confirm)` (description 에 **"채팅 입력에서 N개 후보를 추출했습니다"** 포함) → `done(interrupt)` |
| 2 | resume: `tool_call` → `token("N개 ... 승인했습니다")` → `tool_result(success)` → `done(stop)` |

**기대 UI**:

- ConfirmData 모달 제목: `"1개 요구사항 후보를 승인하시겠습니까?"`
- 본문: "채팅 입력에서 1개 요구사항 후보를 추출했습니다. 섹션 분포: ..."
- 승인 후 Records 탭 자동 갱신, 새 record 의 `source_location: "user_input"`, `is_auto_extracted: true`

**검증 SQL**:

```sql
SELECT content->>'source_location', content->>'is_auto_extracted'
FROM artifacts WHERE project_id = '<UUID>' AND artifact_type = 'record'
ORDER BY created_at DESC LIMIT 1;
-- 기대: 'user_input', 'true'
```

---

## 시나리오 11: 우측 판넬 빈 상태 — "직접 추가" 버튼

**목적**: Records 패널 빈 상태에서 폼 모달로 수동 입력.

**사전 조건**: Records 0개, 활성 섹션 ≥ 1.

**단계**:

1. Records 탭 열기 → 빈 상태 화면에 안내 텍스트 + "직접 추가" 버튼 노출 확인
2. "직접 추가" 클릭 → ManualRecordModal 모달 등장
3. 섹션 select (예: FR), 본문 입력 (예: "결제 모듈은 PCI-DSS Level 1 준수해야 한다."), 출처는 비워둠
4. "추가" 버튼 클릭

**기대 UI**:

- 빈 상태 안내 문구가 3가지 추출 방식 명시:
  > 레코드는 세 가지 방법으로 추가할 수 있습니다:
  > • 채팅에 "레코드 추출" 입력 → 지식 문서에서 자동 추출
  > • 채팅에 요구사항 문장 직접 입력 → 자동 분해 후 후보 생성
  > • 아래 "직접 추가" 버튼으로 폼 입력
- 모달 제목: "레코드 직접 추가"
- 폼 검증: 섹션 미선택 시 "섹션을 선택해주세요", 본문 4자 이하면 "최소 5자 이상 입력해주세요"
- 추가 후 모달 닫힘 → Records 목록 즉시 갱신 (자동 폴링 / bumpRefresh)
- 새 record 카드 상단에 `display_id` 옆 작은 outline 배지 **"수동 입력"** 표시
- `confidence_score` 는 노출 안 됨 (수동은 null)

**검증 SQL**:

```sql
SELECT content->>'is_auto_extracted', content->>'confidence_score'
FROM artifacts WHERE project_id = '<UUID>' AND artifact_type = 'record'
ORDER BY created_at DESC LIMIT 1;
-- 기대: 'false', NULL
```

---

## 시나리오 12: 헤더 "+ 추가" 버튼 (records ≥ 1)

**목적**: 빈 상태가 아닌 일반 records 화면에서도 동일한 모달 진입 가능.

**사전 조건**: 시나리오 10 또는 11 후 records ≥ 1.

**단계**:

1. Records 탭의 헤더 (필터 드롭다운 옆) "추가" 버튼 (Plus 아이콘) 클릭
2. 모달 → 섹션 + 본문 입력 → "추가"

**기대 UI**:

- 헤더 우측에 작은 ghost 버튼 "추가" 노출 (records 0 이면 빈 상태 화면이라 안 보임)
- 동일한 ManualRecordModal 등장
- 추가 후 records 목록에 새 항목 inline 추가, "수동 입력" 배지

---

## 디버깅 체크리스트

테스트 실패 시 확인 순서:

1. **백엔드 로그** (`./start-dev.sh` 또는 uvicorn 출력)
   - `RequirementAgent.run_stream` 진입 로그 보이는지
   - `interrupt` event 발행 로그 (없으면 supervisor 가 다른 에이전트로 라우팅됐는지 확인)
2. **브라우저 DevTools**
   - Network 탭에서 `POST /api/v1/agent/chat` 응답이 `text/event-stream` 인지
   - SSE 메시지에 `{"type":"interrupt","data":{...}}` 가 보이는지
   - Console 에 `[useChatStream]` 또는 SSE 파싱 에러 없는지
3. **DB**
   - `LANGGRAPH_CHECKPOINT_URL` 미설정 시 hitl_state 는 in-memory — 백엔드 재시작하면 사라짐
   - 시나리오 4 (dismiss) 검증 시 동일 백엔드 프로세스에서 curl 호출
4. **프론트 상태**
   - React DevTools 로 `useChatStream` 의 `pendingHitl` 값 확인
   - 모달이 안 뜨면 pendingHitl 이 null 인 채로 onInterrupt 가 호출됐을 수 있음

---

## 자동 테스트 실행 (보조)

수동 시나리오 전후로 자동 회귀 한 번:

```bash
cd backend && PGSSLMODE=disable .venv/Scripts/python.exe -m pytest \
  tests/test_orchestration.py \
  tests/test_requirement_agent.py \
  tests/test_hitl_interrupt.py -v
# 32 passed 기대
```

```bash
cd frontend && pnpm tsc --noEmit
# 에러 없음 기대
```
