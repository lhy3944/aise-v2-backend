# PROGRESS.md — 진행 상황

> **규칙**: 각 Phase 착수/완료 시 상태 테이블과 작업 로그를 동시에 갱신. 세션 간 인계의 단일 원천.
> **선행 문서**: `DESIGN.md`, `FRONTEND_DESIGN.md`, `ANALYSIS.md`, `MIGRATION_PLAN.md`, `CLAUDE.md`

---

## 상태 테이블

| Phase | 구간 | 상태 | 진행률 | 비고 |
|---|---|---|---|---|
| **Phase 0** | Lift (프로토타입 이관) | ✅ 완료 | 100% | 2026-04-21 |
| **Phase 1** | 기반 아키텍처 (LangGraph + 레지스트리 + SSE 계약) | ✅ 완료 | 100% | 2026-04-21 · 게이트 보강 3건(`f45dbd8` DB 부트스트랩 / `dcc54d3` DI / `dff384f` 체크포인터 env) |
| **Phase 2** | 멀티 에이전트 + 산출물 Editor | ✅ 완료 | 100% | 2026-04-24 — N1/N3 이어 N4 SrsEditor + N5 TestCaseList 완성. 단, staging/PR 워크플로우는 record-only (ChangesWorkspaceModal 제네릭화 후속). |
| **Phase 3** | HITL (interrupt + resume + 컴포넌트 3종) | ⏸ | 0% | P2 선행 |
| **Phase 4** | 품질·버전·영향도 (PLAN_ARTIFACT_LINEAGE.md A~G) | ✅ 완료 | 100% | 2026-04-28 — Phase A~G 7단계 + 후속 #1(soft delete + MinIO) #2(record version UI) 완료. #3(stale UI 재설계) 의사결정 대기 |
| **Phase 5** | 운영화 (RBAC/SSO/DOCX) | ⏸ | 0% | |

**범례**: ✅ 완료 · 🟢 진행 중 · 🟡 대기 · ⏸ 미시작 · ❌ 블록됨

---

## 알려진 이슈 / 후속 작업

다음 세션에서 다시 확인·보강할 항목. 긴급도는 `P?` 로 표기(P1 = 빠른 대응 권장, P2 = 여유 있음).

### [P1] Stale 알림 / 영향도 모달 UI 재설계 — Phase 7 과 통합 보류 (2026-04-28 오픈, 2026-04-28 보류)

> **2026-04-28 결정**: Phase 3 → 5 → 6 → 7 로드맵 확정 시 본 항목 **Phase 7 (추적성 보강) 과 함께 재설계** 로 보류. Backward Traceability / Orphan / Uncovered 가시화와 Stale UI 가 같은 화면 컨텍스트(추적성 매트릭스)에서 결합되는 편이 자연스럽다. 단독 재작업은 진행하지 않음.

**맥락** — Phase 4 후속 #3. Phase G 1차 구현(탭바 우측 amber `stale N` 버튼 + ImpactPanel 모달 체크박스 리스트)에 대해 사용자가 위치/모양 재설계 요청.

**현재 동작 위치**: [ArtifactPanel.tsx](frontend/src/components/artifacts/ArtifactPanel.tsx) 탭바 옆 (line 87 부근). 모달 본문은 [ImpactPanel.tsx](frontend/src/components/artifacts/workspace/ImpactPanel.tsx).

**디자인 결정 옵션 (다음 세션 시작 시 사용자 선택 받기)**:

1. **위치** (4가지): A. 영향받는 각 artifact 화면 헤더 안 inline alert ⭐ / B. 우측 사이드바 상단 알림 / C. 하단 sticky banner / D. 현재 (탭바 우측)
2. **모달 본문** (3가지): α. 카드 형태 (artifact별 카드 + 카드별 "재생성") ⭐ / β. 의존성 그래프 시각화 / γ. 변경 시간순 타임라인
3. **진입 빈도** (3가지): stale > 0 일 때만 ⭐ / 항상 보임 / 토글

**권장 조합**: A + α + 현재(stale > 0일 때만) — 각 화면 헤더에 inline banner, 카드별 재생성 버튼. stale 0이면 hide.

**결정 후 작업 추정**: ~150 LOC. 위치 변경(ArtifactPanel 제거 + Srs/Design/TC 헤더 inline) + ImpactPanel 본문을 카드형으로 재작성.

---

### [P3] SRS PDF 다운로드 — 방식 미결정 (2026-04-24 오픈)

**맥락** — 2026-04-24 SrsArtifact 에 Markdown 다운로드 구현(`2660cd2` 이후 후속 커밋). PDF 는 사용자 요청으로 일단 보류. MD 파일에는 섹션 타이틀을 포함하지 않음 — content 자체에 헤딩이 이미 들어 있어 중복 방지.

**결정 필요 옵션**:
1. **Print CSS** — `@media print { ... }` 규칙으로 SRS 카드만 남기고 body 나머지 hidden. `window.print()` 경유, 프론트 30~50줄. 번들 영향 0, 구현 단순. 단점: 페이지 나누기/머리글·바닥글 제어 제한.
2. **백엔드 export 엔드포인트** — `GET /api/v1/projects/{id}/srs/{srs_id}/export?format=pdf`, WeasyPrint(Python→HTML→PDF). 한글 폰트 임베딩/페이지 제어/헤더풋터 완전 제어. 단점: cairo/pango 시스템 의존성 → Docker 이미지 재빌드, 프론트는 GET 호출만.
3. **클라이언트 PDF 라이브러리** — jsPDF + html2canvas 또는 react-pdf. 한글 폰트 임베딩 필요(+2~3MB 번들). 비추천.

**권장**: 2번(백엔드) 이 장기적으로 옳으나 **1번(Print CSS) 로 저비용 시작 → 피드백 후 2번으로 업그레이드** 경로. 다른 artifact 타입(TC/Design) 도 같은 결정 재사용 가능.

---

### [P2-RESOLVED] RAG 출처(Sources) 표시 일관성 — 2026-04-22 해결

커밋 `293ed30` (backend) + `cd9973f` (frontend). 설계 옵션 D (백엔드가 결정론적 사실 소유) + UX 옵션 (a)로 구현. legacy `[SOURCES]` 본문 블록 파서는 제거. 본 섹션은 레퍼런스용으로 남김.

---

### [P2] RAG 출처(Sources) 표시 일관성 — 2026-04-21 발견 (✅ 해결)

**증상** — 레거시 경로(`USE_LANGGRAPH=false`, `services/agent_svc.stream_chat`)에서 Knowledge Repository 기반 답변 시, **모델마다 출처 리스트가 표시되거나 안 되거나** 편차가 있음. 사용자 수동 테스트 중 확인.

**원인 구조적 진단**
- 프론트 [MessageRenderer.tsx:58-59](frontend/src/components/chat/MessageRenderer.tsx#L58-L59)는 답변 **본문 안**의 `[SOURCES]...[/SOURCES]` JSON 블록을 정규식으로 파싱해서 `SourceReference` 컴포넌트를 렌더. SSE `sources` 필드는 소비하지 않음.
- 레거시 프롬프트 [prompts/agent/chat.py:198-208](backend/src/prompts/agent/chat.py#L198-L208)는 `[SOURCES]` 블록 출력을 명시 지시 — 하지만 **LLM 준수도에 전적으로 의존**. 모델별로 따르거나 무시.
- 새 LangGraph 프롬프트 [prompts/knowledge/chat.py:32](backend/src/prompts/knowledge/chat.py#L32)는 `[번호]` 인용만 지시하고 `[SOURCES]` 블록 지시가 **없음**. SSE `sources`는 [services/rag_svc.py:137-148](backend/src/services/rag_svc.py#L137-L148)에서 항상 반환되지만 프론트가 소비 안 함 → LangGraph 경로에서는 **거의 항상 출처 UI 미표시**.

**권장 설계(대화에서 합의한 방향 — 옵션 D)** — "LLM에게 스키마 강제" 대신 "백엔드가 결정론적 사실 소유".

1. 새 SSE 이벤트 `sources` 추가 ([schemas/events.py](backend/src/schemas/events.py))
   - payload: `list[{document_id, document_name, chunk_index, content_preview, score}]`
   - `KnowledgeQAAgent` 또는 `run_chat`에서 retrieval 직후 발행
2. [types/agent-events.ts](frontend/src/types/agent-events.ts)에 1:1 반영, `useChatStream`에 `onSources` 콜백 추가
3. [MessageRenderer.tsx](frontend/src/components/chat/MessageRenderer.tsx) 우선순위
   - 1순위: SSE `sources` 이벤트 데이터
   - 2순위(레거시 호환): 본문 `[SOURCES]` 블록 파싱
   - agent_svc 제거 시점에 2순위도 삭제
4. `prompts/knowledge/chat.py`에서 `[1]`·`[2]` 본문 인용 지시는 유지(보너스 UX), `[SOURCES]` 블록 지시는 추가하지 않음(백엔드가 소유)

**UX 결정 점 (다음 확인 필요)** — 본문 `[1]` 인용이 전혀 없을 때 화면 처리 방식
- (a) 답변 아래 "참조한 문서: …" 리스트만 — 가장 단순, 권장
- (b) (a) + 답변 끝에 `[1] [2] …` 자동 뱃지
- (c) 백엔드 후처리로 인라인 `[1]` 자동 삽입 (매칭 품질이 새 불확실성)

**예상 스코프 & 배치** — 1~2시간, 작은 PR 1~2개. Phase 2 증분 3 직전 또는 증분 5(프론트 N1 AgentInvocationCard) 작업과 묶어 처리 권장. 새 envelope 이벤트 패턴이 이후 SRS/TC artifact_created 이벤트 설계에도 재사용됨.

**부가 이점** — 프롬프트 10여 줄 단축(토큰 비용), LLM 준수도 테스트 불필요(hermetic), Phase 2 증분 3의 Critic 에이전트와 연결 가능("답변의 `[1]` 인용이 실제 sources에 있는지" 검증).

---

## 기준선 (Phase 0 완료 시점)

### Backend
- **테스트**: **96 passed in 23.63s** (프로토타입 ANALYSIS 당시 "93 passed / 3 skipped" 대비 3건 추가 통과)
- **의존성**: `uv sync --frozen` 성공 (Python 3.14.2 + uv 0.9.26)
- **DB**: PostgreSQL 16 + pgvector, Alembic 16 migrations 적용
  - 개발 DB: `postgresql://aise:aise1234@localhost:5432/aise`
  - 테스트 DB: `postgresql://aise:aise1234@localhost:5432/aise_test`
- **Docker 컨테이너**: `aise2_postgres` (5432), `aise2_minio` (9000, 9001) 실행 중

### Frontend
- **빌드**: `pnpm build` 성공 (Next.js 16.1.6 Turbopack, 20.9s compile + 8 static pages)
- **Lint**: `pnpm lint` 22 problems (8 errors, 14 warnings) — **프로토타입과 동일한 상태**, Phase 1에서 정리
- **의존성**: `pnpm install --frozen-lockfile` 성공 (pnpm 9.15.0, Node 22.21.1)
- **Lock files**: `package-lock.json` + `pnpm-lock.yaml` 둘 다 존재. 단일화는 D10에서 결정

### DB 스키마 (Alembic 적용 기준)
14개 테이블: `projects`, `project_settings`, `requirement_sections`, `requirements`, `requirement_versions`, `records`, `glossary_items`, `knowledge_documents`, `knowledge_chunks`, `requirement_reviews`, `srs_documents`, `srs_sections`, `sessions`, `session_messages`.

Phase 1 이후 추가 예정: `hitl_requests`, `agent_executions`, LangGraph checkpoints (자동 생성).

---

## 작업 로그

### 2026-04-24 — N4 SrsEditor + N5 TestCaseList (Phase 2 → 100%)

`ffc934f` (project-scoped drafts) 위에 Phase 2 마지막 남은 프론트 UI 2종을 구현.
placeholder 상태였던 SrsArtifact / TestCaseArtifact 를 실동작 컴포넌트로 교체.
**프론트 `tsc --noEmit` 0 error**.

| 커밋 | 범위 | 요약 |
|---|---|---|
| `f62d894` | frontend/artifact | N4 SrsEditor. 상단 버전 select + 상태 chip + 재생성 버튼, 본문 섹션 카드(MessageResponse markdown), 호버시 편집 버튼 → modal (Textarea 16 rows) → PUT `/srs/{id}/sections/{section_id}`. srsService 5 메서드 기존 자산 소비. 빈 상태에서 SRS 생성 버튼. |
| `953913c` | frontend/artifact | N5 TestCaseList. `types/testcase.ts` 신설(TestCaseContent/Priority/Type — 백엔드 `schemas/api/artifact_testcase.py` 1:1 동기). artifactService.list(projectId, {artifact_type:'testcase'}) 로 조회, display_id numeric sort. 카드: priority tone + type chip + title + 사전/스텝 ol/기대결과. 편집 에디터: title/priority/type select + 스텝 useFieldArray add/remove, zod 검증. 필터 드롭다운(priority × type 다중). |

#### 설계 결정
- **staging/PR 미통합**: ChangesWorkspaceModal 이 현재 record-specific (content payload 구조가 `{text, section_id, source_document_id, …}` 하드코딩) → SRS/TC 에 바로 재사용 불가. 이번 증분은 직접 저장(`artifactService.update` / `srsService.updateSection`) 방식. **후속 과제**: ChangesWorkspaceModal artifact_type 제네릭화.
- **srsService.regenerate 는 srs_id 를 무시하고 generate_srs 를 재호출** (백엔드 동작 그대로) — 프론트에서 "재생성" 버튼은 UX 명확성 용도로 유지하되 내부적으로 generate 와 동등.
- **TestCase staging 미지원**: memo 에선 staging-store 재사용 가능하다고 적었으나 실제 content 가 JsonObject 인 TC 와 string 인 record 는 타입 불일치. 별도 genericize 없이는 재사용 불가 — 후속 작업.

#### Phase 3 진입 조건
Phase 2 종료 — HITL (interrupt + resume + 컴포넌트 3종) 착수 가능. MIGRATION_PLAN §2.3 참조.

### 2026-04-24 — DiffViewer + SRS/TestCase/Critic 에이전트 5커밋

Artifact governance 리팩터링 검증 push 직후 이어 작업. **백엔드 154 passed**
(신규 test_srs_generator_agent 3 + test_critic_agent 6 + test_testcase_generator_agent 4 포함),
프론트 `tsc --noEmit` 0 error (DiffViewer까지).

| 커밋 | 범위 | 요약 |
|---|---|---|
| `6f27004` | frontend/artifact | DiffViewer + FieldDiffRow. PR 머지 전 리뷰어가 HEAD vs base 스냅샷 차이를 overlay modal 로 확인. added/removed/modified/unchanged 카테고리별 카운트 chip, 변경 없음 토글. 백엔드 `GET /api/v1/versions/{version_id}/diff` 자산 재사용 (plan §3-7). |
| `25e2fc4` | backend/agents | SrsGeneratorAgent (3a). srs_svc.generate_srs 래핑. state.srs_generated = {srs_id, version, section_count, based_on_records_count}. tool_result 에 section_count/srs_version 노출. |
| `31fd98e` | backend/agents | CriticAgent (3c). 결정론적 citation integrity check — 답변의 [N] 인용이 sources ref 에 존재하는지 검증. LLM 호출 없음 (retrieval_gate / query_rewriter 의 결정성 유지). state.critic_report = {passed, issues, checked_citations, valid_citations}. 6 테스트 (all resolve / unknown ref / citation but empty sources / no citations / no prior answer / positional fallback). |
| `cf83190` | backend/agents | TestCaseGeneratorAgent (3b). 최신 completed SRS 섹션별로 LLM 호출 → TC JSON 배열 파싱 → artifact_type='testcase' Artifact 저장 (working_status='dirty'). prompts/testcase/generate.py + services/testcase_svc.py + schemas/api/artifact_testcase.py 신설. display_id 'TC-<n:03d>' 연번. 섹션 JSON 파싱 실패는 skipped_sections 로 수용. |

#### 후속 작업 (Phase 2 90% → 100%)
- **N1 AgentInvocationCard**: tool_call/tool_result 카드 (이미 ToolCall 컴포넌트 있으나 agent별 result metadata 포맷 개선 필요 — records_count / section_count / testcase_count / critic_passed).
- **N3 PlanProgress**: plan_update 이벤트 받아 step별 상태 표시 패널. 이미 chat-store 에 plan 상태는 있지만 시각화 미구현.
- **N4 SrsEditor**: ArtifactRecordEditor 패턴 재사용. SRS 섹션별 편집 + artifact_type='srs' PR workflow.
- **N5 TestCaseList**: testcase artifact 목록/편집. ArtifactRecordsPanel 구조 재사용.

Phase 2 마무리 후 Phase 3 HITL 착수.

### 2026-04-24 — Artifact Governance + Retrieval 품질 레이어 (12 커밋 정리)

세션에 쌓여 있던 대규모 WIP(+1085/−1989, 42 파일)를 논리 단위로 나눠 11 커밋 + 검증 중 발견된 check constraint 수정 1 커밋으로 정리. **백엔드 141 passed** (신규 test_artifact_svc / test_artifact_record / test_query_rewriter / test_retrieval_gate 포함; Windows ProactorEventLoop+psycopg 호환성으로 인한 2건 Postgres checkpointer 테스트는 환경 이슈). **프론트 `tsc --noEmit` 0 error, `pnpm build` 성공**.

| 커밋 | 범위 | 요약 |
|---|---|---|
| `959ca74` | backend/db | artifact governance 스키마 (artifacts + versions + PRs + dependencies) |
| `5553575` | backend/models | Artifact 모델 도입, Record 제거 (artifact_type='record' 로 흡수) |
| `7eacf6d` | backend/artifact | artifact_svc / artifact_record_svc + routers + schemas + 테스트 |
| `e26a650` | backend/rag | Query Rewriter + Retrieval Gate + SSE 이벤트(query_rewritten/gate_decision) 통합 |
| `cd744e2` | backend/svc | srs/suggestion이 Artifact 기반으로 조회 (storage_svc MinIO 포트 9100→9000 정정) |
| `1072041` | backend/db | records→artifacts 백필 + records 테이블 drop 마이그레이션 |
| `cb4fe40` | frontend/overlay | PromptDialog + overlay-store/useOverlay 확장 |
| `d0bdf13` | frontend/types | artifact/PR 이벤트 + QueryRewritten/GateDecision 타입 |
| `2807db6` | frontend/artifact | services/stores/workspace UI/citation + legacy RecordsArtifact 제거 |
| `8adc8d7` | frontend/chat | SSE stream + MessageRenderer의 citation/artifact 이벤트 반영 |
| `169bb57` | frontend/landing | HeroSection 포맷 + 미사용 import 정리 |
| `95c750f` | backend/fix | artifact 초기 working_status='clean'→'dirty' (check constraint 일치) + conftest cleanup 수정 |

#### Git-like Artifact Governance 핵심
- Artifact = working copy (clean/dirty/staged) + ArtifactVersion = 불변 스냅샷
- PullRequest staging → review → merge 라이프사이클, ChangeEvent 감사 로그
- ArtifactDependency 그래프로 영향도 전파(HITL/Critic에서 활용 예정)
- Record/SRS/Design/TestCase가 artifact_type 으로 통합됨

#### Retrieval 품질 레이어
- `services/query_rewriter`: 세션 컨텍스트 기반 follow-up 재작성
- `orchestration/retrieval_gate`: 질문이 실제 retrieval을 요구하는지 gate 결정(skip/proceed) — small talk / 문서 없음 / low-score cut-off
- 두 결정 모두 SSE 이벤트로 프론트에 노출

#### 후속 작업 (세션 인계)
- **DiffViewer (plan §3 7번)**: PR 생성 시 HEAD vs base diff 를 리뷰어에게 hunk 단위로 노출. 구조: `components/artifacts/workspace/diff/{DiffViewer,FieldDiffRow}.tsx`, `GET /api/v1/versions/{version_id}/diff` 연결.
- Phase 2 증분 3a/3b/3c(SRS/TestCase/Critic agents)는 남은 과제.

### 2026-04-22 — `expose_as_tool` 플래그 (general_chat UI 정리)

general_chat에 "도구 호출" 카드가 보이는 게 의미론적으로 틀렸다는 피드백 — **general_chat은 도구가 아니라 에이전트의 직접 응답**. `AgentCapability.expose_as_tool: bool = True` 필드를 추가하고 `GeneralChatAgent`는 `False`로 선언. `run_chat`/`_execute_plan`이 이 플래그를 보고 `tool_call`/`tool_result` SSE를 생략 → 프론트는 이벤트가 안 오니 카드도 안 뜸 (프론트 변경 0). `plan_update`는 영향 없어 plan 내 step 가시성은 유지. 커밋 해시는 다음 커밋.

테스트: `test_supervisor_routes_greeting_to_general_chat` 시퀀스 assertion이 `TokenEvent × 3 → DoneEvent`로 단순화. 120 passed.

### 2026-04-22 — GeneralChatAgent 추가 (잡담/인사 처리)

Supervisor가 "안녕", "이름이 뭐야?", "뭐 할 수 있어?" 같은 **의도가 명확한 비-RAG 입력**을 `clarify`로 분류해 "어떤 정보를 찾고 계신가요?"로 응답하던 오분류를 해결. clarify는 다시 본래 역할(진짜 모호한 질문)로 축소. 커밋 `f85db72`, **120 passed**.

#### 추가
- [prompts/general/chat.py](backend/src/prompts/general/chat.py): 짧고 친근한 톤, 프로젝트 지식 상상 금지, 지식 질문은 RAG 경로로 유도, 능력 밖 요청은 한 줄 거절 + 대안 제시
- [agents/general_chat.py](backend/src/agents/general_chat.py): `BaseAgent` + `@register_agent`. `run_stream`이 `llm_svc.chat_completion_stream`으로 토큰 스트리밍 — RAG 답변과 동일 UX. sources 없음.
- [agents/registry.py](backend/src/agents/registry.py): `_BUILTIN_AGENT_MODULES`에 `general_chat` 등록. Supervisor 프롬프트는 레지스트리 기반이라 자동 발견.
- [prompts/supervisor.md](backend/src/prompts/supervisor.md): **Routing precedence** 절 추가 — greeting/self-intro/capability question/thanks/out-of-scope 거절은 `general_chat`, `clarify`는 "진짜로 모호한" 경우로 한정.

#### 테스트
- `test_general_chat::test_run_stream_emits_tokens_and_final` — 3 deltas → 3 TokenEvents + terminal final, sources 없음
- `test_general_chat::test_supervisor_routes_greeting_to_general_chat` — E2E: stub supervisor가 general_chat 선택, 시퀀스 `tool_call → token × 3 → tool_result → done`
- `test_general_chat::test_run_stream_error_produces_final_error` — LLM 실패 시 `final.update.error`로 surfacing

#### 설계 결정
(B) "Supervisor 프롬프트에 답변 능력 추가" 대신 (A) "전용 에이전트" 선택. 이유:
- Supervisor completion이 JSON-only라 (B)는 토큰 스트리밍 불가 → 방금 복원한 스트리밍 UX 회귀
- 레지스트리 + `BaseAgent.run_stream` 패턴 재사용 → 아키텍처 일관성
- 향후 FAQ/튜토리얼/설정 도우미 같은 보조 에이전트의 참조 구현

### 2026-04-22 — UX 버그픽스: 렌더 순서 + tool_result 상태

스트리밍 복원 직후 실제 트래픽에서 드러난 2건. 커밋 `0b7bd29`.

- **렌더 순서**: `MessageRenderer`가 legacy "답변 → toolCalls → sources"로 하드코딩돼 있어 knowledge_qa 도구 카드가 답변 *아래*에 나타남. SSE 도착 순서(`tool_call → sources → token × N → tool_result`)와 시각적으로 일치하도록 "toolCalls → sources → 답변 텍스트"로 재배열.
- **"오류" 상태**: `handleToolResult`가 legacy `agent_svc`의 `result.success: bool` 컨벤션을 검사했는데, 새 `_result_payload()`는 카운터만 담음 → `undefined` → falsy → 항상 error. SSE `data.status`를 `onToolResult`로 전달해 우선 판단 기준으로 사용. legacy `result.success === false`는 OR 결합(backward-compat).
- 덤: `_formatToolResult`에 `knowledge_qa`("문서 N건 참조") / `requirement`("후보 N건 추출") 포맷. `TOOL_DISPLAY_NAMES`에 agent 한글 라벨.

### 2026-04-22 — 토큰 스트리밍 복원 (BaseAgent.run_stream)

sources 이벤트 작업 직후 확인됐던 "SSE `token` 이벤트가 1개 = 최종 답변 전체" 회귀를 해결. Phase 1 때 `graph.ainvoke` + 사후 합성 패턴으로 바꾸면서 legacy `agent_svc`가 제공하던 OpenAI SSE delta 중계가 빠져있었음. 커밋 `410de54`, 117 passed.

#### 복원 구조
- **`BaseAgent.run_stream(state, ctx)`** — discriminator `kind` 기반 async generator. `{"kind": "sources"}` / `{"kind": "token"}` / `{"kind": "final"}` 세 종류. 기본 구현은 `run()` 한 번 호출 후 sources(?) + 단일 token + final로 래핑해 backward-compatible.
- **`KnowledgeQAAgent.run_stream`** override — `rag_svc.search_and_prepare()` (retrieval + 프롬프트 빌드 + sources, LLM 호출 없음) → sources emit → `llm_svc.chat_completion_stream()` delta → token emit → final emit. `run()`은 `run_stream`을 드레인해서 호환 surface 유지.
- **`rag_svc` 분리** — `search_and_prepare()` 신설, 기존 `chat()`은 `search_and_prepare() + chat_completion()` 합성으로 단축 (HTTP API `/knowledge/chat`이 여전히 사용).
- **`orchestration/graph._drive_agent_stream()`** — agent.run_stream을 consume해서 SSE 모델(`SourcesEvent`/`TokenEvent`)로 재방출. final update는 sentinel dict로 caller에 반환 → caller가 `tool_result` 합성.
- **`run_chat` single path** — `graph.ainvoke`를 호출하지 않고 `supervisor_node`를 직접 호출한 뒤 선택된 agent를 `_drive_agent_stream`으로 구동. `graph` 매개변수는 호환 유지용(plan 우회 없는 compile 호출자 있음).
- **`_execute_plan`** — 각 step을 `_drive_agent_stream`으로 호출. **마지막 step만 token forward**, 중간 step의 token은 shared_state에만 누적. sources는 어느 step이든 forward.

#### 새 스트리밍 순서
| 경로 | 시퀀스 |
|---|---|
| single | `tool_call → [sources] → token × N → tool_result → done` |
| plan | `plan_update(pending) → [per step: plan_update(running) → tool_call → [sources] → token × N (last only) → tool_result → plan_update(completed)] → done` |

프론트 파서는 이미 `onToken`을 여러 번 받아 누적하는 구조라 추가 변경 없음. `tool_result`가 마지막에 오므로 "에이전트 실행 중" 인디케이터가 스트리밍 동안 유지됨 — 자연스런 UX.

#### 테스트
시퀀스 assertion 3건 업데이트 (`test_orchestration.py` happy path / 2-step plan E2E, `test_requirement_agent.py` graph E2E). stub 공용화 — `chat_completion_stream`을 async generator로 monkey-patch해 canned answer를 2 deltas로 쪼개 방출 → 스트리밍 순서를 테스트에서 관찰.

---

### 2026-04-22 — [P2] RAG sources SSE 이벤트 (2커밋)

`/home/workspace/aise-v3/PROGRESS.md` L27에 기록돼 있던 "RAG 출처 표시 일관성" 이슈를 해결. legacy `agent_svc` 제거 직후라 본문 `[SOURCES]` 블록 파서 fallback도 같이 정리 가능했음. **117 passed** (신규 검증 어설션 포함), 프론트 `tsc --noEmit` 0 error.

| 커밋 | 범위 | 변경 요약 |
|---|---|---|
| `293ed30` | backend | 새 SSE 이벤트 `sources` (docs/events.md §2.6). [schemas/events.py](backend/src/schemas/events.py)의 `SourceRef`/`SourcesEventData`/`SourcesEvent` + discriminated union 등재. [KnowledgeChatSource](backend/src/schemas/api/knowledge.py)에 `file_type` 필드 추가 + [rag_svc.py](backend/src/services/rag_svc.py) 문서 메타 조회 확장. [orchestration/graph.py](backend/src/orchestration/graph.py)의 `_sources_event()` 헬퍼 — agent가 state에 올린 `sources` 리스트를 1-based `ref`로 재번호하여 single path(`run_chat`)에선 `tool_result` 뒤 `token(answer)` 앞, plan path(`_execute_plan`)에선 각 step `tool_result` 뒤에 emit. 관련 테스트 3건 시퀀스 업데이트 + sources 어설션. |
| `cd9973f` | frontend | [types/agent-events.ts](frontend/src/types/agent-events.ts) `SourceRef`/`SourcesEvent`/`isSourcesEvent` 추가. [agent-service.ts](frontend/src/services/agent-service.ts) dispatch + `onSources` 콜백. [chat-store.ts](frontend/src/stores/chat-store.ts) `ChatMessage.sources?: SourceRef[]`. [useChatStream.ts](frontend/src/hooks/useChatStream.ts)는 `onSources`에서 `updateLastAssistant`로 sources를 메시지에 세팅. [MessageRenderer.tsx](frontend/src/components/chat/MessageRenderer.tsx)는 `SOURCES_BLOCK_RE` + 파싱 로직 + 스트리밍 incomplete-tag set에서 'SOURCES' 제거; `message.sources`를 citation-`[N]` DOM wiring과 `SourceReference` 렌더 양쪽에서 소비. |

#### 설계 근거
- **백엔드 소유 원칙(옵션 D)**: 프롬프트에 `[SOURCES]` 블록 지시 대신 SSE 이벤트로. LLM 준수도 테스트 불필요(hermetic). 프롬프트 토큰 절약(지시 문장 10여 줄 미삭감).
- **UX 결정 (a)**: 답변 아래 "출처" 리스트만. 별도 인라인 뱃지 자동 삽입은 하지 않음 — `[1]` 본문 인용이 LLM에 의해 드물더라도 출처 리스트는 항상 노출됨.
- **발행 타이밍**: single path `tool_result` 뒤 → `token(answer)` 앞. 프론트는 답변 스트림이 들어오기 시작하는 시점에 이미 sources 맵을 갖춰 `[N]` 인용을 클릭 가능한 span으로 wiring 가능.
- **미래 활용**: 증분 3c(Critic 에이전트)가 "답변의 `[N]` 인용이 실제 sources에 있는지"를 검증할 때 동일한 결정론적 채널 재사용.

#### 캐리오버
- [useChatStream.ts](frontend/src/hooks/useChatStream.ts)에 `generate_srs` 디스패치 + `markToolCallError` + `triggerGenerateSrs` 관련 SRSGeneratorAgent prep 변경이 본 PR에 딸려 들어감 (같은 파일이라 분리 비용 vs 가치 고려). 짝이 되는 백엔드 `agents/srs_generator.py`는 증분 3a에서 완성.
- [backend/src/services/llm_svc.py](backend/src/services/llm_svc.py)의 `chat_completion_stream()`은 계속 워킹 트리에 남김 — 증분 3a(SRS 토큰 스트리밍)에서 연결.

---

### 2026-04-22 — Phase 2 마무리 정리 (플래그 · legacy agent_svc · assist_*)

Phase 2 증분 로드맵의 "마무리" 3종 세트를 묶어 제거. MIGRATION_PLAN §5 D3 실행 포함. **117 passed** (이전 131 − test_assist.py 14개 = 117, 예상대로 감소). 프론트 `tsc --noEmit` 0 에러.

| 커밋 | 범위 | 변경 요약 |
|---|---|---|
| 1 | `refactor: remove USE_LANGGRAPH flag and legacy agent_svc` | [routers/agent.py](backend/src/routers/agent.py) 단일 경로로 재작성(`_use_langgraph()` · legacy 분기 · `agent_svc` import 전부 제거). [services/agent_svc.py](backend/src/services/agent_svc.py) + [prompts/agent/](backend/src/prompts/agent/) 디렉토리 삭제. `.env.*.example`, [start-dev.sh](start-dev.sh)/[start-local.sh](start-local.sh), [test_agent.py](backend/tests/test_agent.py), [smoke 스크립트](backend/scripts/smoke_langgraph_chat.py)에서 `USE_LANGGRAPH` 전부 삭제. 프론트 [agent-service.ts](frontend/src/services/agent-service.ts) dispatch를 신 envelope 전용으로 단순화(legacy flat envelope 분기 + `SSEEvent` export 제거). 부차적으로 start-dev.sh가 호스트 DB를 가정하도록 postgres docker 섹션 주석 + pnpm 전환. |
| 2 | `refactor(assist): remove deprecated endpoints and UI (D3)` | 백엔드: [routers/assist.py](backend/src/routers/assist.py), [services/assist_svc.py](backend/src/services/assist_svc.py), [schemas/api/assist.py](backend/src/schemas/api/assist.py), [prompts/assist/](backend/src/prompts/assist/), [tests/test_assist.py](backend/tests/test_assist.py) 전부 삭제 + [routers/__init__.py](backend/src/routers/__init__.py), [main.py](backend/src/main.py)에서 `assist_router` 언와이어. 프론트: [assist-service.ts](frontend/src/services/assist-service.ts), `ChatPanel.tsx`, `RefineCompare.tsx`, `SuggestionPanel.tsx`, `ExtractedRequirementList.tsx`, `ExtractedRequirementCard.tsx` 삭제. [RequirementInput.tsx](frontend/src/components/requirements/RequirementInput.tsx) `onRefine`/`isRefining` prop + AI 정제 버튼 제거. [RequirementsArtifact.tsx](frontend/src/components/artifacts/RequirementsArtifact.tsx)에서 refine/suggest UI 전체 제거. [requirements/page.tsx](frontend/src/app/\(main\)/projects/\[id\]/requirements/page.tsx)에서 mode toggle(구조화/대화) + ChatPanel + refine/suggest 전체 제거 — "요구사항 다듬기는 메인 Agent 채팅으로 일원화" UX 정책으로 통일. [types/project.ts](frontend/src/types/project.ts)에서 `RefineRequest/Response`, `SuggestRequest/Response`, `Suggestion`, `ChatMessage`(project.ts 것), `ChatRequest/Response`, `ExtractedRequirement` 타입 제거. |
| 3 | `docs(progress): log flag/legacy/assist removal` | 본 로그 엔트리 + 상태 테이블 Phase 2 진행률 40% → 55%. |

#### 설계 근거
- **왜 지금**: Phase 1 스모크 + 증분 1A/1B/2 실환경 테스트 통과 → 롤백 보험료가 테스트 매트릭스 2배화 비용을 넘었음. CLAUDE.md "Don't use feature flags or backwards-compatibility shims when you can just change the code" 원칙과 일치.
- **왜 한 PR**: 세 정리가 논리적으로 얽혀있음 — 플래그를 제거하면 legacy `agent_svc` 호출자가 사라지고, assist_*는 legacy OpenAI Function Calling loop에 연결돼 있던 옵션 기능이었으므로. 분리하면 "중간 상태에 잠시 머무는 어정쩡함"이 생김.
- **UX 정책 변경**: assist_*의 refine/suggest 버튼 + 대화 모드 패널은 "요구사항 다듬기는 메인 Agent 채팅(RequirementAgent)으로 일원화"로 대체. 별도 보조 버튼/서브 채팅을 유지하면 또 정리 대상이 되므로 과감히 삭제. MIGRATION_PLAN §5 D3에서 합의한 방향.

### 2026-04-21 — Phase 2 착수 (증분 1A/1B/2)

Phase 1 게이트 정리 + `USE_LANGGRAPH=true` 수동 스모크까지 통과한 뒤 Phase 2 본 작업 착수. 총 3커밋, **131 passed** (5회 연속 full-suite).

| 커밋 | 증분 | 변경 요약 |
|---|---|---|
| `13d6084` | 1A · Supervisor LLM 라우팅 | `prompts/supervisor.{md,py}` + `orchestration/supervisor.py` 재작성. LLM 기반 3-액션 분류(single/plan/clarify) + 파싱·검증 실패 시 clarify 폴백. run_chat이 clarify/plan 케이스도 의미 있는 token으로 스트리밍. 5개 단위 테스트 추가. |
| `744ea16` | 1B · RequirementAgent | `agents/requirement.py` — `record_svc.extract_records` 래핑. AppException → state["error"] 변환으로 AGENT_ERROR 깨끗 발행. `records_extracted` state + `records_count` in tool_result. 4개 테스트(단위 + 그래프 E2E). |
| `9b6ef7b` | 2 · Plan 실행 + plan_update | `orchestration/graph._execute_plan` async generator — 순차 실행, per-step `plan_update(pending/running/completed)` + tool_call/tool_result 스트리밍, 공유 세션. `routers/agent.py`가 session_factory를 run_chat에 주입. 2-step plan E2E 테스트 추가. **플래키 해결**: per-step 세션 열기 → 단일 세션 공유로 NullPool 경합 제거. |

#### 실 환경 스모크 (OpenAI gpt-4o, `scripts/smoke_langgraph_chat.py`)
| 질문 | Supervisor 결정 | 결과 |
|---|---|---|
| "이 프로젝트의 주요 기능을 한 문장으로 요약해줘" | `single` → `knowledge_qa` | RAG 5-chunk → 106자 요약, 4.55s |
| "이 프로젝트의 요구사항 후보를 뽑아줘" | `single` → `requirement` | 19 candidates 추출, 18.7s |
| "먼저 핵심 개념을 정리하고, 그 다음에 요구사항 후보 리스트를 뽑아줘" | `plan` → `[knowledge_qa, requirement]` | plan_update로 진행 상태 스트리밍, 20 candidates, 총 27s |

#### 남은 Phase 2 작업 (MIGRATION_PLAN §2.2)
- 증분 3 — `agents/srs_generator.py` (srs_svc 래핑) + `agents/testcase_generator.py` + `agents/critic.py`
- 증분 4 — `routers/artifacts.py` (통합 목록/상세/편집/재생성)
- 증분 5 — 프론트 N1 AgentInvocationCard / N3 PlanProgress / N4 SrsEditor / N5 TestCaseList (신 envelope UI 확인 포함)
- 마무리 — `USE_LANGGRAPH=true` 기본화, legacy `agent_svc` 제거, D3 `assist_*` 실제 삭제

---

### 2026-04-21 — Phase 1 게이트 보강 (Phase 2 진입 전 정합화)

코드 리뷰(4건) 결과 문서-코드 불일치 및 테스트 인프라 약점 발견 → Phase 2 착수 전 3개 게이트로 정리. 총 3커밋, **121 passed**.

| 커밋 | Gate | 변경 요약 |
|---|---|---|
| `f45dbd8` | C (테스트 인프라) | `scripts/setup_test_db.{py,sh}` 신설(`CREATE DATABASE` + `alembic upgrade head`) + conftest autouse probe가 DB 부재 시 pytest.exit로 친절 에러. 테스트는 DB를 자동 생성하지 않음(팀 정책). |
| `dcc54d3` | B (DI 경로) | `core.database.get_session_factory()` 추가. `/api/v1/agent/chat` LangGraph 분기가 `Depends(get_session_factory)`로 주입받아 테스트 override 존중. `_get_graph`는 factory id별 캐시. 회귀 테스트(`test_langgraph_path_honors_session_factory_override`) 추가. |
| `dff384f` | A (체크포인터 env) | `orchestration/graph.get_checkpointer()` — `LANGGRAPH_CHECKPOINT_URL` 없으면 `MemorySaver`, 있으면 공유 `AsyncConnectionPool` + `AsyncPostgresSaver`(+ idempotent `setup()`). `build_graph(..., checkpointer=)` 주입 가능. URL dialect 정규화 유틸 + 3개 신규 테스트. |

#### 발견된 불일치 (해소 완료)
- **D7 "PostgresSaver 완료" ↔ 코드 `MemorySaver`**: env-switch로 재해석(Phase 1=Memory 기본 / Phase 3 HITL 시 env로 Postgres) → MIGRATION_PLAN/PROGRESS 표기 수정.
- **D3 "assist_* 제거 완료" ↔ 라우터 여전히 등록**: 결정 확정은 ✅이되 **실제 삭제는 Phase 2 작업 M**임을 명시.
- **테스트 DB 부재 시 12 errors**: 이제 `pytest.exit`으로 조기 종료 + 부트스트랩 스크립트 안내.
- **LangGraph 경로 DI 우회**: 테스트 override 불가했던 구조를 해결 + 회귀 테스트로 고정.

---

### 2026-04-21 — Phase 1 기반 아키텍처 완료

총 13개 커밋 · 백엔드 117 passed · 프론트 build 성공.

#### 커밋 히스토리 (Phase 1)
| 커밋 | 단계 | 변경 요약 |
|---|---|---|
| `fb75b9d` | A | D1~D10 결정 확정 (MIGRATION_PLAN §5 + PROGRESS 체크리스트) |
| `aad1598` | B | SSE 이벤트 계약 3파일 동시 작성 (docs/events.md + schemas/events.py + types/agent-events.ts) |
| `c88d9f1` | C | pnpm 단일화 (package-lock.json 제거, packageManager/preinstall 명시) |
| `f6e42f3` | D | 백엔드 의존성: deepagents 제거, langgraph/litellm/redis/psycopg 추가, docker-compose에 redis 서비스 |
| `f045b86` | E | rag_svc P0 fix (project_id 필수 + is_active + status=completed) + 7개 격리 테스트 |
| `9aadc81` | F | agents/base.py + registry.py (@register_agent, 9개 테스트) |
| `d8e020f` | G+H | orchestration/{state,supervisor,graph}.py + agents/knowledge_qa.py + 2개 통합 테스트 |
| `46e1979` | I | routers/agent.py 이중 경로 (USE_LANGGRAPH flag) + routers/agents.py GET /agents/[/{name}] + 3개 테스트 |
| `ef8017c` | J | llm_svc.chat_completion을 LiteLLM acompletion으로 교체 (시그니처 유지) |
| `bda4be1` | K | 프론트엔드 SSE 파서를 @microsoft/fetch-event-source로 교체 (신·구 envelope 모두 파싱) |
| `5fe5701` | L | 프론트엔드 useAgentList/useAgent hook + AgentCapability 타입 |
| `1012b2e` | M | assist_* 스냅샷(docs/legacy/assist-reference/) + DEPRECATED 마킹 |

#### 핵심 성과
1. **SSE 계약 단일 원천 확립**: `docs/events.md` ↔ `backend/src/schemas/events.py` ↔ `frontend/src/types/agent-events.ts`. 이후 이벤트 변경은 3파일을 한 PR에서 수정.
2. **LangGraph 기반 오케스트레이션 뼈대**: Supervisor → KnowledgeQAAgent End-to-End 작동. `/api/v1/agent/chat`이 `USE_LANGGRAPH=true` 시 새 경로로 스트리밍.
3. **에이전트 레지스트리 패턴**: `@register_agent` 데코레이터만 붙이면 `/api/v1/agents` GET에 자동 노출.
4. **P0 보안 이슈 해소**: RAG 검색 시 project_id 누락 방지 + 비활성/미완료 문서 필터 + 교차 프로젝트 격리 테스트 강제.
5. **LLM 프로바이더 추상화**: Azure/OpenAI 자동 라우팅을 LiteLLM으로 이관. 기존 호출자는 시그니처 변경 없음.
6. **프론트 SSE 라이브러리 교체**: `useChatStream`의 토큰 버퍼링은 그대로 보존, 파서만 `@microsoft/fetch-event-source`로. 신·구 envelope 자동 감지.
7. **레거시 정리 로드맵 확정**: assist_* 스냅샷 + DEPRECATED 마킹 + Phase 2 말 제거 TODO.

#### 테스트 추이
| 시점 | 통과 | 증분 |
|---|---|---|
| Phase 0 완료 | 96 | — |
| E (rag_svc P0) | 103 | +7 (isolation) |
| F (registry) | 112 | +9 (registry) |
| G+H (orchestration) | 114 | +2 (graph E2E) |
| I (agents router) | 117 | +3 (GET /agents) |
| J, K, L, M | 117 | (기존 회귀 보장) |

#### 현재 시스템 동작 모드
- **기본 (USE_LANGGRAPH=false)**: 기존 `agent_svc.stream_chat` 경로 — 프로토타입 Phase 0 동작과 동일.
- **새 경로 (USE_LANGGRAPH=true)**: LangGraph Supervisor → KnowledgeQA → SSE 이벤트 신 envelope.

Phase 2 착수 시 기본값을 true로 전환 + 레거시 경로 제거 PR.

---

### 2026-04-21 — Phase 0 Lift 완료

#### 선행 작업 (동일 세션)
1. **설계 문서 숙지** — `DESIGN.md`, `FRONTEND_DESIGN.md` 정독 후 핵심 아키텍처 요약 (3계층/레지스트리/Supervisor 3-액션/HITL/RAG 격리/구조화 산출물).
2. **프로토타입 상세 분석** — 백엔드·프론트엔드 병렬 분석 수행. `.prototype-ref/aise-v2/`에 shallow clone.
3. **`ANALYSIS.md` 작성** — 97개 컴포넌트, 50+ 엔드포인트, 11 스토어, 14 훅 재활용 등급(A/B/C) 부여. 가장 중요한 발견: **프로토타입은 Phase 1~4 대부분 구현된 프로덕션급**.
4. **`MIGRATION_PLAN.md` 작성** — Lift→Shift 2단계 전략 수립. REFECTORING.md(프로토타입의 Harness 로드맵) ↔ DESIGN.md(LangGraph) 용어 매핑 확정. Phase 0~5 분해 + 12개 위험 요소 + 10개 결정 보류 항목(D1~D10).
5. **최초 커밋·푸시** (`76564b4`): 6개 문서 (.gitignore, CLAUDE.md, DESIGN.md, FRONTEND_DESIGN.md, ANALYSIS.md, MIGRATION_PLAN.md).

#### Phase 0 Lift — 커밋 히스토리
| 커밋 | 범위 | 변경 |
|---|---|---|
| `76564b4` | docs | 설계 + 분석 + 마이그레이션 계획 (초기 커밋) |
| `edd2ece` | chore(.gitignore) | Python/Node/Next/Docker 아티팩트 제외 |
| `d248f15` | feat(backend) | 프로토타입 FastAPI backend 통째 복사 (135 files, 13,843 insertions) |
| `ac9b537` | feat(frontend) | 프로토타입 Next.js frontend 통째 복사 (255 files, 52,423 insertions) |
| `cf94965` | chore(root) | docker-compose, .env.example, deploy, start-*.sh, .github/workflows, references 복사 (15 files) |
| `16d878a` | docs(legacy) | 프로토타입 원본 문서 `docs/legacy/` 보존 (15 files) |

#### Smoke Test 결과
- Backend: `DATABASE_URL=... uv run alembic upgrade head` → 16 migrations OK
- Backend: `uv run pytest tests/ -v` → **96 passed in 23.63s** ✅
- Frontend: `pnpm install --frozen-lockfile` → Done in 18.5s ✅
- Frontend: `pnpm lint` → 22 problems (프로토타입과 동일) ⚠️ (Phase 1 정리 대상)
- Frontend: `pnpm build` → 성공 ✅ (8 pages, Turbopack 20.9s)

---

## Phase 2 착수 전 체크리스트

### 선행 조건
- [x] Phase 1 완료 (LangGraph 뼈대 + SSE 계약 + KnowledgeQA)
- [x] **필수 게이트 정리** (2026-04-21 보강 — 커밋 `f45dbd8` / `dcc54d3` / `dff384f`)
  - [x] Gate C: 테스트 DB 부트스트랩 스크립트(`backend/scripts/setup_test_db.{py,sh}`) + conftest fail-fast probe
  - [x] Gate B: `/api/v1/agent/chat` LangGraph 경로가 `Depends(get_session_factory)` 통해 DI 오버라이드 존중 (테스트 DB 격리 회복)
  - [x] Gate A: 체크포인터 env 스위치(`LANGGRAPH_CHECKPOINT_URL` → `AsyncPostgresSaver`, 미설정 시 `MemorySaver`)
- [x] `USE_LANGGRAPH=true` 환경에서 수동 smoke test 통과 (2026-04-21)
  - 스크립트: `backend/scripts/smoke_langgraph_chat.py` (in-process ASGI, 실제 OpenAI + real RAG)
  - 결과: `tool_call → tool_result(duration=4552ms, sources=5) → token(106자) → done`, 4.55s 소요
- [ ] 프론트 `agent-service.ts`의 신 envelope 파싱 UI 수동 확인 (tool_call → AgentInvocationCard 없이는 표시 못함, Phase 2 N1에서 해결)

### Phase 2 증분 로드맵 — 진행 상황

1. 신규 에이전트 등록
   - [x] **1A** Supervisor LLM 3-액션 라우팅 (`13d6084`)
   - [x] **1B** `agents/requirement.py` (`744ea16`)
   - [x] **3a** `agents/srs_generator.py` (`25e2fc4`)
   - [x] **3b** `agents/testcase_generator.py` (`cf83190`)
   - [x] **3c** `agents/critic.py` (`31fd98e`)
2. Plan 실행
   - [x] **2** 순차 plan 실행 + 실시간 `plan_update` (`9b6ef7b`)
   - [ ] (옵션) 임베딩 top-K 기반 하이브리드 라우팅 — 현재 Supervisor는 description/triggers 텍스트만 사용
3. [ ] **4** artifacts 통합 라우터 (`routers/artifacts.py`) — GET 목록/상세, PATCH section, POST regenerate
4. 프론트 (FRONTEND_DESIGN §20)
   - [x] **5a** N1 AgentInvocationCard (`4435403`)
   - [x] **5b** N3 PlanProgress (`4435403`)
   - [x] **5c** N4 SrsEditor (`f62d894`, 2026-04-24)
   - [x] **5d** N5 TestCaseList (`953913c`, 2026-04-24)
5. 마무리
   - [x] `USE_LANGGRAPH` 플래그 완전 제거 (2026-04-22, 단일 LangGraph 경로로 확정)
   - [x] 레거시 `agent_svc` 제거 (2026-04-22)
   - [x] **D3 실제 제거**: assist_* (backend router/service + frontend 3 호출부) 삭제 → 메인 Agent 채팅으로 일원화 (2026-04-22)

### 이전 기록용: 결정 확정 (2026-04-21, MIGRATION_PLAN §5)

체크박스는 **결정 확정 여부**에 대한 것. 실행 상태는 별도 표기.

- [x] D1 복사 이관 (결정·실행 모두 완료, Phase 0)
- [x] D2 artifacts 도메인별 분리 유지 + 조회 유틸 (결정 확정, 실행은 Phase 2 이후)
- [x] **D3 assist_* 제거 결정 + 실행 완료** (2026-04-22) — 라우터/서비스/프론트 3 호출부 모두 삭제. 메인 Agent 채팅(RequirementAgent)으로 일원화
- [x] D4 LiteLLM Phase 1 (결정·실행 모두 완료, 커밋 `ef8017c`)
- [x] D5 fetch-event-source Phase 1 전면 (결정·실행 모두 완료, 커밋 `bda4be1`)
- [x] D6 라우트 분리 Phase 4 (결정 확정, 실행은 Phase 4)
- [x] **D7 PostgresSaver (env-switched)** — 결정·구현 완료(Phase 1, 커밋 `dff384f`). 기본값 Memory, `LANGGRAPH_CHECKPOINT_URL` 설정 시 즉시 Postgres. Phase 3 HITL 도입 시점부터 env로 실사용 전환
- [x] **D8 Langfuse 자가호스팅** (결정 확정, 실행은 Phase 4, `LANGFUSE_HOST` 환경변수로 감쌈)
- [x] D9 deepagents Phase 1 즉시 제거 (결정·실행 모두 완료, 커밋 `f6e42f3`)
- [x] **D10 pnpm 단일 유지** (`package-lock.json` 삭제, `packageManager` 필드 명시, 커밋 `c88d9f1`)

### Phase 1 시작 시 선행 작업 (MIGRATION_PLAN §2.1)
- [ ] **SSE 이벤트 스키마 합의 문서** (`docs/events.md`) 작성 후 사용자 검토
- [ ] `types/agent-events.ts` (프론트) ↔ `backend/src/schemas/events.py` (백엔드) 1:1 동기화 규칙 정의
- [ ] 기존 SSE 동작(`useChatStream` 토큰 버퍼링) A/B 검증 시나리오 정리

### Phase 1 우선 작업 (MIGRATION_PLAN §2.2)
1. `backend/pyproject.toml`에 `langgraph`, `langgraph-checkpoint-postgres`, `litellm`, `redis` 추가 + `deepagents` 제거
2. `backend/src/agents/` 레지스트리 뼈대 (`base.py`, `registry.py`)
3. `backend/src/orchestration/` (`state.py`, `supervisor.py`, `graph.py`)
4. `KnowledgeQAAgent` — 기존 `rag_svc` 래핑
5. `rag_svc` **P0 fix**: `project_id` 필수 + `is_active=True` + `status='completed'` 필터 + 교차 프로젝트 격리 테스트 강제
6. `routers/agent.py` 내부를 `graph.astream_events`로 교체 (외부 SSE 계약 유지)
7. `routers/agents.py` 신설 (`GET /agents` 레지스트리 노출)
8. 프론트: `@microsoft/fetch-event-source` 설치 + `services/agent-service.ts` 파서 교체
9. 프론트: `types/agent-events.ts` 신규

---

## 세션 간 인계 메모

- **현재 브랜치**: `main`
- **원격**: `https://github.com/lhy3944/aise-v2-backend.git`
- **로컬 `.prototype-ref/aise-v2/`** 는 분석용 clone, gitignore 처리됨. 참고만.
- **`docs/legacy/`는 읽기 전용**. 수정 시 활성 문서(루트)로 반영.
- **DB 컨테이너 상시 실행** 가정 (`aise2_postgres`, `aise2_minio`). 중단 시 `docker compose up -d postgres minio`.
- **Backend 테스트 DB 부트스트랩** (최초 1회 또는 DB 재생성 후):
  ```bash
  cd backend && bash scripts/setup_test_db.sh
  ```
  이후 `uv run pytest tests/`로 실행. 테스트가 DB를 자동 생성하지 않음(팀 정책). 누락 시 conftest가 친절 에러로 조기 종료.
