# REFECTORING 작업 인수인계 노트 (2026-04-18)

## 0) 이번 세션 결론 요약
- 백엔드(`backend/src`) 전 파일을 기준으로 엔트리/모델/라우터/서비스/프롬프트/유틸을 재분석함.
- 테스트 상태: `cd backend && uv run pytest tests/` -> `93 passed, 3 skipped`.
- 현재 구조는 CRUD/RAG/SRS 기능은 안정적이나, 에이전트 경로(`agent_svc`)가 프롬프트 의존 + 오케스트레이션 집중으로 일관성/예측가능성이 낮음.
- 리팩토링 핵심은 "프롬프트 규칙"을 "하네스 강제"로 이동하는 것.

---

## 1) 백엔드 구조/기능 맵 (현재 구현)

### 1-1. 엔트리/인프라
- `backend/src/main.py`
  - FastAPI 앱 생성, 예외 핸들러/미들웨어/라우터 등록.
- `backend/src/core/database.py`
  - SQLAlchemy async engine/session (`get_db`) 제공.
- `backend/src/core/cors.py`
  - CORS 정책 주입.
- `backend/src/core/exceptions.py`
  - `AppException`, 글로벌 예외 핸들러.
- `backend/src/core/logging.py`
  - Loguru sink/포맷/파일 로깅 세팅.
- `backend/src/middleware/logging_middleware.py`
  - 요청/응답 로깅 + AppException/예외 응답 처리.
- `backend/src/middleware/logging_middleware_asgi.py`
  - Pure ASGI 로깅 미들웨어(현재 main에 미연결).

### 1-2. 모델
- `models/project.py`: `Project`, `ProjectSettings`.
- `models/requirement.py`: `RequirementSection`, `Requirement`, `RequirementVersion`, `DEFAULT_SECTIONS`.
- `models/record.py`: 추출 레코드.
- `models/knowledge.py`: 문서/청크/벡터(pgvector).
- `models/glossary.py`: 용어집.
- `models/review.py`: 리뷰 결과(JSONB, project unique).
- `models/srs.py`: SRS 문서/섹션.
- `models/session.py`: 세션/메시지.

### 1-3. 라우터 (엔드포인트 기능)
- `routers/project.py`
  - 프로젝트 CRUD, readiness, settings, prompt suggestions.
- `routers/requirement.py`
  - 요구사항 CRUD/선택/순서/버전저장.
- `routers/section.py`
  - 섹션 CRUD/활성화/순서/AI 섹션 추출.
- `routers/record.py`
  - 레코드 CRUD/순서/AI 레코드 추출(SSE 포함)/approve.
- `routers/glossary.py`
  - 용어 CRUD/생성/추출/approve.
- `routers/review.py`
  - 요구사항 리뷰 실행/최신 리뷰 조회.
- `routers/knowledge.py`
  - 문서 업로드/목록/재처리/미리보기/삭제/knowledge chat/chunk 조회.
- `routers/srs.py`
  - SRS 생성/조회/섹션수정/재생성.
- `routers/session.py`
  - 세션 생성/목록/조회/수정/삭제.
- `routers/assist.py`
  - refine/suggest/chat assist.
- `routers/agent.py`
  - Agent SSE chat.
- `routers/dev/chat.py`
  - 개발용 Responses API 실험 라우터.
- `routers/sample.py`
  - 샘플/헬스체크.

### 1-4. 서비스 (핵심 함수)
- `services/agent_svc.py`
  - `stream_chat`: 세션 히스토리 + RAG + 툴콜 루프 + SSE 출력.
  - `_execute_backend_tool`: 백엔드 툴 실행(create/update/delete/search record).
  - `_fetch_*`: records/knowledge/glossary/requirements 컨텍스트 로딩.
- `services/llm_svc.py`
  - OpenAI/Azure 클라이언트 생성, 모델 선택, `chat_completion` 공통 래퍼.
- `services/assist_svc.py`
  - 요구사항 정제/보완제안/대화형 추출.
- `services/review_svc.py`
  - conflict/duplicate 리뷰 실행 + 최신 결과 저장/조회.
- `services/record_svc.py`
  - 레코드 CRUD/정렬/검색 + 문서기반 추출 + approve + SSE 스트림.
- `services/requirement_svc.py`
  - 요구사항 CRUD/선택/정렬/버전 snapshot 저장.
- `services/section_svc.py`
  - 섹션 CRUD/정렬/활성화 + 문서기반 섹션 후보 추출.
- `services/project_svc.py`
  - 프로젝트/설정 CRUD + readiness 요약.
- `services/readiness_svc.py`
  - readiness 전용 계산(프로젝트 서비스와 중복 책임 존재).
- `services/knowledge_svc.py`
  - 문서 업로드/조회/재처리/미리보기/삭제/chunk-context.
- `services/document_processor.py`
  - 파일 파싱->청킹->임베딩->chunk 저장 background pipeline.
- `services/embedding_svc.py`
  - 임베딩 배치 호출.
- `services/rag_svc.py`
  - 벡터 유사도 검색 + knowledge chat 응답.
- `services/srs_svc.py`
  - 승인 레코드 기반 SRS 문서/섹션 생성.
- `services/session_svc.py`
  - 세션/메시지 저장 및 history 로딩.
- `services/suggestion_svc.py`
  - 프로젝트 컨텍스트 fingerprint + 질문카드 캐시 생성.
- `services/storage_svc.py`
  - MinIO 업로드/다운로드/삭제.
- `services/glossary_svc.py`
  - 용어 CRUD/요구사항 기반 생성/문서 기반 추출/approve.

### 1-5. 프롬프트
- `prompts/agent/chat.py`: Agent 정책/출력 규칙 대형 system prompt.
- `prompts/assist/*`: refine/suggest/chat JSON 응답 규칙.
- `prompts/review/requirements.py`: conflict/duplicate 리뷰 포맷.
- `prompts/srs/generate.py`: 섹션별 SRS 생성 프롬프트.
- `prompts/glossary/*`: 용어 생성/추출.
- `prompts/knowledge/chat.py`: 지식챗 답변 프롬프트.

### 1-6. 유틸
- `utils/json_parser.py`: 코드블록 제거 후 JSON 파싱.
- `utils/reorder.py`: 재정렬 ID 병합/검증.
- `utils/db.py`: `get_or_404`.
- `utils/text_chunker.py`: 마크다운 친화 청킹/토큰 분할.

### 1-7. 미연결/스텁성 코드
- `schemas/api/import_export.py`, `member.py`, `notification.py`, `testcase.py`, `usecase.py`, `user.py`, `version.py`는 현재 라우터 미연결.
- `integrations/jira`, `integrations/polarion`는 `__init__.py`만 존재.
- `agents/`, `agents/skills/`도 현재 실코드 없음.

---

## 2) 상세 리뷰 (우선순위 기준)

### [P0] 에이전트 일관성/예측가능성
1. Tool args 파싱 실패를 `{}`로 강행
- 근거: `backend/src/services/agent_svc.py:316-319`.
- 영향: 모델 출력이 살짝 깨져도 도구가 빈 인자로 실행되어 오동작 가능.

2. 프런트 위임 툴의 실제 실행 전/후 상태가 모델에 불명확
- 근거: `backend/src/services/agent_svc.py:383-387` (`delegated_to_frontend`).
- 영향: 모델이 실행 완료로 오인하고 다음 단계를 진행할 수 있음.

3. 구조화 출력이 프롬프트 강제 중심, 런타임 스키마 강제가 약함
- 근거: `backend/src/utils/json_parser.py:25-33` 단순 파싱 실패 -> 502.
- 영향: 모델/버전 변경 시 안정성 급락.

### [P0] 기능 정합성 리스크
4. RAG 검색이 문서 활성/완료 상태를 직접 필터링하지 않음
- 근거: `backend/src/services/rag_svc.py:43-47`.
- 영향: 비활성/실패 문서 chunk가 근거로 재사용될 위험.

5. 프로젝트 `llm_model` 설정이 주요 호출 경로에 반영되지 않음
- 근거: 저장은 `project_svc.update_project_settings` (`190-209`)에서 수행,
  실제 모델 선택은 `llm_svc._get_default_model` (`19-24`)의 env 우선.
- 영향: 프로젝트별 모델 전략이 실질적으로 무력화.

6. display_id 생성의 동시성 취약
- 근거: `requirement_svc._next_display_id` (`51-67`), `record_svc._next_display_id` (`107-117`).
- 영향: 경쟁 트랜잭션에서 충돌 가능. requirement는 unique로 예외, record는 중복 방어 약함.

### [P1] API/아키텍처 부채
7. GET 요청이 쓰기(side effect) 수행
- 근거: `section_svc.get_sections` (`79-85`) -> `_ensure_default_sections` -> `commit` (`73`).
- 영향: 조회 API 멱등성 저하, 캐시/모니터링 해석 난이도 증가.

8. 지원 파일타입 선언과 파서 구현이 불일치
- 근거: `knowledge_svc.ALLOWED_FILE_TYPES` (`20`)는 `pdf/txt/md`만 허용,
  `document_processor.parse_document` (`25-32`)는 `docx/pptx/xlsx` 분기 존재.
- 영향: 죽은 코드 또는 요구사항 누락 가능성.

9. readiness 계산 책임 중복
- 근거: `project_svc._get_readiness` (`55-81`) vs `readiness_svc.get_readiness` (`14-56`).
- 영향: 로직 드리프트/수정 누락 가능.

10. 미사용 대형 주석 코드 유지
- 근거: `review_svc.py:156-300`.
- 영향: 가독성 저하, 유지보수 비용 증가.

### [P1] 운영/보안 기본값
11. DB/MinIO 보안 기본값이 개발 친화 고정
- 근거: `core/database.py:13-17` (`ssl=False`), `storage_svc.py:22-27` (`secure=False`).
- 영향: 운영 환경으로 전파 시 보안사고 가능.

---

## 3) 에이전트 일관성 진화안 (Harness Engineering)

### 3-1. 목표
- 현재: "긴 시스템 프롬프트 + JSON 파싱".
- 목표: "하네스가 상태/도구/출력을 강제".

### 3-2. 제안 구조 (Phase-1)
`src/agents/harness/` 신설:
1. `contracts.py`
- `Intent`, `PlanStep`, `ToolCall`, `ToolResult`, `AgentTurnOutput` (Pydantic).

2. `intent_router.py`
- 유저 발화를 `qa / retrieve / record_cud / extract / srs_generate / clarify`로 분류.

3. `context_loader.py`
- records/glossary/requirements/rag를 목적별 최소 로딩.

4. `tool_gateway.py`
- 단일 registry + 실행 policy + 파라미터 검증.
- 프런트 위임도 동일 envelope(`status`,`payload`,`error`,`trace_id`,`source`) 사용.

5. `orchestrator.py`
- `plan -> execute -> summarize` 루프와 재시도 정책 소유.

6. `renderers.py`
- SSE 이벤트 직렬화 표준화(token/tool/progress/done/error).

### 3-3. Structured Output 적용 원칙
- 프롬프트에서 JSON 강요 대신, 응답 스키마를 코드로 선언하고 strict 검증.
- 파싱 실패 시 정책화:
  - 1차: 자동 복구 재시도(temperature 낮춤 + schema 재주입)
  - 2차: fallback renderer(사용자 친화 에러 + 재질문)
  - 3차: 안전중단(툴 실행 금지)

### 3-4. Tool Gateway 규칙
- `validate_input` -> `authorize` -> `execute` -> `normalize_output`.
- unknown tool / invalid args / partial args는 실행 금지, 명시적 에러 리턴.
- side-effect tool은 idempotency key와 audit log 필수.

### 3-5. 모델 편차 대응
- `ModelProfile` (capabilities: structured_output, tool_calling, context_limit, cost) 도입.
- 프로젝트 설정(`llm_model`) + 프로파일 기반 resolver 구현.
- 모델 변경 시 동일 golden dataset으로 회귀(Eval Harness) 자동 비교.

### 3-6. SKILL/MCP 관점 적용
- SKILL: 긴 정책 텍스트를 기능별 skill 문서로 분해(clarify rules, citation rules, tool policy).
- MCP: 외부 도구 연동 시 Tool Gateway 밖에서 직접 호출 금지, MCP server 경유로 일관화.
- 최종 원칙: "도구 호출 계약은 코드가, 언어 스타일은 프롬프트가 담당".

---

## 4) 다음 세션 TODO (실행 순서)
1. `agent_svc` 분해 시작
- `stream_chat`에서 하네스 오케스트레이션 호출만 남기기.

2. `ToolGateway` + DTO 우선 구현
- `ToolCall/ToolResult` 스키마 및 validator 도입.

3. `parse_llm_json` 대체 경로 추가
- strict schema + typed parser + retry 정책.

4. RAG 정합성 수정
- `rag_svc.search_similar_chunks`에서 `KnowledgeDocument` join 후 active/completed 필터 강제.

5. project model resolver 연결
- `ProjectSettings.llm_model`을 `chat_completion` 입력에 연결.

6. 테스트 추가
- `tests/services/test_agent_harness.py` 신설.
- 케이스: invalid args, unknown tool, delegated tool ack, schema retry, safety abort.

---

## 5) 리서치 근거 링크 (공식 문서 위주)
- OpenAI Harness Engineering (2026-02-11)
  - https://openai.com/index/harness-engineering/
- OpenAI Structured Outputs Guide
  - https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Function Calling Guide
  - https://developers.openai.com/api/docs/guides/function-calling
- OpenAI Agent Evals Guide
  - https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI Guardrails/Human Review
  - https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
- LangChain Structured Output (create_agent response_format)
  - https://docs.langchain.com/oss/python/langchain/structured-output
- LangGraph Overview (durable execution, HITL, stateful orchestration)
  - https://docs.langchain.com/oss/python/langgraph/overview
- MCP Specification (latest 2025-11-25)
  - https://modelcontextprotocol.io/specification/

---

## 6) 빠른 실행 커맨드
- 백엔드 테스트:
  - `cd backend && uv run pytest tests/`
- 커버리지:
  - `cd backend && uv run pytest --cov=src --cov-report=term-missing -q`
- 핵심 서비스만 빠르게 확인:
  - `cd backend && uv run pytest tests/services -q`

---

## 7) 다음 세션 시작 프롬프트
"`REFECTORING.md` 기준으로 Phase-1(Agent Harness 뼈대) 구현을 시작해줘. 기존 API 계약(`routers/*`)은 유지하고 `agent_svc` 내부 오케스트레이션을 `src/agents/harness/`로 분리해줘. 먼저 `contracts.py`, `tool_gateway.py`, `orchestrator.py`를 만들고, `stream_chat`은 새 하네스를 호출하도록 연결해줘. 테스트(`test_agent_harness.py`)도 함께 추가해줘."
