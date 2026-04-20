# PROGRESS.md — 진행 상황

> **규칙**: 각 Phase 착수/완료 시 상태 테이블과 작업 로그를 동시에 갱신. 세션 간 인계의 단일 원천.
> **선행 문서**: `DESIGN.md`, `FRONTEND_DESIGN.md`, `ANALYSIS.md`, `MIGRATION_PLAN.md`, `CLAUDE.md`

---

## 상태 테이블

| Phase | 구간 | 상태 | 진행률 | 비고 |
|---|---|---|---|---|
| **Phase 0** | Lift (프로토타입 이관) | ✅ 완료 | 100% | 2026-04-21 |
| **Phase 1** | 기반 아키텍처 (LangGraph + 레지스트리 + SSE 계약) | ✅ 완료 | 100% | 2026-04-21 (같은 날 연속 진행) |
| **Phase 2** | 멀티 에이전트 + 산출물 Editor | 🟡 대기 | 0% | 시작 신호 대기. assist_* 실제 제거는 이 Phase 말 |
| **Phase 3** | HITL (interrupt + resume + 컴포넌트 3종) | ⏸ | 0% | P2 선행 |
| **Phase 4** | 품질·버전·영향도 | ⏸ | 0% | Langfuse 자가호스팅 도입 |
| **Phase 5** | 운영화 (RBAC/SSO/DOCX) | ⏸ | 0% | |

**범례**: ✅ 완료 · 🟢 진행 중 · 🟡 대기 · ⏸ 미시작 · ❌ 블록됨

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
- [ ] `USE_LANGGRAPH=true` 환경에서 수동 smoke test (개발 서버에서 실제 Agent Chat 왕복)
- [ ] 프론트 `agent-service.ts`의 신 envelope 파싱 UI 수동 확인 (tool_call → AgentInvocationCard 없이는 표시 못함, Phase 2 N1에서 해결)

### Phase 2 우선 작업 (MIGRATION_PLAN §2.2 요약)
1. 신규 에이전트 등록
   - `agents/requirement.py` (기존 `record_svc` 래핑)
   - `agents/srs_generator.py` (기존 `srs_svc` 래핑 + structured output)
   - `agents/testcase_generator.py` (신규)
   - `agents/critic.py` (신규)
2. Supervisor 하이브리드 라우팅
   - 임베딩 top-5 후보 필터 → LLM 판정 → single / **plan** / clarify
   - `plan` 액션 실행 노드 (state에 plan 배열 누적, plan_update SSE 발행)
3. artifacts 통합 라우터 (`routers/artifacts.py`)
   - GET /projects/{id}/artifacts, GET /artifacts/{id}
   - PATCH /artifacts/{id}/sections/{sid} · POST /artifacts/{id}/regenerate
4. 프론트 신규 컴포넌트 (FRONTEND_DESIGN §20)
   - N1 AgentInvocationCard (toolCalls 인라인 collapse)
   - N3 PlanProgress
   - N4 SrsEditor (RecordsArtifact 패턴 차용)
   - N5 TestCaseList
5. `USE_LANGGRAPH=true` 기본화 + 레거시 `agent_svc` 제거
6. **D3 실제 제거**: assist_*(backend + frontend 3 호출부) 삭제 → Requirement Agent 경로로 대체

### 이전 기록용: 결정 확정 (2026-04-21, MIGRATION_PLAN §5)
- [x] D1 복사 이관 (Phase 0 완료)
- [x] D2 artifacts 도메인별 분리 유지 + 조회 유틸
- [x] **D3 assist_* 제거** (Phase 1 말~2 초, `docs/legacy/assist-reference/`로 스냅샷 후 삭제)
- [x] D4 LiteLLM Phase 1
- [x] D5 fetch-event-source Phase 1 전면
- [x] D6 라우트 분리 Phase 4
- [x] D7 PostgresSaver
- [x] **D8 Langfuse 자가호스팅** (Phase 4, `LANGFUSE_HOST` 환경변수로 감쌈)
- [x] D9 deepagents Phase 1 즉시 제거
- [x] **D10 pnpm 단일 유지** (`package-lock.json` 삭제, `packageManager` 필드 명시)

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
- **Backend 테스트 실행 전** `DATABASE_URL="postgresql+asyncpg://aise:aise1234@localhost:5432/aise_test" uv run alembic upgrade head` 필요 시 수행.
