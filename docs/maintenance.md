# Maintenance

이 문서는 AISE+ 코드베이스를 유지보수할 때 자주 확인해야 하는 변경 지점, 검증 명령, 장애 확인 순서를 정리한다. 대상 독자는 저장소를 처음 인수받은 신입 개발자이며, 코드와 설정 파일에서 확인한 내용만 확정 정보로 적는다. 운영 서버, 클라우드 계정, 저장소에 없는 CI/CD 운영 절차, 비밀 관리, 장애 대응 기준처럼 저장소만으로 확정할 수 없는 내용은 `확인 필요`로 표시한다.

## 관련 파일

| 영역 | 주요 파일 | 유지보수 시 확인할 내용 |
| --- | --- | --- |
| 실행/환경 | `start-dev.sh`, `start-local.sh`, `docker-compose.yml`, `docker-compose.preview.yml`, `.env.prod.example`, `.env.preview.example` | 로컬/컨테이너 포트, 서비스명, 환경변수, PostgreSQL/MinIO/Redis 연결값 |
| 백엔드 진입점 | `backend/src/main.py`, `backend/src/routers/__init__.py`, `backend/src/core/cors.py`, `backend/src/core/exceptions.py`, `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py` | FastAPI 앱 조립, 라우터 등록, CORS, 전역 예외, 요청 로깅 |
| DB/마이그레이션 | `backend/src/core/database.py`, `backend/alembic/env.py`, `backend/alembic/versions/*.py`, `backend/src/models/*.py`, `backend/tests/conftest.py` | `DATABASE_URL`, Alembic 모델 import, 테이블/제약 변경, 테스트 DB 격리 |
| 프로젝트/도메인 데이터 | `backend/src/models/project.py`, `backend/src/models/requirement.py`, `backend/src/models/knowledge.py`, `backend/src/models/artifact.py`, `backend/src/services/*_svc.py` | 프로젝트 cascade, 요구사항/섹션, 지식 문서, 산출물 버전/PR 상태 전이 |
| AI/RAG/문서 처리 | `backend/src/services/llm_svc.py`, `backend/src/services/embedding_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/rag_svc.py`, `backend/src/services/storage_svc.py`, `backend/src/utils/text_chunker.py`, `backend/src/prompts/*` | LLM provider, 임베딩 차원, 문서 파싱/청킹, MinIO 원본 파일, RAG 출처 |
| Agent/HITL/SSE | `backend/src/agents/registry.py`, `backend/src/orchestration/graph.py`, `backend/src/orchestration/supervisor.py`, `backend/src/orchestration/retrieval_gate.py`, `backend/src/services/hitl_state_svc.py`, `backend/src/schemas/events.py`, `docs/events.md` | 에이전트 등록, 명시적 산출물 생성 라우팅, LangGraph checkpoint, SSE 이벤트 계약, HITL 상태 |
| 프론트엔드 API/상태 | `frontend/src/lib/api.ts`, `frontend/next.config.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `frontend/src/services/*-service.ts`, `frontend/src/stores/*.ts`, `frontend/src/types/*.ts` | API base/rewrite, SSE proxy, 도메인별 서비스, Zustand 상태, 타입 계약 |
| 프론트엔드 UI | `frontend/src/app/(main)`, `frontend/src/components`, `frontend/src/config`, `frontend/src/constants`, `frontend/src/app/globals.css` | 화면 라우팅, 레이아웃, 프로젝트/채팅/아티팩트 컴포넌트, 디자인 토큰 |
| 검증 | `backend/tests`, `backend/scripts/setup_test_db.sh`, `backend/scripts/smoke_langgraph_chat.py`, `frontend/package.json`, `frontend/eslint.config.mjs` | pytest, 테스트 DB 준비, LangGraph smoke, lint/build 스크립트 |
| 배포 보조 | `backend/Dockerfile`, `frontend/Dockerfile`, `deploy.sh`, `deploy/preview.sh`, `docker-compose.yml`, `docker-compose.preview.yml` | 컨테이너 빌드, compose 배포 명령, preview/prod 배포 보조 명령 |

위 표는 유지보수 이슈가 들어왔을 때 처음 열어볼 대표 파일이다. 더 구체적인 작업 단위별 파일은 아래 `유지보수 포인트별 코드/설정 파일 매핑`과 `변경 유형별 체크리스트`에서 다시 연결한다. 이 문서에 적힌 경로 중 `*.py`, `*.ts`, `*.tsx`, `*.yml`, `*.sh`, `.env.*.example`은 저장소에서 확인 가능한 코드 또는 설정 근거이며, 실제 운영 secret 값이나 계정 정보처럼 저장소에 없어야 하는 항목은 경로 대신 `확인 필요`로 분리한다.

## 주요 코드 위치와 모듈별 책임

처음 유지보수 이슈를 맡으면 파일 이름만으로 책임 범위를 추측하지 말고 아래 표에서 "어느 계층의 책임인가"를 먼저 나눈다. 이 코드베이스는 화면, API client, 백엔드 router, service, model, migration, test가 같은 도메인 이름으로 반복되는 구조라서 한 계층만 수정하면 계약 불일치가 생기기 쉽다.

| 모듈/디렉터리 | 책임 | 자주 여는 파일 | 같이 확인할 파일 |
| --- | --- | --- | --- |
| 루트 실행/배포 설정 | 로컬 실행, compose 기반 통합 실행, preview/prod 배포 보조, 예시 환경변수 관리 | `start-dev.sh`, `start-local.sh`, `docker-compose.yml`, `docker-compose.preview.yml`, `deploy.sh`, `deploy/preview.sh`, `.env.prod.example`, `.env.preview.example` | `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/next.config.ts`, `backend/src/core/database.py` |
| 백엔드 앱 조립 | FastAPI 앱 생성, 로깅/CORS/예외 미들웨어 등록, built-in agent 로드, router include | `backend/src/main.py`, `backend/src/routers/__init__.py`, `backend/src/core/cors.py`, `backend/src/core/exceptions.py`, `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py` | 신규 router를 추가한 경우 `backend/src/routers/*.py`, `backend/tests/test_*router*.py` 또는 도메인 테스트 |
| 백엔드 router 계층 | HTTP URL, request/response schema, dependency injection, status code, background task 연결 | `backend/src/routers/project.py`, `backend/src/routers/requirement.py`, `backend/src/routers/knowledge.py`, `backend/src/routers/agent.py`, `backend/src/routers/artifact.py`, `backend/src/routers/srs.py`, `backend/src/routers/design.py`, `backend/src/routers/impact.py`, `backend/src/routers/session.py` | 같은 도메인의 `backend/src/schemas/api/*.py`, `backend/src/services/*_svc.py`, `frontend/src/services/*-service.ts` |
| 백엔드 service 계층 | 비즈니스 규칙, DB 트랜잭션, 외부 API/MinIO/LLM 호출, 상태 전이, 도메인 오류 처리 | `backend/src/services/project_svc.py`, `backend/src/services/requirement_svc.py`, `backend/src/services/knowledge_svc.py`, `backend/src/services/artifact_svc.py`, `backend/src/services/impact_svc.py`, `backend/src/services/llm_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/rag_svc.py` | 같은 도메인의 router/schema/model/test, 외부 의존 설정인 `.env.*.example`, `docker-compose.yml` |
| 백엔드 model/migration 계층 | SQLAlchemy 모델, FK/cascade/check constraint, pgvector 컬럼, Alembic schema 변경 | `backend/src/models/*.py`, `backend/alembic/env.py`, `backend/alembic/versions/*.py`, `backend/tests/conftest.py` | `backend/src/schemas/api/*.py`, `backend/src/services/*_svc.py`, `backend/scripts/setup_test_db.sh` |
| Agent/오케스트레이션 계층 | built-in agent 등록, supervisor routing, LangGraph 실행, HITL interrupt, SSE 이벤트 생성 | `backend/src/agents/registry.py`, `backend/src/agents/*.py`, `backend/src/orchestration/graph.py`, `backend/src/orchestration/supervisor.py`, `backend/src/orchestration/retrieval_gate.py`, `backend/src/orchestration/state.py`, `backend/src/services/hitl_state_svc.py`, `backend/src/schemas/events.py` | `frontend/src/types/agent-events.ts`, `frontend/src/hooks/useChatStream.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `docs/events.md` |
| Prompt/LLM 생성 계층 | SRS, Design, Test Case, Review, Knowledge QA용 prompt와 생성 결과 파싱 | `backend/src/prompts/srs/generate.py`, `backend/src/prompts/design/generate.py`, `backend/src/prompts/testcase/generate.py`, `backend/src/prompts/knowledge/chat.py`, `backend/src/prompts/review/requirements.py`, `backend/src/services/llm_svc.py`, `backend/src/utils/json_parser.py` | 생성 agent/service 테스트인 `backend/tests/test_srs_generator_agent.py`, `backend/tests/test_design_generator_agent.py`, `backend/tests/test_testcase_generator_agent.py` |
| 지식/RAG/문서 처리 계층 | 업로드 원본 저장, 문서 파싱, chunking, embedding, 검색 후보 추출, 출처 반환 | `backend/src/services/knowledge_svc.py`, `backend/src/services/storage_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/embedding_svc.py`, `backend/src/services/query_rewriter.py`, `backend/src/services/rag_svc.py`, `backend/src/utils/text_chunker.py`, `backend/src/models/knowledge.py` | `backend/tests/test_rag_isolation.py`, `backend/tests/test_query_rewriter.py`, `backend/tests/test_text_chunker.py`, `frontend/src/services/knowledge-service.ts` |
| 프론트엔드 라우트/레이아웃 | Next.js App Router 화면 진입점, 프로젝트/Agent/Workflow/Dashboard 페이지, 공통 layout | `frontend/src/app/(main)/layout.tsx`, `frontend/src/app/(main)/page.tsx`, `frontend/src/app/(main)/projects/page.tsx`, `frontend/src/app/(main)/projects/[id]/page.tsx`, `frontend/src/app/(main)/projects/[id]/requirements/page.tsx`, `frontend/src/app/(main)/agent/[[...sessionId]]/page.tsx`, `frontend/src/app/(main)/workflow/page.tsx` | 관련 도메인의 `frontend/src/components/*`, `frontend/src/services/*-service.ts`, `frontend/src/stores/*.ts` |
| 프론트엔드 API client/service 계층 | API base URL, JSON 오류 처리, 401 redirect, 도메인별 REST 호출, SSE proxy | `frontend/src/lib/api.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `frontend/src/services/project-service.ts`, `frontend/src/services/requirement-service.ts`, `frontend/src/services/knowledge-service.ts`, `frontend/src/services/agent-service.ts`, `frontend/src/services/artifact-service.ts`, `frontend/src/services/impact-service.ts` | 백엔드 `backend/src/routers/*.py`, `backend/src/schemas/api/*.py`, 타입 정의 `frontend/src/types/*.ts` |
| 프론트엔드 상태/store 계층 | 프로젝트 선택, 채팅, 산출물, staging/PR, 패널/오버레이/toast 상태 유지 | `frontend/src/stores/project-store.ts`, `frontend/src/stores/chat-store.ts`, `frontend/src/stores/artifact-store.ts`, `frontend/src/stores/artifact-record-store.ts`, `frontend/src/stores/staging-store.ts`, `frontend/src/stores/panel-store.ts`, `frontend/src/stores/overlay-store.ts`, `frontend/src/hooks/useProjectScopedReset.ts` | 해당 store를 사용하는 `frontend/src/components/**`, API service, `frontend/src/types/*.ts` |
| 프론트엔드 UI 컴포넌트 | 채팅, 프로젝트, 요구사항, 지식, 산출물 workspace, 공통 layout/overlay/ui 표현 | `frontend/src/components/chat/*`, `frontend/src/components/projects/*`, `frontend/src/components/requirements/*`, `frontend/src/components/artifacts/*`, `frontend/src/components/artifacts/workspace/*`, `frontend/src/components/layout/*`, `frontend/src/components/overlay/*`, `frontend/src/components/ui/*` | 관련 route, service, store, `frontend/src/config/*.ts`, `frontend/src/constants/*.ts`, `frontend/src/app/globals.css` |
| 테스트/검증 | 테스트 DB 준비, backend domain/unit/integration test, Agent smoke, frontend lint/build | `backend/tests/conftest.py`, `backend/tests/test_*.py`, `backend/scripts/setup_test_db.sh`, `backend/scripts/smoke_langgraph_chat.py`, `frontend/package.json`, `frontend/eslint.config.mjs` | 변경한 모듈의 router/service/model/component와 직접 연결되는 테스트 |

작업별 1차 진입점은 다음 기준으로 고른다.

| 들어온 요청 | 먼저 볼 위치 | 이유 | 최소 검증 |
| --- | --- | --- | --- |
| "API 응답이 이상하다" | `frontend/src/services/*-service.ts`와 `backend/src/routers/*.py` | 프론트엔드가 기대하는 URL/body와 백엔드 schema/status가 어긋났는지 가장 빨리 확인할 수 있다. | `cd backend && uv run pytest tests/test_*.py`, `cd frontend && pnpm lint` |
| "DB 컬럼/상태값을 바꿔야 한다" | `backend/src/models/*.py`, `backend/alembic/versions/*.py`, `backend/tests/conftest.py` | 모델만 바꾸면 migration과 테스트 cleanup이 따라오지 않아 로컬/CI가 깨질 수 있다. | `cd backend && uv run alembic upgrade head`, 관련 pytest |
| "Agent 답변/라우팅이 이상하다" | `backend/src/orchestration/graph.py`, `backend/src/orchestration/supervisor.py`, `backend/src/agents/registry.py` | 명시적 산출물 라우팅, supervisor routing, agent 등록 목록이 답변 경로를 결정한다. | `cd backend && uv run pytest tests/test_orchestration.py tests/test_agent_registry.py` |
| "채팅 스트리밍이 끊긴다" | `backend/src/routers/agent.py`, `frontend/src/app/api/v1/agent/chat/route.ts`, `frontend/src/hooks/useChatStream.ts`, `backend/src/schemas/events.py` | 백엔드 SSE 생성, Next.js proxy, 프론트 이벤트 파싱 중 어디서 끊기는지 나눠 볼 수 있다. | `cd backend && uv run pytest tests/test_agents_router.py tests/test_hitl_interrupt.py`, 필요 시 smoke script |
| "문서 업로드/RAG가 실패한다" | `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/storage_svc.py`, `backend/src/services/rag_svc.py` | 원본 저장, background parsing, embedding, 검색 후보 필터가 한 흐름으로 이어진다. | `cd backend && uv run pytest tests/test_rag_isolation.py tests/test_text_chunker.py` |
| "SRS/Design/TC 생성 품질을 바꾼다" | `backend/src/prompts/*/generate.py`, `backend/src/services/*_svc.py`, `backend/src/agents/*_generator.py` | prompt, 생성 service, agent 이벤트가 함께 결과 형식을 만든다. | 생성 agent 테스트와 `backend/src/utils/json_parser.py` 영향 확인 |
| "산출물 버전/PR/영향도 문제가 있다" | `backend/src/models/artifact.py`, `backend/src/services/artifact_svc.py`, `backend/src/services/artifact_record_svc.py`, `backend/src/services/impact_svc.py`, `frontend/src/components/artifacts/workspace/*` | working copy, version snapshot, open PR, lineage, UI staging 상태가 같이 움직인다. | `cd backend && uv run pytest tests/test_artifact_svc.py tests/test_artifact_record.py tests/test_artifact_generation_routing.py` |
| "화면 상태가 프로젝트 전환 후 남아 있다" | `frontend/src/stores/*.ts`, `frontend/src/hooks/useProjectScopedReset.ts`, 관련 page/component | project-scoped store reset 누락일 가능성이 높다. | `cd frontend && pnpm lint && pnpm build`, 프로젝트 전환 수동 확인 |
| "배포 후 접속이 안 된다" | `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/next.config.ts`, `backend/src/core/cors.py` | service name, port, env, CORS, rewrite 문제를 분리할 수 있다. | `docker compose config`, `docker compose logs backend frontend`, health curl |

## 기본 유지보수 원칙

AISE+는 Next.js 프론트엔드와 FastAPI 백엔드가 분리되어 있고, 백엔드는 라우터, 서비스, 모델, 에이전트/오케스트레이션 계층으로 나뉜다. 기능을 고칠 때는 화면 컴포넌트에서 바로 백엔드 구현으로 뛰어가기보다 다음 순서로 추적한다.

1. 프론트엔드 화면: `frontend/src/app/(main)` 또는 `frontend/src/components`에서 사용자 동작을 찾는다.
2. 프론트엔드 서비스: `frontend/src/services/*-service.ts`에서 호출 API, 요청 body, 응답 타입을 확인한다.
3. 백엔드 라우터: `backend/src/routers/*.py`에서 URL, Pydantic 스키마, DB 세션 주입 방식을 확인한다.
4. 백엔드 서비스: `backend/src/services/*_svc.py`에서 실제 비즈니스 규칙, commit/rollback, 외부 API 호출을 확인한다.
5. 모델/마이그레이션: `backend/src/models/*.py`와 `backend/alembic/versions/*.py`에서 테이블, 제약, 인덱스, cascade를 확인한다.
6. 테스트: 변경한 기능과 같은 이름의 `backend/tests/test_*.py`를 우선 실행하고, 프론트엔드는 `pnpm lint`와 필요 시 `pnpm build`를 실행한다.

공통 검증 명령:

```bash
# 백엔드 테스트 DB 최초 준비
cd backend
./scripts/setup_test_db.sh

# 백엔드 전체 테스트
uv sync
uv run pytest

# 백엔드 특정 테스트
uv run pytest tests/test_project.py
uv run pytest tests/test_orchestration.py
uv run pytest tests/test_artifact_svc.py

# 프론트엔드 정적 검사와 빌드
cd ../frontend
pnpm install
pnpm lint
pnpm build

# 컨테이너 구성 확인
cd ..
docker compose config
docker compose up -d postgres minio redis
```

공통 빌드/패키징 명령:

```bash
# 프론트엔드 production build
cd frontend
pnpm install --frozen-lockfile
pnpm build

# 루트에서 backend/frontend Docker 이미지 빌드
cd ..
docker build -t aise2-backend:local ./backend
docker build -t aise2-frontend:local ./frontend

# compose 기준 패키징 확인
docker compose build
docker compose -f docker-compose.preview.yml build
```

| 명령 | 유지보수 시 확인할 것 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- |
| `pnpm build` | 화면, API service, 타입, Next.js rewrite 변경이 production build에서 깨지지 않는지 확인한다. | `frontend/package.json`, `frontend/next.config.ts`, `frontend/src/app`, `frontend/src/services` | 운영/preview별 `BACKEND_URL` 표준 값 |
| `docker build -t aise2-backend:local ./backend` | `uv.lock` 기준 런타임 의존성과 FastAPI entrypoint가 이미지로 패키징되는지 확인한다. | `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock` | Python 3.14 RC 운영 사용 여부 |
| `docker build -t aise2-frontend:local ./frontend` | Next.js standalone 산출물이 runner 이미지로 복사되는지 확인한다. | `frontend/Dockerfile`, `frontend/package.json`, `frontend/next.config.ts` | `npm ci`와 pnpm 정책 불일치 해결 기준 |
| `docker compose build` | backend/frontend service build context와 build args가 깨지지 않았는지 확인한다. | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | image registry, tag, cache 정책 |
| `docker compose -f docker-compose.preview.yml build` | preview 포트/볼륨/환경 파일 분리 상태로 패키징되는지 확인한다. | `docker-compose.preview.yml`, `deploy/preview.sh` | preview Redis 대상과 secret 주입 방식 |

확인 필요:

- 현재 워크트리에서 `.github/workflows`, `Jenkinsfile`, `.gitlab-ci.yml` 같은 CI/CD 파이프라인 파일은 확인되지 않는다. 실제 필수 테스트 게이트와 자동 배포 절차는 확인 필요다.
- 운영 배포 전 승인자, 코드 리뷰 기준, release branch 전략은 확인 필요다.
- 운영 장애 등급, 대응 시간, 온콜 체계, 알림 채널은 확인 필요다.

## 핵심 제약사항, 의존성, 변경 리스크

아래 표는 유지보수 작업을 시작하기 전에 반드시 확인해야 하는 제약사항, 외부/내부 의존성, 변경 리스크를 한곳에 모은 것이다. 코드에서 확인되는 제약은 근거 파일을 함께 적고, 운영 정책이나 계정처럼 저장소에서 확인할 수 없는 내용은 `확인 필요`로 분리한다.

| 영역 | 코드에서 확인되는 제약사항 | 주요 의존성 | 변경 리스크 | 먼저 확인할 파일 | 최소 검증 |
| --- | --- | --- | --- | --- | --- |
| 프론트엔드 패키지 관리 | `frontend/package.json`은 `packageManager: pnpm@9.15.0`, `engines.node >=20`, `preinstall: npx only-allow pnpm`을 명시한다. | Node 20 이상, pnpm lockfile, Next.js 16 standalone build | `npm install` 또는 `npm ci` 기준으로 스크립트/Dockerfile을 바꾸면 로컬 설치와 컨테이너 빌드 정책이 어긋날 수 있다. | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/Dockerfile`, `start-local.sh` | `cd frontend && pnpm install --frozen-lockfile && pnpm lint && pnpm build` |
| 프론트엔드 API 연결 | `NEXT_PUBLIC_API_URL`이 없으면 `/api`를 호출하고, `frontend/next.config.ts`가 `BACKEND_URL`로 rewrite한다. Agent SSE는 별도 Route Handler가 직접 중계한다. | `BACKEND_URL`, Next.js rewrite, `frontend/src/app/api/v1/agent/chat/route.ts`, 백엔드 `/api/v1` | rewrite와 SSE proxy를 통합하거나 경로를 바꾸면 일반 REST는 동작해도 streaming token 표시가 지연되거나 끊길 수 있다. | `frontend/src/lib/api.ts`, `frontend/next.config.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `backend/src/routers/agent.py` | `pnpm build`, `curl -I http://localhost:4000`, Agent stream 수동 확인 |
| 백엔드 런타임 | `backend/Dockerfile`은 `python:3.14-rc-slim`, `uv sync --frozen --no-dev`, `uvicorn src.main:app --port 8081`에 의존한다. | `backend/pyproject.toml`, `backend/uv.lock`, FastAPI, SQLAlchemy async, Alembic | Python RC 버전, uv lock, entrypoint를 바꾸면 로컬 테스트는 통과해도 이미지 빌드나 운영 런타임에서 의존성 해석이 달라질 수 있다. | `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/src/main.py` | `docker build -t aise2-backend:local ./backend`, `cd backend && uv run pytest` |
| DB schema와 migration | 모델 변경은 SQLAlchemy model, Pydantic schema, Alembic migration, 테스트 cleanup을 함께 갱신해야 한다. | PostgreSQL, pgvector, Alembic, `backend/tests/conftest.py` | migration 없이 모델만 바꾸면 신규 환경과 기존 DB가 갈라지고, 테스트 cleanup 누락 시 FK/cascade 때문에 테스트 간 데이터가 섞일 수 있다. | `backend/src/models/*.py`, `backend/alembic/versions/*.py`, `backend/alembic/env.py`, `backend/tests/conftest.py` | `cd backend && uv run alembic upgrade head && uv run pytest` |
| pgvector/임베딩 | `KnowledgeChunk.embedding`은 `Vector(1536)`이고 임베딩 서비스는 100개 단위 batch 흐름에 의존한다. | 외부 embedding API, PostgreSQL pgvector, `knowledge_chunks` 데이터 | 임베딩 모델이나 차원을 바꾸면 기존 vector 데이터와 검색 로직이 동시에 깨질 수 있어 재임베딩/마이그레이션 계획이 필요하다. | `backend/src/models/knowledge.py`, `backend/src/services/embedding_svc.py`, `backend/src/services/rag_svc.py`, `backend/alembic/versions/a1b2c3d4e5f6_add_knowledge_documents_and_chunks.py` | `uv run pytest tests/test_rag_isolation.py tests/test_text_chunker.py`, 재임베딩 정책 확인 필요 |
| Artifact 버전/PR 상태 | `working_status`는 `clean`, `dirty`, `staged`만 허용되고, `clean`은 `current_version_id`, `staged`는 `open_pr_id`가 필요하다. open PR은 artifact당 최대 1개다. | PostgreSQL check constraint, partial unique index, artifact service, staging UI | 상태 전이를 우회하거나 version을 직접 수정하면 PR merge, 영향도 계산, current version 표시가 깨질 수 있다. | `backend/src/models/artifact.py`, `backend/src/services/artifact_svc.py`, `backend/src/services/impact_svc.py`, `frontend/src/stores/staging-store.ts` | `uv run pytest tests/test_artifact_svc.py tests/test_artifact_record.py tests/test_artifact_generation_routing.py` |
| 문서 원본과 청크 정합성 | 지식 문서 원본은 MinIO에, 문서 메타데이터/청크/embedding은 PostgreSQL에 저장된다. 처리 실패는 `failed` 상태와 `error_message`로 남긴다. | MinIO/S3 API, FastAPI `BackgroundTasks`, document parser, embedding API | DB만 삭제하거나 MinIO 객체만 삭제하면 재처리, 미리보기, RAG 출처 조회가 orphan 상태가 될 수 있다. | `backend/src/services/storage_svc.py`, `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/models/knowledge.py` | `uv run pytest tests/test_rag_isolation.py tests/test_text_chunker.py`, 샘플 업로드/재처리 수동 확인 |
| LLM/프롬프트 출력 계약 | SRS/Design/Test Case/Review/Glossary 생성은 prompt, LLM service, JSON parser, Pydantic schema, artifact 저장 구조가 함께 맞아야 한다. | Azure OpenAI 또는 OpenAI, LiteLLM, prompt templates, `json_parser.py` | prompt만 바꾸면 LLM 출력 형식이 달라져 schema 검증 실패, 부분 생성, skipped section 증가가 발생할 수 있다. | `backend/src/services/llm_svc.py`, `backend/src/prompts/*`, `backend/src/utils/json_parser.py`, `backend/src/services/srs_svc.py`, `backend/src/services/design_svc.py`, `backend/src/services/testcase_svc.py` | 생성 agent/service pytest, 실패 응답 수동 확인, provider/model 정책 확인 필요 |
| Agent registry와 라우팅 | built-in agent는 directory scan이 아니라 `registry.py`의 명시 목록 import로 등록된다. 명시적 산출물 생성 라우팅은 `_GENERATION_TERMS`와 `_ARTIFACT_GENERATION_ROUTES`를 먼저 통과한다. | LangGraph, agent registry, supervisor, retrieval gate | 새 Agent 파일만 추가하고 registry에 넣지 않으면 운영에서 발견되지 않는다. 키워드 변경은 RAG 질문과 생성 명령의 라우팅 오분류를 만들 수 있다. | `backend/src/agents/registry.py`, `backend/src/orchestration/graph.py`, `backend/src/orchestration/supervisor.py`, `backend/src/orchestration/retrieval_gate.py` | `uv run pytest tests/test_agent_registry.py tests/test_orchestration.py tests/test_artifact_generation_routing.py` |
| HITL/checkpoint/SSE | `LANGGRAPH_CHECKPOINT_URL`이 없으면 `MemorySaver`, 있으면 PostgreSQL checkpointer를 사용한다. SSE 이벤트 스키마는 백엔드/프론트/문서가 함께 맞아야 한다. | PostgreSQL checkpoint, `hitl_requests`, Next.js SSE proxy, 브라우저 EventSource/fetch stream | 운영에서 메모리 checkpointer를 쓰면 프로세스 재시작 후 HITL 재개 보장이 약해진다. 이벤트 payload 변경 누락은 프론트 채팅 UI 오류로 이어진다. | `backend/src/orchestration/graph.py`, `backend/src/services/hitl_state_svc.py`, `backend/src/schemas/events.py`, `frontend/src/types/agent-events.ts`, `frontend/src/hooks/useChatStream.ts`, `docs/events.md` | `uv run pytest tests/test_agents_router.py tests/test_hitl_interrupt.py`, SSE 수동 확인, 프록시 timeout 확인 필요 |
| 프론트엔드 상태 격리 | 프로젝트별 화면 상태는 여러 Zustand store와 `useProjectScopedReset`에 나뉘어 있다. | `project-store`, `chat-store`, `artifact-store`, `staging-store`, route params | 프로젝트 전환 시 reset 누락이 있으면 이전 프로젝트의 산출물, PR, 채팅 pending 상태가 새 프로젝트 화면에 남을 수 있다. | `frontend/src/stores/*.ts`, `frontend/src/hooks/useProjectScopedReset.ts`, `frontend/src/app/(main)/projects/[id]/layout.tsx`, `frontend/src/components/artifacts/workspace/*` | `pnpm lint && pnpm build`, 프로젝트 전환/Artifact workspace 수동 확인 |
| Docker Compose 네트워크 | backend는 compose 서비스명 `postgres`, `redis`, `minio`를 사용하고 frontend는 `backend:8081`에 접근한다. | `docker-compose.yml`, `docker-compose.preview.yml`, env_file, Docker network | 컨테이너명이나 포트를 바꾸면서 서비스명/env를 같이 바꾸지 않으면 로컬/preview에서만 재현되는 연결 장애가 생길 수 있다. | `docker-compose.yml`, `docker-compose.preview.yml`, `.env.prod.example`, `.env.preview.example`, `backend/src/core/database.py`, `frontend/next.config.ts` | `docker compose config`, `docker compose up -d postgres minio redis`, `docker compose logs backend frontend` |
| 배포 migration 처리 | backend entrypoint는 `alembic upgrade head` 실패 시 `alembic stamp head`를 시도하고 서버 시작을 계속한다. | Alembic, 운영 DB, compose 재기동, 배포 보조 스크립트 | 실패한 migration을 stamp 처리하면 schema와 migration history가 불일치할 수 있다. 운영에서 허용할 정책인지 확인 전제로 다루면 데이터 손상 위험이 있다. | `backend/Dockerfile`, `backend/alembic/versions/*.py`, `deploy.sh`, `deploy/preview.sh`, `docker-compose.yml`, `docker-compose.preview.yml` | `uv run alembic upgrade head`, `docker compose build backend`, 운영 rollback/stamp 허용 기준 확인 필요 |

변경 전 판단 기준:

1. 표의 "코드에서 확인되는 제약사항"을 깨는 변경이면 먼저 관련 테스트와 migration/문서 갱신 범위를 정한다.
2. "주요 의존성"이 외부 계정, 운영 secret, 서버 설정에 걸려 있으면 로컬에서 추측하지 말고 `확인 필요`로 남긴 뒤 담당자에게 확인한다.
3. "변경 리스크"가 데이터 정합성, SSE, LLM 출력 형식, 배포 migration에 닿으면 단일 파일 수정으로 보지 말고 사용자 흐름과 운영 복구 흐름까지 검증한다.

## 유지보수 포인트별 코드/설정 파일 매핑

아래 표는 이 문서의 주요 유지보수 포인트마다 먼저 열어볼 코드/설정 파일을 명시한다. 문서 본문을 읽다가 판단 근거가 필요하면 이 표의 파일을 기준으로 실제 구현을 확인한다.

| 유지보수 포인트 | 관련 코드/설정 파일 경로 | 확인할 내용 |
| --- | --- | --- |
| 로컬/컨테이너 실행 환경 | `start-dev.sh`, `start-local.sh`, `docker-compose.yml`, `docker-compose.preview.yml`, `.env.prod.example`, `.env.preview.example`, `backend/src/core/database.py`, `frontend/next.config.ts`, `frontend/src/lib/api.ts`, `frontend/src/app/api/v1/agent/chat/route.ts` | 포트, 서비스명, DB/MinIO/Redis 접속값, API rewrite, SSE proxy, 환경변수 기본값 |
| 백엔드 앱 조립과 공통 미들웨어 | `backend/src/main.py`, `backend/src/routers/__init__.py`, `backend/src/core/cors.py`, `backend/src/core/exceptions.py`, `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py`, `backend/src/middleware/logging_middleware_asgi.py` | 라우터 등록, CORS origin, 예외 응답 형식, 요청/응답 로깅 |
| DB 모델과 Alembic migration | `backend/src/core/database.py`, `backend/alembic/env.py`, `backend/alembic/versions/*.py`, `backend/src/models/*.py`, `backend/src/schemas/api/*.py`, `backend/src/services/*_svc.py`, `backend/tests/conftest.py`, `backend/scripts/setup_test_db.sh` | 모델 metadata, migration 적용, 테스트 DB 정리 순서, FK/cascade/check constraint |
| 프로젝트/요구사항/섹션 데이터 | `backend/src/models/project.py`, `backend/src/models/requirement.py`, `backend/src/services/project_svc.py`, `backend/src/services/requirement_svc.py`, `backend/src/services/section_svc.py`, `backend/src/routers/project.py`, `backend/src/routers/requirement.py`, `backend/src/routers/section.py`, `frontend/src/services/project-service.ts`, `frontend/src/services/requirement-service.ts`, `frontend/src/services/section-service.ts` | soft/hard delete, 섹션 활성화, display/order, API 요청/응답 계약 |
| 지식 문서, 객체 스토리지, RAG | `backend/src/models/knowledge.py`, `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/storage_svc.py`, `backend/src/services/embedding_svc.py`, `backend/src/services/rag_svc.py`, `backend/src/services/query_rewriter.py`, `backend/src/utils/text_chunker.py`, `backend/tests/test_rag_isolation.py`, `backend/tests/test_text_chunker.py` | 문서 상태 전이, MinIO key/prefix, 파싱/청킹, 임베딩 차원, completed 문서 필터 |
| LLM provider와 프롬프트 | `backend/src/services/llm_svc.py`, `backend/src/prompts/srs/generate.py`, `backend/src/prompts/design/generate.py`, `backend/src/prompts/testcase/generate.py`, `backend/src/prompts/knowledge/chat.py`, `backend/src/prompts/review/requirements.py`, `backend/src/agents/*`, `backend/tests/test_srs_generator_agent.py`, `backend/tests/test_design_generator_agent.py`, `backend/tests/test_testcase_generator_agent.py` | provider별 환경변수, content filter 처리, prompt 입력/출력 형식, 생성 테스트 |
| Agent registry, LangGraph, HITL, SSE | `backend/src/agents/registry.py`, `backend/src/routers/agent.py`, `backend/src/orchestration/graph.py`, `backend/src/orchestration/supervisor.py`, `backend/src/orchestration/retrieval_gate.py`, `backend/src/orchestration/state.py`, `backend/src/services/hitl_state_svc.py`, `backend/src/schemas/events.py`, `frontend/src/types/agent-events.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `docs/events.md` | built-in agent import 목록, 명시적 산출물 라우팅, checkpoint, HITL 상태, SSE 이벤트 계약 |
| Artifact version, PR, 영향도 | `backend/src/models/artifact.py`, `backend/src/services/artifact_svc.py`, `backend/src/services/artifact_record_svc.py`, `backend/src/services/impact_svc.py`, `backend/src/services/srs_svc.py`, `backend/src/services/design_svc.py`, `backend/src/services/testcase_svc.py`, `backend/src/routers/artifact.py`, `backend/src/routers/impact.py`, `frontend/src/components/artifacts/workspace/*`, `frontend/src/services/artifact-service.ts`, `frontend/src/services/impact-service.ts`, `frontend/src/stores/staging-store.ts`, `frontend/src/stores/artifact-store.ts` | working_status 제약, append-only version, open PR unique index, lineage, 영향도 재생성 |
| 프론트엔드 API, 상태, UI | `frontend/src/app/(main)`, `frontend/src/components`, `frontend/src/services/*-service.ts`, `frontend/src/stores/*.ts`, `frontend/src/types/*.ts`, `frontend/src/hooks/useProjectScopedReset.ts`, `frontend/src/lib/api.ts`, `frontend/src/config/*.ts`, `frontend/src/app/globals.css`, `frontend/package.json`, `frontend/eslint.config.mjs` | 화면 라우팅, 서비스/store 계약, project-scoped 상태 초기화, 오류 처리, lint/build |
| 배포 스크립트와 compose | `deploy.sh`, `deploy/preview.sh`, `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/next.config.ts` | compose build/up, preview/prod 포트, Docker build 방식 |
| 장애 확인과 로그 | `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py`, `backend/src/core/exceptions.py`, `frontend/src/lib/api.ts`, `frontend/src/lib/toast.ts`, `docker-compose.yml`, `docker-compose.preview.yml` | Loguru 설정, 요청 로그, API 오류 변환, compose logs |

## 실행 환경과 환경변수 유지보수

`docker-compose.yml`은 PostgreSQL(pgvector), MinIO, Redis, backend, frontend를 같은 compose 네트워크에서 실행한다. backend는 `DATABASE_URL`, `LANGGRAPH_CHECKPOINT_URL`, `REDIS_URL`, `MINIO_*`, `CORS_ORIGINS`를 받고, frontend는 `BACKEND_URL=http://backend:8081`로 Next.js rewrite와 SSE proxy가 백엔드를 바라보도록 구성되어 있다. 로컬 스크립트는 `start-dev.sh`와 `start-local.sh`가 있지만 포트와 패키지 매니저 사용이 다르므로 수정 전 반드시 두 파일을 함께 비교한다.

유지보수 포인트:

- `backend/src/core/database.py`의 기본 DB URL은 `postgresql+asyncpg://aise:aise1234@localhost:5432/aise`다. 운영/preview에서는 compose 또는 환경 파일이 이 값을 덮어쓴다.
- `backend/src/core/database.py`는 `connect_args={"ssl": False}`로 엔진을 만든다. 운영 DB가 TLS를 요구하면 코드 또는 환경별 분기 수정이 필요하다.
- `frontend/src/lib/api.ts`는 `NEXT_PUBLIC_API_URL`이 없으면 같은 도메인의 `/api`를 호출한다. 이 경우 `frontend/next.config.ts` rewrite 또는 `frontend/src/app/api/v1/agent/chat/route.ts` proxy가 `BACKEND_URL`을 통해 백엔드로 넘긴다.
- `start-local.sh`는 최초 설치에 `npm install`을 사용할 수 있지만 `frontend/package.json`은 `pnpm@9.15.0`과 `only-allow pnpm`을 강제한다. 로컬 스크립트를 수정할 때 패키지 매니저 정책을 맞춰야 한다.
- `.env.prod.example`과 `.env.preview.example`은 예시 파일이다. 실제 키를 커밋하지 않는다.

점검 명령:

```bash
docker compose config
docker compose ps
curl -s http://localhost:8081/api/v1/sample/health
curl -I http://localhost:4000
```

확인 필요:

- 운영 서버 주소, 도메인, TLS 종료 지점, 프록시 timeout, CORS 최종 origin 목록은 확인 필요다.
- 운영 환경변수 주입 방식과 secret rotation 절차는 확인 필요다.
- Redis는 compose와 환경변수에 포함되어 있지만 현재 애플리케이션 코드에서 직접 사용처가 확인되지 않는다. 실제 운영 의존 여부는 확인 필요다.

## 데이터베이스와 Alembic 유지보수

백엔드는 SQLAlchemy async 모델과 Alembic migration을 함께 사용한다. `backend/alembic/env.py`는 `.env`를 로드하고 `DATABASE_URL`을 Alembic용 sync driver URL로 바꾼 뒤 `src.models`를 import해 metadata를 구성한다. 모델 변경은 반드시 migration과 테스트를 같이 확인한다.

유지보수 포인트:

- 새 테이블이나 컬럼을 추가할 때 `backend/src/models/*.py`, `backend/src/schemas/api/*.py`, `backend/src/services/*_svc.py`, `backend/alembic/versions/*.py`를 함께 갱신한다.
- `backend/tests/conftest.py`는 테스트 DB를 자동 생성하지 않는다. `aise_test`가 없으면 `./backend/scripts/setup_test_db.sh` 실행을 안내하고 pytest를 종료한다.
- 테스트 후 정리는 `CLEANUP_TABLES` 순서로 수행된다. 새 테이블을 추가하면 FK 순서에 맞춰 `backend/tests/conftest.py`의 정리 목록도 갱신해야 테스트 간 데이터가 섞이지 않는다.
- `artifacts`와 `artifact_versions`는 순환 FK가 있어 테스트 정리 시 `current_version_id`, `open_pr_id`를 먼저 `NULL`로 푼다. 산출물 모델의 check constraint를 바꾸면 테스트 cleanup도 다시 확인한다.
- `KnowledgeChunk.embedding`은 `Vector(1536)`이다. 임베딩 모델이나 차원을 바꾸면 DB 컬럼 차원, 기존 데이터 재임베딩, RAG 검색 테스트를 함께 계획해야 한다.

점검 명령:

```bash
cd backend
uv run alembic current
uv run alembic upgrade head
uv run pytest tests/test_project.py tests/test_requirement.py tests/test_artifact_svc.py
```

확인 필요:

- 운영 DB 백업/복구 절차, migration 승인자, migration 적용 시간대, 롤백 절차는 확인 필요다.
- 운영 pgvector 인덱스 정책과 대용량 데이터 vacuum/analyze 기준은 확인 필요다.
- 운영 DB 계정 권한과 암호 rotation 기준은 확인 필요다.

## 프로젝트, 요구사항, 지식 데이터 유지보수

프로젝트는 대부분의 도메인 데이터의 상위 단위다. `backend/src/models/project.py`는 `requirements`, `requirement_sections`, `glossary_items`, `settings`에 cascade 관계를 둔다. 지식 문서와 산출물은 별도 모델에 `project_id` FK를 갖고, 삭제나 hard delete 경로에서 DB와 MinIO를 같이 정리해야 한다.

유지보수 포인트:

- 프로젝트 삭제는 soft delete와 hard delete가 분리되어 있다. UI에서 복구 가능한 삭제와 영구 삭제를 명확히 구분해야 한다.
- hard delete 경로는 DB cascade와 MinIO prefix 삭제를 같이 고려한다. `backend/src/services/storage_svc.py`의 `delete_prefix()`는 `{project_id}/` prefix 단위 삭제를 지원한다.
- 요구사항 생성/수정은 `Requirement.is_selected`, `Requirement.status`, 섹션의 `is_active`, order/display ID가 후속 Review, Record 추출, SRS 생성 입력에 영향을 준다.
- 지식 문서 상태는 `pending`, `processing`, `completed`, `failed` 흐름이다. `completed` 문서만 RAG/후보 추출에 포함되는 경로가 있으므로 상태 전이와 error message 처리를 보존한다.
- 지식 문서 원본은 MinIO에 저장되고 청크와 임베딩은 PostgreSQL에 저장된다. DB와 객체 스토리지 중 한쪽만 삭제되면 재처리와 출처 조회가 깨질 수 있다.

점검 명령:

```bash
cd backend
uv run pytest tests/test_project.py tests/test_requirement.py tests/test_section.py
uv run pytest tests/test_rag_isolation.py tests/test_text_chunker.py
```

확인 필요:

- soft delete 보관 기간을 실제로 실행하는 scheduler/cron/job은 코드에서 확인되지 않는다.
- 운영 MinIO 버킷 정책, 백업, lifecycle, 암호화, 용량 알림 기준은 확인 필요다.
- 업로드 가능한 파일 크기 제한과 악성 파일 검사 정책은 확인 필요다.

## AI, RAG, 프롬프트 유지보수

LLM 호출은 `backend/src/services/llm_svc.py`가 중심이다. `LLM_PROVIDER=openai`이면 `OPENAI_API_KEY`와 `OPENAI_MODEL`을 사용하고, 기본 provider인 `azure`에서는 SRS/TC 용도별 `SRS_API_KEY`, `SRS_ENDPOINT`, `TC_API_KEY`, `TC_ENDPOINT`, 모델명을 사용한다. 문서 임베딩은 `backend/src/services/embedding_svc.py`, 문서 파싱과 청킹은 `backend/src/services/document_processor.py`와 `backend/src/utils/text_chunker.py`가 담당한다.

유지보수 포인트:

- 프롬프트를 바꿀 때는 해당 생성 서비스와 테스트를 함께 본다. 예를 들어 SRS는 `backend/src/prompts/srs/generate.py`, `backend/src/services/srs_svc.py`, `backend/tests/test_srs_generator_agent.py`를 같이 확인한다.
- Azure content filter 거절은 `llm_svc.py`에서 422 `AppException`으로 변환된다. 프론트엔드 오류 표시 문구를 바꿀 때 이 상태 코드를 고려한다.
- 임베딩은 100개 단위 batch와 1536차원 vector 저장 흐름에 의존한다. 모델을 바꾸면 기존 `knowledge_chunks.embedding` 데이터와 검색 로직을 같이 마이그레이션해야 한다.
- `document_processor.py`는 FastAPI `BackgroundTasks`에서 독립 DB 세션을 열어 MinIO 다운로드, 파싱, 청킹, 임베딩, 청크 저장, 문서 상태 갱신을 수행한다. 실패 시 `status='failed'`와 `error_message`를 저장한다.
- `parse_document()`는 `txt`, `md`, `pdf`, `docx`, `pptx`, `xlsx`를 지원한다. 새 파일 형식을 추가하면 파서 의존성, MIME/확장자 검증, 테스트 데이터를 함께 추가한다.

점검 명령:

```bash
cd backend
uv run pytest tests/test_query_rewriter.py tests/test_rag_isolation.py tests/test_text_chunker.py
uv run pytest tests/test_srs_generator_agent.py tests/test_design_generator_agent.py tests/test_testcase_generator_agent.py
```

확인 필요:

- 실제 Azure/OpenAI 계정, deployment name, 모델 버전, rate limit, 비용 한도는 확인 필요다.
- LLM 장애 시 provider fallback, 재시도 횟수, 사용자 공지 문구는 확인 필요다.
- 장시간 문서 처리 작업의 timeout, 재시도, 별도 worker 분리 계획은 확인 필요다.

## Agent, HITL, SSE 유지보수

앱 시작 시 `backend/src/main.py`가 `load_builtin_agents()`를 호출하고, `backend/src/agents/registry.py`의 명시 목록이 built-in agent 모듈을 import한다. Agent 채팅은 `backend/src/routers/agent.py`에서 LangGraph 실행과 SSE 스트림으로 이어지고, 프론트엔드는 `frontend/src/app/api/v1/agent/chat/route.ts`가 rewrite buffering을 피하기 위해 백엔드 stream을 직접 전달한다.

유지보수 포인트:

- 새 Agent를 추가하려면 `@register_agent`가 붙은 클래스를 만들고 `backend/src/agents/registry.py`의 `_BUILTIN_AGENT_MODULES`에 모듈을 명시적으로 추가한다. 이 목록은 directory walk가 아니라 결정적 import 목록이다.
- 명시적 산출물 생성 라우팅은 `backend/src/orchestration/graph.py`의 `_ARTIFACT_GENERATION_ROUTES`와 `_GENERATION_TERMS`를 먼저 통과한다. "테스트케이스 생성" 같은 workflow 명령이 RAG로 잘못 가지 않도록 키워드를 신중히 관리한다.
- `LANGGRAPH_CHECKPOINT_URL`이 없으면 `MemorySaver`, 있으면 PostgreSQL 기반 `AsyncPostgresSaver`를 사용한다. HITL 재개 기능을 운영에서 보장하려면 checkpoint 영속화 설정이 필요하다.
- SSE 이벤트 스키마는 `backend/src/schemas/events.py`, 프론트엔드 타입은 `frontend/src/types/agent-events.ts`, 설명 문서는 `docs/events.md`를 함께 맞춘다.
- plan 실행 경로의 HITL interrupt는 현재 `allow_interrupt=False`로 억제되는 코드 경로가 있다. plan-path HITL을 확장할 때 이 제한을 먼저 확인한다.

점검 명령:

```bash
cd backend
uv run pytest tests/test_agent_registry.py tests/test_agents_router.py
uv run pytest tests/test_orchestration.py tests/test_hitl_interrupt.py
uv run python scripts/smoke_langgraph_chat.py
```

확인 필요:

- 운영 checkpoint 보존 기간, checkpoint 테이블 정리 방식, 장기 세션 복구 정책은 확인 필요다.
- SSE 앞단 프록시의 buffering 비활성화, idle timeout, 재연결 정책은 확인 필요다.
- HITL 요청 만료 시간, 사용자 알림 채널, 미응답 처리 기준은 확인 필요다.

## Artifact 버전, PR, 영향도 유지보수

산출물은 `backend/src/models/artifact.py`의 공통 모델로 관리된다. `Artifact`는 working copy, `ArtifactVersion`은 불변 snapshot, `PullRequest`는 staging/review/merge 라이프사이클, `ArtifactDependency`와 `source_artifact_versions`는 영향도 추적을 담당한다.

유지보수 포인트:

- `Artifact.working_status`는 `clean`, `dirty`, `staged`만 허용된다. `clean`이면 `current_version_id`가 필요하고, `staged`이면 `open_pr_id`가 필요하다는 DB check constraint가 있다.
- `ArtifactVersion`은 append-only snapshot 역할이다. 기존 version 내용을 수정하는 방식보다 새 version을 추가하는 방식으로 기능을 설계한다.
- artifact당 open PR은 부분 unique index로 최대 1개다. PR 생성/merge/reject 흐름을 바꿀 때 중복 open PR과 `open_pr_id` 정리를 같이 검증한다.
- SRS, Design, Test Case 생성은 upstream artifact version lineage를 기록한다. 영향도 계산은 이 lineage가 정확하다는 전제에 의존한다.
- `impact_svc.py`의 적용 흐름은 현재 SRS/Design 재생성 중심이며 record/testcase는 skipped로 응답하는 경로가 있다. UI 문구와 API 응답을 일치시킨다.

점검 명령:

```bash
cd backend
uv run pytest tests/test_artifact_svc.py tests/test_artifact_record.py
uv run pytest tests/test_artifact_generation_routing.py
```

확인 필요:

- PR 승인자 권한, audit log 보존 기간, 산출물 버전 rollback 운영 절차는 확인 필요다.
- 영향도 재생성 실패 시 수동 복구 절차와 사용자 공지 기준은 확인 필요다.

## 프론트엔드 상태와 UI 유지보수

프론트엔드는 Next.js App Router 기반이며, 도메인 API 호출은 `frontend/src/services`, 전역/도메인 상태는 `frontend/src/stores`, 공통 API 오류 처리는 `frontend/src/lib/api.ts`에 분리되어 있다. 화면 수정은 컴포넌트만 보지 말고 서비스와 store를 함께 확인한다.

유지보수 포인트:

- 공통 JSON API는 `api.get/post/put/patch/delete`를 사용하지만 파일 업로드와 SSE는 직접 `fetch`를 사용하는 경로가 있다. `Content-Type: application/json`이 붙으면 안 되는 업로드 경로를 공통 API로 바꾸지 않는다.
- 401 응답은 `frontend/src/lib/api.ts`에서 `/login`으로 이동하도록 되어 있다. 현재 인증 구현 전체는 코드에서 명확히 확인되지 않으므로 로그인/권한 화면을 확장할 때 백엔드 인증 정책을 먼저 확인한다.
- Agent SSE는 `frontend/src/app/api/v1/agent/chat/route.ts`가 백엔드 stream body를 그대로 반환한다. 이 경로를 일반 rewrite로 합치면 토큰 단위 표시가 지연될 수 있다.
- Zustand store는 화면 상태와 API 결과를 나눠 들고 있다. 프로젝트 전환 시 오래된 project-scoped 상태가 남지 않도록 `useProjectScopedReset`과 관련 store를 확인한다.
- UI 변경 후에는 데스크톱뿐 아니라 모바일 레이아웃, drawer, right panel, artifact workspace modal을 함께 확인한다.

점검 명령:

```bash
cd frontend
pnpm lint
pnpm build
```

확인 필요:

- 프론트엔드 E2E 테스트 도구와 필수 시나리오는 `frontend/package.json`에서 확인되지 않는다.
- 실제 인증/인가 정책, 세션 저장 위치, 로그인 라우팅 정책은 확인 필요다.

## 배포와 운영 유지보수

코드에서 확인되는 배포 보조 흐름은 Docker Compose와 shell script 중심이다. `docker-compose.yml`은 기본 실행, `docker-compose.preview.yml`은 preview 실행, `deploy.sh`와 `deploy/preview.sh`는 배포 보조 스크립트 역할을 한다. 현재 워크트리에서 `.github/workflows`, `Jenkinsfile`, `.gitlab-ci.yml`, Terraform/Kubernetes manifest는 확인되지 않는다. 실제 운영 서버 계정, secret 값, 자동 배포 여부, 승인/롤백 절차는 코드에서 확정할 수 없다.

유지보수 포인트:

- compose 서비스명 기준으로 backend는 `postgres`, `redis`, `minio`에 접근하고 frontend는 `backend:8081`에 접근한다. 컨테이너명을 바꾸더라도 서비스명 의존성을 유지한다.
- backend container는 `backend/Dockerfile`에서 `uv sync --frozen --no-dev`와 `uvicorn src.main:app --host 0.0.0.0 --port 8081`로 실행된다.
- frontend container는 `frontend/next.config.ts`의 `output: 'standalone'` 전제에 의존한다. 단, `frontend/Dockerfile`은 `npm ci`를 사용하는데 저장소 정책은 pnpm이다. Docker frontend 빌드 경로는 별도 확인이 필요하다.
- 자동 CI/CD workflow 파일은 현재 워크트리에서 확인되지 않는다. 저장소 기준으로 확정 가능한 배포 진입점은 `deploy.sh`, `deploy/preview.sh`, `docker-compose.yml`, `docker-compose.preview.yml`이다.
- production으로 보이는 기본 compose는 `docker compose up -d --build` 또는 `./deploy.sh`로 실행할 수 있지만, 이 구성이 실제 production인지 staging인지 확인 필요다.
- preview compose는 `./deploy/preview.sh` 또는 `docker compose -f docker-compose.preview.yml up -d --build`로 실행할 수 있다. preview 서버, DNS/TLS, 승인 절차, 알림 채널은 확인 필요다.
- 배포 전에 DB migration 적용 순서와 애플리케이션 재시작 순서를 분리해서 점검한다. 코드상 backend 컨테이너 시작 시 `backend/Dockerfile`의 entrypoint가 `alembic upgrade head`를 자동 실행하고, 실패하면 `alembic stamp head`를 시도한 뒤 서버를 계속 시작한다. 이 실패 처리 정책을 운영에서 허용할지는 확인 필요다.
- MinIO와 PostgreSQL volume은 compose volume으로 유지된다. 운영에서는 volume 백업/복구와 데이터 보존 정책이 필요하다.

점검 명령:

```bash
docker compose config
docker compose build backend
docker compose build frontend
docker compose up -d
docker compose logs -f backend
docker compose logs -f frontend
```

확인 필요:

- 저장소 워크플로우 밖의 운영 CI/CD 절차, 배포 승인 방식, image registry 사용 여부, rollback 방식은 확인 필요다.
- 운영 DB migration 적용 담당자와 실패 시 복구 기준은 확인 필요다.
- TLS 인증서, reverse proxy, 로드밸런서, health check 경로, 로그 수집/알림 도구는 확인 필요다.

## 장애 확인과 로그

백엔드는 Loguru 기반 로깅과 요청 로깅 미들웨어를 사용한다. FastAPI 예외는 `backend/src/core/exceptions.py`의 전역 예외 처리 경로를 거쳐 프론트엔드의 `ApiError`와 toast 표시로 이어진다. 운영 로그 수집 도구는 저장소에서 확인되지 않는다.

장애를 볼 때는 먼저 사용자가 겪은 증상을 코드 경로로 나눈다. "화면이 안 뜬다", "API가 실패한다", "채팅 스트림이 끊긴다", "문서 처리만 실패한다"는 서로 다른 계층의 문제다. 아래 순서대로 확인하면 프론트엔드, 백엔드, 인프라, 외부 API 중 어디서 끊겼는지 빠르게 좁힐 수 있다.

### 공통 점검 순서

1. 증상과 영향 범위를 분리한다.
   - 화면 접속: `curl -I http://localhost:4000`
   - frontend 경유 API: `curl http://localhost:4000/api/v1/sample/`
   - backend 직접 API: `curl http://localhost:8081/api/v1/sample/`
   - backend docs: `curl -I http://localhost:8081/docs`
   - preview는 `4000/8081` 대신 `4100/8181`을 사용한다.
2. 컨테이너 상태와 최근 로그를 확인한다.

```bash
docker compose ps
docker compose logs --since 30m backend frontend
docker compose logs --tail 100 postgres minio redis
```

3. backend 파일 로그에서 같은 request_id를 따라간다.

```bash
docker compose exec backend sh -lc 'tail -n 200 var/logs/app.log'
docker compose exec backend sh -lc 'tail -n 200 var/logs/app.json'
```

4. 최근 변경 축을 확인한다.
   - API/화면 변경: `frontend/src/services`, `frontend/src/stores`, `backend/src/routers`, `backend/src/schemas/api`
   - DB 변경: `backend/src/models`, `backend/alembic/versions`
   - 배포/env 변경: `docker-compose.yml`, `docker-compose.preview.yml`, `.env.prod.example`, `.env.preview.example`, `deploy.sh`, `deploy/preview.sh`
   - Agent/SSE 변경: `backend/src/routers/agent.py`, `backend/src/orchestration`, `backend/src/schemas/events.py`, `frontend/src/app/api/v1/agent/chat/route.ts`, `frontend/src/hooks/useChatStream.ts`
5. 운영 정책이 필요한 판단은 추측하지 않는다. 장애 등급, 사용자 공지, rollback 승인, secret 조회, 백업 복구, 외부 LLM 장애 대응은 저장소에서 기준을 확인할 수 없으므로 `확인 필요`로 남긴다.

### 장애별 1차 확인 순서

| 증상 | 점검 기준 | 확인 명령/파일 | 관련 로그·설정 위치 | 유지보수 포인트 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 백엔드가 뜨지 않음 | 컨테이너 시작, DB 연결, Alembic, env 누락을 순서대로 본다. | `docker compose ps backend`, `docker compose logs --tail 300 backend`, `docker compose exec postgres pg_isready -U aise` | `backend/Dockerfile`, `backend/src/core/database.py`, `backend/alembic/env.py`, `backend/alembic/versions`, `.env.prod.example`, `docker-compose.yml` | migration 실패 후 `stamp head`가 실행될 수 있으므로 schema와 migration history 불일치를 의심한다. | 운영 rollback/downgrade, 백업 복구, `stamp head` 허용 기준 |
| 프론트엔드 API 호출 실패 | frontend rewrite 문제인지 backend API 문제인지 분리한다. | `curl http://localhost:4000/api/v1/sample/`, `curl http://localhost:8081/api/v1/sample/`, `docker compose logs --tail 100 frontend` | `frontend/src/lib/api.ts`, `frontend/next.config.ts`, `frontend/Dockerfile`, `backend/src/core/cors.py`, `backend/src/main.py` | `NEXT_PUBLIC_API_URL`이 없으면 같은 origin `/api`를 쓰고, Next.js rewrite가 `BACKEND_URL`로 보낸다. | 운영 도메인, TLS, reverse proxy, allowed origin |
| 사용자는 500 toast만 봄 | backend가 `detail` 또는 `error` body를 어떻게 내려주는지 확인한다. | `docker compose logs --since 30m backend`, 브라우저 Network response body 확인 | `backend/src/core/exceptions.py`, `backend/src/middleware/logging_middleware.py`, `frontend/src/lib/api.ts`, `frontend/src/lib/toast.ts` | `AppException`은 status/detail로 응답하고, 프론트는 500 이상이면 "서버 오류가 발생했습니다" toast를 띄운다. | 사용자 노출 문구, 장애 공지 기준, request_id 전달 방식 |
| Agent 스트리밍 지연 또는 끊김 | 일반 API rewrite와 SSE proxy를 분리해서 본다. | `docker compose logs --since 30m backend frontend`, `cd backend && uv run pytest tests/test_agents_router.py tests/test_hitl_interrupt.py` | `frontend/src/app/api/v1/agent/chat/route.ts`, `backend/src/routers/agent.py`, `backend/src/orchestration/graph.py`, `backend/src/services/hitl_state_svc.py`, `backend/src/schemas/events.py`, `docs/events.md` | Next.js rewrite는 SSE를 버퍼링할 수 있어 별도 route handler가 스트림을 전달한다. 프록시 timeout과 LangGraph checkpoint를 같이 확인한다. | SSE buffering, idle timeout, 재연결, HITL 만료, checkpoint 보존 |
| 문서 업로드 후 처리 실패 | 원본 저장, background parsing, embedding, chunk 저장, 상태 갱신 중 어디서 실패했는지 본다. | `docker compose logs --since 30m backend`, `docker compose logs --tail 100 minio`, 관련 API 응답 확인 | `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/storage_svc.py`, `backend/src/services/embedding_svc.py`, `backend/src/models/knowledge.py` | 실패 문서는 `failed` 상태와 `error_message`를 남기는 흐름이 있으므로 DB 상태와 MinIO object를 함께 확인한다. | 파일 크기 제한, 악성 파일 검사, 재처리 절차, MinIO 백업/lifecycle |
| RAG 답변 출처 누락 | completed/active 문서 필터, chunk/embedding 저장, query rewrite를 확인한다. | `cd backend && uv run pytest tests/test_rag_isolation.py tests/test_query_rewriter.py tests/test_text_chunker.py` | `backend/src/services/rag_svc.py`, `backend/src/services/query_rewriter.py`, `backend/src/models/knowledge.py`, `backend/src/services/embedding_svc.py` | 임베딩 차원은 `Vector(1536)`이므로 모델 변경 시 기존 데이터와 검색 로직을 같이 봐야 한다. | 재임베딩 계획, pgvector index/vacuum/analyze 기준 |
| SRS/Design/TC 생성 실패 | LLM env/auth/quota/content filter와 prompt 출력 schema를 같이 본다. | `docker compose logs --since 30m backend | grep -Ei "llm|openai|azure|quota|rate|content|timeout|401|403|429|500" || true` | `backend/src/services/llm_svc.py`, `backend/src/prompts`, `backend/src/agents`, `backend/src/services/srs_svc.py`, `backend/src/services/design_svc.py`, `backend/src/services/testcase_svc.py`, `.env.*.example` | provider key 문제와 prompt/schema parse 실패를 구분한다. Azure content filter는 422 `AppException`으로 변환된다. | 실제 provider, model, deployment name, quota, fallback, 비용 알림 |
| pytest가 전부 실패 | 테스트 DB 존재와 migration 적용부터 확인한다. | `docker compose up -d postgres`, `cd backend && bash scripts/setup_test_db.sh`, `cd backend && uv run pytest -q` | `backend/tests/conftest.py`, `backend/scripts/setup_test_db.sh`, `backend/scripts/setup_test_db.py`, `backend/alembic` | `backend/tests/conftest.py`는 테스트 DB가 없으면 모든 테스트를 불투명하게 실패시키지 않고 setup script 실행을 안내한다. | CI 테스트 DB 생성 권한, 필수 테스트 게이트 |
| preview만 실패 | preview compose 포트/env와 Redis 누락 가능성을 확인한다. | `docker compose -f docker-compose.preview.yml ps`, `docker compose -f docker-compose.preview.yml logs --tail 200 backend frontend` | `docker-compose.preview.yml`, `deploy/preview.sh`, `.env.preview.example` | preview compose에는 Redis 서비스가 없지만 env 예시는 Redis URL을 포함한다. 같은 Docker daemon에서 기본 compose와 컨테이너명 충돌 가능성도 확인한다. | preview Redis 대상, DNS/TLS, 데이터 보존/삭제 |

### 로그와 설정 파일 위치

| 구분 | 위치 | 확인할 내용 | 주의사항 |
| --- | --- | --- | --- |
| Docker 로그 | `docker compose logs <service>`, `docker compose -f docker-compose.preview.yml logs <service>` | 컨테이너 시작 오류, runtime traceback, build 후 실행 상태 | 운영 로그 공유 시 secret, 토큰, 사용자 입력 마스킹 필요 |
| Backend app 로그 | 컨테이너 내부 `var/logs/app.log`, `var/logs/app.json` | request_id, method/path, status, 처리 시간, `AppException`, unhandled exception | compose volume mount가 없어 컨테이너 재생성 시 보존되지 않을 수 있다. 중앙 수집은 확인 필요 |
| 로깅 설정 | `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py`, `backend/src/core/exceptions.py` | `LOG_LEVEL`, `ENVIRONMENT`, 파일 rotation `00:00`, retention `7 days`, JSON 로그 | `ENVIRONMENT`가 prod/staging이 아니면 diagnose가 켜진다. 운영 환경명 오설정 주의 |
| Frontend 오류 처리 | `frontend/src/lib/api.ts`, `frontend/src/lib/toast.ts`, `frontend/src/app/global-error.tsx`, `frontend/src/app/not-found.tsx` | `ApiError`, 401 redirect, 4xx/5xx toast, Next.js 전역 오류 화면 | 백엔드 오류 body 형식 변경 시 프론트 표시가 달라질 수 있다. |
| API/SSE 연결 설정 | `frontend/next.config.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `docker-compose.yml`, `docker-compose.preview.yml` | `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, `/api/*` rewrite, SSE proxy | 일반 REST와 Agent stream은 다른 경로로 프록시된다. |
| 데이터/외부 의존 설정 | `.env.prod.example`, `.env.preview.example`, `backend/src/core/database.py`, `backend/src/services/storage_svc.py`, `backend/src/services/llm_svc.py` | DB URL, MinIO, Redis/checkpoint, LLM provider/key/endpoint | 실제 secret 값과 운영 계정은 저장소에 없으므로 `확인 필요` |

확인 필요:

- 운영 로그 저장 위치, retention, 검색 도구, request_id 추적 방식은 확인 필요다.
- 장애 등급, 사용자 공지 기준, postmortem 양식은 확인 필요다.
- 백업 복구 drill 주기와 담당자는 확인 필요다.

## 유지보수 작업 후 검증 방법

유지보수 작업을 마친 뒤에는 변경 파일의 위치만 보고 검증 범위를 줄이지 말고, 사용자 흐름과 데이터 흐름 기준으로 검증한다. 예를 들어 프론트엔드 컴포넌트만 수정했더라도 API 호출 계약이나 Zustand store를 함께 바꿨다면 백엔드 관련 테스트 또는 수동 API 확인까지 포함한다.

검증은 아래 순서로 진행한다.

1. 변경 파일과 영향 범위를 정리한다.
   - 근거 파일: `git diff --name-only`, `frontend/src/services/*-service.ts`, `frontend/src/stores/*.ts`, `backend/src/routers/*.py`, `backend/src/services/*_svc.py`, `backend/src/models/*.py`
   - 확인 내용: API 계약 변경, DB schema 변경, background task 변경, SSE 이벤트 변경, Docker/환경변수 변경 여부
   - 실행 명령:

```bash
git diff --name-only
git diff --stat
```

2. 백엔드 변경은 테스트 DB와 migration 상태를 먼저 확인한다.
   - 근거 파일: `backend/pyproject.toml`, `backend/tests/conftest.py`, `backend/scripts/setup_test_db.sh`, `backend/alembic/env.py`
   - `backend/tests/conftest.py`는 테스트 DB가 없으면 `setup_test_db.sh` 실행을 안내하고 종료하므로, 신규 환경에서는 테스트 DB를 먼저 만든다.
   - 실행 명령:

```bash
cd backend
./scripts/setup_test_db.sh
uv sync
uv run alembic current
uv run alembic upgrade head
```

3. 변경 영역과 직접 연결된 백엔드 테스트를 실행한다.
   - 근거 파일: `backend/tests/test_*.py`
   - 전체 테스트가 오래 걸리거나 외부 LLM/임베딩 환경변수에 영향을 받는 경우에도, 변경한 router/service/model과 같은 도메인의 테스트는 먼저 통과시킨다.
   - 실행 명령:

```bash
cd backend
uv run pytest tests/test_project.py
uv run pytest tests/test_requirement.py tests/test_section.py
uv run pytest tests/test_artifact_svc.py tests/test_artifact_record.py
uv run pytest tests/test_orchestration.py tests/test_hitl_interrupt.py
uv run pytest
```

4. 프론트엔드 변경은 lint와 production build를 모두 확인한다.
   - 근거 파일: `frontend/package.json`, `frontend/eslint.config.mjs`, `frontend/next.config.ts`
   - `frontend/package.json`은 `pnpm@9.15.0`과 `preinstall`의 `only-allow pnpm`을 명시한다. 로컬 검증은 pnpm 기준으로 실행한다.
   - 실행 명령:

```bash
cd frontend
pnpm install
pnpm lint
pnpm build
```

5. 컨테이너/환경변수/배포 설정 변경은 compose 설정 렌더링과 이미지 빌드를 확인한다.
   - 근거 파일: `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `deploy.sh`, `deploy/preview.sh`, `.env.prod.example`, `.env.preview.example`
   - compose 설정 검증은 실제 secret 값을 출력할 수 있으므로 운영 환경에서는 로그 공유 전에 민감정보 노출 여부를 확인한다.
   - 실행 명령:

```bash
docker compose config
docker compose -f docker-compose.preview.yml config
docker compose build backend
docker compose build frontend
docker compose up -d postgres minio redis
docker compose ps
```

6. 앱 구동 후 smoke check를 수행한다.
   - 근거 파일: `backend/src/main.py`, `backend/src/routers/sample.py`, `frontend/next.config.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `backend/scripts/smoke_langgraph_chat.py`
   - Agent smoke script는 실제 seeded session, LLM, embedding, RAG retrieval에 의존한다. 필요한 데이터와 API 키가 없는 환경에서는 `확인 필요`로 남기고 router/service 단위 테스트로 대체한다.
   - 실행 명령:

```bash
curl -s http://localhost:8081/api/v1/sample/health
curl -I http://localhost:4000

cd backend
uv run python scripts/smoke_langgraph_chat.py --session-id <uuid> --message "질문"
```

변경 유형별 최소 검증 기준은 다음과 같다.

| 변경 유형 | 반드시 실행할 검증 | 추가로 확인할 사용자 흐름 |
| --- | --- | --- |
| 백엔드 router/schema/service 변경 | 관련 `uv run pytest tests/test_*.py`, 필요 시 `uv run pytest` | Swagger 또는 curl로 요청/응답 status, error body, 빈 데이터 응답 확인 |
| DB model/Alembic 변경 | `uv run alembic upgrade head`, 관련 pytest, 테스트 cleanup 확인 | 신규/수정 테이블의 FK, cascade, check constraint, 기존 데이터 migration 영향 확인 |
| 문서 처리/RAG/임베딩 변경 | `tests/test_rag_isolation.py`, `tests/test_text_chunker.py`, 관련 service 테스트 | 샘플 파일 업로드, 문서 상태 `completed/failed`, 출처 포함 답변 확인 |
| Agent/HITL/SSE 변경 | `tests/test_agent_registry.py`, `tests/test_agents_router.py`, `tests/test_orchestration.py`, `tests/test_hitl_interrupt.py` | 채팅 stream, HITL 승인/거절/재개, 프론트엔드 이벤트 렌더링 확인 |
| Artifact/PR/영향도 변경 | `tests/test_artifact_svc.py`, `tests/test_artifact_record.py`, `tests/test_artifact_generation_routing.py` | 산출물 생성, staging, PR merge/reject, 영향도 재생성 확인 |
| 프론트엔드 API/store/UI 변경 | `pnpm lint`, `pnpm build` | 프로젝트 전환, 로딩/에러/빈 상태, 모바일 drawer/right panel/artifact modal 확인 |
| Docker/배포 설정 변경 | `docker compose config`, `docker compose build backend`, `docker compose build frontend` | compose service name, 포트, env_file, backend/frontend 통신, 로그 확인 |

검증 결과 기록 시 남길 정보:

- 실행한 명령과 성공/실패 결과
- 실패한 테스트 이름과 첫 번째 원인
- 수동 확인한 화면 또는 API 경로
- DB migration을 실행했는지 여부와 대상 DB
- 외부 LLM, MinIO, Redis, GitHub Secrets, 운영 서버처럼 로컬 코드만으로 재현할 수 없어 `확인 필요`로 남긴 항목

확인 필요:

- 저장소에는 백엔드 lint/type-check 명령이 명시되어 있지 않다. Python 정적 검사 도구를 필수 게이트로 둘지는 확인 필요다.
- 프론트엔드 E2E 테스트 스크립트는 `frontend/package.json`에서 확인되지 않는다. 필수 브라우저 시나리오와 도구는 확인 필요다.
- 운영 배포 전 필수 CI 테스트 목록, 승인자, 실패 시 rollback 기준은 확인 필요다.
- Agent smoke 검증에 필요한 seeded project/session과 LLM/embedding 계정 값은 저장소에서 확인되지 않는다.

## 변경 유형별 체크리스트

| 변경 유형 | 관련 코드/설정 파일 경로 | 수정 전 확인 | 수정 후 검증 |
| --- | --- | --- | --- |
| API 추가/변경 | `frontend/src/services/*-service.ts`, `backend/src/routers/*.py`, `backend/src/schemas/api/*.py`, `backend/src/core/exceptions.py`, `frontend/src/lib/api.ts` | 프론트엔드 서비스, 백엔드 라우터, Pydantic schema, 오류 응답 형식 | 관련 `backend/tests/test_*.py`, `pnpm lint`, Swagger 수동 확인 |
| DB 모델 변경 | `backend/src/models/*.py`, `backend/alembic/versions/*.py`, `backend/alembic/env.py`, `backend/tests/conftest.py`, `backend/src/services/*_svc.py` | SQLAlchemy 모델, Alembic migration, 테스트 cleanup 순서, cascade/FK | `uv run alembic upgrade head`, 관련 pytest |
| 프롬프트/LLM 변경 | `backend/src/prompts/*`, `backend/src/services/llm_svc.py`, `backend/src/services/srs_svc.py`, `backend/src/services/design_svc.py`, `backend/src/services/testcase_svc.py`, `backend/src/utils/json_parser.py` | prompt 입력 데이터, 모델/provider 환경변수, JSON 파싱/검증 코드 | 생성 agent/service 테스트, 실패 응답 수동 확인 |
| 지식 문서 처리 변경 | `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/storage_svc.py`, `backend/src/services/embedding_svc.py`, `backend/src/utils/text_chunker.py`, `backend/src/models/knowledge.py` | 지원 확장자, 파서 의존성, 청킹/임베딩 차원, MinIO key | RAG/text chunker 테스트, 실제 샘플 파일 업로드 |
| Agent 라우팅 변경 | `backend/src/agents/registry.py`, `backend/src/orchestration/supervisor.py`, `backend/src/orchestration/graph.py`, `backend/src/orchestration/retrieval_gate.py`, `backend/src/schemas/events.py`, `frontend/src/types/agent-events.ts` | registry 명시 목록, supervisor routing, explicit generation terms, SSE schema | orchestration/HITL 테스트, `/agent` 수동 스트리밍 확인 |
| Artifact/PR 변경 | `backend/src/models/artifact.py`, `backend/src/services/artifact_svc.py`, `backend/src/services/artifact_record_svc.py`, `backend/src/services/impact_svc.py`, `frontend/src/components/artifacts/workspace/*`, `frontend/src/stores/staging-store.ts` | working_status constraint, open PR unique index, version lineage, impact 계산 | artifact/impact 테스트, PR 생성/merge 수동 확인 |
| 프론트엔드 화면 변경 | `frontend/src/app/(main)`, `frontend/src/components`, `frontend/src/services/*-service.ts`, `frontend/src/stores/*.ts`, `frontend/src/hooks/useProjectScopedReset.ts`, `frontend/src/app/globals.css` | App Router 경로, 서비스/store 계약, responsive layout, loading/error state | `pnpm lint`, `pnpm build`, 주요 화면 수동 확인 |
| 배포 설정 변경 | `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `deploy.sh`, `deploy/preview.sh` | compose service name, env_file, Dockerfile package manager, exposed port, 수동 배포 스크립트 | `docker compose config`, `docker compose build`, smoke curl |

## 변경 영향 범위 매트릭스

아래 표는 유지보수 작업을 시작할 때 영향 범위를 빠르게 자르는 기준이다. 수정한 파일이 한 칸에만 속해 보여도, 저장 데이터나 API 계약을 공유하면 인접 영역까지 검증한다.

| 변경 영역 | 1차 영향 범위 | 2차 영향 범위 | 검증 우선순위 |
| --- | --- | --- | --- |
| API 계약 | 백엔드 router/schema/service, 프론트엔드 service/type/store | 오류 응답, loading/empty state, 문서의 주요 API 목록 | 관련 backend pytest, `pnpm lint`, Swagger 또는 curl 수동 확인 |
| 데이터 모델 | SQLAlchemy model, Alembic migration, DB constraint, fixture cleanup | 삭제/복원, Artifact lineage, RAG 검색, 운영 백업/복구 | `uv run alembic upgrade head`, 관련 pytest, migration rollback 정책 확인 필요 |
| 외부 저장소 | PostgreSQL, pgvector, MinIO, Redis/checkpoint | 지식 문서 처리, RAG, HITL resume, hard delete | compose 상태, service 테스트, 백업/복구 및 orphan 정리 기준 확인 필요 |
| LLM/프롬프트 | prompt, LLM service, JSON parser, 생성 service/agent | 생성 산출물 schema, partial failure, 비용/쿼터, fallback | 생성 관련 pytest, 실패 응답 수동 확인, provider/model 정책 확인 필요 |
| Streaming/HITL | SSE event schema, Agent router, LangGraph checkpoint, frontend stream parser | 프록시 buffering, 세션 보존, interrupt resume UX | orchestration/HITL 테스트, `scripts/smoke_langgraph_chat.py`, 운영 SSE timeout 확인 필요 |
| 배포/운영 | Dockerfile, compose, deploy script, env_file, runtime port | CORS, reverse proxy, secret 주입, migration 자동 실행 | `docker compose config`, build/smoke check, CI/CD/승인/롤백 기준 확인 필요 |

## 확인 필요

아래 항목은 현재 저장소의 코드, Docker Compose, 배포 스크립트, 예시 환경 파일만으로 확정할 수 없다. 유지보수 작업에서 이 항목을 전제로 삼아야 할 때는 추측하지 말고 운영 담당자, 클라우드 콘솔, secret 저장소, 별도 운영 문서에서 먼저 확인한다.
본문의 각 유지보수 영역에 흩어져 있는 `확인 필요` 메모는 빠른 작업 중 놓치지 않기 위한 현장 메모이고, 아래 표는 운영 인수인계 전에 반드시 별도 확인해야 하는 불확실 항목의 통합 목록이다.

| 분류 | 확인 필요 항목 | 저장소에서 확인한 근거 | 확인해야 하는 이유 |
| --- | --- | --- | --- |
| 운영 서버/계정 | 실제 production 서버 주소, SSH 접속 계정, 작업 디렉터리, 클라우드 또는 사내 인프라 계정은 `확인 필요`다. | `deploy.sh`와 `deploy/preview.sh`는 compose 실행 절차만 정의하고, 실제 서버 계정과 접속 방식은 저장소에 없다. | 장애 대응, 배포, 로그 확인을 누가 어디에서 수행하는지 문서만으로 확정할 수 없다. |
| 환경변수/Secret | `.env`, `.env.prod`, `.env.preview`, secret 저장소의 실제 값과 주입 방식, secret rotation 절차는 `확인 필요`다. | `.env.prod.example`, `.env.preview.example`, `docker-compose.yml`, `docker-compose.preview.yml`에는 예시 변수명과 기본값만 있다. | LLM API key, DB/MinIO password, 운영 credential은 저장소에 없어야 하는 운영 비밀이다. |
| CI/CD 게이트 | 운영 배포 전 필수 테스트, lint/build 게이트, 승인자, release branch 전략, 실패 시 중단 기준은 `확인 필요`다. | 현재 워크트리에서 `.github/workflows`, `Jenkinsfile`, `.gitlab-ci.yml` 같은 CI/CD 파일은 확인되지 않는다. | 변경 반영 전 어떤 검증을 통과해야 하는지 모르면 회귀 위험을 운영 정책으로 통제할 수 없다. |
| 배포/롤백 | 무중단 배포 여부, image registry 사용 여부, rollback 명령, migration 실패 시 rollback 또는 `stamp head` 허용 기준은 `확인 필요`다. | `deploy.sh`는 `docker compose down` 후 재빌드/재기동하고, `backend/Dockerfile` entrypoint는 `alembic upgrade head` 실패 시 `alembic stamp head`를 시도한다. | 현재 스크립트는 운영 트래픽, 데이터 migration 실패, frontend/backend 버전 불일치에 대한 정책을 설명하지 않는다. |
| 데이터 백업/복구 | PostgreSQL, pgvector embedding, MinIO object, Redis 또는 LangGraph checkpoint의 백업 주기, RTO/RPO, 복구 drill, retention은 `확인 필요`다. | `docker-compose.yml`, `docker-compose.preview.yml`은 volume을 정의하지만 백업 job, lifecycle, 복구 절차는 없다. | 프로젝트, 요구사항, 지식 문서, artifact version lineage가 유실되면 서비스 기능과 추적성이 동시에 깨진다. |
| 네트워크/TLS | 운영 도메인, TLS 종료 지점, reverse proxy, load balancer, CORS 최종 origin, SSE buffering 비활성화와 idle timeout은 `확인 필요`다. | `frontend/next.config.ts`, `backend/src/core/cors.py`, `docker-compose.preview.yml` 주석에는 일부 origin과 preview 도메인만 보인다. | Agent SSE는 프록시 buffering/timeout에 민감하고, CORS/TLS 설정은 배포 환경별로 달라진다. |
| 관측/장애 대응 | 로그 수집 위치, request_id 추적, 모니터링 대시보드, 알림 채널, 장애 등급, 온콜, 사용자 공지와 postmortem 기준은 `확인 필요`다. | `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py`에서 애플리케이션 로그만 확인되고 중앙 수집/알림 설정은 없다. | 코드 로깅은 애플리케이션 내부 로그 형식만 설명하며 운영 관측 체계와 대응 SLA를 정의하지 않는다. |
| LLM/외부 API | Azure OpenAI/OpenAI 계정, deployment name, 모델 버전, rate limit, 비용 한도, 장애 시 fallback/재시도 정책은 `확인 필요`다. | `backend/src/services/llm_svc.py`, `.env.prod.example`, `.env.preview.example`은 provider별 변수와 기본 모델 예시만 제공한다. | 생성 기능과 RAG 품질, 비용, 장애 응답이 외부 계정 정책에 의존한다. |
| 문서 처리/보안 | 업로드 파일 크기 제한, 악성 파일 검사, 개인정보/민감정보 처리, MinIO 암호화와 bucket 정책은 `확인 필요`다. | `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/storage_svc.py`에서 처리 흐름은 보이지만 운영 보안 정책은 없다. | 지식 문서 원본과 파싱 결과가 저장되므로 보안/컴플라이언스 기준이 필요하다. |
| 인증/권한 | 실제 로그인, 세션 저장 위치, 사용자/역할 권한, PR 승인자 권한, audit log 보존 기준은 `확인 필요`다. | `frontend/src/lib/api.ts`는 401 시 `/login` 이동을 처리하지만 백엔드 인증/인가 정책은 명확히 확인되지 않는다. | 유지보수 중 관리자 기능, artifact PR, 데이터 삭제 권한을 임의로 가정하면 보안 결함으로 이어질 수 있다. |
| 테스트 데이터/Smoke | Agent smoke 검증에 필요한 seeded project/session, 외부 LLM/embedding 계정, 프론트엔드 E2E 필수 시나리오와 도구는 `확인 필요`다. | `backend/scripts/smoke_langgraph_chat.py`, `frontend/package.json`, `backend/tests/conftest.py`는 일부 검증 수단만 보여준다. | 신입 개발자가 로컬에서 재현 가능한 검증과 운영 의존 검증을 구분해야 한다. |
| 데이터 삭제/보관 | soft delete 보관 기간, hard delete 승인 절차, 개인정보 삭제 요청 처리, artifact version 보존 기간은 `확인 필요`다. | `backend/src/models/project.py`, `backend/src/services/project_svc.py`, `backend/src/models/artifact.py`에는 데이터 구조와 일부 삭제 경로만 확인된다. | 데이터 lifecycle 정책은 코드 구조만으로 결정할 수 없는 운영/법무 기준이다. |
