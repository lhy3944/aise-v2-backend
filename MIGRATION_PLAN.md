# MIGRATION_PLAN.md — 이관·통합 계획

> **선행 문서**: `DESIGN.md`, `FRONTEND_DESIGN.md`, `ANALYSIS.md`
> **작성일**: 2026-04-21
> **핵심 원칙**: A등급 자산은 **통째 이관 후 보존**. 오케스트레이션 레이어만 LangGraph 기반으로 재구성. 신규 기능(HITL·Impact·Version)은 설계대로 추가.

---

## 0. 전략 요약

### 0.1 기본 방향

프로토타입은 Phase 1~4 대부분이 이미 구현되어 있으므로(ANALYSIS §0.1), **"이관(Lift) → 리팩토링(Shift)"** 2단계 전략을 채택한다.

```
Phase 0: Lift
  프로토타입 backend/ frontend/ 를 현 저장소에 통째 복사
  → 즉시 동작하는 기준선 확보

Phase 1~5: Shift
  그 위에 DESIGN.md / FRONTEND_DESIGN.md 아키텍처를 덮어씌움
  → 각 Phase마다 "동작하는 상태"를 유지하며 점진적 전환
```

**이 전략의 장점**:
1. 매 Phase마다 회귀 테스트 가능 (기존 93 passed 유지)
2. REFECTORING.md가 이미 식별한 P0/P1 이슈를 Phase 1에 묶어 해결
3. 완전 재작성 리스크 회피

### 0.2 REFECTORING.md ↔ DESIGN.md 용어 매핑

기존 팀(REFECTORING.md)과 설계서(DESIGN.md)의 개념이 서로 다른 용어로 같은 것을 가리키므로, 본 문서에서는 **DESIGN.md 용어**로 통일한다.

| REFECTORING.md | DESIGN.md / 본 프로젝트 | 비고 |
|---|---|---|
| Intent Router | **Supervisor** | 자연어 → 에이전트 라우팅 (single/plan/clarify) |
| Context Loader | **AgentState 구성 노드** | 프로젝트/섹션/지식/용어/히스토리 조립 |
| Tool Gateway | **에이전트 레지스트리 + LangGraph 노드 디스패치** | `@register_agent`로 등록, 노드에서 호출 |
| Orchestrator | **LangGraph StateGraph** | interrupt/resume/체크포인트 포함 |
| Renderer | **SSE 이벤트 발행자 + 프론트 컴포넌트** | `types/agent-events.ts`로 계약화 |
| (없음) | **interrupt()** | HITL — DESIGN §6, 신규 도입 |
| (없음) | **Critic Agent** | 자가 검토 — DESIGN §8.3, 신규 |

---

## 1. 재사용 전략 결정

### 1.1 백엔드

#### A. 그대로 재사용 (복사 후 수정 없음)

| 영역 | 대상 |
|---|---|
| 모델 | `models/` 전 8종 (project, requirement, record, srs, session, knowledge, glossary, review) |
| 마이그레이션 | `alembic/versions/` 16개 전체 |
| 라우터 | `routers/project.py`, `record.py`, `section.py`, `srs.py`, `glossary.py`, `knowledge.py`, `session.py`, `review.py` |
| 서비스 | `record_svc`, `section_svc`, `srs_svc`, `review_svc`, `embedding_svc`, `knowledge_svc`, `session_svc`, `glossary_svc`, `suggestion_svc` |
| 프롬프트 | `prompts/srs/`, `prompts/review/`, `prompts/glossary/`, `prompts/knowledge/` |
| 유틸 | `utils/reorder.py`, `utils/text_chunker.py`, `utils/db.py` |
| 코어/미들웨어 | `core/database.py`, `core/exceptions.py`, `core/cors.py`, `core/logging.py`, `middleware/logging_middleware.py` |
| 테스트 | `tests/` 전체 (수정 없이 유지, 신규 테스트만 추가) |
| Docker | `Dockerfile`, `docker-compose.yml`, `alembic.ini` |

#### B. 개조 후 재사용 (구조 유지, 내부 교체)

| 대상 | 개조 내용 |
|---|---|
| `routers/agent.py` | 핸들러 유지, 내부를 **LangGraph 그래프 호출**로 교체 + `/chat/{session_id}/resume` 추가 |
| `services/agent_svc.py` | **LangGraph 기반으로 전면 재작성**하되, 기존 도구 실행 로직은 **LangGraph 노드로 래핑해 기능 보존** |
| `services/llm_svc.py` | **LiteLLM 어댑터로 감싸기** (LiteLLM.completion 호출로 Azure/OpenAI 통합) |
| `services/rag_svc.py` | **문서 활성/완료 필터 추가** (P0). `project_id` 필수 매개변수화 |
| `services/project_svc.py` + `readiness_svc.py` | 병합 (P1) |
| `services/document_processor.py` | `ALLOWED_FILE_TYPES` ↔ 실제 파서 분기 일관성 (P1) |
| `services/storage_svc.py` | 운영/개발 환경별 `secure`/`ssl` 분리 (P1) |
| `utils/json_parser.py` | `with_structured_output` 도입 후 보조 유틸로 축소 (P0) |
| `prompts/agent/chat.py` | **Supervisor 프롬프트 + 에이전트별 프롬프트로 분할** → `prompts/supervisor.md`, `prompts/agents/*.md` |
| `routers/requirement.py`, `routers/assist.py` | 레거시 호환성 유지, 신규 개발 없음 |
| `schemas/api/agent.py` | `AgentChatRequest`에 `interrupt_id` 선택 필드 추가, `resume` body 스키마 추가 |

#### C. 완전 신규

| 영역 | 신설 내용 |
|---|---|
| `agents/base.py` | `BaseAgent`, `AgentCapability` (DESIGN §4.1) |
| `agents/registry.py` | `AGENT_REGISTRY`, `@register_agent` 데코레이터 (DESIGN §4.2) |
| `agents/knowledge_qa.py` | RAG 에이전트 (기존 `rag_svc` 래핑) |
| `agents/requirement.py` | Records 추출 에이전트 (기존 도구 래핑) |
| `agents/srs_generator.py` | SRS 에이전트 (기존 `srs_svc` 래핑) |
| `agents/testcase_generator.py` | TC 에이전트 (신규) |
| `agents/critic.py` | 자가 검토 (신규) |
| `orchestration/graph.py` | LangGraph StateGraph |
| `orchestration/supervisor.py` | 라우팅 노드 (3-action: single/plan/clarify) |
| `orchestration/state.py` | `AgentState` Pydantic |
| `orchestration/hitl.py` | `interrupt()` 래퍼 + resume 핸들러 |
| 모델 | `models/hitl_request.py`, `models/agent_execution.py`, (통합) `models/artifact.py` |
| 마이그레이션 | 신규 3~4개 (hitl_requests, agent_executions, artifacts 통합 테이블, 필요 시 설계문서 확장) |
| 라우터 | `routers/agents.py` (레지스트리 노출), `routers/artifacts.py` (통합 CRUD/버전/영향도) |
| `rag/` 디렉토리 | DESIGN §11 구조 (`embedder.py`, `vectorstore.py`, `chunker.py`, `retriever.py` — 기존 서비스에서 추출해 재편성) |
| Redis 통합 | `docker-compose.yml`에 Redis 서비스 추가 + 세션 캐시/락 |

#### D. 폐기 (또는 무기한 미사용)

| 대상 | 이유 |
|---|---|
| `deepagents` 의존성 | LangGraph 도입으로 불필요. `pyproject.toml`에서 제거 |
| `src/agents/skills/` 빈 디렉토리 | 신규 `agents/` 구조로 대체 |
| `schemas/api/` 미연결 스터브 (user, member, notification, testcase, usecase, import_export, version) | 필요 시점에 신규 작성, 현 파일은 제거 |

### 1.2 프론트엔드

#### A. 그대로 재사용 (72개)

| 영역 | 대상 |
|---|---|
| 훅 | `useChatStream` 포함 14개 중 12개 |
| 스토어 | `chat-store`, `panel-store`, `artifact-store`, `project-store`, `overlay-store`, `record-store`, `readiness-store`, `search-store` (8개) |
| lib/services | `lib/api.ts`, `services/*` 전체 |
| 레이아웃 | Header / HeaderTabs / LeftSidebar / RightPanel / ResizeHandle / PanelToggleBar / ReadinessMiniView / Mobile* (10개) |
| 채팅 | MessageRenderer, ChatArea, ChatInput, ExtractedRequirements, PromptSuggestions, SourceReference, SessionList, SessionItem, ActionCards, SuggestionChips |
| 아티팩트 | ArtifactPanel, RecordsArtifact (기본 구조) |
| 프로젝트 | ProjectCard, ListItem, OverviewTab, KnowledgeTab, GlossaryTab, SectionsTab, ReadinessCard, Selector, GlossaryTable, GlossaryAddForm, GlossaryGeneratePanel, KnowledgePreviewModal |
| 요구사항 | RequirementTable, Item, Input, ExtractedList, ExtractedCard, ChatPanel, SuggestionPanel |
| 오버레이 | Modal, AlertDialog, ConfirmDialog, AppsDropdown, ProfileDropdown, SearchDialog, SettingsDialog |
| Shared/Landing | 전체 |
| shadcn/ui | 전체 |

#### B. 확장 후 재사용 (12개)

| 대상 | 확장 내용 |
|---|---|
| `hooks/useChatStream.ts` | **SSE 파서만 교체** (`@microsoft/fetch-event-source`), 토큰 버퍼링·콜백은 보존. `onInterrupt`/`onPlanUpdate`/`onArtifactCreated` 콜백 추가 |
| `services/agent-service.ts` | `SSEEvent` 타입에 신규 이벤트 추가 + `streamAgentChat` 교체 |
| `chat/MessageRenderer.tsx` | 신규 블록 파싱 추가 (기존 `[CLARIFY]` 구조 유지) |
| `chat/ChatInput.tsx` | interrupt 대기 상태 시각화 |
| `chat/SessionList/Item.tsx` | 에이전트 아이콘·턴수·산출물 배지·HITL 대기 상태 추가 |
| `chat/SourceViewerPanel.tsx` | diff 뷰 옵션 |
| `artifacts/RecordsArtifact.tsx` | 직접 확장 없음. **SRS/TC Editor 작성 시 레퍼런스로만** |
| `projects/ProjectKnowledgeTab/GlossaryTab/SectionsTab.tsx` | 라우트(`/knowledge`, `/glossary`, `/sections`)로 이관 |
| `projects/ProjectCreateForm.tsx` | 모듈 선택 UX 확장 |
| `requirements/RefineCompare.tsx` | `react-diff-viewer-continued` 기반 고급 diff |

#### C. 개조 (5개)

| 대상 | 개조 내용 |
|---|---|
| `chat/ClarifyQuestion.tsx` | `HitlData` 타입 통합, multi-step, cancel → **ClarifyCard**로 개명/리팩토링 |
| `chat/Questionnaire.tsx` | DecisionData 통합 |
| `requirements/RequirementTable.tsx` | 에디터 기능 강화 |
| `chat/SourceViewerPanel.tsx` | diff 기능 추가 |
| `chat/GenerateSrsProposal.tsx` | stub → 실구현 (SRS 생성 제안 CTA) |

#### D. 신규 작성 (§20 설계대로)

| # | 컴포넌트 / 페이지 | 위치 |
|---|---|---|
| N1 | AgentInvocationCard | `components/chat/AgentInvocationCard.tsx` |
| N2 | HITL 3종 (Clarify/Confirm/Decision) + useHitlResume | `components/chat/hitl/` |
| N3 | PlanProgress | `components/chat/PlanProgress.tsx` |
| N4 | SrsEditor + SrsSection + SrsToolbar | `components/artifacts/srs/` |
| N5 | TestCaseList + TestCaseCard + CoverageBadge | `components/artifacts/testcase/` |
| N6 | DesignDoc | `components/artifacts/design/` |
| N7 | VersionHistory + DiffViewer + RegenerateDialog | `components/artifacts/shared/` |
| N8 | ImpactGraph + ImpactList | `components/impact/` |
| N9 | Artifact Hub + Impact 라우트 | `app/(main)/projects/[id]/artifacts/*`, `/impact` |
| N10 | 신규 스토어: hitl-store, version-store, impact-store | `stores/` |
| N11 | `types/agent-events.ts` 단일 타입 파일 | `types/` |
| N12 | i18n 인프라 (Phase 4) | `next-intl` |

---

## 2. Phase별 작업 분해

### Phase 0 — Lift (프로토타입 이관, 2~3일)

**목표**: 프로토타입 코드를 현 저장소에 통째 복사하고, 즉시 동작하는 기준선 확보.

#### 0.1 공통
- [ ] `.prototype-ref/aise-v2/backend/` → `aise-v2-backend/backend/` 복사 (uv.lock 포함)
- [ ] `.prototype-ref/aise-v2/frontend/` → `aise-v2-backend/frontend/` 복사
- [ ] `.prototype-ref/aise-v2/docker-compose.yml`, `deploy/`, `start-*.sh` → 루트 복사 (검토 후)
- [ ] `.prototype-ref/aise-v2/CLAUDE.md`, `PLAN.md`, `PROGRESS.md`, `REFECTORING.md`, `AGENTS.md` → `docs/legacy/` 로 이동 (참고 보존)
- [ ] 루트 `.gitignore`에 `.prototype-ref/` 유지
- [ ] `PROGRESS.md` 신규 작성 시작 (세션 인계용)

#### 0.2 백엔드
- [ ] `backend/pyproject.toml` 그대로 (LangGraph/LiteLLM은 Phase 1에서 추가)
- [ ] `backend/alembic upgrade head` 동작 확인
- [ ] `cd backend && pytest` → 93 passed 재현
- [ ] `uvicorn src.main:app --reload` → 기존 API 호출 smoke test

#### 0.3 프론트엔드
- [ ] `frontend/package.json` 그대로
- [ ] `cd frontend && pnpm install && pnpm build` 성공
- [ ] `pnpm dev` → 기존 화면(프로젝트/요구사항/Agent) 동작 확인
- [ ] `pnpm lint` → 기존 기준 유지

#### 0.4 문서
- [ ] 루트 `CLAUDE.md` 유지 (이미 존재, 본 프로젝트 가이드)
- [ ] `docs/legacy/` 에 원본 문서 보존 (변경 금지)
- [ ] `start-dev.sh` 작성 (backend + frontend 동시 기동)

**완료 기준**: 신 저장소에서 기존 프로토타입 기능(프로젝트 CRUD, 지식 업로드, Records 추출, SRS 생성, Agent Chat)이 프로토타입과 동일하게 동작.

---

### Phase 1 — 기반 아키텍처 (2~3주)

**목표**: LangGraph 뼈대 + 에이전트 레지스트리 + SSE 이벤트 계약 확정 + 단일 에이전트 RAG 왕복이 새 아키텍처로 동작.

#### 1.1 공통 (API 계약 — 최우선)
- [ ] **`types/agent-events.ts` 신규 작성** (프론트). 단일 타입 소스:
  ```ts
  type AgentStreamEvent =
    | { type: 'token', data: { text: string } }
    | { type: 'tool_call', data: ToolCallData }
    | { type: 'tool_result', data: { name: string; result: unknown } }
    | { type: 'plan_update', data: PlanUpdateData }       // 신규
    | { type: 'interrupt', data: HitlData }               // 신규
    | { type: 'artifact_created', data: ArtifactRef }     // 신규
    | { type: 'done', data: { finish_reason: string } }
    | { type: 'error', data: { message: string } };
  ```
- [ ] **`backend/src/schemas/events.py`** 신규 — 위와 1:1 대응 Pydantic. SSE 발행 함수는 이 스키마 검증 강제
- [ ] **이벤트 네이밍 규약 문서** (`docs/events.md`): 기존 `token/tool_call/tool_result/done/error`는 유지, 신규 3종 추가

#### 1.2 백엔드
- [ ] **의존성 추가**: `langgraph`, `langgraph-checkpoint-postgres`, `litellm`, `redis`, `langfuse` (선택)
- [ ] **의존성 제거**: `deepagents` (미사용)
- [ ] **`agents/` 디렉토리** 신설 (`base.py`, `registry.py`, `knowledge_qa.py`)
- [ ] **`orchestration/` 디렉토리** 신설 (`state.py`, `supervisor.py`, `graph.py`)
- [ ] **최소 LangGraph 그래프**: `Supervisor → KnowledgeQA` (단일 에이전트)
- [ ] **`routers/agent.py` 재구성**: 내부 호출을 `graph.astream_events`로 교체. 기존 SSE 이벤트 포맷 100% 호환 유지
- [ ] **LangGraph thread_id ↔ `sessions.id`** 규약 확정. 체크포인터는 `PostgresSaver` — 자동 테이블 생성 확인
- [ ] **`llm_svc.py` → LiteLLM 어댑터** (Azure/OpenAI 동일 인터페이스)
- [ ] **`rag_svc.py` P0 픽스**: `project_id` 필수 매개변수 + 문서 `is_active=True` + `status='completed'` 필터. 교차 프로젝트 반환 0건 테스트 강제
- [ ] **`routers/agents.py` 신설**: `GET /agents` (레지스트리 노출), `GET /agents/{name}`
- [ ] **`docker-compose.yml`에 Redis 서비스 추가**
- [ ] **테스트**:
  - Supervisor 라우팅 단위 테스트 (single 케이스)
  - `project_id` 필터 교차 프로젝트 격리 테스트 강제 (픽스처에서 두 프로젝트 생성)
  - LangGraph 그래프 1회 왕복 smoke test

#### 1.3 프론트엔드
- [ ] **`@microsoft/fetch-event-source` 설치** 및 `services/agent-service.ts`의 `streamAgentChat` 파서만 교체. `useChatStream` 훅 인터페이스 불변 확인
- [ ] **기존 SSE 동작 회귀 테스트** (토큰 버퍼링, 모바일 청크 크기)
- [ ] **`types/agent-events.ts`** 신규 작성 (백엔드 `schemas/events.py`와 1:1)
- [ ] **`services/agent-service.ts`의 SSEEvent 타입** 교체
- [ ] **`useChatStream`에 신규 콜백** `onInterrupt`/`onPlanUpdate`/`onArtifactCreated` 추가 (사용은 Phase 2~3에서)
- [ ] **`hooks/useAgentMeta.ts`** 신규 — `GET /agents` 캐시(SWR)

#### 1.4 공통 완료 기준
- [ ] 기존 Agent Chat 동작을 LangGraph 경로로 재현 (RAG 질문 → 답변)
- [ ] `/api/v1/agents` 엔드포인트에서 `KnowledgeQAAgent`가 리턴됨
- [ ] RAG 교차 프로젝트 격리 테스트 통과
- [ ] 기존 93 passed 전부 통과 + 신규 테스트 추가
- [ ] 프론트 기존 화면 회귀 없음

**마일스톤 커밋 제안**:
- `feat(backend): introduce LangGraph + agent registry with KnowledgeQA`
- `feat(frontend): migrate SSE parser to fetch-event-source, preserve buffering`
- `fix(rag): enforce project_id + active+completed filters (P0)`

---

### Phase 2 — 멀티 에이전트 + 산출물 (3~4주)

**목표**: Supervisor 3-액션 라우팅 + 기존 도구들을 에이전트로 재편성 + SRS/TC/Design Editor 실구현.

#### 2.1 공통
- [ ] 통합 `artifacts` 테이블 스펙 확정 (SRS/Design/TC를 단일 테이블로 관리할지, 도메인별 분리 유지할지 결정)
  - **권장**: 도메인별 테이블 유지 (srs_documents 기존) + 상위 개념 `artifact_refs` 뷰 또는 조회 유틸 추가

#### 2.2 백엔드
- [ ] **`agents/requirement.py`**: Records 추출 도구를 에이전트로 래핑 (기존 `services/record_svc` + extract 로직)
- [ ] **`agents/srs_generator.py`**: 기존 `srs_svc.generate` + IEEE 830 프롬프트 재사용. `with_structured_output(SRSDocument)` 강제
- [ ] **`agents/testcase_generator.py`** (신규): `with_structured_output(TestCase)` + 요구사항 ↔ TC 연결
- [ ] **`agents/critic.py`** (신규): 완전성/일관성/EARS/커버리지 평가
- [ ] **Supervisor 3-액션 라우팅** 완성 (single/plan/clarify). 하이브리드(임베딩 top-5 + LLM) 구현
- [ ] **Plan 기반 순차 실행** 노드 (LangGraph)
- [ ] **SSE `plan_update` 이벤트 발행** — 단계 시작/완료마다
- [ ] **`routers/artifacts.py` 신설**:
  - `GET /projects/{id}/artifacts` (통합 목록)
  - `GET /artifacts/{id}` (통합 상세)
  - `PATCH /artifacts/{id}` / `PATCH /artifacts/{id}/sections/{sid}`
  - `POST /artifacts/{id}/regenerate` / `POST /artifacts/{id}/sections/{sid}/regenerate`
  - `POST /artifacts/{id}/export` (md 먼저, docx/pdf는 Phase 5)
- [ ] **`prompts/agent/chat.py` 분할**: `prompts/supervisor.md`, `prompts/agents/{name}.md`
- [ ] **테스트**: 각 에이전트 단위 + plan 체인(requirement → srs → critic) 통합

#### 2.3 프론트엔드
- [ ] **N1: AgentInvocationCard** — `toolCalls` 인라인 collapse (running/completed/error 상태)
- [ ] **N3: PlanProgress** — step별 pending/running/completed + 취소 버튼
- [ ] **N4: SrsEditor** — RecordsArtifact 패턴 차용. 섹션별 독립 저장, 섹션 메뉴(AI 재생성/수동 편집/비활성화/복사)
- [ ] **N5: TestCaseList** — 요구사항 그룹핑 + 커버리지 배지
- [ ] **N6: DesignDoc** — 기본 스텁 + 확장 구조
- [ ] **`types/agent-events.ts`에 PlanStep, ToolCallData 실사용**
- [ ] **`artifact-store` 확장**: 활성 아티팩트 ID + 섹션 편집 상태
- [ ] **회귀**: 기존 RecordsArtifact 동작 유지

#### 2.4 완료 기준
- [ ] "이 프로젝트의 요구사항을 뽑아줘" → Plan(knowledge_qa → requirement) → Records 탭 업데이트 (UC-03)
- [ ] "SRS 만들어줘" → Plan(requirement → srs_gen → critic) → SrsEditor 섹션별 스트리밍 (UC-04)
- [ ] 섹션 재생성 (UC-05) 동작
- [ ] TC 일괄 생성 + 커버리지 뱃지 (UC-06)
- [ ] `GET /agents` 응답에 5개 에이전트 모두 노출

---

### Phase 3 — HITL (2~3주)

**목표**: `interrupt()` 기반 구조화 HITL + 세션 재개 + HITL 컴포넌트 3종.

#### 3.1 공통
- [ ] SSE `interrupt` 이벤트 스키마 확정 (HitlData `{type: clarify|confirm|decision, interrupt_id, ...}`)

#### 3.2 백엔드
- [ ] **`orchestration/hitl.py`**: `interrupt()` 래퍼 (DESIGN §6.1)
- [ ] **`POST /api/v1/chat/{session_id}/resume`** 신설. body: `{ interrupt_id, response }`. `Command(resume=...)` 재개
- [ ] **Supervisor `clarify` 액션**이 `interrupt()`를 호출하도록 연결
- [ ] **중대한 변경 confirm** (예: 기존 요구사항 다량 삭제) — `agents/critic.py` 또는 전용 노드에서 `interrupt()`
- [ ] **모델 추가**: `hitl_requests` 테이블 + 마이그레이션 (감사용)
- [ ] **세션 TTL**: Redis 기반 대기 세션 정리 워커 (DESIGN §13) — 초기엔 단순 cron
- [ ] **테스트**: 모호한 질문 → interrupt → resume → 연속 스트림 검증 (E2E)

#### 3.3 프론트엔드
- [ ] **`stores/hitl-store.ts`** 신설 — interrupt 큐/응답 이력
- [ ] **N2a: ClarifyCard** — 기존 `ClarifyQuestion.tsx`를 `components/chat/hitl/ClarifyCard.tsx`로 이전 + `HitlData` 타입 통합 + multi-step
- [ ] **N2b: ConfirmCard** 신규 (impact 영향도 표시 포함)
- [ ] **N2c: DecisionCard** 신규 (다중 선택)
- [ ] **`useHitlResume(sessionId)`** 훅 신설 — `POST /chat/{id}/resume` + store 갱신
- [ ] **`useChatStream.onInterrupt`** 실배선 → `hitl-store` push
- [ ] **`MessageRenderer`** 인터셉트 업데이트 (신규 이벤트 → 전용 카드 렌더)
- [ ] **기존 `[CLARIFY]` 블록 병존 기간**: 양쪽 모두 렌더 가능(이행기 2~4주)
- [ ] **SessionList 강화**: HITL 대기 세션 배지 + "이어가기" 버튼

#### 3.4 완료 기준
- [ ] "인증 기능 좀 추가해줘" → ClarifyCard 렌더 → 선택 → resume → 스트림 이어짐 (UC-07)
- [ ] 세션이 끊긴 뒤 재접속해도 HITL 대기 상태에서 재개 가능
- [ ] HITL 이력 DB 기록 확인

---

### Phase 4 — 품질·버전·영향도 (지속)

**목표**: 하이브리드 검색 + 리랭킹 + 산출물 버전/Diff + 영향도 분석 + 관측성.

#### 4.1 백엔드
- [ ] **하이브리드 검색** (BM25 + 벡터) — pgvector + ts_vector
- [ ] **리랭킹** — Cohere Rerank 또는 BGE-reranker (Phase 전반)
- [ ] **Query rewriting** 노드
- [ ] **산출물 버전**:
  - `artifacts_versions` 테이블 + 자동 snapshot (PATCH 시)
  - `GET /artifacts/{id}/versions`, `/versions/{v}/diff`, `POST /artifacts/{id}/restore/{v}`
- [ ] **영향도 분석**:
  - `GET /projects/{id}/impact?changed_ids=...` (그래프 JSON)
  - `POST /projects/{id}/impact/apply` (일괄 재생성)
  - `agents/critic.py`에 `calculate_impact` 도구 추가
- [ ] **관측성**: Langfuse 연동 + `agent_executions` 테이블 기록(비용/지연/상태)
- [ ] **RAGAS 평가 파이프라인** (배치)
- [ ] **프롬프트 버저닝** (Langfuse 또는 파일 버전)

#### 4.2 프론트엔드
- [ ] **N7: VersionHistory + DiffViewer** — `react-diff-viewer-continued`
- [ ] **N8: ImpactGraph + ImpactList** — `@xyflow/react`
- [ ] **`/projects/[id]/impact` 페이지**
- [ ] **라우트 분리**: `/knowledge`, `/glossary`, `/sections` (기존 탭 상태 보존 훅)
- [ ] **Artifact Hub**: `/projects/[id]/artifacts/*`
- [ ] **`stores/version-store.ts`, `impact-store.ts`** 신설
- [ ] **i18n 인프라**: `next-intl` 도입 (한국어 기본 → 영어 추가)

#### 4.3 완료 기준
- [ ] FR-003 편집 → 영향도 토스트 → Impact 페이지 (UC-08)
- [ ] SRS 버전 3개 이상 누적 후 Diff 뷰 + Restore 동작

---

### Phase 5 — 운영화 (이후)

#### 5.1 백엔드
- [ ] RBAC (권한 시스템)
- [ ] 감사 로그
- [ ] Celery + Redis 브로커 (대규모 배치)
- [ ] DOCX/PDF export
- [ ] A/B 테스트 인프라
- [ ] SSO (Keycloak/LDAP)

#### 5.2 프론트엔드
- [ ] 모바일 최적화 마무리
- [ ] 접근성(WCAG AA) 감사
- [ ] A/B 테스트 UI
- [ ] 에이전트 성능 대시보드

---

## 3. 위험 요소 및 사전 조치

| # | 위험 | 조치 | 담당 Phase |
|---|---|---|---|
| **R1** | LangGraph 이관 시 기존 Agent Chat 회귀 | Phase 0에서 기준선 smoke test 스크립트 작성 → Phase 1에서 새 경로가 동일 출력 보장 테스트 | P0, P1 |
| **R2** | SSE 이벤트 백엔드/프론트 불일치 | `types/agent-events.ts` ↔ `schemas/events.py` 동기화 규칙 + PR 체크리스트. 변경 시 반드시 양쪽 함께 | P1~ |
| **R3** | `useChatStream` 버퍼링 × `fetch-event-source` 간섭 | Phase 1 초반 A/B 검증(기존/신규 병행). 모바일 저대역폭 시뮬레이션 | P1 |
| **R4** | `interrupt()` 기반 HITL ↔ 기존 `[CLARIFY]` 블록 UX 단절 | 이행기 2~4주 양쪽 렌더 병존. `FEATURE_FLAG_HITL_STRUCTURED` 환경변수로 토글 | P3 |
| **R5** | RAG project_id 누락 보안 사고 | **Phase 1 초반 최우선 수정 + 교차 프로젝트 테스트 강제**. CI에 `pytest tests/test_rag_isolation.py` 차단 게이트 | P1 |
| **R6** | 프론트 라우트 분리 시 기존 탭 상태 유실 | `artifact-store.activeTab` ↔ URL 양방향 동기화 훅(`useTabRoute`) | P4 |
| **R7** | REFECTORING.md ↔ DESIGN.md 용어 혼선 | §0.2 매핑 표를 `docs/glossary.md`로 정식화. 신규 코드는 DESIGN 용어만 사용 | P0, P1 |
| **R8** | Phase 0 이관 중 `node_modules` / `__pycache__` / `.next` 혼입 | `.gitignore` 사전 점검 후 복사 | P0 |
| **R9** | 기존 테스트 환경(NullPool, DB 클린업)이 새 마이그레이션과 충돌 | 신규 테이블 추가 시 `tests/conftest.py` 클린업 순서 업데이트 (FK 의존성) | P1~ |
| **R10** | Langfuse/LiteLLM 도입 시 LLM 비용·지연 증가 | Phase 4 도입 전 성능 벤치마크 (기존 vs LiteLLM wrapper) | P4 |
| **R11** | 프로토타입 한국어 Azure OpenAI 의존성이 LiteLLM에서 동일 동작 | 기존 Azure endpoint/key 2세트(`SRS_*`, `TC_*`) 유지 방식 검토. LiteLLM `azure/` 프로바이더로 매핑 | P1 |
| **R12** | `storage_svc` `secure=False` 운영 사고 | Phase 1에서 환경변수 분리 (P1 fix) | P1 |

---

## 4. 의존성 그래프

### 4.1 Phase 간 선행 관계

```
P0 Lift (코드 이관, 93 passed 재현)
  │
  ├─→ P1 기반 아키텍처
  │     ├─ SSE 이벤트 스키마 확정 ──────────┐
  │     ├─ LangGraph + 레지스트리 + KnowledgeQA
  │     ├─ LiteLLM 어댑터
  │     ├─ RAG project_id 필터 (P0 fix)
  │     └─ /agents 엔드포인트
  │
  ├─→ P2 멀티 에이전트 + 산출물
  │     ├─ Supervisor 3-액션 (P1의 레지스트리 필요)
  │     ├─ requirement/srs/tc/critic 에이전트
  │     ├─ plan_update 이벤트 (SSE 스키마 필요)
  │     └─ SrsEditor/TestCaseList/DesignDoc (프론트) ←─ P1 useChatStream 확장 필요
  │
  ├─→ P3 HITL
  │     ├─ interrupt() (P1 LangGraph + P2 Supervisor clarify 필요)
  │     ├─ /chat/{id}/resume
  │     ├─ hitl-store + Clarify/Confirm/DecisionCard (P2 컴포넌트 패턴 필요)
  │     └─ 세션 재개 E2E 테스트
  │
  ├─→ P4 품질·버전·영향도
  │     ├─ 하이브리드 검색 (P1 RAG 기반)
  │     ├─ artifact_versions (P2 artifacts 기반)
  │     ├─ 영향도 API + Graph (P2 artifacts + P3 critic 필요)
  │     └─ 라우트 분리 (프론트)
  │
  └─→ P5 운영화
        ├─ RBAC / SSO
        ├─ Celery 배치
        └─ DOCX/PDF export
```

### 4.2 주요 작업 단위의 선후 관계 (Phase 내부)

**Phase 1 (백엔드)**:
```
pyproject.toml 의존성 업데이트
  → agents/base.py + registry.py
  → orchestration/state.py
  → agents/knowledge_qa.py (rag_svc 래핑)
  → orchestration/supervisor.py (최소 — single만)
  → orchestration/graph.py
  → routers/agent.py 내부 교체
  → routers/agents.py 신설
  (병행) rag_svc P0 fix + 테스트
  (병행) llm_svc LiteLLM 어댑터
```

**Phase 1 (프론트)**:
```
@microsoft/fetch-event-source 설치
  → agent-service.ts streamAgentChat 교체
  → useChatStream 콜백 인터페이스 확장
  (병행) types/agent-events.ts 신규
  → hooks/useAgentMeta.ts
```

**Phase 2 (백엔드)**:
```
agents/requirement.py (record_svc 래핑)
  → agents/srs_generator.py (srs_svc 래핑)
  → agents/testcase_generator.py (신규)
  → agents/critic.py (신규)
  → Supervisor plan 액션 (LLM 판정 + 임베딩 필터)
  → plan 실행 노드 (state에 plan 누적)
  → routers/artifacts.py
```

**Phase 2 (프론트)**:
```
AgentInvocationCard (toolCalls 인라인)
  → PlanProgress (plan_update 이벤트 소비)
  → SrsEditor (RecordsArtifact 패턴)
  → TestCaseList
  → DesignDoc
```

**Phase 3 (백엔드)**:
```
hitl_requests 마이그레이션
  → orchestration/hitl.py (interrupt 래퍼)
  → supervisor clarify → interrupt() 연결
  → /chat/{id}/resume 엔드포인트
```

**Phase 3 (프론트)**:
```
types/agent-events.ts HitlData 확장
  → hitl-store
  → ClarifyCard (기존 ClarifyQuestion 이전)
  → ConfirmCard / DecisionCard
  → useHitlResume
  → MessageRenderer 라우팅
  → SessionList HITL 배지
```

### 4.3 크리티컬 패스

**가장 선행되는 것** (다른 모든 것의 전제):
1. Phase 0 이관 완료 + 93 passed 재현
2. SSE 이벤트 스키마 확정 (`types/agent-events.ts` ↔ `schemas/events.py`)
3. LangGraph 최소 그래프 동작 (KnowledgeQA 단일 에이전트)
4. RAG project_id 필터 (P0 보안)

**가장 후행되는 것** (앞의 모든 기반 필요):
- HITL resume E2E (P1+P2+P3 통합)
- 영향도 분석 (P2 artifacts + P3 critic + P4 version)

---

## 5. 결정 사항 (확정, 2026-04-21)

| # | 결정 사항 | 확정 | 비고 |
|---|---|---|---|
| **D1** | 프로토타입 코드 이관 방식 | ✅ **복사 이관** — Phase 0에서 완료 | 현 저장소 `backend/` / `frontend/` 서브디렉토리 |
| **D2** | `artifacts` 통합 vs 도메인별 분리 | ✅ **분리 유지 + 상위 조회 유틸** | `srs_documents` 등 기존 테이블 보존. Design/TC는 각자 도메인 테이블 유지. 공통 조회는 서비스 레이어에서 |
| **D3** | `assist_*` 레거시 엔드포인트 | ✅ **제거 결정** (실행: Phase 2 초) | 프롬프트·로직 `docs/legacy/assist-reference/`로 스냅샷 + 본 코드에 `DEPRECATED` 마킹 완료. **라우터/서비스/프론트 호출부 실제 삭제는 Phase 2 작업 M에서 수행** (현 시점 라우터는 여전히 등록·응답함) |
| **D4** | LiteLLM 도입 시점 | ✅ **Phase 1** | `llm_svc`를 LiteLLM 어댑터로 재감쌈. Azure/OpenAI 동일 인터페이스 |
| **D5** | `@microsoft/fetch-event-source` 교체 | ✅ **Phase 1 전면 교체** | `useChatStream` 토큰 버퍼링·콜백 인터페이스는 보존. `services/agent-service.ts`의 파서만 교체 |
| **D6** | 라우트 분리 (`/knowledge`·`/glossary`·`/sections`·`/impact`) | ✅ **Phase 4** | 핵심 기능 우선. UX 개선은 후반 |
| **D7** | LangGraph 체크포인터 | ✅ **PostgresSaver (env-switched)** | 기존 Postgres 재사용. DESIGN.md §3 명시. 구현은 Phase 1에 완료 — `LANGGRAPH_CHECKPOINT_URL` 설정 시 `AsyncPostgresSaver`, 미설정 시 기본 `MemorySaver`. Phase 1은 HITL 없어 Memory로 충분, Phase 3 HITL 도입 시 env만 켜면 전환 완료. Phase 4에 Redis 필요 시 교체 |
| **D8** | Langfuse | ✅ **자가호스팅** — Phase 4에 `docker-compose.yml`에 컨테이너 추가 | **이유**: 트레이스에 사내 요구사항/SRS/설계문서 포함 → LGE 보안심사 리스크. 이미 Postgres/MinIO 운영 중이라 인프라 추가 비용 미미. Phase 4 전까지는 `LANGFUSE_HOST` 환경변수로 감싸 클라우드/자가호스팅 전환 가능하게 설계 |
| **D9** | `deepagents` 패키지 | ✅ **Phase 1 즉시 제거** | 미사용 확인. `pyproject.toml`에서 제거 |
| **D10** | 프론트엔드 패키지 매니저 | ✅ **pnpm 단일 유지** | `package-lock.json` 삭제, `pnpm-lock.yaml`만 유지. `package.json`에 `packageManager: pnpm@...` 명시 |

---

## 6. 바로 다음 액션 (Step 4 승인 후 착수 시)

1. **Phase 0 먼저 실행** — 이관 PR 1개
2. Phase 1 시작 전 SSE 이벤트 스키마 합의 문서 작성
3. 주요 마일스톤마다 커밋 제안 + `PROGRESS.md` 업데이트
4. 한 세션에서 10개 이상 새 파일 생성 시 중간 체크포인트

---

**작성일**: 2026-04-21
**선행 문서**: `DESIGN.md`, `FRONTEND_DESIGN.md`, `ANALYSIS.md`
**다음 액션**: 사용자 검토 → 승인 후 Phase 0 착수
