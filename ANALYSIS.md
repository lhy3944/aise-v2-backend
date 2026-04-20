# ANALYSIS.md — 기존 프로토타입 자산 상세 분석

> **분석 대상**: https://github.com/lhy3944/aise-v2 (`.prototype-ref/aise-v2/`에 shallow clone)
> **분석 기준**: `DESIGN.md` (백엔드 설계) + `FRONTEND_DESIGN.md` (프론트엔드 설계)
> **작성일**: 2026-04-21
> **다음 문서**: `MIGRATION_PLAN.md`

---

## 0. 핵심 발견 사항 (Executive Summary)

### 0.1 프로토타입의 실제 상태 — 당초 가정과 크게 다름

기존 프로토타입은 **"초기 스캐폴딩"이 아니라 Phase 1~4 대부분 구현이 완료된 프로덕션급 프로토타입**이다. 다음 수치가 이를 보여준다:

| 영역 | 실측 | DESIGN.md Phase 매핑 |
|---|---|---|
| 백엔드 코드 라인 (src) | ~8,000줄 | Phase 1~4 대부분 구현 |
| Alembic 마이그레이션 | **16개** | MVP → Phase 4 전체 |
| 테스트 | **93 passed / 3 skipped** (~2,146줄) | Phase 3까지 회귀 안정 |
| API 라우터 | **13개 / 50+ 엔드포인트** | DESIGN §10 대부분 커버 |
| 프론트엔드 컴포넌트 | **97개** | UC-01~UC-06 기본 동작 |
| Zustand 스토어 | **11개** | FRONTEND_DESIGN §22.1 전부 구현 |
| 훅 | **14개** | `useChatStream.ts`(453줄) 등 핵심 완성 |

**즉, 본 프로젝트는 "신규 구축"이 아니라 "이관 + 아키텍처 리팩토링 + 누락 기능 추가"이다.**

### 0.2 DESIGN.md 목표와의 가장 큰 Gap 3가지

| # | Gap | 현황 | 영향 |
|---|---|---|---|
| **G1** | **LangGraph 미도입** | Agent Chat은 OpenAI Function Calling 직접 호출로 구현 (`agent_svc.py` 450줄). `deepagents` 의존성은 설치되어 있으나 미사용 | HITL `interrupt()`, 체크포인트, `/resume` 엔드포인트 없음. DESIGN §6 재설계 필요 |
| **G2** | **LiteLLM 미도입** | `llm_svc.py`가 OpenAI SDK + Azure OpenAI를 직접 래핑 | 모델 교체·비용 트래킹·프로바이더 추상화가 없음. 단, 현 구조도 Azure/OpenAI 스위치는 가능 |
| **G3** | **에이전트 레지스트리 패턴 부재** | 에이전트는 `agent_svc.stream_chat()`의 단일 함수 내 tool 배열로 표현. `BaseAgent`/`@register_agent` 없음 | DESIGN §4 "플러그인 자동 등록"은 미구현. `src/agents/skills/` 디렉토리만 존재(빈 상태) |

### 0.3 재활용 판단 — 한 문장 요약

- **백엔드**: 모델·마이그레이션·CRUD 서비스·라우터·테스트는 **A등급(그대로 유지)**. 오케스트레이션 레이어(`agent_svc.py`, `utils/json_parser.py`, 프롬프트 강제 로직)는 **C등급(신규 아키텍처로 대체)** — 단, 기존이 제공하던 **기능(도구 실행, 세션 영속, SSE 스트리밍, RAG 호출)은 LangGraph 노드로 감싸서 보존**.
- **프론트엔드**: 훅·스토어·lib·API 서비스·레이아웃·대부분의 채팅/프로젝트 컴포넌트는 **A등급**. `RecordsArtifact.tsx`(473줄)는 **SRS/TC Editor의 템플릿 레퍼런스**. 신규 HITL 3종·PlanProgress·AgentInvocationCard·VersionHistory·ImpactGraph·3개 stub Artifact(SRS/Design/TC)는 **신규 작성**.

### 0.4 REFECTORING.md가 이미 식별한 부채 (P0 중복 주의)

기존 팀이 최근(2026-04-18) 작성한 `REFECTORING.md`에 **DESIGN.md와 동일한 방향의 리팩토링 로드맵**이 명시되어 있다. 즉, **Harness Engineering (Intent Router + Context Loader + Tool Gateway + Orchestrator + Renderers)** 구조로 이관 중이며, 이는 DESIGN.md의 Supervisor + LangGraph 노드 + 에이전트 레지스트리 개념과 정확히 대응된다.

**→ 우리는 REFECTORING.md의 미완 항목을 DESIGN.md 규격(LangGraph 기반)으로 완성하는 형태로 진행해야 한다.** (중복 노력 방지)

---

## 1. 백엔드 기존 자산

### 1.1 의존성 요약

| 카테고리 | 기술 | 버전 | 비고 |
|---|---|---|---|
| 언어/런타임 | Python | ≥3.14 | uv 패키지 관리 |
| 웹 프레임워크 | FastAPI | ≥0.135.2 | uvicorn + pydantic v2 |
| DB/ORM | SQLAlchemy (async) | ≥2.0.0 | asyncpg |
| 비동기 드라이버 | asyncpg | ≥0.30.0 | PostgreSQL |
| 벡터 DB | pgvector | ≥0.4.0 | 인덱스 포함 |
| 마이그레이션 | Alembic | ≥1.18.4 | 16개 버전 |
| LLM | OpenAI SDK | ≥2.30.0 | Azure + OpenAI 모두 지원 |
| LLM 에이전트 | **deepagents** | ≥0.4.12 | **설치만 됨, 미사용** |
| 객체 스토리지 | MinIO | ≥7.2.0 | 지식 문서 |
| 파일 파서 | pymupdf, python-docx, python-pptx, openpyxl | 최신 | PDF/DOCX/PPTX/XLSX |
| 토큰 | tiktoken | ≥0.9.0 | 청킹 |
| 로깅 | Loguru | ≥0.7.3 | 구조화 |
| 테스트 | pytest, pytest-asyncio, pytest-cov | 최신 | 93 passed / 3 skipped |

**DESIGN.md 대비 없는 것**: LangGraph · LiteLLM · LangGraph PostgresSaver · Langfuse · Celery · Redis

### 1.2 디렉토리 구조

```
backend/
├── pyproject.toml                 # uv, pytest 설정
├── Dockerfile                     # 2-stage (builder → runner)
├── alembic.ini / alembic/versions/*   # 16개 마이그레이션
├── src/
│   ├── main.py                    # FastAPI 진입점 (33줄) · 13개 라우터 등록
│   ├── core/
│   │   ├── database.py            # async 엔진 (29줄)
│   │   ├── cors.py
│   │   ├── exceptions.py          # AppException (31줄)
│   │   └── logging.py             # Loguru
│   ├── middleware/
│   │   ├── logging_middleware.py
│   │   └── logging_middleware_asgi.py (미연결)
│   ├── models/                    # SQLAlchemy ORM (~360줄)
│   │   ├── project.py (43), requirement.py (75), record.py (32)
│   │   ├── srs.py (39), session.py (45), knowledge.py (45)
│   │   ├── glossary.py (35), review.py (25)
│   ├── schemas/api/               # Pydantic (~1,087줄)
│   ├── routers/                   # 13개 (~960줄)
│   ├── services/                  # 16개 (~4,460줄)
│   ├── prompts/                   # agent, assist, review, srs, glossary, knowledge
│   ├── utils/                     # json_parser, reorder, db, text_chunker
│   ├── integrations/              # jira/, polarion/ (미구현)
│   └── agents/                    # skills/ 디렉토리만 존재 (빈 상태)
└── tests/ (~2,146줄, 93 passed)
```

### 1.3 모듈별 역할 상세 (주요 항목)

| 경로 | 라인수(대략) | 역할 | 등급 | 판단 근거 |
|---|---|---|---|---|
| **models/** 전체 | 340 | SQLAlchemy ORM 8종 | **A** | Phase 1~4 스키마 완성, 마이그레이션 16개로 안정 |
| core/database.py | 29 | AsyncSession 엔진 | **A** | 프로덕션 설정 완료 |
| core/exceptions.py | 31 | AppException + handler | **A** | 표준 구조 |
| middleware/logging_middleware.py | - | 요청/응답 로깅 | **A** | 안정 동작 |
| routers/project.py | 120 | 프로젝트 CRUD + settings + readiness | **A** | API 명확 |
| routers/record.py | 119 | Record CRUD + SSE 추출 | **A** | Phase 3 완성 |
| routers/section.py | 96 | 섹션 CRUD + AI 추출 | **A** | 기본 섹션 보장 로직 |
| routers/srs.py | 67 | SRS 생성/조회/섹션편집/재생성 | **A** | Phase 4 완성 |
| routers/glossary.py | 87 | 용어 CRUD + AI 생성/추출/승인 | **A** | |
| routers/knowledge.py | 108 | 문서 업로드 + 청크 + RAG chat | **A** | Phase 2 완성 |
| routers/session.py | 64 | 세션 CRUD | **A** | |
| routers/review.py | 76 | 요구사항 리뷰 (conflict/dup/clarity) | **A** | |
| **routers/agent.py** | 33 | **Agent Chat SSE 진입점** | **B** | 핸들러 유지, 내부 로직은 LangGraph로 교체 |
| routers/assist.py | 64 | refine/suggest/chat (Phase 1 레퍼런스) | **B** | Agent Chat으로 통합 예정 |
| routers/requirement.py | 99 | 레거시 CRUD | **B** | Record로 대체되지만 호환성 유지 |
| services/record_svc.py | 250+ | Record 추출/승인 + display_id 채번 | **A** | Phase 3 안정 |
| services/section_svc.py | 150+ | 섹션 + 기본 섹션 보장 | **A** | 부분 재정렬 충돌 방지 |
| services/srs_svc.py | 80+ | IEEE 830 기반 SRS 생성 | **A** | 프롬프트 섹션별 재사용 |
| services/llm_svc.py | 100+ | Azure/OpenAI 프로바이더 추상 | **B** | 모델 설정 연동(P1) + LiteLLM 이관 시 re-wrap |
| services/review_svc.py | 200+ | 리뷰 엔진 | **A** | 안정 |
| services/embedding_svc.py | 50+ | 임베딩 배치 | **A** | |
| services/knowledge_svc.py | 150+ | 문서 + MinIO + 청크 파이프라인 | **A** | |
| services/session_svc.py | 100+ | 세션/메시지 CRUD | **A** | |
| services/glossary_svc.py | 150+ | 용어 CRUD + 생성/추출 | **A** | |
| services/project_svc.py | 150+ | 프로젝트 + readiness | **B** | `readiness_svc`와 책임 중복(P1) |
| services/readiness_svc.py | 50+ | 준비도 계산 | **C** | `project_svc`로 병합 |
| **services/agent_svc.py** | **450+** | **Agent Chat 오케스트레이션 + SSE + Function Calling** | **C** | **LangGraph 그래프로 전면 재구성** (기능은 보존) |
| services/rag_svc.py | 100+ | pgvector 검색 + Knowledge Chat | **B** | 문서 활성/완료 필터 부재(P0) |
| services/document_processor.py | 100+ | 파일 파싱 + 청킹 + 임베딩 | **B** | ALLOWED_FILE_TYPES와 파서 분기 불일치(P1) |
| services/storage_svc.py | 80+ | MinIO 래퍼 | **B** | `secure=False` 고정(P1 보안) |
| services/assist_svc.py | 150+ | Phase 1 어시스트 레퍼런스 | **B** | Agent로 통합 or 유지 |
| services/suggestion_svc.py | 50+ | Fingerprint 캐시 | **A** | |
| prompts/agent/chat.py | 300+ | Agent Chat 시스템 프롬프트 (대형) | **B** | 분할 후 Supervisor/각 에이전트별로 재배치 |
| prompts/srs/generate.py | - | IEEE 830 기반 | **A** | 그대로 재사용 |
| prompts/assist/*, review/*, glossary/*, knowledge/* | - | | **A/B** | |
| **utils/json_parser.py** | 40 | JSON fence 제거 + 파싱 | **B** | 파싱 실패 → 502 즉발(P0), `with_structured_output` 도입 후 축소 |
| utils/reorder.py | 50+ | 부분 재정렬 충돌 방지 | **A** | |
| utils/text_chunker.py | - | 토큰 기반 청킹 (500 + 50 overlap) | **A** | |
| tests/ | 2,146 | 10개 테스트 파일, 93 passed | **A** | 그대로 유지, HITL/Agent 테스트 추가 |

### 1.4 DB 모델 & 마이그레이션

**현재 테이블(14개, 16개 마이그레이션 적용)**:

| 테이블 | PK | 주요 FK | 상태 |
|---|---|---|---|
| projects | UUID | - | ✅ |
| project_settings | UUID | projects | ✅ (llm_model, 언어) |
| requirement_sections | UUID | projects | ✅ (기본 5개 자동) |
| requirements | UUID | projects, sections | ✅ (레거시) |
| requirement_versions | UUID | projects | ✅ |
| records | UUID | projects, sections, knowledge_documents | ✅ (Phase 3 핵심) |
| glossary_items | UUID | projects, knowledge_documents | ✅ |
| knowledge_documents | UUID | projects | ✅ (status: pending/processing/completed/failed, is_active) |
| knowledge_chunks | UUID | knowledge_documents | ✅ (pgvector 포함) |
| requirement_reviews | UUID | projects | ✅ (JSONB) |
| srs_documents | UUID | projects | ✅ |
| srs_sections | UUID | srs_documents, sections | ✅ |
| sessions | UUID | projects | ✅ (Agent 대화) |
| session_messages | UUID | sessions | ✅ (JSONB tool_calls) |

**DESIGN §9 목표 스키마 대비 Gap**:

| 목표 테이블 | 현황 | 판단 |
|---|---|---|
| projects | ✅ 동일 | 유지 |
| knowledge_documents | ✅ 동일 | 유지 |
| document_chunks (pgvector) | ✅ `knowledge_chunks`로 구현 | **이름만 다름, 테이블 추가 불필요** |
| conversations (= thread_id) | ✅ `sessions` + `session_messages`로 구현 | 유지 (단, LangGraph thread_id를 `sessions.id`에 일치시키는 규약 확정 필요) |
| artifacts (JSONB) | ⚠️ `srs_documents` + `srs_sections`로 구현 (SRS 전용) | **Design/TC 일반화 필요** — §8.1의 `artifacts(type, content JSONB)` 통합 테이블 신설 검토 |
| hitl_requests | ❌ 미구현 | **신설 필요** (DESIGN §6) |
| agent_executions | ❌ 미구현 (`session_messages.tool_calls`에 부분 기록) | **신설 필요** (비용/지연 추적용) |
| LangGraph checkpoints | ❌ 미구현 | **PostgresSaver가 자동 생성** (마이그레이션 수동 작성 불필요) |

### 1.5 API 엔드포인트 목록 (50+)

| Method | Path | 목적 | DESIGN §10 매핑 | 등급 |
|---|---|---|---|---|
| **프로젝트** | | | | |
| POST/GET/GET/PUT/DELETE | `/api/v1/projects[/{id}]` | 프로젝트 CRUD | §10.2 | A |
| GET/PUT | `/api/v1/projects/{id}/settings` | 설정(LLM/언어) | §10.2 | A |
| GET | `/api/v1/projects/{id}/readiness` | 준비도 | 확장 | A |
| **요구사항(레거시)** | | | | |
| GET/POST/PUT/DELETE | `/api/v1/projects/{id}/requirements[/{req_id}]` | | | B |
| PUT | `.../requirements/reorder` | 순서 변경 | | B |
| POST | `.../requirements/select` | 선택(SRS 포함 여부) | | B |
| **섹션** | | | | |
| GET/POST/PUT/DELETE | `/api/v1/projects/{id}/sections[/{sid}]` | 섹션 CRUD | | A |
| PATCH | `.../sections/{sid}/toggle` | 활성화 토글 | | A |
| PUT | `.../sections/reorder` | 순서 변경 | | A |
| POST | `.../sections/extract` | AI 섹션 추출 | | A |
| **레코드 (Phase 3 핵심)** | | | | |
| GET/POST/PUT/DELETE | `/api/v1/projects/{id}/records[/{record_id}]` | Record CRUD | | A |
| PUT | `.../records/reorder` | 순서 변경 | | A |
| PATCH | `.../records/{record_id}/status` | draft/approved/excluded | | A |
| POST | `.../records/extract` | **AI 추출(SSE)** | | A |
| POST | `.../records/extract-section` | 특정 섹션 재추출 | | A |
| POST | `.../records/approve` | 일괄 승인 | | A |
| **SRS (Phase 4)** | | | | |
| POST | `.../srs/generate` | SRS 생성 | §10.3 | A |
| GET | `.../srs[/{srs_id}]` | SRS 목록/상세 | §10.3 | A |
| PUT | `.../srs/{srs_id}/sections/{sid}` | 섹션 편집 | §20.4 | A |
| POST | `.../srs/{srs_id}/regenerate` | 재생성 | §20.5 | A |
| **용어** | | | | |
| GET/POST/PUT/DELETE | `.../glossary[/{item_id}]` | | | A |
| POST | `.../glossary/generate` | 기존 요구사항 기반 | | B |
| POST | `.../glossary/extract` | 지식문서 기반 추출 | | A |
| POST | `.../glossary/approve` | 일괄 승인 | | A |
| **지식** | | | | |
| GET/POST | `.../documents` | 목록/업로드 | §10.2 | A |
| PATCH/DELETE | `.../documents/{doc_id}[/toggle]` | 활성화/삭제 | | A |
| GET | `.../documents/{doc_id}/preview` | 텍스트 미리보기 | | A |
| POST | `.../documents/{doc_id}/reprocess` | 재처리 | | A |
| GET | `.../documents/{doc_id}/chunks` | 청크 목록 | | A |
| POST | `.../knowledge/chat` | **RAG 지식챗** | | A |
| **리뷰** | | | | |
| POST | `.../review/requirements` | conflict/dup/clarity | | A |
| GET | `.../reviews/latest` | 최신 리뷰 | | A |
| **Agent Chat (DESIGN §10.1)** | | | | |
| POST | `/api/v1/agent/chat` | **Agent Chat SSE** | §10.1 | **B** → **C** 재구성 |
| **Assist (Phase 1 레거시)** | | | | |
| POST | `.../assist/refine` / `.../assist/suggest` / `.../assist/chat` | | | B |
| **Session** | | | | |
| POST/GET/GET/PATCH/DELETE | `/api/v1/sessions[/{session_id}]` | 세션 CRUD | §10.1 부분 | A |

**DESIGN §10 대비 없는 것**:
- `POST /chat/{session_id}/resume` (HITL 재개) — **신설 필요**
- `GET /agents` / `GET /agents/{agent_name}` — **신설 필요** (레지스트리 노출)
- `POST /artifacts/{artifact_id}/export` (md/docx/pdf) — **신설 필요**
- 영향도 분석 API (`GET /projects/{id}/impact`) — **신설 필요** (FRONTEND_DESIGN §20.6)
- 산출물 버전 API (`GET /artifacts/{id}/versions`, `/diff`, `/restore`) — **신설 필요**

### 1.6 Pydantic 스키마 목록

| 경로 | 주요 스키마 | 등급 |
|---|---|---|
| api/project.py | ProjectCreate/Update/Response, ProjectSettingsResponse | A |
| api/record.py | RecordCreate/Update/Response, RecordExtractResponse, RecordApproveRequest | A |
| api/section.py | SectionCreate/Update/Response | A |
| api/srs.py | SrsDocumentResponse, SrsSectionResponse, SrsListResponse | A |
| api/glossary.py | GlossaryCreate/Update/Response, GlossaryApproveRequest | A |
| api/knowledge.py | KnowledgeDocumentResponse, KnowledgeChunkResponse, KnowledgeChatRequest/Response | A |
| api/session.py | SessionCreate/Response, SessionMessageResponse | A |
| api/agent.py | AgentChatRequest | A (확장: `interrupt_id`, resume body) |
| api/review.py | ReviewRequest/Response, ReviewIssue | A |
| api/assist.py | AssistRequest/Response, ExtractedRequirement | B |
| api/readiness.py | ReadinessResponse | A |
| api/requirement.py | RequirementCreate/Update/Response, RequirementVersionResponse | B |
| api/* (미연결) | user, member, notification, testcase, usecase, import_export, version | C (필요 시 신규) |

### 1.7 인증/세션/DB 연결 패턴

- **인증**: 현재 **구현 없음**. `created_by` 필드만 String으로 존재. CLAUDE.md에 Keycloak/LDAP 언급은 있으나 코드 부재. Phase 5에서 도입 예정.
- **세션(대화)**: DB 기반 (`sessions` + `session_messages`). 프론트엔드는 `/agent/[[...sessionId]]` 다이나믹 라우트. LangGraph 도입 시 `sessions.id` = `thread_id` 규약으로 연결.
- **DB 연결**:
  ```python
  engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": False})
  async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
  async def get_db():
      async with async_session() as session:
          yield session
  ```
  테스트는 `NullPool` 사용해 "operation in progress" 회피.

### 1.8 기존 에이전트 구현 여부

| 항목 | 상태 |
|---|---|
| LangGraph | ❌ 없음 |
| LiteLLM | ❌ 없음 |
| 에이전트 구현체 | ⚠️ `src/agents/skills/`만 존재, 코드 없음 |
| Agent Chat 서비스 | ✅ `agent_svc.py` 450줄 — 직접 구현된 OpenAI Function Calling 오케스트레이션 |
| Function Calling | ✅ 8개 도구: `extract_records`, `generate_srs`, `create/update/delete_record`, `update_record_status`, `search_records` 등 |
| 도구 실행 전략 | ⚠️ 혼합 — 프론트 위임(`extract_records`, `generate_srs`) + 백엔드 직접 실행(CRUD) |
| SSE 스트리밍 | ✅ `stream_chat()` async generator → StreamingResponse |
| HITL | ❌ 없음 (`interrupt()` 없음, `resume` 엔드포인트 없음) |
| 체크포인트 | ❌ 없음 |

**현 `agent_svc.stream_chat()` 요약**:
```
1. DB에서 세션 히스토리 로드(최근 50건)
2. RAG로 관련 지식 청크 검색 (pgvector)
3. Glossary / Requirements / Records 컨텍스트 조합
4. agent_chat_prompt 시스템 프롬프트 + 히스토리 → LLM 호출
5. tool_call 루프:
   - FRONTEND_TOOLS → SSE 이벤트만 전달 (프론트가 실제 실행)
   - BACKEND_TOOLS → 직접 실행 → 결과를 LLM 히스토리에 피드백
6. 최종 메시지 → DB 저장
yield: {type: "token"} / {type: "tool_call"} / {type: "tool_result"} / {type: "done"}
```

**DESIGN §6 HITL과의 Gap**:
- `interrupt()`가 없으므로 "모호한 요청 → 되묻기 → 사용자 응답 → 재개" 플로우 불가.
- 현재는 프롬프트로 `[CLARIFY]` 블록을 강제하고 프론트가 `ClarifyQuestion.tsx`로 렌더하는 **프롬프트 기반 HITL**이다 (부분적 대체). 이는 `REFECTORING.md`가 P0로 지적한 부분과 일치.

### 1.9 테스트/로깅/에러 핸들링

- **테스트**: 10개 파일 · 93 passed · 3 skipped · NullPool + 수동 클린업
  - 주목할 검증: 교차 프로젝트 source_document 차단(test_record, test_glossary), 부분 재정렬 충돌 방지(test_section, test_requirement)
- **로깅**: Loguru + 환경별 레벨 + JSON. `middleware/logging_middleware.py`가 요청/응답/예외 자동 로깅.
- **에러 핸들링**: `AppException(status_code, detail)` → `JSONResponse`. 모든 서비스에서 통일.

### 1.10 Docker/배포

- `docker-compose.yml`: postgres(pgvector/pgvector:pg16) + minio + backend + frontend
- `Dockerfile`: 2-stage (builder: uv sync → runner: uv sync --frozen + Alembic upgrade + uvicorn)
- 환경 변수 파일: `.env.prod.example`, `.env.preview.example`, `.env` (LLM_PROVIDER=azure/openai, Azure endpoint/key 2세트, OPENAI_API_KEY, POSTGRES_*, MINIO_*)
- 보안 이슈: `ssl=False`(DB), `secure=False`(MinIO) 고정 → 운영 환경 설정 분리 필요(P1)

### 1.11 루트 문서 요약

- **CLAUDE.md (8,940B)**: Phase 1~7 전체 로드맵. Phase 1(CRUD+Assist) 완료, Phase 2~4(지식/레코드/SRS) 진행. GitHub Flow + PostToolUse hook(pytest).
- **PLAN.md (24,483B)**: Phase 1 ✅ · Phase 2 ✅ (지식/용어/섹션/준비도) · Phase 3 ✅ (Agent 레이아웃 + 레코드 추출 + 액션 카드) · Phase 4 진행 중 (SRS 생성 완료, UI 확장 중) · Phase 5~7(TC/버전/SSO) 미래.
- **PROGRESS.md (38,172B)**: 작업 로그 2026-03-25~04-18. 2026-04-18 최신: 백엔드 전수 분석 + REFECTORING.md 작성. 93 passed.
- **REFECTORING.md (12,992B)** ⭐⭐⭐ — **본 프로젝트의 직접 선행 작업**:
  - **P0**: Agent 일관성/예측가능성, 구조화 출력 폴백 부재
  - **P1**: RAG 필터, llm_model 미반영, display_id 동시성, API 부채, 보안 기본값
  - **해결안**: Harness Engineering (Intent Router + Context Loader + Tool Gateway + Orchestrator + Renderers) → **DESIGN.md의 Supervisor + LangGraph + 에이전트 레지스트리 개념과 정확히 일치**
- **AGENTS.md (8,939B)**: CLAUDE.md와 거의 중복 (프로젝트 에이전트 가이드).

### 1.12 재활용 판단 종합표 (백엔드)

| 분류 | 자산 | 등급 | 신규 시스템에서 할 일 |
|---|---|---|---|
| **모델** | models/*.py (8개) | A | 그대로. 단, `hitl_requests` / `agent_executions` / 통합 `artifacts` 테이블 신설 |
| **마이그레이션** | alembic/versions/ (16개) | A | 그대로 적용 + 신규 테이블용 마이그레이션 추가 |
| **라우터** | project/record/section/srs/glossary/knowledge/session/review | A | 그대로 |
| | agent.py | **B → 재구성** | 핸들러는 유지, 내부를 LangGraph 그래프 호출로 교체 + `/chat/{session_id}/resume` 신설 |
| | assist.py, requirement.py | B | 호환성 유지, 신규 개발 없음 |
| **서비스** | record/section/srs/llm/review/embedding/knowledge/session/glossary/storage/suggestion | A | 그대로 (llm_svc는 LiteLLM 어댑터로 재감싸기 검토) |
| | project_svc + readiness_svc | B | 병합 (P1) |
| | rag_svc | B | 문서 활성/완료 필터 추가 (P0) |
| | document_processor | B | ALLOWED_FILE_TYPES 일관성 (P1) |
| | **agent_svc** | **C** | **LangGraph 그래프로 전면 재구성**. 기존 도구 실행/세션 영속/RAG 호출 로직은 LangGraph 노드로 래핑해 **기능 보존** |
| | assist_svc | B | 레퍼런스 유지 또는 제거 |
| **프롬프트** | prompts/srs/*, review/*, glossary/*, knowledge/* | A | 그대로 |
| | prompts/agent/chat.py | B | Supervisor + 개별 에이전트별로 분할 재배치 |
| | prompts/assist/* | B | 레퍼런스 유지 |
| **유틸** | reorder, text_chunker | A | 그대로 |
| | json_parser | B | `with_structured_output` 도입 후 보조 역할 축소 |
| | db | A | 그대로 |
| **Core** | database / exceptions / cors / logging | A | 그대로 |
| **미들웨어** | logging_middleware | A | 그대로 |
| **테스트** | tests/ | A | 유지 + Supervisor/HITL/Agent 레지스트리/RAG 격리 테스트 추가 |
| **Docker/배포** | Dockerfile / docker-compose / .env.*.example | A/B | ssl/secure 운영 설정 분리 (P1) + Redis 서비스 추가 |
| **문서** | CLAUDE.md, PLAN.md, PROGRESS.md, **REFECTORING.md**, AGENTS.md | A | 참고 자료로 보존 (`.prototype-ref/` 유지) |

---

## 2. 프론트엔드 기존 자산

### 2.1 의존성 정확한 버전 (package.json 기준)

| 카테고리 | 패키지 | 버전 | FRONTEND_DESIGN.md 일치 |
|---|---|---|---|
| Framework | next | 16.1.6 | ✅ |
| | react / react-dom | 19.2.3 | ✅ |
| Language | typescript | ^5.9.3 | ✅ |
| Styling | tailwindcss / @tailwindcss/postcss | ^4 | ✅ |
| UI | radix-ui | ^1.4.3 | ✅ (shadcn 기반) |
| | shadcn | ^3.8.5 | ✅ |
| State | zustand | ^5.0.11 | ✅ |
| Data | swr | ^2.4.1 | ✅ |
| Form | react-hook-form / zod / @hookform/resolvers | ^7.72 / ^4.3 / ^5.2 | ✅ |
| Animation | motion | ^12.38.0 | ✅ |
| Icons | lucide-react | ^0.577.0 | ✅ |
| Markdown | react-markdown / remark-gfm / streamdown | ^10.1 / ^4.0 / ^2.5 | ✅ |
| Markdown ext. | @streamdown/cjk, /code, /math, /mermaid | 최신 | ✅ |
| Code highlight | shiki | ^4.0.2 | ✅ |
| Toast | sonner | ^2.0.7 | ✅ |
| Cmd palette | cmdk | ^1.1.1 | ✅ |
| Drawer | vaul | ^1.1.2 | ✅ |
| DnD | @dnd-kit/core, /sortable, /utilities | ^6.3 / ^10.0 / ^3.2 | ✅ |
| Theme | next-themes | ^0.4.6 | ✅ |
| Loader | nextjs-toploader | ^3.9.17 | ✅ |
| Utility | clsx, tailwind-merge, cva, nanoid | 최신 | ✅ |
| AI SDK | ai | ^6.0.143 | ✅ (메시지 타입 참고) |
| Dev | react-compiler, eslint 9, prettier 3.8 | | ✅ |

**신규 도입 예정 (미설치)**:
- ❌ `@microsoft/fetch-event-source` (FRONTEND_DESIGN §16.3)
- ❌ `react-diff-viewer-continued` (§20.5)
- ❌ `@xyflow/react` 또는 `reactflow` (§20.6)
- ❌ `next-intl` (§24.4, Phase 4)

### 2.2 라우팅 구조

```
src/app/
├── (auth)/
│   └── layout.tsx                          # 현재 미구현
├── (main)/
│   ├── layout.tsx                          # Main 레이아웃 + Header
│   ├── page.tsx                            # 랜딩
│   ├── dashboard/page.tsx
│   ├── projects/
│   │   ├── page.tsx                        # 프로젝트 목록
│   │   └── [id]/
│   │       ├── layout.tsx
│   │       ├── page.tsx                    # 개요 탭
│   │       └── requirements/page.tsx       # 요구사항 페이지
│   ├── agent/
│   │   ├── layout.tsx                      # 동적 패널 레이아웃
│   │   └── [[...sessionId]]/page.tsx       # 채팅 (optional catch-all)
│   └── workflow/page.tsx                   # 미구현
├── api/v1/agent/chat/route.ts              # 프록시 라우트 (미사용 — 백엔드 직접 호출)
├── layout.tsx / global-error.tsx / not-found.tsx
```

**FRONTEND_DESIGN §17 신규 라우트 대비 Gap**:

| 신규 라우트 | 프로토타입 상태 | 조치 |
|---|---|---|
| `/projects/[id]/knowledge` | ❌ `ProjectKnowledgeTab`으로 탭 제공 | 라우트 분리 |
| `/projects/[id]/glossary` | ❌ `ProjectGlossaryTab`으로 탭 제공 | 라우트 분리 |
| `/projects/[id]/sections` | ❌ `ProjectSectionsTab`으로 탭 제공 | 라우트 분리 |
| `/projects/[id]/artifacts[/srs\|design\|testcases]` | ⚠️ `ArtifactPanel`로 우측 패널 제공 (탭 기반) | 허브 라우트 추가 (기존 패널과 병행 가능) |
| `/projects/[id]/impact` | ❌ 없음 | 신규 |

### 2.3 컴포넌트 재활용 맵 (97개 파일, 주요 항목)

| 경로 | 라인 | 역할 | 등급 | 비고 |
|---|---|---|---|---|
| **Hooks (14개)** | | | | |
| hooks/useChatStream.ts | **453** | SSE + 토큰 버퍼링 | **A** | SSE 파서만 교체 대상 |
| hooks/useMutation.ts | 83 | API 변이 래퍼 | A | |
| hooks/useMediaQuery / useResize / useOverlay / useChatScroll / useIsMobile / useFocusPromptInput / useDeferredLoading / useStoreHydration / useIsMounted | - | | A | |
| hooks/useFetch.ts | - | SWR 래퍼 | B | 상태 분화 보강 가능 |
| hooks/useReview.ts | - | Review API | B | 미구현 |
| hooks/useTurnLayout.ts | - | ? | C | 사용처 확인 필요 |
| **Stores (11개, 총 681줄)** | | | | |
| stores/chat-store.ts | 142 | 메시지/스트리밍 Map<sid, Message[]> | A | |
| stores/panel-store.ts | 175 | 레이아웃 모드 + 패널 너비 | A | persist `aise-panel` |
| stores/artifact-store.ts | 31 | activeTab | A | persist `aise-artifact` |
| stores/project-store.ts | 56 | currentProject + viewMode | A | persist `aise-project` |
| stores/overlay-store.ts | 64 | alert/confirm/modal | A | |
| stores/record-store.ts | 34 | 추출 후보/상태 | A | |
| stores/readiness-store.ts | 35 | 프로젝트 준비도 | A | |
| stores/search-store.ts | 42 | recentItems (max 5) | A | persist `aise-search` |
| stores/suggestion-store.ts / toast-store.ts / ui-preference-store.ts | - | | B | 파일 내용 상세 확인 필요 |
| **lib / services (7개, 589줄)** | | | | |
| lib/api.ts | **117** | ApiError + api.get/post/put/patch/delete + skipErrorHandling + 401→/login | **A** | |
| services/agent-service.ts | 128 | streamAgentChat(request, callbacks) — SSEEvent 파싱 | **A** | interrupt/plan_update/artifact_created 이벤트 추가 + SSE 파서 교체 타겟 |
| services/record-service.ts | 132 | streamExtractRecords(projectId, handlers) | A | |
| services/session / project / requirement / glossary-service.ts | 31~51 | 각 도메인 CRUD | A | |
| **UI (shadcn + ai-elements)** | - | Dialog/Dropdown/Popover/Tabs/Collapsible/... | A | 기본 |
| **Layout (13개)** | | | | |
| layout/Header + HeaderTabs + HeaderActions + LeftSidebar + RightPanel + ResizeHandle + PanelToggleBar + NotificationPanel + ReadinessMiniView + MobileBottomDrawer + MobileRightDrawer + MobileMenu + Footer | - | | A | NotificationPanel·Footer는 B/C |
| **Chat (14개, 2,506줄)** | | | | |
| chat/MessageRenderer.tsx | **461** | 메시지 렌더 + `[CLARIFY]`/`[REQUIREMENTS]`/`[SUGGESTIONS]`/`[SOURCES]` 블록 파싱 | **A (확장)** | 신규 블록 추가 가능 |
| chat/ChatArea.tsx | 216 | 스크롤 + 메시지 렌더 | A | |
| chat/ChatInput.tsx | 319 | 입력창 | A (확장) | interrupt 대기 상태 표시 추가 |
| chat/ClarifyQuestion.tsx | 111 | **현 HITL UI** (옵션/자유입력) | **B (개조)** | HitlData 통합, multi-step, cancel |
| chat/ExtractedRequirements.tsx | 107 | 추출 요구사항 카드 | A | |
| chat/Questionnaire.tsx | 313 | 다중 질문 | B | 타입 통합 |
| chat/PromptSuggestions.tsx | 252 | 제안 칩 | A | |
| chat/SourceReference.tsx | 68 | 출처 링크 | A | |
| chat/SourceViewerPanel.tsx | 172 | 출처 뷰어 | A (확장) | |
| chat/SuggestionChips.tsx | 53 | | A | |
| chat/SessionList.tsx / SessionItem.tsx | 129 / 98 | 세션 목록 | A (확장) | §19.8 에이전트/턴수/산출물 배지 |
| chat/ActionCards.tsx | 133 | 빠른 작업 카드 | A | |
| chat/GenerateSrsProposal.tsx | 74 | stub | C | |
| **Artifacts (6개)** | | | | |
| artifacts/ArtifactPanel.tsx | - | 탭 컨테이너 | A | |
| artifacts/**RecordsArtifact.tsx** | **473** | 레코드 편집 UI (**SRS/TC Editor 템플릿 레퍼런스**) | **A (확장)** | 섹션 필터 + 상태 필터 + 이중 모드(초기/추출) 패턴 |
| artifacts/SrsArtifact.tsx / DesignArtifact.tsx / TestCaseArtifact.tsx | - | **stub** | **C** | §20.4~20.6 신규 작성 |
| artifacts/RequirementsArtifact.tsx | - | 요구사항 문서 | B | 에디터 기능 추가 |
| **Projects (15개)** | | | | |
| projects/ProjectCard, ProjectListItem, ProjectOverviewTab, ProjectReadinessCard, ProjectListSkeleton, ProjectSelector | - | | A | |
| projects/ProjectCreateForm | - | 모듈 선택 포함 | A (확장) | |
| projects/ProjectKnowledgeTab / GlossaryTab / SectionsTab | - | 탭 방식 | A (확장) | 라우트 분리 시 이전 |
| projects/GlossaryTable, GlossaryAddForm, GlossaryGeneratePanel, KnowledgePreviewModal | - | | A | |
| projects/ModuleGraph.tsx | - | stub | C | reactflow 도입 후 |
| **Requirements (9개)** | | | | |
| RequirementTable / RequirementItem / RequirementInput / ExtractedRequirementList / ExtractedRequirementCard / ChatPanel / SuggestionPanel | - | | A | |
| RefineCompare.tsx | - | | A (확장) | react-diff-viewer 도입 후 |
| ReviewModal.tsx | - | | B | Review API 연동 미완 |
| **Overlay (12개)** | | | | |
| overlay/Modal, AlertDialog, ConfirmDialog, AppsDropdown, ProfileDropdown, SearchDialog, SettingsDialog, SettingsGeneral, SettingsAccount, AnimatedGridMenu | - | | A | |
| overlay/AlertDialogCustom, LabsDialog | - | | B | 사용 적음 |
| **Shared (6개)** | Logo / EmptyState / AgentCard / ListSkeleton / ThemeToggle | - | A | |
| **Landing (3개)** | HeroSection / AgentShowcase / OrchestrationShowcase | - | A | |

**집계**: 97개 중 A(그대로) 72 · A(확장) 12 · B(개조) 5 · C(신규) 8.

### 2.4 `useChatStream` 상세 분석 (보존 최우선 자산)

**현재 구현 방식**:
- 수동 `fetch` + `response.body.getReader()` + `TextDecoder` + 개행 기준 이벤트 파싱
- 불완전 JSON 행은 다음 chunk와 결합해 버퍼링 (`pendingRef`)
- 세션별 토큰 버퍼(`tokenBufferRef: Map<sid, string>`) + 드레인 타이머(`tokenDrainTimerRef`)
- 모바일: 타이머 18ms / 청크 28자, 데스크탑: 10ms / 120자 → 리플로우 최소화
- 렌더 중 setState 금지 (cascading render 회피)

**콜백 시그니처**:
```ts
{
  onToken: (token: string) => void;
  onToolCall: (tc: { name: string; arguments: Record<string, unknown> }) => void;
  onToolResult?: (tr: { name: string; arguments: Record<string, unknown>; result: Record<string, unknown> }) => void;
  onDone: () => void;
  onError: (error: string) => void;
}
```

**SSE 라이브러리 교체 시 변경 경계**:
- ✅ **교체 대상**: `services/agent-service.ts`의 `streamAgentChat` 내부 (fetch + TextDecoder 파싱) → `@microsoft/fetch-event-source`의 `fetchEventSource()` 호출로
- ❌ **보존 대상**: `useChatStream` 훅의 토큰 버퍼링·드레인 타이머·모바일 분기·콜백 인터페이스

**신규 이벤트 추가 시 작업 위치**:
| 신규 이벤트 | 추가 위치 |
|---|---|
| `interrupt` | `agent-service.ts:SSEEvent`에 추가 → `useChatStream`에 `onInterrupt` 콜백 → `chat-store` + `hitl-store` 연동 |
| `plan_update` | 동일 구조 + `plan-store` 또는 `chat-store.messages[].plan` 갱신 |
| `artifact_created` | 동일 구조 + `artifact-store` 갱신 + 토스트 |

### 2.5 SSE 이벤트 현재 스키마

**현 Agent Chat SSE** (`services/agent-service.ts`):
```ts
export interface SSEEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'done' | 'error';
  content?: string;        // token, error
  name?: string;           // tool_call, tool_result
  arguments?: Record<string, unknown>;  // tool_call, tool_result
  result?: Record<string, unknown>;     // tool_result
}
```

**현 Record Extract SSE** (`services/record-service.ts`):
```ts
export interface ExtractStreamEvent {
  type: 'progress' | 'done' | 'error';
  stage?: string;
  message?: string;
  candidates?: RecordExtractedItem[];  // done 시
  status?: number;
}
```

**DESIGN §6 + FRONTEND_DESIGN §22.4 신규 이벤트와의 Gap**:
| 이벤트 | 현재 | 필요 조치 |
|---|---|---|
| `interrupt` (HITL) | ❌ `[CLARIFY]` 마크다운 블록으로 대체 | LangGraph `interrupt()` 페이로드 전달 |
| `plan_update` | ❌ 없음 | Supervisor plan step별 상태 |
| `artifact_created` | ⚠️ `tool_result`에 `{artifact_id}` 포함 가능 | 명시 이벤트 분리 |

**진실 원천**: 현재는 백엔드 `agent_svc.py` 출력 형식 = 프론트 수동 타입. LangGraph 이관 시 **백엔드 이벤트 카탈로그 문서화 → 프론트 `types/agent-events.ts`에 동기화**가 필수.

### 2.6 Zustand 스토어 카탈로그 (11개)

| 스토어 | 라인 | 핵심 상태 | persist | 비고 |
|---|---|---|---|---|
| chat-store | 142 | `sessionMessages: Map<sid, ChatMessage[]>`, `streamingSessionIds: Set` | ❌ | `addMessage`/`appendToLastAssistant`/`updateLastAssistantMessage`/`finishStreaming` |
| panel-store | 175 | `leftSidebarOpen`, `rightPanelOpen`, `rightPanelWidth`, `layoutMode` (WIDE/SPLIT/CLOSED), `isMobile` | ✅ `aise-panel` | `setRightPanelPreset(LayoutMode)` |
| artifact-store | 31 | `activeTab: records\|srs\|design\|testcase` | ✅ `aise-artifact` | |
| project-store | 56 | `projects`, `currentProject`, `viewMode` | ✅ `aise-project` | |
| overlay-store | 64 | alert/confirm/modal options | ❌ | |
| record-store | 34 | `extracting`, `candidates`, `extractError`, `refreshNonce` | ❌ | |
| readiness-store | 35 | 준비도 데이터 | ❌ | |
| search-store | 42 | `recentItems` (max 5) | ✅ `aise-search` | |
| suggestion-store | - | - | ? | 상세 확인 필요 |
| toast-store | - | - | ? | sonner 도입으로 축소 가능 |
| ui-preference-store | - | - | ? | 테마/폰트 크기 |

**신규 필요** (FRONTEND_DESIGN §22.2): `hitl-store`(interrupt 큐·응답 이력), `version-store`(산출물 버전 캐시), `impact-store`, `i18n-store`.

### 2.7 참고할 UI 패턴

1. **RecordsArtifact 패턴**: Header(필터/액션) + ScrollArea(섹션 그룹핑 + 레코드 항목 + hover 액션) + 이중 모드(초기/추출 대기/완료/에러). → **SRS/TC Editor의 레퍼런스**.
2. **ClarifyQuestion 패턴**: 단일 질문 + 옵션 배열 + 자유 입력 + Submit. `answered` 플래그로 재선택 차단. → HITL 3종(Clarify/Confirm/Decision)의 기반, 멀티 스텝 확장 필요.
3. **탭 ↔ 레이아웃 연동**: `setActiveTab()` + `setRightPanelPreset(SPLIT)` 동시 호출. → 라우트 분리 후에도 동일 패턴 유지.
4. **MessageRenderer 블록 파싱**: 정규식으로 `[CLARIFY]`/`[REQUIREMENTS]`/`[SUGGESTIONS]`/`[SOURCES]` 추출 → 각 컴포넌트로 라우팅 + cleanContent 렌더. → 신규 블록 타입 추가 시 동일 패턴.
5. **프로젝트 모듈 선택**: `ProjectCreate.modules = ['requirements'|'design'|'testcase'][]` 프리셋 + 커스텀 조합.

### 2.8 타입 정의 현황

**현재 `types/project.ts`(~250줄) + `types/index.ts`**:
- Project / ProjectCreate / ProjectUpdate / ProjectReadiness
- Requirement / RequirementType / RefineRequest/Response
- Section / SectionCreate/Update
- GlossaryItem / GlossaryExtractedItem / GlossaryCreate/Update
- Record / RecordExtractedItem / RecordStatus / RecordCreate/Update
- ChatMessage / ExtractedRequirement
- ReviewRequest / ReviewResponse

**FRONTEND_DESIGN.md 신규 타입과 Gap**:
| 신규 타입 | 현재 | 조치 |
|---|---|---|
| `ToolCallData` | ✅ chat-store에 부분 정의 | 확장 (state: running/completed/error + 실행시간) |
| `HitlData` | ⚠️ toolData로 부분 | 전용 정의 |
| `ClarifyData` | ⚠️ `[CLARIFY]` 블록 파싱 | 전용 interface |
| `ConfirmData` | ❌ | 신규 (§20.2b) |
| `DecisionData` | ❌ | 신규 (§20.2c) |
| `PlanStep` | ❌ | 신규 (§20.3) |
| `ArtifactData` / 버전 / 영향도 | ❌ | 신규 |

→ **신규 파일 `types/agent-events.ts`에 모두 집약**, 백엔드와 공유(OpenAPI 또는 수작업 동기화).

### 2.9 lib/api.ts 래퍼 시그니처

```ts
class ApiError extends Error {
  code: string;    // 'UNKNOWN_ERROR' | 'API_ERROR' | 'NOT_FOUND' ...
  status: number;
  detail?: string | null;
  constructor(status, error);
}

const api = {
  get:    <T>(path, options?) => Promise<T>;
  post:   <T>(path, body?, options?) => Promise<T>;
  put:    <T>(path, body?, options?) => Promise<T>;
  patch:  <T>(path, body?, options?) => Promise<T>;
  delete: <T>(path, options?) => Promise<T>;
};

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  skipErrorHandling?: boolean;
}
```

**에러 흐름**: `!response.ok` → response.json() → `ApiError` → 글로벌 핸들러(401→/login, ≥500→'서버 오류' 토스트, ≥400→메시지 토스트) → `throw`. `skipErrorHandling: true`면 호출자 위임.

### 2.10 재활용 판단 종합표 (프론트엔드)

| 분류 | 개수 | 대표 | 조치 |
|---|---|---|---|
| **그대로 유지 (A)** | 72 | 훅 대부분, 스토어 8개, lib/api, services/* (session/project/record/requirement/glossary), 대부분의 chat/projects/overlay/shared/landing 컴포넌트, shadcn UI | 문서화만 갱신 |
| **확장 (A 확장)** | 12 | useChatStream(신규 이벤트), ChatInput, MessageRenderer, RecordsArtifact(→SRS/TC 템플릿), SourceViewerPanel, ProjectKnowledge/Glossary/Sections Tab(라우트 분리), RefineCompare, ClarifyQuestion(멀티스텝) | 기존 패턴 유지 + 기능 추가 |
| **개조 (B)** | 5 | ClarifyQuestion(HitlData 통합), Questionnaire, RequirementTable, RefineCompare(diff), SourceViewerPanel(diff) | 타입/로직 교체 |
| **신규 (C)** | 8+ | AgentInvocationCard, PlanProgress, HITL 3종(Clarify/Confirm/Decision + useHitlResume), SrsArtifact, DesignArtifact, TestCaseArtifact, GenerateSrsProposal, VersionHistory+DiffViewer, ImpactGraph+ImpactList, 새 라우트들 (/knowledge, /glossary, /sections, /impact) | §20 설계대로 |

---

## 3. 교차 분석 — 백엔드 ↔ 프론트엔드 동기화 포인트

| # | 포인트 | 현재 상태 | 확정 필요 시점 |
|---|---|---|---|
| **S1** | SSE 이벤트 스키마 | 백엔드 `agent_svc` 형식 = 프론트 수동 타입 (token/tool_call/tool_result/done/error) | **Phase 1 초반** — `types/agent-events.ts` 단일 소스 지정 |
| **S2** | 신규 이벤트 (interrupt/plan_update/artifact_created) | ❌ 양쪽 모두 없음 | **Phase 2 초반** |
| **S3** | `/chat/{session_id}/resume` API | ❌ 없음 (HITL 미구현) | **Phase 3 초반** |
| **S4** | LangGraph thread_id ↔ `sessions.id` 일치 규약 | 현재 `sessions.id`만 존재 | **Phase 1 중반** (LangGraph 도입 시) |
| **S5** | artifact 버전/Diff/Restore API + UI | ❌ 양쪽 없음 | **Phase 4** |
| **S6** | 영향도 API + Impact Graph/List | ❌ 양쪽 없음 | **Phase 4** |
| **S7** | 에이전트 메타 API (`GET /agents`) | ❌ 없음 | **Phase 2 중반** (레지스트리 구축 이후) |
| **S8** | `project_id` 필터 필수화 | ⚠️ rag_svc에 누락 (P0) | **Phase 1 초반** 테스트 강제 |

---

## 4. 핵심 위험 요소 (ANALYSIS 시점에서 식별)

| # | 위험 | 근거 | 영향 |
|---|---|---|---|
| **R1** | **LangGraph 이관 시 기존 `agent_svc`의 tool 루프/세션 영속/RAG 호출 동작 변화** | 기존 구현이 정밀한 상태 관리를 하고 있음 (50-turn 히스토리, FRONTEND_TOOLS/BACKEND_TOOLS 분리) | 회귀 위험 高 → 기존 테스트 보강 + LangGraph 노드로 래핑한 뒤 동일 출력 보장 |
| **R2** | **REFECTORING.md의 Harness 개념 ↔ DESIGN.md의 LangGraph 구조 간 용어·경계 혼선** | Intent Router / Context Loader / Tool Gateway / Orchestrator / Renderers 가 DESIGN의 Supervisor / state / 에이전트 레지스트리 / LangGraph 그래프 / 프론트 렌더러에 대응되지만 1:1은 아님 | 용어 매핑 문서 작성 필수 (MIGRATION_PLAN §5) |
| **R3** | **SSE 이벤트 스키마가 백엔드·프론트 양쪽 수동 정의** | OpenAPI 자동화 없음 | 스키마 불일치 → 런타임 에러. 단일 소스(`types/agent-events.ts`) + 백엔드 Pydantic 모델 동기화 규칙 |
| **R4** | **`ClarifyQuestion.tsx`의 프롬프트 기반 HITL을 `interrupt()` 기반으로 전환하는 과정에서 UX 단절** | 현재는 `[CLARIFY]` 블록이 메시지 안에 인라인, 전환 후엔 별도 이벤트 | 이행기에는 양쪽 병존 허용 (프론트가 두 방식 모두 렌더) |
| **R5** | **pgvector 필터 누락 보안 사고 (`rag_svc`)** | REFECTORING.md P0로 식별됨 | **Phase 1에서 즉시 수정 + 교차 프로젝트 검색 테스트 강제** |
| **R6** | **프론트 신규 라우트 분리 시 기존 탭 상태 보존** | `artifact-store.activeTab` persist | 라우트 ↔ 스토어 양방향 동기화 훅 필요 |
| **R7** | **`useChatStream`의 토큰 버퍼링이 `@microsoft/fetch-event-source`와 간섭 가능성** | 버퍼링 주기(18/10ms)가 라이브러리 자체 버퍼링과 겹침 | 교체 시 A/B 테스트 + 모바일 회귀 검증 |

---

## 5. ANALYSIS 결론

1. **이 프로젝트는 "신규 구축"이 아니라 "이관 + 아키텍처 리팩토링 + 기능 확장"이다.** 프로토타입의 ~80% 자산을 보존하고, 오케스트레이션 레이어와 신규 기능(HITL·Impact·Version)만 새로 작성한다.
2. **REFECTORING.md의 미완 로드맵이 본 프로젝트의 직접 선행 작업이다.** DESIGN.md는 그 로드맵을 LangGraph 구조로 완성하는 것과 등가이다.
3. **재활용 기준**: A등급 자산은 파일 단위로 옮겨오고, B등급은 내부만 교체, C등급만 §20 설계대로 신규.
4. **다음 액션**: `MIGRATION_PLAN.md` 작성 — 재사용 전략 확정 + Phase별 백엔드/프론트엔드 병렬 작업 분해 + 위험 사전 조치 + 의존성 그래프.

---

**작성일**: 2026-04-21
**다음 문서**: `MIGRATION_PLAN.md`
