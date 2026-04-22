# PROGRESS.md — 진행 상황

> **규칙**: 각 Phase 착수/완료 시 상태 테이블과 작업 로그를 동시에 갱신. 세션 간 인계의 단일 원천.
> **선행 문서**: `DESIGN.md`, `FRONTEND_DESIGN.md`, `ANALYSIS.md`, `MIGRATION_PLAN.md`, `CLAUDE.md`

---

## 상태 테이블

| Phase | 구간 | 상태 | 진행률 | 비고 |
|---|---|---|---|---|
| **Phase 0** | Lift (프로토타입 이관) | ✅ 완료 | 100% | 2026-04-21 |
| **Phase 1** | 기반 아키텍처 (LangGraph + 레지스트리 + SSE 계약) | ✅ 완료 | 100% | 2026-04-21 · 게이트 보강 3건(`f45dbd8` DB 부트스트랩 / `dcc54d3` DI / `dff384f` 체크포인터 env) |
| **Phase 2** | 멀티 에이전트 + 산출물 Editor | 🟢 진행 중 | 55% | 증분 1A/1B/2 + 마무리(USE_LANGGRAPH 플래그/legacy agent_svc/assist_* 실 제거) 완료. 남은 증분 3~5 |
| **Phase 3** | HITL (interrupt + resume + 컴포넌트 3종) | ⏸ | 0% | P2 선행 |
| **Phase 4** | 품질·버전·영향도 | ⏸ | 0% | Langfuse 자가호스팅 도입 |
| **Phase 5** | 운영화 (RBAC/SSO/DOCX) | ⏸ | 0% | |

**범례**: ✅ 완료 · 🟢 진행 중 · 🟡 대기 · ⏸ 미시작 · ❌ 블록됨

---

## 알려진 이슈 / 후속 작업

다음 세션에서 다시 확인·보강할 항목. 긴급도는 `P?` 로 표기(P1 = 빠른 대응 권장, P2 = 여유 있음).

### [P2] RAG 출처(Sources) 표시 일관성 — 2026-04-21 발견

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
   - [ ] **3a** `agents/srs_generator.py` (`srs_svc` 래핑 + structured output)
   - [ ] **3b** `agents/testcase_generator.py` (신규)
   - [ ] **3c** `agents/critic.py` (신규)
2. Plan 실행
   - [x] **2** 순차 plan 실행 + 실시간 `plan_update` (`9b6ef7b`)
   - [ ] (옵션) 임베딩 top-K 기반 하이브리드 라우팅 — 현재 Supervisor는 description/triggers 텍스트만 사용
3. [ ] **4** artifacts 통합 라우터 (`routers/artifacts.py`) — GET 목록/상세, PATCH section, POST regenerate
4. 프론트 (FRONTEND_DESIGN §20)
   - [ ] **5a** N1 AgentInvocationCard
   - [ ] **5b** N3 PlanProgress
   - [ ] **5c** N4 SrsEditor (RecordsArtifact 패턴)
   - [ ] **5d** N5 TestCaseList
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
