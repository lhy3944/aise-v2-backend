# PROGRESS.md — 진행 상황

> **규칙**: 각 Phase 착수/완료 시 상태 테이블과 작업 로그를 동시에 갱신. 세션 간 인계의 단일 원천.
> **선행 문서**: `DESIGN.md`, `FRONTEND_DESIGN.md`, `ANALYSIS.md`, `MIGRATION_PLAN.md`, `CLAUDE.md`

---

## 상태 테이블

| Phase | 구간 | 상태 | 진행률 | 비고 |
|---|---|---|---|---|
| **Phase 0** | Lift (프로토타입 이관) | ✅ 완료 | 100% | 2026-04-21 |
| **Phase 1** | 기반 아키텍처 (LangGraph + 레지스트리 + SSE 계약) | 🟡 대기 | 0% | 시작 전 D1~D10 최종 승인 권장 |
| **Phase 2** | 멀티 에이전트 + 산출물 Editor | ⏸ | 0% | P1 선행 |
| **Phase 3** | HITL (interrupt + resume + 컴포넌트 3종) | ⏸ | 0% | P2 선행 |
| **Phase 4** | 품질·버전·영향도 | ⏸ | 0% | |
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

## Phase 1 착수 전 체크리스트

### 사용자 승인 대기 항목 (MIGRATION_PLAN §5)
- [ ] D1 코드 이관 방식 (추천: 복사 — **이미 Phase 0에서 복사 이관 완료**)
- [ ] D2 artifacts 테이블 통합 vs 분리 (추천: 분리 유지 + 뷰)
- [ ] D3 assist_* 레거시 유지 여부 (추천: 유지)
- [ ] D4 LiteLLM 도입 시점 (추천: Phase 1)
- [ ] D5 fetch-event-source 전면 vs 점진 (추천: Phase 1 전면)
- [ ] D6 라우트 분리 시점 (추천: Phase 4)
- [ ] D7 체크포인터 Postgres vs Redis (추천: Postgres)
- [ ] D8 Langfuse 자가호스팅 vs 클라우드 — 논의 필요
- [ ] D9 deepagents 제거 (추천: Phase 1 즉시)
- [ ] D10 pnpm-lock vs package-lock 단일화 — 사용자 결정

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
