# AISE 2.0 Backend 전수 리뷰 (v2)

- **작성일**: 2026-04-20 (v2 reviewed)
- **대상 브랜치**: `claude/streaming-render-refactor-EsTgN` (HEAD `a197af6`)
- **작성자**: AI-assisted review (Claude Opus 4.7)
- **v2 변경점**: 외부 피드백 통합 — (1) RAG 필터/동시성/GET 부작용 등 **기능 정합성 버그 6건** 추가, (2) **보안 긴급 사안**(.env 실키·TLS 비활성) 별도 섹션화, (3) **Agent Harness + Tool Gateway + Eval Harness** 진화안 통합
- **관련 플랜**: `~/.claude/plans/shimmering-wiggling-flame.md` (v1 approved 2026-04-20)
- **문서 성격**: Living document. 갱신 시 날짜 suffix로 새 파일 생성
- **읽는 법**:
  - 프로젝트 소유자 → §1 Executive Summary → §8 보안 긴급 → §3.4 버그 → §10 로드맵 → §D ADR
  - 후속 작업자 → §4.0 버그 수정 → §4 파일 분리 → §6 횡단 → §10 체크리스트
  - LLM 파이프라인 엔지니어 → §5 에이전트 → §9 Harness 진화 → §11 부록 G (Eval 시나리오)

---

## 0. 문서 개요

본 문서는 `aise-v2/backend/` 전수 진단과 6~15주 리팩토링 로드맵의 단일 진실 공급원(SSOT)이다. v2는 초판(v1) 작성 직후 수렴된 외부 피드백을 반영하여 **기능 정합성 버그**와 **보안 긴급 사안**을 별도 트랙으로 분리했다.

### 0.1 조사 범위

| 영역 | 통계 | 비고 |
|---|---|---|
| Services | 20 파일 | `services/` 최상위 (서브디렉토리 없음) |
| Routers | 13 파일 | `routers/` + `routers/dev/` |
| Models | 9 파일 | SQLAlchemy 비동기 ORM |
| Schemas | 14 (API) + N (LLM) | `schemas/api/`, `schemas/llm/` |
| Prompts | 9 파일 (698 LOC) | 6개 도메인 디렉토리 |
| Utilities | 4 파일 | `utils/{db,json_parser,reorder,text_chunker}.py` |
| Agents | 빈 디렉토리 | `agents/__init__.py` + `agents/skills/__init__.py` 뿐 |
| Integrations | Jira / Polarion | stub 수준 (미구현) |
| Tests | 10 모듈 (2,146 LOC) | 전체 커버리지 추정 ~59%, `test_agent.py` 13줄 |
| Alembic | 17 migrations | squash 없이 누적 |
| pyproject | 17 의존성 + 4 dev | Python 3.14 / UV 관리 |

### 0.2 조사 방법 및 근거

- **정량 데이터**: `wc -l`, `grep -rn`, `find` 실측 (2026-04-20)
- **구조 분석**: 파일 헤더 직접 열람, import 그래프 실측
- **외부 피드백 검증**: 사용자가 지적한 6건 버그 주장을 모두 코드로 재검증 후 반영

### 0.3 제외 범위

Frontend, `docker-compose.yml`, `start-dev.sh`, `legacy/aise1.0/`, Keycloak/LDAP 엔드포인트(미구현), UI/UX.

---

## 1. Executive Summary

**한 줄 요약**: 골격은 건강하다. 하지만 **보안 긴급 사안 2건**과 **기능 정합성 버그 6건**을 먼저 고쳐야 리팩토링을 시작할 수 있다.

### 1.1 Top-8 Risk

| # | 리스크 | 근거 | 영향 | 등급 |
|---|---|---|---|---|
| R1 | **.env에 실키 API 키 노출 + TLS 비활성** | `backend/.env` 실재(698B), `core/database.py:16 ssl:False`, `storage_svc.py:26 secure=False` | 키 유출 시 LLM 비용 폭주 / MITM 가능 | **🔴 보안 긴급** |
| R2 | **Schema-level 출력 강제 없음** | 12 에이전트가 prompt-level 규칙 + `parse_llm_json` 엄격 파싱. 툴 인자 파싱 실패 시 `{}` silent fallback (`agent_svc.py:317-319`) | LLM 모델 교체 시 502 또는 잘못된 도구 실행 | **🔴 에이전트 정합성** |
| R3 | **프런트/백엔드 툴 혼재 + `delegated_to_frontend` 거짓 신호** | `agent_svc.py:386`에서 프런트 위임 툴에 더미 성공 응답을 LLM에 반환 | LLM이 실행되지 않은 작업을 완료로 인식 → 후속 플랜 오류 | **🔴 에이전트 정합성** |
| R4 | **에이전트 아키텍처 부재** | `agents/` 빈 디렉토리. 12 에이전트가 `services/*_svc.py`에 흩어짐. 프롬프트에만 규칙 집약 | 모델 교체·신규 에이전트 추가 비용 큼 | **P0** |
| R5 | **기능 정합성 버그 6건** | RAG is_active 미필터링 / ProjectSettings.llm_model 미연결 / display_id 동시성 / GET side effect 등 | 사용자 혼란·비활성 데이터 노출·트랜잭션 충돌 | **P0~P1** |
| R6 | **단일 함수 초거대화** | `stream_chat` 240 LOC / `review_requirements` 230 LOC / `build_agent_chat_prompt` 221 LOC | 단위 테스트 불가, 회귀 위험 | **P0** |
| R7 | **설정/예외/DI 미성숙** | pydantic-settings 미도입, AppException 단일 클래스, 모듈 전역 싱글톤 | 배포 환경별 검증 불가, 오류 분류 불가 | **P0** |
| R8 | **핵심 영역 테스트 공백** | agent_svc 13%, llm_svc 23%, knowledge_svc 24%, rag_svc 25%, srs_svc 21%, document_processor 14% | 리팩토링 안전망 부재 | **P0 (안전망)** |

### 1.2 Top-5 Opportunity

| # | 기회 | 근거 |
|---|---|---|
| O1 | `deepagents>=0.4.12` 이미 `pyproject` 선언 (실제 import 0건) | 의존성 PoC 불필요, 도입 시점만 결정 |
| O2 | `.claude/skills/` 11개 skill 자산 | Skills 도입 패턴 내재화, 학습 곡선 낮음 |
| O3 | `references/` 4개 선행 리서치 | Deep Agents/Azure Responses API/AISE1 분석 완료 |
| O4 | 테스트 2,146 LOC | 커버리지는 얕지만(59%) 요구사항/리뷰/어시스트는 두꺼움 (437/412/319 LOC) — 분리 시 일부 안전망 |
| O5 | Router → Service → Model 계층이 얇음 | 큰 아키텍처 변경 없이 **내부 분리**만으로 60~70% 개선 |

### 1.3 로드맵 한 줄

```
Week 0      : 🔴 보안 핫픽스 (.env 로테이션 + Settings 도입 준비)
Week 1──2   : P0-A 버그 수정 6건 + 인프라(Config/예외/DI)
Week 2──3   : P0-B 에이전트 씨앗(assist/prompts/tools registry)
Week 3──7   : P1 핫스팟 분리 + Structured Output + LLM mock + 핵심 테스트 보강
Week 8──15  : P2 Harness 재구성 + Skills + MCP + Deep Agents + Eval Harness
```

상세 체크리스트는 §10.

---

## 2. 현재 아키텍처 스냅샷

### 2.1 레이어 다이어그램 (실제 import 그래프)

```
┌──────────────────────────────────────────────┐
│ routers/                     (1,094 LOC)      │
│  project·requirement·assist·review·session…  │
└──────────────┬───────────────────────────────┘
               │ FastAPI Depends(get_db)
               ▼
┌──────────────────────────────────────────────┐
│ services/                    (~5,000 LOC)    │
│                                              │
│   ┌──────── llm_svc (허브) ─────────┐        │
│   │                                 │        │
│   ├─ agent_svc ─┬─> record_svc ──┐  │        │
│   │             └─> rag_svc ───┐ │  │        │
│   ├─ assist_svc ────────────────┤ │  │        │
│   ├─ review_svc ────────────────┤ │  │        │
│   ├─ srs_svc / record_svc / ...─┘ │  │        │
│   │                                 │        │
│   └─────────────────────────────────┘        │
│                                              │
│   knowledge_svc ─> document_processor        │
└──────────────┬───────────────────────────────┘
               ▼
┌──────────────────────────────────────────────┐
│ models/ (364 LOC)     integrations/ (stub)   │
│ schemas/ (1,087 LOC)  utils/ (~700 LOC)      │
└──────────────────────────────────────────────┘
```

### 2.2 Service-to-Service Import Matrix (실측)

```
agent_svc      -> llm_svc, rag_svc
assist_svc     -> llm_svc
embedding_svc  -> llm_svc
glossary_svc   -> llm_svc
knowledge_svc  -> document_processor
rag_svc        -> llm_svc
record_svc     -> llm_svc
review_svc     -> llm_svc
section_svc    -> llm_svc
srs_svc        -> llm_svc
suggestion_svc -> llm_svc
```

**관찰**: `llm_svc`는 10개 서비스의 허브. Settings DI·Structured Output·LLMParseError를 이 허브에 도입하면 하위 10개 서비스가 자연 혜택을 받는다 → P0 1순위.

**관찰**: 서비스 간 **간접 결합**은 적다. Router 레벨에서 조합이 대부분 → **분리 비용이 낮다**.

### 2.3 런타임 스택

| 계층 | 기술 | 버전 | 비고 |
|---|---|---|---|
| Runtime | Python | 3.14 | **너무 높음** — 3.12로 완화 권장 |
| Package mgr | UV | - | `uv.lock` 커밋됨 |
| Web | FastAPI[standard] | ≥0.135.2 | `uvicorn` 표준 포함 |
| ORM | SQLAlchemy | ≥2.0 (async) | `asyncpg` 드라이버 |
| DB | PostgreSQL + pgvector | 16 / 0.4+ | dev Docker, **TLS 비활성** |
| Obj storage | MinIO | 7.2+ | S3 호환, **TLS 비활성** |
| LLM | Azure OpenAI (+ OpenAI fallback) | openai 2.30+ | `api_version="2025-03-01-preview"` 하드코딩 |
| Logging | loguru | 0.7.3+ | JSON 포맷 병행 |
| Tokenizer | tiktoken | 0.9+ | 전역 singleton encoding |
| Doc parser | pymupdf / python-docx / python-pptx / openpyxl | 최신 | `document_processor.py` |
| **Agent fw** | **deepagents** | **≥0.4.12 (미사용)** | **pyproject 선언만, 실제 import 0건** |

### 2.4 현재 "에이전트" 위치 지도

```
agents/                  ← 빈 디렉토리 (__init__.py만)
services/agent_svc.py    ← Agent Chat (630 LOC)
services/assist_svc.py   ← Refine/Suggest/Chat (167 LOC, 3 에이전트)
services/review_svc.py   ← Review Requirements (333 LOC)
services/srs_svc.py      ← SRS Generate (219 LOC)
services/glossary_svc.py ← Extract + Generate (291 LOC, 2 에이전트)
services/record_svc.py   ← Record Extract (605 LOC, CRUD 혼재)
services/suggestion_svc.py ← Prompt Suggestions (238 LOC)
services/section_svc.py  ← Section AI bootstrap (303 LOC)
services/rag_svc.py      ← RAG Chat (139 LOC)
prompts/                 ← 9 파일 698 LOC (§5에서 상술)
```

**결론**: "에이전트"는 있지만 **이름이 없고 장소가 없다**. §4·§9의 핵심은 이 재분류·재배치.

---

## 3. 복잡도 전수 진단

### 3.1 핫스팟 랭킹 (라인 수 내림차순)

| Rank | 파일 | LOC | 함수/클래스 | 평균 LOC/함수 | 책임 | LLM | DB | I/O | 테스트 | 등급 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | services/agent_svc.py | 630 | 7 | ~90 | 5 | ★★★ | ★★ | ★ (SSE) | **13 LOC (13%)** | **P0** |
| 2 | services/record_svc.py | 605 | 23 | ~26 | 5 | ★★ | ★★★ | - | 195 | **P1** |
| 3 | utils/text_chunker.py | 446 | 11 | ~40 | 3 | - | - | - | 167 | **P1** |
| 4 | services/knowledge_svc.py | 346 | 12 | ~29 | 5 | - | ★★ | ★★★ (MinIO) | 0 (**24%**) | **P1** |
| 5 | services/requirement_svc.py | 341 | 12 | ~28 | 6 | - | ★★★ | - | 437 | **P1** |
| 6 | services/review_svc.py | 333 | 3 | **~111** | 5 | ★★★ | ★★ | - | 412 | **P1** |
| 7 | services/section_svc.py | 303 | 10 | ~30 | 4 | ★★ | ★★ | - | 113 | **P2** |
| 8 | services/glossary_svc.py | 291 | 9 | ~32 | 5 | ★★★ | ★★ | - | 179 | **P2** |
| 9 | services/suggestion_svc.py | 238 | 7 | ~34 | 3 | ★★★ | ★ | - | 0 | **P2** |
| 10 | prompts/agent/chat.py | 221 | **1** | **221** | 5 | - | - | - | - | **P0** |
| 11 | services/srs_svc.py | 219 | 5 | ~44 | 4 | ★★★ | ★★ | - | 0 (**21%**) | **P2** |
| 12 | services/project_svc.py | 209 | 12 | ~17 | 3 | - | ★★★ | - | 170 | **P2**(N+1) |
| 13 | services/assist_svc.py | 167 | 3 | **~56** | 3 | ★★★ | ★ | - | 319 | **P0** |

### 3.2 단일 함수 ≥ 100 LOC 랭킹

| Rank | 함수 | 파일 | 대략 LOC | 책임 과다 징후 |
|---|---|---|---|---|
| 1 | `stream_chat` | agent_svc.py (L188) | ~240 | LLM 루프 + tool chunk 누적 + 백엔드 도구 dispatch + SSE 포맷 + **frontend delegation** |
| 2 | `review_requirements` | review_svc.py (L72) | ~230 | 조회 분기 + 프롬프트 빌드 + LLM + 파싱 + delete+insert + 응답 조립 |
| 3 | `build_agent_chat_prompt` | prompts/agent/chat.py (L4) | ~217 | 4 섹션 + 규칙 + 도구 가이드 |
| 4 | `_execute_backend_tool` | agent_svc.py (L443) | ~100 | 5종 도구 dispatch + 개별 구현 |
| 5 | `extract_records` | record_svc.py (L299) | ~120 | 프롬프트 + LLM + 파싱 + DB 저장 |
| 6 | `upload_document` | knowledge_svc.py (L101) | ~70 | MinIO + DB + BackgroundTasks |

### 3.3 중복 패턴 매트릭스

| 패턴 | 반복 위치 | 추출 후보 |
|---|---|---|
| `_to_response(model)` 매퍼 | 8+ 서비스 | 서비스별 `mapper.py` (P1), 공통화는 보류 |
| `_next_display_id(type)` / `_next_order_index()` | `requirement_svc`, `record_svc`, `glossary_svc` | `services/_common/display_id.py` (P2) — **동시성 안전**(§4.0 Bug-3) |
| `_load_documents_by_ids(ids)` | `knowledge_svc`, `record_svc`, `glossary_svc` | `services/_common/loaders.py` (P2) |
| `parse_llm_json(raw) → AppException(502)` | 모든 LLM 에이전트 | `agents/shared/json_agent.py` + `LLMParseError` (P0) |
| `chat_completion(messages, temperature=X)` 호출 | 12+ 위치 | `agents/shared/agent_config.py` + `AgentConfig` dataclass (P0) |

### 3.4 기능 정합성 버그 (신설, v2)

복잡도 차원 외에 **실행 결과가 잘못되거나 안전하지 않은** 지점을 별도 트랙으로 추적한다. 파일 분리보다 **먼저** 고쳐야 한다.

| Bug# | 위치 | 현상 | 영향 | 등급 |
|---|---|---|---|---|
| **B-1** | `rag_svc.search_similar_chunks()` | `KnowledgeDocument.is_active`/`status` 필터 부재 — grep 0건 | **비활성화된 문서의 청크가 RAG 답변 근거로 재등장** | 🔴 P0 |
| **B-2** | `llm_svc.*`·`agent_svc.*` | `ProjectSettings.llm_model` 실사용 0건 (`project_svc`만 CRUD) | 사용자가 모델을 바꿔도 반영 안 됨 | 🟠 P0 |
| **B-3** | `requirement_svc._next_display_id`, `record_svc._next_display_id` | `max(id)+1` 방식, 동시 요청 시 경쟁 | requirement는 unique constraint로 실패 / record는 중복 저장 가능 | 🟠 P1 |
| **B-4** | `section_svc.get_sections` (L79→L84) | `await _ensure_default_sections(db, project_id)` 내부에서 INSERT + commit | **GET에서 write 부작용 (REST 위반, 동시 GET 시 경쟁)** | 🟠 P1 |
| **B-5** | `agent_svc.stream_chat` (L317-319) | `json.loads(args)` 실패 시 `args = {}` silent fallback | LLM이 의도한 도구를 **빈 인자로 실행** — 엉뚱한 결과 | 🔴 P0 |
| **B-6** | `agent_svc.stream_chat` (L386) | 프런트 위임 툴에 `{"status": "delegated_to_frontend"}`를 더미 응답으로 LLM에 반환 | LLM이 실행되지 않은 작업을 완료로 인식 → 후속 플랜 오류 | 🟠 P0 |

각 버그의 수정안은 §4.0에서 상세.

---

## 4. 핫스팟 파일별 상세 리팩토링 제안

본 섹션은 **§4.0(버그 수정)** → **§4.1~§4.8(파일 분리)** → **§4.9(P2 요약)** 순으로 진행한다.

---

### 4.0 먼저 고칠 버그 6건 (P0 버그 트랙)

#### Bug-1: RAG가 비활성 문서를 답변 근거에 포함

- **증상**: 사용자가 지식 문서를 `is_active=False` 또는 처리 실패 상태로 놓아도 `rag_svc.search_similar_chunks()`가 해당 청크를 여전히 반환
- **근거**: `grep -n "is_active\|status" src/services/rag_svc.py` → 0건
- **수정**:
  ```python
  # services/rag_svc.py (의사코드)
  stmt = (
      select(KnowledgeChunk, KnowledgeDocument)
      .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
      .where(
          KnowledgeDocument.project_id == project_id,
          KnowledgeDocument.is_active == True,
          KnowledgeDocument.status == "processed",   # 인덱싱 완료된 것만
      )
      .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
      .limit(k)
  )
  ```
- **테스트**: `tests/test_rag.py` 신설 — 비활성 문서 청크가 결과에서 배제되는지 단언
- **영향**: `agent_svc.stream_chat`, `knowledge_svc.get_chunk_with_context` 호출 경로. 기존 대화 세션에서 비활성 문서를 참조하던 답변 품질 향상
- **소요**: 0.5일

#### Bug-2: ProjectSettings.llm_model이 실호출 경로에 반영 안 됨

- **증상**: `ProjectSettings.llm_model`(`models/project.py:37 default="gpt-5.2"`)은 CRUD만 되고, `llm_svc`·`agent_svc` 어디에서도 읽지 않음
- **근거**: `grep -rn "llm_model" src/services/` → `project_svc.py`의 CRUD만 나옴. `llm_svc.chat_completion`에서 참조 없음
- **수정안 A (권장)**: `chat_completion` 시그니처 확장
  ```python
  # llm_svc.py
  async def chat_completion(
      messages: list[dict],
      *,
      client_type: str = "srs",
      model: str | None = None,   # <-- 추가
      temperature: float = 0.3,
      ...,
  ):
      client = get_client(client_type)
      effective_model = model or _get_default_model(client_type)
      return await client.chat.completions.create(model=effective_model, ...)
  ```
  호출자(서비스)는 `project_svc`에서 `ProjectSettings.llm_model`을 로드해 전달.
- **수정안 B (구조적)**: `agents/shared/model_resolver.py`에 프로젝트→모델 해석기
  ```python
  async def resolve_model(project_id: UUID, db) -> str:
      settings = await project_svc.get_settings(db, project_id)
      return settings.llm_model or DEFAULT_MODEL
  ```
  `AgentConfig` 생성 시 호출.
- **테스트**: `tests/test_project.py`에 "llm_model 변경 후 chat_completion이 전달받는지" 단언 추가
- **소요**: 1일

#### Bug-3: display_id / order_index 동시성 경쟁

- **증상**: `_next_display_id`가 `select func.max(...)` 후 +1 → 동시 insert 시 requirement는 unique constraint로 실패, record는 중복 허용
- **수정안 A (짧은 경로)**: PostgreSQL 시퀀스 도입 — 프로젝트·타입별 sequence를 서비스 코드로 생성 관리
  ```sql
  -- migration
  CREATE SEQUENCE IF NOT EXISTS requirement_display_seq_{project_uuid}_{type};
  -- 프로젝트 생성 시 모든 시퀀스 선 생성
  ```
- **수정안 B (ORM-친화)**: `FOR UPDATE` 락 (프로젝트+타입 row 한 건 잠금)
  ```python
  counter = await db.execute(
      select(DisplayCounter)
      .where(
          DisplayCounter.project_id == project_id,
          DisplayCounter.type == type_,
      )
      .with_for_update()  # row lock
  )
  counter.next_value += 1
  ```
- **수정안 C (단순)**: unique constraint 위반 시 최대 3회 재시도
- **제안**: B (가장 명시적·이식성 좋음). `services/_common/display_id.py` 도입과 묶어서
- **테스트**: `pytest-asyncio + asyncio.gather`로 동시 create 10건 → 모두 다른 display_id인지 검증
- **소요**: 2일 (requirement/record/glossary 3곳)

#### Bug-4: GET에서 write 부작용

- **증상**: `section_svc.get_sections` L84에서 `await _ensure_default_sections(...)` → INSERT + commit 가능
- **문제**: REST 위반, 동시 GET 경쟁 시 duplicate INSERT. 모니터링·캐싱에도 불리
- **수정**: 기본 섹션 생성은 **프로젝트 생성 시점**에 명시적으로 수행
  ```python
  # services/project_svc.create_project
  project = Project(...)
  db.add(project)
  await db.flush()
  await bootstrap.ensure_default_sections(db, project.id)  # 명시적 bootstrap
  await db.commit()
  ```
- **`section_svc.get_sections`**: write 제거, 순수 조회
- **마이그레이션 가드**: 기존 프로젝트는 Alembic 데이터 마이그레이션으로 일괄 보강
- **테스트**: `tests/test_section.py`에 "GET 두 번 호출해도 INSERT 발생 안 함" 단언
- **소요**: 0.5일 + 마이그레이션 0.5일

#### Bug-5: Tool args `{}` silent fallback

- **증상**: `agent_svc.py:317-319`
  ```python
  try:
      args = json.loads(tc["arguments"]) if tc["arguments"] else {}
  except json.JSONDecodeError:
      args = {}
  ```
  LLM이 깨진 JSON을 보내도 **빈 인자로 도구 실행** → `create_record()` 등이 엉뚱한 기본값으로 동작
- **수정**:
  ```python
  try:
      args = json.loads(tc["arguments"]) if tc["arguments"] else {}
  except json.JSONDecodeError as e:
      raise LLMToolArgsError(tool=tc["name"], raw=tc["arguments"], cause=e)

  # 상위에서 잡아서 SSE error 이벤트 + 재시도 또는 사용자 알림
  ```
- **추가**: `agents/tools/registry.py`에서 도구별 Pydantic input schema 정의 → `args = ToolRegistry[name].input_schema.model_validate(args)` 2차 검증
- **테스트**: "깨진 JSON arguments 전달 시 도구 실행 안 함 + error SSE" 단언
- **소요**: 1일 (Phase 1 Structured Output과 묶으면 0.5일)

#### Bug-6: `delegated_to_frontend` 거짓 성공 신호

- **증상**: `agent_svc.py:386`에서 프런트 위임 툴에 `{"status": "delegated_to_frontend"}`를 **더미 tool result**로 LLM에 돌려줌. LLM은 "완료됐다"고 이해하고 후속 답변/계획을 생성
- **수정안**: **Tool Envelope 표준**을 도입하고, frontend 위임 툴은 "응답 생성 전 종료" 패턴으로 전환
  ```python
  # 옵션 A: 프런트 위임 툴 호출 직후 LLM 루프 종료, 실제 결과는 차후 사용자 메시지로 피드백
  # 옵션 B: 위임 툴 전용 명시 태그 — {"status": "pending_client", "resume_token": "..."}
  #          LLM이 실제 실행 상태를 체크할 수 있게 별도 도구 제공
  ```
- **제안**: 옵션 A (단순). 프런트가 도구 완료 시 새 사용자 메시지로 후속 발화
- **영향**: `agents/tools/frontend_tools.py` 분리 + `streaming_loop.py`에서 위임 툴 감지 시 루프 break
- **테스트**: "프런트 위임 툴 호출 후 LLM이 재호출되지 않는지" 단언
- **소요**: 2일 (프런트 연동 확인 포함)

---

### 4.1 `services/agent_svc.py` (630 LOC) — **P0**

#### 4.1.1 현재 구조

| 심볼 | 라인 | LOC | 책임 |
|---|---|---|---|
| `TOOLS = [...]` | L33 | 153 | Function Calling 도구 스펙 7종 하드코딩 |
| `async def stream_chat` | L188 | 240 | LLM 루프 + SSE + Tool chunk 누적 + 백엔드 도구 dispatch |
| `async def _execute_backend_tool` | L443 | 100 | 5종 백엔드 도구 dispatch + 구현 |
| `async def _fetch_records` | L542 | 18 | DB → records |
| `async def _fetch_knowledge_chunks` | L560 | 35 | pgvector 검색 |
| `async def _fetch_glossary` | L595 | 13 | DB → glossary |
| `async def _fetch_requirements` | L608 | 21 | DB → requirements |
| `def _sse_event` | L629 | 3 | SSE 직렬화 |

#### 4.1.2 문제점

1. **7책임 집약** — 도구 정의 / 스트리밍 루프 / 도구 dispatch / 컨텍스트 수집 / SSE / 소스 주입 / 프런트 위임 처리
2. **`stream_chat` 240 LOC** — 단위 테스트 불가능
3. **도구 정의 하드코딩 153 LOC** — 타입 체크 없음
4. **도구 실행이 3곳 분산** — TOOLS 스키마 / stream_chat 호출 분기 / `_execute_backend_tool` 구현
5. **Bug-5 + Bug-6** — 위 §4.0 참조
6. **Temperature 0.3 고정** — 프로젝트별 조정 불가

#### 4.1.3 Before → After 도식 (Harness 구조 통합)

**Before**:
```
services/agent_svc.py  [630 LOC]
 ├─ TOOLS             (153 LOC, dict literal)
 ├─ stream_chat       (240 LOC, 모든 책임)
 ├─ _execute_backend  (100 LOC, dispatch + 구현)
 ├─ _fetch_* (4종)    ( 87 LOC)
 └─ _sse_event        (  3 LOC)
```

**After (Agent Harness 계층)**:
```
src/agents/
 ├─ harness/                   ← 5단계 파이프라인 (사용자 제안 반영)
 │  ├─ __init__.py             (public: run_chat_harness)
 │  ├─ intent.py               intent 분류 (~40 LOC) — P2에 확장
 │  ├─ context_loader.py       _fetch_* 4종 통합 (~90 LOC)
 │  ├─ planner.py              tool plan 생성 (~50 LOC) — P2에 확장
 │  ├─ executor.py             스트리밍 + tool 실행 오케스트레이션 (~120 LOC)
 │  └─ renderer.py             SSE 이벤트 렌더 + [SOURCES] 보완 (~60 LOC)
 ├─ tools/
 │  ├─ __init__.py             (public: TOOL_REGISTRY, ToolGateway)
 │  ├─ registry.py             Tool 객체(name/desc/input_schema/handler/target) (~110 LOC)
 │  ├─ gateway.py              ToolGateway — 실행 + 표준 envelope (~50 LOC)
 │  ├─ dto.py                  ToolCall / ToolResult / ToolError envelope (~30 LOC)
 │  ├─ frontend_tools.py       extract_records / generate_srs 선언
 │  └─ backend_tools/
 │     ├─ create_record.py
 │     ├─ update_record.py
 │     ├─ delete_record.py
 │     ├─ update_record_status.py
 │     └─ search_records.py
 └─ sse.py                     SSEEvent enum + serializer (~20 LOC)
```

**핵심 변화**:
- `stream_chat` 분해 → intent·context·planner·executor·renderer 5단계
- Tool 실행이 **ToolGateway**로 단일화 → 프런트 위임도 동일 envelope
- Bug-5, Bug-6이 `ToolGateway`·`registry.input_schema`로 구조적 해결

#### 4.1.4 Tool Envelope 표준 (v2 신설)

```python
# agents/tools/dto.py
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict  # Pydantic 검증 전

class ToolResult(BaseModel):
    id: str
    name: str
    status: Literal["success", "pending_client", "error"]
    result: dict | None = None
    error: ToolError | None = None
    trace_id: str

class ToolError(BaseModel):
    code: Literal["invalid_arguments", "not_found", "external_failure", "timeout"]
    message: str
    cause: str | None = None
```

- `status="pending_client"`: 프런트 위임 (Bug-6 해결). LLM 루프는 이 시점에 종료
- `status="error"`: Bug-5 해결 — LLM에 명확한 실패 신호 전달

#### 4.1.5 함수 이동 매핑

| 원래 | 새 위치 | 변경 |
|---|---|---|
| `TOOLS` dict | `agents/tools/registry.py` | 각 도구를 `Tool(name, description, input_schema, handler, target=BACKEND|FRONTEND)` |
| `stream_chat` LLM 루프 | `agents/harness/executor.py` | `streaming_loop`과 협력 |
| `_execute_backend_tool` | `agents/tools/gateway.py::dispatch` | `TOOL_REGISTRY[name].handler(args, db)` |
| `_fetch_*` | `agents/harness/context_loader.py` | `ChatContext` dataclass 반환 |
| `_sse_event` | `agents/sse.py` | Enum 기반 |

#### 4.1.6 영향 범위

- `src/routers/agent.py` — import 1줄 변경
- `src/services/record_svc.py` — 호출 심볼 유지 (record_svc 분리는 §4.5)
- `tests/test_agent.py` — **확장 필수**: ToolRegistry / ToolGateway / harness 단계별 단위 테스트. 목표 70%+ (§6.6)
- 공개 API 유지 (`stream_chat` 시그니처 동일)

#### 4.1.7 위험 / 우선순위

- **위험**: 중 — 스트리밍 경계 케이스 테스트 먼저
- **선행**: §4.3(`assist_svc`)과 `agents/shared/agent_config.py` 먼저 생성
- **소요**: 재작성 3일 + 테스트 2일 = 5 영업일 (P1 본격 분리 시점)

---

### 4.2 `prompts/agent/chat.py` (221 LOC, 단일 함수) — **P0**

#### 4.2.1 현재 구조

단일 함수 `build_agent_chat_prompt(...)`가 knowledge/glossary/requirements/records 섹션 + 고정 규칙 + 도구 가이드를 거대한 f-string으로 조립.

#### 4.2.2 문제점

1. 단일 함수 221 LOC — diff 리뷰 불가
2. 조건 분기가 f-string 내부에 중첩
3. 재사용 불가 (knowledge 섹션을 `rag_svc`가 재사용 못 함)
4. Skills 이식 불가능 (§9 Phase 3 의존성)

#### 4.2.3 After

```
prompts/agent/chat/
 ├─ __init__.py                 (public: build_agent_chat_prompt)
 ├─ builder.py                  조립 (~25 LOC)
 ├─ sections/
 │  ├─ knowledge.py             render_knowledge_section(chunks)
 │  ├─ glossary.py              render_glossary_section(glossary)
 │  ├─ requirements.py          render_requirements_section(reqs)
 │  └─ records.py               render_records_section(records)
 ├─ rules.py                    대화 톤 + [CLARIFY]/[SOURCES] 포맷 (~80 LOC)
 └─ tool_guide.py               extract_records / generate_srs 설명 (~40 LOC)
```

#### 4.2.4 Skills 이식 경로

| 현재 | Skill 후보 (Phase 3) |
|---|---|
| `sections/knowledge.py` | `skills/rag-knowledge-context/SKILL.md` |
| `sections/glossary.py` | `skills/glossary-context/SKILL.md` |
| `sections/requirements.py` | `skills/requirements-context/SKILL.md` |
| `sections/records.py` | `skills/records-context/SKILL.md` |
| `rules.py` | `skills/aise-chat-protocol/SKILL.md` |
| `tool_guide.py` | `agents/tools/registry.py` description에 자연 병합 |

**원칙(사용자 제안 반영)**: Prompt는 "행동 정책(rule)"에서 "도메인 지식(knowledge)"으로 축소한다. 길고 복합적인 규칙은 코드 정책으로 이동.

#### 4.2.5 영향

- `services/agent_svc.py` (→ `agents/harness/executor.py`) import 1곳
- 위험: 하
- 소요: 1~2일

---

### 4.3 `services/assist_svc.py` (167 LOC, 3 함수) — **P0**

#### 4.3.1 현재 구조

| 함수 | 라인 | LOC | Temperature |
|---|---|---|---|
| `refine_requirement` | L24 | ~20 | 0.3 |
| `suggest_requirements` | L44 | ~60 | 0.5 |
| `chat_assist` | L105 | ~60 | **0.7** (비정상) |

각 함수: DB 조회 → 프롬프트 빌드 → `chat_completion` → `parse_llm_json` → AppException(502) on error → 응답 조립. 공통 스캐폴드 없음.

#### 4.3.2 문제점

1. 3 에이전트 한 파일, 물리적 분리 없음
2. 공통 스캐폴드 없음 — "LLM → JSON → Pydantic" 패턴 3번 반복
3. temperature 0.7 (chat_assist)은 다른 JSON 에이전트의 2배 — 근거 없음, Bug-5 성질의 파싱 실패 증가 가능
4. **"에이전트 레이어"의 씨앗** — 여기를 먼저 정리해야 agent_svc / review_svc / glossary_svc 분리 패턴이 정립

#### 4.3.3 After

```
src/agents/
 ├─ assist/
 │  ├─ __init__.py              (public: refine, suggest, chat)
 │  ├─ refine.py                refine_requirement
 │  ├─ suggest.py               suggest_requirements
 │  └─ chat.py                  chat_assist
 └─ shared/
    ├─ agent_config.py          AgentConfig dataclass
    ├─ json_agent.py            run_json_agent 공통 스캐폴드
    └─ model_resolver.py        ProjectSettings.llm_model 해석 (Bug-2 해결)
```

#### 4.3.4 `json_agent.py` 스캐폴드 (의사코드)

```python
async def run_json_agent[T: BaseModel](
    *,
    messages: list[dict],
    config: AgentConfig,
    response_model: type[T],
    client_type: str = "srs",
) -> T:
    """LLM → JSON → Pydantic 공통 파이프라인.
    Structured Output 지원 시 response_format 사용, 미지원 시 parse_llm_json fallback.
    """
    if await supports_structured_output(config):
        raw = await chat_completion_structured(
            messages, config,
            response_format=response_model,
            client_type=client_type,
        )
    else:
        raw = await chat_completion(
            messages, config=config, client_type=client_type,
        )
        raw = _strip_code_fence(raw)
    try:
        return response_model.model_validate_json(raw)
    except ValidationError as e:
        raise LLMParseError(
            agent=config.name, model=config.model, cause=e,
        ) from e
```

- **재시도 훅**: `config.retry_policy`(후속 ADR-012)로 wrapping
- **재사용**: review / glossary extract / record extract / suggestion / section에서 동일 스캐폴드 소환

#### 4.3.5 영향

- `src/routers/assist.py` — import 3줄 변경
- `src/schemas/llm/` — `RefineOutput`, `SuggestOutput`, `ChatAssistOutput` Pydantic 스키마 신설
- `tests/test_assist.py` 319 LOC — 유지, 함수별 모듈 단위로 분리

---

### 4.4 `services/review_svc.py` (333 LOC / 3 함수) — **P1**

(초판과 동일 — 생략 없이 재수록)

#### 4.4.1 현재 구조

| 함수 | 라인 | LOC | 책임 |
|---|---|---|---|
| `_parse_review_response` | L26 | ~46 | Pydantic 응답 조립 |
| `review_requirements` | L72 | **~230** | 5단계 파이프라인 단일 함수 |
| `get_latest_review` | L303 | ~30 | 단순 조회 |

#### 4.4.2 After

```
src/services/review/
 ├─ __init__.py                 (public: review_requirements, get_latest_review)
 ├─ service.py                  오케스트레이터 (~40 LOC)
 ├─ query.py                    요구사항 조회 분기 (~40 LOC)
 ├─ prompt_adapter.py           req → LLM DTO (~25 LOC)
 ├─ response_parser.py          _parse_review_response (~55 LOC)
 └─ repository.py               upsert_review, get_latest (~65 LOC)
```

`service.review_requirements` 본체 (의사코드):

```python
async def review_requirements(project_id, request, db):
    reqs = await query.get_target_requirements(project_id, request, db)
    payload = prompt_adapter.build(reqs)
    output = await run_json_agent(
        messages=prompts.review.build(payload),
        config=REVIEW_CONFIG,
        response_model=ReviewOutput,
    )
    review = await repository.upsert_review(project_id, reqs, output, db)
    return response_parser.to_response(review)
```

**위험**: 중 (DB delete+insert 경계). **소요**: 3 영업일.

---

### 4.5 `services/record_svc.py` (605 LOC / 23 함수) — **P1**

#### 책임 분포

| 책임 | 함수 | 라인 |
|---|---|---|
| 매퍼 | `_to_response` | L46~ |
| display_id | `_display_prefix`, `_build_display_counters`, `_next_display_id`, ... | L60~140 (**Bug-3 해결 지점**) |
| CRUD | list/create/update/delete/update_status | L185~297 |
| LLM Extract 동기 | `extract_records` | L299~422 (~120 LOC) |
| LLM Extract 스트리밍 | `stream_extract_records` | L432~490 |
| 조회 | search/get_by_display_id/get_section_by_name | L492~570 |
| 승인/순서 | approve_records, reorder_records | L570~605 |

#### After

```
services/record/
 ├─ __init__.py                 (public re-export)
 ├─ crud.py                     (~150 LOC)
 ├─ display_id.py               (~80 LOC, FOR UPDATE 락 — §4.0 Bug-3)
 ├─ query.py                    (~90 LOC)
 ├─ extractor.py                (~200 LOC)
 ├─ approval.py                 (~50 LOC)
 ├─ mapper.py                   (~25 LOC)
 └─ loaders.py                  (~30 LOC, P2 공통화 후보)
```

#### 호출자 영향

`agent_svc.py`에서 `get_section_by_name`, `approve_records`, `create_record`, `update_record`, `delete_record`, `update_record_status`, `search_records` 호출 — `services/record/__init__.py`의 re-export로 방어.

**위험**: 중하 — 대부분 순수 CRUD. extractor만 LLM+DB 결합. **소요**: 4 영업일.

---

### 4.6 `services/requirement_svc.py` (341 LOC / 12 함수) — **P1**

#### 책임

CRUD + display_id (Bug-3) + section 검증 + selection + reorder + version + mapper.

#### After

```
services/requirement/
 ├─ crud.py                     (~100 LOC)
 ├─ display_id.py               (~40 LOC, FOR UPDATE 락)
 ├─ section_guard.py            (~25 LOC)
 ├─ selection.py                (~40 LOC)
 ├─ ordering.py                 (~60 LOC)
 ├─ versioning.py               (~50 LOC)
 └─ mapper.py
```

**안전망**: `tests/test_requirement.py` 437 LOC. **소요**: 3 영업일.

---

### 4.7 `services/knowledge_svc.py` (346 LOC / 12 함수) — **P1**

#### After

```
services/knowledge/
 ├─ upload.py                   upload_document + reprocess (~110 LOC)
 ├─ query.py                    list/get/preview/chunk_context (~120 LOC)
 ├─ mutation.py                 toggle/delete (~50 LOC)
 ├─ mapper.py                   (~60 LOC)
 └─ background.py               BackgroundTasks (~30 LOC)
```

**리스크**: **테스트 부재** (`tests/test_knowledge.py` 없음, 커버리지 24%) → **분리 전 최소 커버 신설 필수**. MinIO 업로드 mock fixture 포함. **소요**: 2일(테스트) + 2일(분리) = 4 영업일.

---

### 4.8 `utils/text_chunker.py` (446 LOC / 11 함수) — **P1**

#### After

```
utils/chunking/
 ├─ __init__.py                 (public: chunk_text)
 ├─ tokenizer.py                (~30 LOC, DI 가능)
 ├─ markdown_parser.py          (~100 LOC)
 ├─ splitters/{table,code,list_block,text}.py
 └─ strategy.py                 (~150 LOC)
```

**안전망**: `tests/test_text_chunker.py` 167 LOC. **소요**: 3 영업일.

---

### 4.9 P2 핫스팟 요약

| 파일 | LOC | 분리안 | 핵심 포인트 |
|---|---|---|---|
| `services/section_svc.py` | 303 | `bootstrap.py` / `crud.py` / `ai.py` 3분할 | **Bug-4 해결** (GET side effect 제거) |
| `services/glossary_svc.py` | 291 | `glossary/{crud,generate,extract,repository}.py` | 2 에이전트 분리 |
| `services/suggestion_svc.py` | 238 | `agents/suggestion/` 이동 | 완전한 LLM 에이전트 |
| `services/srs_svc.py` | 219 | `agents/srs/` + `services/srs/repository.py` | LLM + DB 혼재 |
| `services/project_svc.py` | 209 | `project/{query,mutation,settings,readiness}.py` | **list_projects N+1** 선 해결 |
| `services/session_svc.py` | 167 | prompt_suggestions를 `agents/suggestion/`으로 | 나머지는 얇은 CRUD |

---

## 5. LLM 에이전트 레이어 진단

### 5.1 에이전트 인벤토리 (12종)

| # | 에이전트 | 위치 | 입력 | 출력 | temp | max_tok | client | 스트리밍 | FuncCall | 프롬프트 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Agent Chat** | agent_svc.stream_chat | session_id + message | SSE (token/tool_call/tool_result/done) | 0.3 | - | srs | ✓ | ✓ (7 tools) | prompts/agent/chat.py (221) |
| 2 | **Assist·Refine** | assist_svc.refine_requirement | text + type | JSON `{refined_text}` | 0.3 | default | srs | - | - | prompts/assist/refine.py (49) |
| 3 | **Assist·Suggest** | assist_svc.suggest_requirements | requirement_ids | JSON `{suggestions[]}` | 0.5 | 4096 | srs | - | - | prompts/assist/suggest.py (49) |
| 4 | **Assist·Chat** | assist_svc.chat_assist | message + history | JSON `{reply, extracted[]}` | **0.7** | 4096 | srs | - | - | prompts/assist/chat.py (100) |
| 5 | **Review** | review_svc.review_requirements | requirement_ids | JSON `{issues[], summary}` | 0.3 | 2048 | srs | - | - | prompts/review/requirements.py (72) |
| 6 | **SRS Generate** | srs_svc.generate_srs | (auto records) | Markdown (섹션별) | 0.2 | 4096 | srs | - | - | prompts/srs/generate.py (62) |
| 7 | **Glossary·Generate** | glossary_svc.generate_glossary | (auto requirements) | JSON `{glossary[]}` | 0.3 | 4096 | default | - | - | prompts/glossary/generate.py (40) |
| 8 | **Glossary·Extract** | glossary_svc.extract_glossary | document_ids | JSON `{glossary[]}` | 0.3 | 4096 | default | - | - | prompts/glossary/extract.py (44) |
| 9 | **Record Extract** | record_svc.extract_records / stream | knowledge_document_ids | JSON 스트림 | 0.2 | 8192 | default | ✓ | - | **프롬프트 없음 (svc 내부)** |
| 10 | **Prompt Suggestions** | suggestion_svc.suggest_prompts | project meta | JSON `{suggestions[]}` | 0.5 | 2048 | default | - | - | **프롬프트 없음** |
| 11 | **RAG Chat** | rag_svc.ask | question + doc_ids | SSE | 0.3 | - | default | ✓ | - | prompts/knowledge/chat.py (40) |
| 12 | **Section AI** | section_svc.* | project | JSON | 0.3 | 2048 | default | - | - | **프롬프트 없음** |

**총 12 에이전트**. 3개(Record Extract, Prompt Suggestions, Section AI)는 **프롬프트 파일조차 없이 서비스 파일에 f-string으로 내장**.

### 5.2 프롬프트 카탈로그 (9 파일 / 698 LOC)

| 파일 | LOC | 주요 섹션 | 언어 | 모델 가정 |
|---|---|---|---|---|
| `agent/chat.py` | 221 | [CLARIFY]/[REQUIREMENTS]/[SUGGESTIONS]/[SOURCES] 블록 + 4종 컨텍스트 | KO | GPT-계열 JSON 블록 안정 가정 |
| `assist/chat.py` | 100 | JSON 강제, 사용자 언어 매칭 | EN | JSON-only 출력 가정 |
| `review/requirements.py` | 72 | IEEE 29148, 충돌/중복만 | EN | 표준 학습 가정 |
| `srs/generate.py` | 62 | IEEE 830 / ISO 29148, 레코드 ID 참조 | KO/EN 혼용 | 표준 학습 가정 |
| `assist/refine.py` | 49 | SHALL/SHOULD 명시 | KO | SHALL 키워드 이해 가정 |
| `assist/suggest.py` | 49 | 갭 분석 | KO | - |
| `glossary/extract.py` | 44 | 동의어/약어, 중복 제외 | KO | - |
| `glossary/generate.py` | 40 | "JSON 형식으로만 응답" 최소 | KO | JSON mode 가정 |
| `knowledge/chat.py` | 40 | 청크별 참고 포맷 | KO | - |

### 5.3 Temperature 매트릭스 (일관성 문제)

| 에이전트 | temp | 평가 |
|---|---|---|
| record extract / srs generate | 0.2 | ✅ 적절 |
| refine / review / glossary / rag / section / agent chat | 0.3 | ✅ 적절 |
| suggest / suggestion | 0.5 | ⚠️ 근거 주석 없음 |
| **chat_assist** | **0.7** | **❌ 비정상. 다른 JSON 에이전트의 2배. 파싱 실패 증가 가능** |

**권장 표준** (ADR-001로 확정):
- JSON 에이전트: 0.2~0.3
- 대화형(SSE): 0.3~0.5
- 창의 제안: 0.5~0.6
- `chat_assist`: 0.7 → **0.5**로 조정 후 QA 회귀 검증

### 5.4 출력 형식 표준화 매트릭스

| 에이전트 | 현재 | 파싱 | 권장 |
|---|---|---|---|
| Agent Chat | 자유 + `[CLARIFY]` JSON 블록 | regex + 수동 | **유지** (interactive) |
| Assist Refine/Suggest/Chat | 순수 JSON | parse_llm_json | **Structured Output (Pydantic)** |
| Review | JSON | parse_llm_json | **Structured Output** |
| SRS Generate | Markdown | 없음 | **유지** (document) |
| Glossary E/G | JSON | parse_llm_json | **Structured Output** |
| Record Extract | JSON 라인 스트림 | 라인별 json.loads | **Function Calling + Structured Output** |
| Prompt Suggestions | JSON | parse_llm_json | **Structured Output** |
| Section AI | JSON | parse_llm_json | **Structured Output** |

**수렴 목표**: 12 에이전트 → **3 그룹**
1. **Interactive** (2): Agent Chat, RAG Chat
2. **Document** (1): SRS Generate
3. **Structured** (9): Pydantic + Structured Output

### 5.5 파싱 실패 + Tool args fallback 문제 (v2 강화)

| 에이전트 / 지점 | 현상 | 문제 |
|---|---|---|
| Assist / Review / Glossary | `parse_llm_json` 실패 → `AppException(502)` 즉시 | 재시도/폴백 정책 없음 |
| Record Extract (라인) | skip (부분 실패 허용) | **silent drop, 알림 없음** |
| SRS Generate (비동기) | DB에 `error_message` 저장 | 사용자 알림 lag |
| Agent Chat | SSE `error` 이벤트 | 프론트 처리 규약 불명확 |
| **Agent Chat Tool args** | `json.loads` 실패 시 `args = {}` **silent fallback** | **Bug-5 — LLM 오류를 빈 인자 실행으로 전환** |
| **Agent Chat Frontend tool** | `{"status": "delegated_to_frontend"}` 더미 응답 | **Bug-6 — LLM이 완료로 인식** |

**권장** (Phase 2에서 일괄):
1. `LLMParseError(agent, model, cause)` 도메인 예외 도입
2. `LLMToolArgsError(tool, raw, cause)` 분화
3. `agents/shared/llm_retry.py` — exponential backoff 2~3회 정책
4. **Tool Envelope 표준** (`ToolCall/ToolResult/ToolError`) — §4.1.4
5. 프런트 위임 툴은 `status="pending_client"` + LLM 루프 종료 패턴

---

## 6. 횡단 관심사 진단

### 6.1 설정 관리 — **P0**

#### 현재 문제

18개 env var가 `os.getenv`로 10+ 파일 산재. pydantic-settings 미도입.

**Env 인벤토리**:

```
AZURE_EMBEDDING_MODEL    CORS_ORIGINS           ENVIRONMENT
LLM_PROVIDER             LOG_LEVEL              MINIO_ACCESS_KEY
MINIO_BUCKET             MINIO_ENDPOINT         MINIO_SECRET_KEY
OPENAI_API_KEY           OPENAI_EMBEDDING_MODEL OPENAI_MODEL
SRS_API_KEY              SRS_ENDPOINT           SRS_MODEL
TC_API_KEY               TC_ENDPOINT            TC_MODEL
```

**부가**:
- `api_version="2025-03-01-preview"` 하드코딩
- Database URL은 `core/database.py` 직접 조립
- `main.py`가 `load_dotenv()` 호출, but `python-dotenv` 미선언 (§6.7)

#### 권장

```python
# src/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class AzureOpenAISettings(BaseSettings):
    srs_endpoint: str
    srs_api_key: SecretStr
    srs_model: str = "gpt-5.2"
    tc_endpoint: str
    tc_api_key: SecretStr
    tc_model: str = "gpt-5.2"
    api_version: str = "2025-03-01-preview"
    embedding_model: str = "text-embedding-3-large"

class MinIOSettings(BaseSettings):
    endpoint: str
    access_key: SecretStr
    secret_key: SecretStr
    bucket: str
    secure: bool = True   # ← 기본값 True로 변경, dev에서 명시적 override

class DBSettings(BaseSettings):
    url: str
    ssl_mode: Literal["disable", "require", "verify-full"] = "require"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    db: DBSettings
    minio: MinIOSettings
    llm: LLMSettings
    cors_origins: list[str] = ["http://localhost:3000"]
```

- `SecretStr` 사용 → 로그 유출 방지
- `environment` 값에 따라 `secure`/`ssl_mode` 강제 검증 가능

### 6.2 예외 처리 — **P0**

#### 현재

```python
class AppException(Exception):
    def __init__(self, status_code: int, detail: str): ...
```

모든 도메인 오류가 단일 클래스.

#### 권장 위계

```
Exception
 └─ DomainError (base)
    ├─ NotFoundError        (404)
    ├─ ConflictError        (409)
    ├─ ValidationError      (422)
    ├─ UnauthorizedError    (401)
    ├─ ForbiddenError       (403)
    └─ ExternalServiceError (502)
       ├─ LLMError
       │  ├─ LLMParseError          ← parse_llm_json 실패
       │  ├─ LLMToolArgsError       ← Bug-5: 도구 인자 파싱 실패
       │  └─ LLMTimeoutError
       ├─ StorageError              (MinIO)
       └─ VectorSearchError         (pgvector)
```

#### 마이그레이션

1. P0: 클래스 추가, 기존 AppException 유지
2. P0: LLM 실패 지점 5곳 → LLMParseError/LLMToolArgsError
3. P1: `AppException(404, ...)`를 `NotFoundError`로 치환 (`get_or_404` 유틸부터)
4. P1: Exception handler를 타입별 등록 → 로깅·알림 차별화

### 6.3 DI / 싱글톤 — **P0**

#### 현재

```python
# llm_svc.py
_openai_client: AsyncOpenAI | None = None
_srs_client: AsyncAzureOpenAI | None = None
_tc_client: AsyncAzureOpenAI | None = None
```

모듈 전역 싱글톤. 테스트 mock 어려움.

#### 권장

```python
@lru_cache(maxsize=1)
def get_srs_client(settings: Settings = Depends(get_settings)) -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.llm.azure.srs_endpoint,
        api_key=settings.llm.azure.srs_api_key.get_secret_value(),
        api_version=settings.llm.azure.api_version,
    )
```

+ `tests/conftest.py`에 `get_srs_client` override fixture.

### 6.4 DB / 트랜잭션·동시성 — **P0~P2**

#### 즉시 고칠 것 (P0)

- **Bug-3 display_id 동시성**: requirement/record/glossary 3곳에 `FOR UPDATE` 락 또는 sequence 도입 (§4.0)
- **Bug-4 GET side effect**: `section_svc.get_sections` write 제거 (§4.0)
- **project_svc.list_projects N+1**: `selectinload` 적용 (P1)

#### 트랜잭션 경계 전환 (P2)

- 현재: `db.commit()`이 13+ 서비스에 분산
- **옵션 A**: 라우터 레벨 commit
- **옵션 B**: UoW 패턴
- **제안**: 이번 주기는 현행 유지, 분리 후 재검토

### 6.5 로깅·관측 — **P1**

#### 현재

- loguru `contextualize(request_id=...)` 미들웨어 주입
- business context (`project_id`, `user_id`) 거의 없음

#### 권장

```python
from contextlib import contextmanager

@contextmanager
def bind_project(project_id: UUID, session_id: UUID | None = None):
    with logger.contextualize(
        project_id=str(project_id),
        session_id=str(session_id) if session_id else None,
    ):
        yield
```

**Harness 관점 추가**: `ToolGateway` 실행 시 `trace_id` 생성 → `ToolResult.trace_id`로 전달, SSE 이벤트 / 로그 / Eval Harness 모두 동일 trace 사용.

### 6.6 테스트 — **P0 (안전망 선행)**

#### 현재 커버리지 (사용자 제공 추정 + LOC 비율)

| 파일 | 구현 LOC | 테스트 LOC | Coverage 추정 | 등급 |
|---|---|---|---|---|
| agent_svc.py | 630 | 13 | **13%** | 🔴 |
| llm_svc.py | 119 | - | **23%** | 🔴 |
| knowledge_svc.py | 346 | 0 | **24%** | 🔴 |
| rag_svc.py | 139 | - | **25%** | 🔴 |
| srs_svc.py | 219 | - | **21%** | 🔴 |
| document_processor.py | 156 | - | **14%** | 🔴 |
| requirement_svc.py | 341 | 437 | 높음 | ✅ |
| review_svc.py | 333 | 412 | 높음 | ✅ |
| assist_svc.py | 167 | 319 | 높음 | ✅ |
| text_chunker.py | 446 | 167 | 중간 | 🟡 |
| **전체** | - | 2,146 | **~59%** | 🟡 |

#### P0 액션

1. **LLM mock fixture** (`tests/conftest.py`):
   ```python
   @pytest.fixture
   def llm_mock(monkeypatch):
       responses = {}
       async def fake(messages, **kw):
           key = (kw.get("client_type"), kw.get("config", {}).get("name", ""))
           return responses.get(key, '{"default": true}')
       monkeypatch.setattr("src.services.llm_svc.chat_completion", fake)
       return responses
   ```
2. **`tests/test_agent_harness.py` 신설** (사용자 제안 반영) — 최소 케이스:
   - Tool Registry 5건 (등록·검색·스키마 검증)
   - ToolGateway 5건 (정상·invalid args·unknown tool·partial JSON·frontend delegation)
   - streaming_loop 3건 (델타 누적·tool chunk·cancel)
   - context_loader 3건 (RAG filter 포함 — **Bug-1 회귀 테스트**)
3. **`tests/test_knowledge.py`**, **`tests/test_srs.py`**, **`tests/test_rag.py`** 신설
4. 목표: **agent_svc 계열 70%+**, **llm_svc / rag_svc / srs_svc 60%+**

### 6.7 의존성 감사 — **P0**

| 항목 | 현재 | 문제 | 액션 |
|---|---|---|---|
| `psycopg2-binary>=2.9.11` | 있음 | asyncpg와 중복, 동기 블로킹 | **제거** (alembic이 필요 시 dev-only) |
| `python-dotenv` | **없음** | `main.py`가 `load_dotenv` 호출 | **추가** |
| `pydantic-settings` | 없음 | §6.1 필요 | **추가** |
| `httpx` | dev only | - | 유지 |
| `redis` / `celery` | 없음 | 캐시·태스크 큐 | P2 논의 |
| `sentry-sdk` | 없음 | 에러 트래킹 | P2 논의 |
| Python 3.14 | 요구 | 너무 높음 | **3.12로 완화** |
| **`deepagents>=0.4.12`** | 있음 | **실제 import 0건** | Phase 5까지 유지, ADR-002 |
| `langchain-*` | 없음 | Phase 5에 필요 | 추후 |

### 6.8 미연결 모듈 인벤토리 (v2 신설)

현재 `pyproject`·`schemas/`에 선언되어 있으나 실제로 연결되지 않은 자원:

| 모듈 | 상태 | 현황 | 액션 |
|---|---|---|---|
| `schemas/api/import_export.py` | 미연결 | 라우터 없음 | 로드맵 확인 후 연결 or 제거 |
| `schemas/api/member.py` | 미연결 | Keycloak 인증 구현 시 필요 | 보류 |
| `schemas/api/notification.py` | 미연결 | 알림 기능 미구현 | 로드맵 확인 |
| `schemas/api/testcase.py` | 미연결 (111 LOC) | TC 모듈 구현 대기 | 보류 (FR-TC 로드맵 대기) |
| `schemas/api/usecase.py` | 미연결 (79 LOC) | UCD 구현 대기 | 보류 |
| `schemas/api/user.py` | 미연결 | Keycloak 대기 | 보류 |
| `schemas/api/version.py` | 미연결 | 버전 관리 RPC 미구현 | 로드맵 확인 |
| `integrations/jira/` | 미구현 | 빈 모듈 | 로드맵 확인 |
| `integrations/polarion/` | 미구현 | 빈 모듈 | 로드맵 확인 |
| `deepagents` 의존성 | 실사용 0 | Phase 5에서 사용 예정 | 유지 |

**권장**: P1 말미에 팀 미팅으로 "유지 / 제거 / 당장 연결" 3분류. 로드맵에 없는 것은 제거해 노이즈 감소.

---

## 7. 데이터 모델·마이그레이션

### 7.1 ER 요약

```
Project (1) ─── (N) RequirementSection ─── (N) Requirement ─── (N) RequirementVersion
   │
   ├── (N) GlossaryItem
   ├── (N) KnowledgeDocument ─── (N) KnowledgeChunk (pgvector)
   ├── (N) Record
   ├── (N) Review (review_data: JSONB)
   ├── (N) Session ─── (N) Message (tool_calls, tool_data: JSONB)
   ├── (1) ProjectSettings (llm_model: **실사용 안 됨 — Bug-2**)
   └── (N) SrsDocument
```

### 7.2 JSONB 컬럼 스키마 드리프트

| 테이블.컬럼 | 위치 | 스키마 문서화 | 위험 |
|---|---|---|---|
| `requirement_reviews.review_data` | models/review.py:22 | 없음 | Review Agent 출력 변경 시 과거 row 파싱 실패 |
| `requirement_reviews.reviewed_requirement_ids` | models/review.py:23 | `list[str]` 암묵 | 낮음 |
| `session_messages.tool_calls` | models/session.py:36 | 없음 | Function Calling 포맷 변경 시 호환 깨짐 |
| `session_messages.tool_data` | models/session.py:37 | 없음 | 프론트 표시 로직과 결합 |

#### 권장

- `schemas/db/review_data.py` 등에 **schema_version 필드** 포함
- 마이그레이션 시 기존 row의 `schema_version` 미존재 케이스 명시적 처리
- **Tool Envelope 표준**(§4.1.4)이 확정되면 `tool_calls`·`tool_data`도 동일 envelope 사용 → DB 저장 시 v1 버전 태깅

### 7.3 Alembic

- 17 migrations, squash 없음
- P2에서 초기 3~5개 squash 검토
- 각 migration의 `depends_on` 점검

---

## 8. 보안·운영 — 🔴 긴급 사안 (v2 재작성)

### 8.1 보안 긴급 사안

#### S-1: `backend/.env`에 운영 API 키 존재 (즉시 조치)

- **현황**: `backend/.env` 실재 (698 bytes, 2026-04-05 생성)
- **위험**: git 추적 대상은 아니지만, 로컬 백업·스크린 공유·IDE 인덱싱 등으로 유출 가능성 상존
- **즉시 조치**:
  1. `SRS_API_KEY`, `TC_API_KEY`, `OPENAI_API_KEY`, `MINIO_SECRET_KEY` **즉시 폐기 후 재발급**
  2. 새 키는 Vault 또는 환경 변수 주입 (배포 시)
  3. `backend/.env`는 **dev 전용 mock 값**만 유지, 운영 값 금지
  4. `.env.example` 작성, 실제 키 위치는 문서화 (Vault 경로 등)
- **책임자**: 프로젝트 소유자
- **소요**: 1일 (로테이션 + 배포 환경 갱신)

#### S-2: TLS 비활성 기본값

- **위치**:
  - `core/database.py:16` `connect_args={"ssl": False}`
  - `services/storage_svc.py:26` `secure=False` (MinIO)
- **위험**: 로컬 개발용 기본값이 **운영 분기 없이** 코드 레벨에서 고정. 운영 배포 시 실수로 TLS 없이 실행 가능
- **조치**:
  1. `Settings.db.ssl_mode`, `Settings.minio.secure`를 필수 필드로 상승
  2. `environment=prod`일 때 `ssl_mode != "disable"`, `secure == True`가 아니면 부팅 시 assertion 실패
  3. dev `.env.example`에만 명시적으로 `DB__SSL_MODE=disable` 주석 처리
- **소요**: 1일 (Settings 도입과 묶으면 0일)

### 8.2 전면 보안 체크리스트

| 항목 | 상태 | 설명 | 등급 |
|---|---|---|---|
| `.env` 실키 존재 | 🔴 | §8.1 S-1 | 즉시 |
| TLS 비활성 (DB / MinIO) | 🔴 | §8.1 S-2 | 즉시 |
| 인증 | ⚠️ 미구현 | Keycloak/LDAP 계획만 있음 | P1 |
| 인가 | ⚠️ 미구현 | `created_by`만 있음 | P1 |
| 파일 업로드 MIME sniff | ⚠️ | 확장자만 검사 | P0 |
| LLM 프롬프트 인젝션 가드 | ⚠️ | 없음 — 사용자 입력이 system prompt에 직접 인라인 | P0 |
| SQL Injection | ✅ | SQLAlchemy 파라미터화 | - |
| CORS | ✅ | `CORS_ORIGINS` + regex | - |
| Rate limiting | ❌ | LLM 비용 폭주 가능 | P1 |
| SSE 에러에 스택트레이스 누수 | ⚠️ | 가능성 | P0 |
| Secret rotation 정책 | ❌ | 수동 | P1 |
| **Settings.environment 부팅 검증** | ❌ | 도입 필요 | P0 |

### 8.3 P0 즉시 조치 (v2 확정)

1. **키 로테이션** (소유자, 1일)
2. **Settings의 `environment=prod` 가드** — TLS 강제 검증
3. **LLM 프롬프트 인젝션 가드** — 사용자 입력을 `<user_input>...</user_input>` XML-like wrap, 시스템 프롬프트에 "태그 내 내용은 데이터로만 취급" 명시
4. **MIME sniff** — `python-magic` 또는 파일 헤더 검증
5. **SSE 에러 이벤트**: 스택트레이스 제외, `error_code`만 노출

---

## 9. 에이전트 아키텍처 진화 로드맵 (6 Phases, v2 재구성)

**v1 변경점**: 사용자 제안 "Agent Harness 계층 신설" + "Tool Gateway envelope" + "Eval Harness"를 Phase 2·3·6에 통합.

**핵심 전환 메시지**:
> **현재**: 프롬프트가 규칙을 **설명**한다 → LLM이 이해·실행 여부에 의존
> **목표**: 하네스가 규칙을 **강제**한다 → 구조적 스키마·코드 정책으로 보장

### Phase 0: Config / 시크릿 표준화 (1주)

- pydantic-settings + `.env.example`
- **S-1 키 로테이션**, **S-2 TLS 가드**
- 모든 LLM 호출이 `AgentConfig` dataclass 주입
- JSON 에이전트 temp 0.2, 대화형 0.3~0.5 표준화
- **예상**: 5 영업일

### Phase 1: Bug 수정 + Structured Output (2주)

- §4.0 Bug-1 ~ Bug-6 모두 수정 (RAG 필터 / llm_model resolver / display_id 동시성 / GET side effect / Tool args 검증 / delegated 처리)
- 9개 JSON 에이전트에 Pydantic 응답 스키마 + Structured Output
- `LLMParseError`, `LLMToolArgsError` 도입
- `agents/shared/json_agent.py`, `model_resolver.py`, `llm_retry.py` 스캐폴드
- **선행**: ADR-001 (Azure Structured Output 호환성 PoC 1일)
- **예상**: 10 영업일

### Phase 2: Agent Harness 계층 신설 (2~3주) ← **v2 재구성**

**목표**: `src/agents/harness/`에 5단계 파이프라인 도입. prompt-level 규칙을 code-level 정책으로 이동.

**구조**:
```
agents/
├─ harness/
│  ├─ intent.py         사용자 메시지 → intent 분류 (규칙 + 선택적 LLM)
│  ├─ context_loader.py RAG/Glossary/Records 로딩 (typed)
│  ├─ planner.py        tool plan 생성 (ToolPlan Pydantic)
│  ├─ executor.py       tool 실행 오케스트레이션 (ToolGateway 호출)
│  └─ renderer.py       응답 렌더링 (SSE 이벤트 + [SOURCES] 보완)
├─ tools/
│  ├─ registry.py, gateway.py, dto.py
│  ├─ frontend_tools.py, backend_tools/*
└─ shared/
   ├─ agent_config.py, json_agent.py, model_resolver.py, llm_retry.py
```

**각 단계는 typed schema I/O 강제**:

```python
# harness/intent.py
class Intent(BaseModel):
    kind: Literal["chat", "extract_records", "generate_srs", "search_records", ...]
    confidence: float

# harness/context_loader.py → ChatContext (Pydantic)
# harness/planner.py → ToolPlan { calls: list[ToolCall] }
# harness/executor.py → list[ToolResult]
# harness/renderer.py → AsyncGenerator[SSEEvent, None]
```

**대상**: agent_svc.stream_chat → harness로 이전. 기존 `prompts/agent/chat.py` 규칙 중 강제 가능한 것(출력 포맷, 도구 선택)은 코드로 이동, prompt는 톤·도메인 용어·출력 설명만 유지.

**예상**: 10~15 영업일

### Phase 3: Skills 재구성 (2~3주)

- 698 LOC 프롬프트를 `SKILL.md` 형식 재편성
- 순서: `prompts/agent/chat/sections/*` → `skills/agent-chat/*` → 나머지
- `SkillLoader` 헬퍼
- 조건부 on-demand inject (RAG/도메인 조건)
- **예상**: 10~15 영업일

### Phase 4: MCP 파일럿 (1~2주)

- Record CRUD 5종 + Knowledge search를 MCP Tool/Resource로
- `fastapi-mcp` vs `fastmcp` (ADR-003)
- 인증 JWT → MCP session 매핑
- read-only 도구 우선
- **예상**: 5~8 영업일

### Phase 5: Deep Agents 도입 (선택, 3~4주)

- Agent Chat orchestration → `deepagents.create_deep_agent` 또는 LangGraph StateGraph
- SubAgent: extractor / reviewer / srs_generator
- HITL 훅 (`approve_records` → `interrupt()`)
- feature flag로 병행
- **선행**: ADR-002 (0.4.12 vs 0.5.x GA)
- **예상**: 15~20 영업일

### Phase 6: Eval Harness (신설, 지속) ← **v2 사용자 제안 반영**

**목표**: 모델/프롬프트 변경 시 **자동 회귀 평가**.

**구조**:
```
agents/eval/
├─ scenarios/
│  ├─ agent_chat/
│  │  ├─ scenario_001_extract_records.yaml
│  │  ├─ scenario_002_clarify_ambiguous.yaml
│  │  └─ ...
│  ├─ review/
│  ├─ srs/
│  └─ record_extract/
├─ metrics/
│  ├─ schema_valid.py            출력이 Pydantic 스키마 검증 통과?
│  ├─ tool_selection.py          올바른 툴 선택?
│  ├─ tool_argument_validity.py  인자가 input_schema 통과?
│  ├─ side_effect_safety.py      DB 부작용이 기대 내에?
│  ├─ citation_integrity.py      [SOURCES] ref가 실제 존재?
│  └─ latency_cost.py            p95 latency, token cost
└─ runner.py                     pytest-style 실행 + score card
```

**score card 예시**:
```
Model: gpt-5.2 (Azure)
Scenarios: 120
┌─────────────────────────────┬──────────┬──────────┐
│ Metric                      │ Score    │ Baseline │
├─────────────────────────────┼──────────┼──────────┤
│ schema_valid                │ 98.3% ✓ │ 95.0%    │
│ tool_selection_accuracy     │ 91.7% ✓ │ 90.0%    │
│ tool_argument_validity      │ 94.2% ✓ │ 92.0%    │
│ side_effect_safety          │ 99.2% ✓ │ 98.0%    │
│ citation_integrity          │ 87.5% ⚠ │ 90.0%    │
│ p95_latency_ms              │ 4,320    │ 4,000    │
│ avg_cost_per_session_usd    │ 0.038    │ 0.042    │
└─────────────────────────────┴──────────┴──────────┘
```

**사용**:
- Phase 1~5 작업 중 **리팩토링 전/후 자동 비교**
- 모델 교체(gpt-5.2 → Claude Opus 4.7 등) 시 회귀 탐지
- CI에 포함하되 실비용 조절을 위해 주 1회 스케줄

**선행**: Phase 2 완료(Harness 구조 확정 후 시나리오 설계)

**예상**: 초기 구축 10 영업일 + 지속 유지

**전체 소요**: 9~14주 (Phase 0~5) + Phase 6 지속

---

## 10. 리팩토링 실행 로드맵

### 10.1 P0 — 즉시 (Week 0 ~ 2)

#### Week 0 (긴급, 1~2일)
- [ ] 🔴 **S-1 키 로테이션**: SRS/TC/OPENAI/MINIO 키 폐기·재발급
- [ ] 🔴 `backend/.env` 정리 — dev mock 값만
- [ ] `.env.example` 작성

#### Week 1 (인프라)
- [ ] `pydantic-settings` 추가
- [ ] `src/core/settings.py` (LLM / DB / MinIO / Auth 분리, SecretStr)
- [ ] 🔴 **S-2 TLS 가드**: `environment=prod` 시 TLS 강제 검증
- [ ] `llm_svc` `os.getenv` 제거, Settings 주입
- [ ] `python-dotenv` 추가, `psycopg2-binary` 제거
- [ ] `core/exceptions.py` 위계 분화 (DomainError → 6종 + LLM 하위 3종)
- [ ] `llm_svc` 싱글톤 → `lru_cache` + Depends
- [ ] loguru `bind_project` context manager

#### Week 2 (버그 + 에이전트 씨앗)
- [ ] **Bug-1**: `rag_svc`에 `is_active`/`status` 필터 추가
- [ ] **Bug-2**: `llm_svc.chat_completion(model=...)` 파라미터 + `model_resolver`
- [ ] **Bug-3**: `services/_common/display_id.py` + `FOR UPDATE` 락 (3곳)
- [ ] **Bug-4**: `section_svc.get_sections` write 제거, `bootstrap.ensure_default_sections`로 이동
- [ ] **Bug-5**: Tool args 검증 (`LLMToolArgsError`) — Phase 1과 묶음
- [ ] **Bug-6**: `delegated_to_frontend` 제거 → `pending_client` + LLM 루프 종료
- [ ] `agents/shared/{agent_config, json_agent, model_resolver}.py`
- [ ] `services/assist_svc.py` → `agents/assist/{refine,suggest,chat}.py`
- [ ] `prompts/agent/chat.py` → `prompts/agent/chat/sections/*`
- [ ] `services/agent_svc.py`의 TOOLS → `agents/tools/registry.py` (본격 분리는 P1)
- [ ] `LLMParseError`, `LLMToolArgsError` 도입
- [ ] `tests/conftest.py` LLM mock fixture
- [ ] LLM 프롬프트 인젝션 가드 (XML-wrap)
- [ ] MIME sniff, SSE 스택트레이스 제거

**P0 총 소요**: 10~14 영업일

### 10.2 P1 — 단기 (Week 3 ~ 7)

#### Service 분리 (2~3주)
- [ ] `services/agent_svc.py` → `agents/harness/*` + `agents/tools/*` + `agents/sse.py`
- [ ] `services/review_svc.py` → `services/review/*` (5분할)
- [ ] `services/record_svc.py` → `services/record/*` (7분할)
- [ ] `services/requirement_svc.py` → `services/requirement/*` (7분할)
- [ ] `services/knowledge_svc.py` → `services/knowledge/*` (5분할) + `tests/test_knowledge.py` 선행
- [ ] `utils/text_chunker.py` → `utils/chunking/*` 분리

#### Agent Quality (1~2주)
- [ ] Structured Output 9개 에이전트 적용 (또는 FuncCall fallback)
- [ ] temperature 표준화 (chat_assist 0.7 → 0.5)
- [ ] `project_svc.list_projects` N+1 제거 (selectinload)
- [ ] `tests/test_agent_harness.py` 신설 — ToolRegistry / Gateway / harness 단계별
- [ ] `tests/test_rag.py` — Bug-1 회귀 단언 포함
- [ ] `tests/test_srs.py`, `tests/test_knowledge.py`, `tests/test_document_processor.py` 신설
- [ ] 커버리지 목표: agent 계열 70%+, llm/rag/srs 60%+

**P1 총 소요**: 3~5주

### 10.3 P2 — 중기 (Week 8 ~ 15)

- [ ] Phase 3: Skills 재구성 + `SkillLoader`
- [ ] Phase 4: MCP 서버 파일럿 (read-only 도구부터)
- [ ] `services/{glossary,section,suggestion,srs,project,session}_svc.py` 분리
- [ ] `services/_common/{display_id,loaders}.py` 공통화
- [ ] UoW or 라우터-레벨 commit 검토 (ADR-005)
- [ ] Phase 5: Deep Agents 파일럿 (Extract → Review → SRS)
- [ ] **Phase 6: Eval Harness 초기 구축** — 시나리오 30~50건
- [ ] 커버리지 전체 70%+
- [ ] Alembic squash 검토 (초기 3~5개)
- [ ] **미연결 모듈 정리** (§6.8) — 팀 미팅으로 유지/제거 분류
- [ ] Redis 캐시 or Celery 태스크 큐 논의
- [ ] ADR 문서화 10건+

**P2 총 소요**: 5~8주

### 10.4 간트 한 장 (v2)

```
Week: 0  1  2 | 3  4  5  6  7 | 8  9 10 11 12 13 14 15
P0-보안 ██
P0-인프라  ██
P0-버그    ██████
P0-에이전트씨앗 ████
P1-분리            ██████████████
P1-SO+Test         ██████████████
P2-Skills                       ████████████████
P2-MCP                            ████████
P2-DeepAgents                           ████████████
P2-Eval Harness                         ████████████████████ (지속)
```

---

## 11. 부록

### 부록 A. 파일별 함수 전수 리스트 (핫스팟)

#### agent_svc.py
```
L33    TOOLS = [...]
L188   async def stream_chat
L317   try: args = json.loads(...) except: args = {}   ← Bug-5
L386   content: json.dumps({"status": "delegated_to_frontend"})  ← Bug-6
L443   async def _execute_backend_tool
L542   async def _fetch_records
L560   async def _fetch_knowledge_chunks
L595   async def _fetch_glossary
L608   async def _fetch_requirements
L629   def _sse_event
```

#### section_svc.py (Bug-4 위치)
```
L79    async def get_sections(db, project_id, type_filter=None):
L84        await _ensure_default_sections(db, project_id)   ← GET에서 write
L86        stmt = select(RequirementSection)...
```

(나머지 파일은 별첨 요청 시 생성)

### 부록 B. 의존성 그래프 (핵심)

```
routers/project       → services/project_svc → models/project
routers/requirement   → services/requirement_svc → models/requirement
routers/assist        → services/assist_svc → services/llm_svc
routers/review        → services/review_svc → services/llm_svc
routers/agent         → services/agent_svc → services/{record_svc, rag_svc, llm_svc}
routers/record        → services/record_svc → services/llm_svc
routers/knowledge     → services/knowledge_svc → services/document_processor
routers/srs           → services/srs_svc → services/llm_svc
routers/glossary      → services/glossary_svc → services/llm_svc
routers/session       → services/session_svc → services/suggestion_svc → services/llm_svc
```

`llm_svc`: 10개 서비스의 허브. Bug-2 해결 지점.

### 부록 C. 프롬프트 전문 요약

| 파일 | 구성 |
|---|---|
| `prompts/agent/chat.py` | 6 섹션 (knowledge/glossary/req/records/rules/tool_guide) |
| `prompts/assist/refine.py` | SYSTEM + TYPE_GUIDANCE |
| `prompts/assist/suggest.py` | SYSTEM + USER template |
| `prompts/assist/chat.py` | SYSTEM (EN) + JSON schema |
| `prompts/review/requirements.py` | SYSTEM (EN) + 이슈 분류 |
| `prompts/srs/generate.py` | SYSTEM + 레코드 ID 참조 규칙 |
| `prompts/glossary/extract.py` | SYSTEM + 동의어/약어 규칙 |
| `prompts/glossary/generate.py` | SYSTEM (최소) + JSON schema |
| `prompts/knowledge/chat.py` | SYSTEM + 출처 인용 규칙 |

### 부록 D. ADR 초안 (결정 사항 13건, v2 확장)

#### ADR-001: Azure OpenAI Structured Output 호환성
- **상태**: Proposed
- **맥락**: `api_version="2025-03-01-preview"` 고정. GPT-5.2 Structured Output 지원 미검증.
- **옵션 A**: Structured Output 사용 (최안)
- **옵션 B**: Function Calling `tool_choice="required"` (차선)
- **옵션 C**: JSON mode + Pydantic 검증
- **결정**: PoC 1일 후 결정
- **책임**: 소유자

#### ADR-002: Deep Agents 버전 전략
- **상태**: Proposed
- **옵션 A**: 0.4.12 즉시 Phase 5 파일럿
- **옵션 B**: 0.5.x GA 대기
- **제안**: P0~P1 도입 보류, Phase 5 시점 재판단

#### ADR-003: MCP 프레임워크
- **상태**: Proposed
- **옵션 A**: `fastapi-mcp` — 기존 FastAPI 마운트
- **옵션 B**: `fastmcp` — 독립 서버
- **제안**: A (공유 인증 필요)

#### ADR-004: agents/ vs services/ 원칙
- **상태**: Proposed
- **규칙**: "LLM 호출이 핵심이면 `agents/`, DB I/O가 핵심이면 `services/`"
- **경계**: `record_svc.extract_records` → `agents/record_extractor/` + `services/record/repository.py`

#### ADR-005: 트랜잭션 경계 전환
- **상태**: Proposed
- **옵션 A**: 이번 주기 UoW 전환
- **옵션 B**: v3로 분리
- **제안**: B

#### ADR-006: `services/_common/` 도입 시점
- **제안**: P1 말미 `display_id.py`만 우선 추출

#### ADR-007: 테스트 픽스처 선행 전략
- **제안**: LLM mock fixture를 P0에 포함. P1 분리는 fixture 완성 후

#### ADR-008: 리뷰 문서 분할
- **옵션 A**: 단일 `.md` — 현행
- **옵션 B**: 섹션별 분할
- **제안**: A

#### **ADR-009: `.env` 시크릿 관리 (v2 신설)**
- **상태**: Proposed, 긴급
- **맥락**: `backend/.env`에 운영 API 키로 보이는 값 존재
- **옵션 A**: 즉시 로테이션 + Vault 도입 (권장)
- **옵션 B**: 즉시 로테이션 + dev mock만 `.env` 유지, 운영은 배포 시 환경변수 주입
- **제안**: B (Vault는 P2)
- **책임**: 소유자 (1일 내)

#### **ADR-010: 프로젝트별 모델 해석기 (v2 신설)**
- **상태**: Proposed
- **맥락**: `ProjectSettings.llm_model`이 CRUD만 되고 실호출 반영 안 됨 (Bug-2)
- **옵션 A**: `chat_completion(model=...)` 파라미터 추가 + 호출자가 로드
- **옵션 B**: `agents/shared/model_resolver.py` + `AgentConfig` 생성 시 해석
- **제안**: B (구조적)

#### **ADR-011: 동시성 안전 display_id (v2 신설)**
- **상태**: Proposed
- **옵션 A**: PostgreSQL SEQUENCE (프로젝트·타입별)
- **옵션 B**: `FOR UPDATE` 락 (카운터 row)
- **옵션 C**: 재시도 (최대 3회)
- **제안**: B (명시적, 이식성)

#### **ADR-012: Tool Envelope 표준 (v2 신설)**
- **상태**: Proposed
- **맥락**: Bug-5(빈 args silent), Bug-6(delegated_to_frontend 거짓 신호) 해결
- **표준**: `ToolCall / ToolResult(status=success|pending_client|error) / ToolError` Pydantic
- **프런트 위임**: `status="pending_client"` + LLM 루프 종료

#### **ADR-013: Eval Harness 시나리오 데이터셋 (v2 신설)**
- **상태**: Proposed
- **맥락**: 모델·프롬프트 변경 시 회귀 감지 필요 (사용자 제안)
- **범위**: 12 에이전트 × 10 시나리오 ≈ 120 케이스 초기
- **평가축**: schema_valid / tool_selection_accuracy / tool_argument_validity / side_effect_safety / citation_integrity / latency_cost
- **책임**: 에이전트 담당자

### 부록 E. 용어집

| 용어 | 정의 |
|---|---|
| **Harness Engineering** | Agent = Model + Harness. 실행 환경 전체 설계 |
| **Agent Harness** | 본 프로젝트의 `src/agents/harness/` — intent/context/planner/executor/renderer 5단계 파이프라인 |
| **Tool Gateway** | 도구 실행 단일 진입점. registry 조회 + input_schema 검증 + envelope 반환 |
| **Tool Envelope** | `ToolCall / ToolResult / ToolError` 표준 DTO. status=success/pending_client/error |
| **Eval Harness** | 에이전트 회귀 평가 도구. 시나리오 + 메트릭으로 모델·프롬프트 변경 영향 측정 |
| **Context Engineering** | Harness 정보 계층 — 메모리/RAG/상태/도구 스키마 |
| **Skill (Claude Skills)** | YAML frontmatter + 자연어 instructions `.md`. on-demand 로드 |
| **MCP** | Model Context Protocol. Tool/Resource/Prompt 3요소 |
| **Structured Output** | JSON Schema 기반 출력 강제. OpenAI `response_format={"type":"json_schema"}` |
| **Deep Agents** | LangChain 상위 프레임워크. create_deep_agent + SubAgentMiddleware + TodoList + HITL |
| **UoW** | Unit of Work. DB 트랜잭션을 1급 객체로 관리 |
| **LLMParseError** | 도메인 예외 — LLM 응답 스키마 불일치 |
| **LLMToolArgsError** | 도메인 예외 — 도구 인자 파싱 실패 (Bug-5 해결) |
| **Progressive Disclosure** | Harness 원칙 — 필요한 것만 단계적 로드 |
| **Context Isolation** | 서브에이전트 독립 컨텍스트 — 메인 오염 방지 |

### 부록 F. 미연결 모듈 인벤토리 (v2 신설)

§6.8 참조. 액션 결정 대기:

| 모듈 | 연결 필요 시점 | 제거 조건 |
|---|---|---|
| `schemas/api/import_export.py` | Import/Export 기능 구현 시 | 로드맵 제외 확정 시 |
| `schemas/api/member.py` | Keycloak 통합 시 | 인증 전략 재정의 시 |
| `schemas/api/notification.py` | 알림 기능 도입 시 | 로드맵 제외 시 |
| `schemas/api/testcase.py` (111 LOC) | FR-TC Phase 구현 시 | - |
| `schemas/api/usecase.py` (79 LOC) | UCD 구현 시 | - |
| `schemas/api/user.py` | Keycloak 통합 시 | - |
| `schemas/api/version.py` | 버전 RPC 구현 시 | 로드맵 제외 시 |
| `integrations/jira/` | Jira 연동 시 | 로드맵 제외 시 |
| `integrations/polarion/` | Polarion 연동 시 | 로드맵 제외 시 |
| `deepagents` dep | Phase 5 | 최종 아키텍처 비채택 시 |

### 부록 G. Eval Harness 시나리오 후보 (v2 신설)

Phase 6 초기 구축용 시나리오 예시 (12 에이전트 × 3~10 케이스).

#### Agent Chat
- Scenario-AC-01: 명확한 요구사항 입력 → 구조화된 [REQUIREMENTS] 블록 생성
- Scenario-AC-02: 모호한 입력 → [CLARIFY] 질문지 생성
- Scenario-AC-03: 문서 기반 질문 → [SOURCES] 인용 포함 답변
- Scenario-AC-04: 레코드 CRUD 요청 → `create_record` 도구 호출
- Scenario-AC-05: **Bug-5 회귀**: 깨진 JSON arguments → LLMToolArgsError
- Scenario-AC-06: **Bug-6 회귀**: 프런트 위임 툴 → LLM 재호출 없이 종료
- Scenario-AC-07: **Bug-1 회귀**: 비활성 문서가 답변 근거에 없는지

#### Assist Refine
- Scenario-AR-01: 자유 문장 → SHALL 형식 refined_text
- Scenario-AR-02: 이미 정제된 문장 → 변경 최소
- Scenario-AR-03: 다국어(EN 입력) → EN 유지

#### Review
- Scenario-RV-01: 명백한 중복 요구사항 → duplicate issue 검출
- Scenario-RV-02: 충돌 요구사항(상충 SHALL) → conflict issue 검출
- Scenario-RV-03: 건강한 세트 → issues=[]

#### SRS Generate
- Scenario-SRS-01: 승인된 레코드 10건 → 섹션별 SRS, 레코드 ID 참조 포함

#### Record Extract
- Scenario-RE-01: PDF → 레코드 10건 이상 추출
- Scenario-RE-02: 짧은 문서 → 최소 1건
- Scenario-RE-03: 표 포함 → 표 내용 보존

#### Glossary Extract
- Scenario-GE-01: 문서 → 약어/동의어 포함 용어
- Scenario-GE-02: 기존 용어 중복 시 skip

#### Prompt Suggestions
- Scenario-PS-01: 빈 프로젝트 → 초기 설정 제안 5건
- Scenario-PS-02: 활성 프로젝트 → 다음 단계 제안

각 시나리오는 YAML로 정의:
```yaml
# scenarios/agent_chat/AC-07_rag_filter.yaml
id: AC-07
agent: agent_chat
setup:
  project: scenarios/fixtures/project_with_inactive_doc.sql
input:
  message: "문서 1.3절 내용 알려줘"
expected:
  schema_valid: true
  citation_integrity:
    disallowed_doc_ids: ["{{inactive_doc.id}}"]
  latency_p95_ms: 6000
```

---

## 닫는 말 (v2)

본 리뷰 v2는 **현 시점의 백엔드 실측 데이터 + 외부 피드백**을 통합한 스냅샷이자 **6~15주 리팩토링의 설계 기준**이다. v1 대비 변경점은 (1) 보안 긴급 사안의 별도 트랙화, (2) 기능 정합성 버그 6건의 구체화, (3) Agent Harness / Tool Gateway / Eval Harness 설계의 통합이다.

리팩토링 착수 전 부록 D의 **13개 ADR**에 소유자 응답을 받은 뒤, `PLAN.md`·`PROGRESS.md`에 P0 체크리스트(Week 0~2)를 반영하고 **Week 0 보안 핫픽스**부터 시작한다.

핵심 메시지를 한 번 더:

> Router–Service–Model 계층은 건강하다.
> 지금 필요한 것은
> **(0) 보안 핫픽스 (.env 로테이션 + TLS 강제),**
> **(1) 기능 정합성 버그 6건 수정,**
> **(2) 에이전트 레이어의 탄생 (Agent Harness + Tool Gateway),**
> **(3) 거대 함수 3종의 분해,**
> **(4) 설정·예외·DI 3종의 표준화,**
> **(5) Eval Harness로 회귀 탐지.**
>
> 이 6가지가 완료되면 Skills·MCP·Deep Agents 도입 비용이 낮아지고,
> 프롬프트가 규칙을 설명하던 구조에서 **하네스가 규칙을 강제**하는 구조로 이동한다.

— 끝 —
