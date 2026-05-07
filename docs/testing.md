# Testing Guide

## 개요

이 문서는 AISE 코드베이스를 처음 맡은 개발자가 테스트 실행 순서, 테스트 종류, 성공 기준, 실패 시 먼저 확인할 지점을 빠르게 이해하도록 정리한 테스트 전용 문서다. 저장소에서 코드와 설정으로 확인되는 테스트 체계는 backend `pytest`, frontend lint/format/build, Docker Compose smoke check다.

운영 CI/CD에서 어떤 테스트를 필수 게이트로 삼는지, frontend 단위/E2E 테스트를 별도로 운영하는지는 저장소에서 확인되지 않으므로 `확인 필요`로 표시한다.

## 관련 파일

| 영역 | 관련 파일 | 확인할 내용 |
| --- | --- | --- |
| Backend pytest 설정 | `backend/pyproject.toml` | `pytest`, `pytest-asyncio`, `pytest-cov` dev dependency와 `asyncio_mode = "auto"`, `pythonpath = ["."]` 설정 |
| Backend 테스트 fixture | `backend/tests/conftest.py` | 테스트 DB URL, FastAPI dependency override, 테스트 후 테이블 정리 순서, DB 미준비 시 실패 메시지 |
| 테스트 DB 준비 | `backend/scripts/setup_test_db.py`, `backend/scripts/setup_test_db.sh` | `aise_test` 생성, `TEST_DB_*` override, Alembic migration 적용 |
| Backend 테스트 파일 | `backend/tests` | router, service, agent, orchestration, RAG, artifact, HITL 관련 pytest |
| Frontend 검증 스크립트 | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/eslint.config.mjs`, `frontend/tsconfig.json` | pnpm 기반 설치, lint, format check, Next.js build 설정 |
| Runtime smoke check | `docker-compose.yml`, `docker-compose.preview.yml`, `backend/src/main.py`, `backend/src/routers/sample.py`, `frontend/next.config.ts` | backend 직접 접근, frontend rewrite, compose service port |
| 배포 전 테스트 문맥 | `docs/deployment-ops.md`, `docs/setup.md`, `docs/maintenance.md` | 배포 전 검증 순서, 환경 구성, 변경 유형별 테스트 우선순위 |

## 테스트 실행 절차

처음 로컬에서 테스트를 실행할 때는 테스트 DB 준비, backend 테스트, frontend 정적 검증, smoke check 순서로 진행한다. DB가 필요한 backend 테스트가 먼저 실패하면 이후 테스트 결과도 신뢰하기 어렵기 때문이다.

### 1. 테스트 DB 준비

```bash
docker compose up -d postgres
cd backend
bash scripts/setup_test_db.sh
```

성공 기준:

- `docker compose ps postgres`에서 PostgreSQL 컨테이너가 실행 중이다.
- `scripts/setup_test_db.sh`가 `uv run python scripts/setup_test_db.py`를 실행한다.
- `setup_test_db.py`가 `aise_test` DB 존재 여부를 확인하고 `uv run alembic upgrade head`를 성공적으로 완료한다.

실패 시 확인 지점:

- `backend/tests/conftest.py`의 기본 테스트 DB URL은 `postgresql+asyncpg://aise:aise1234@localhost:5432/aise_test`다.
- 기본 compose PostgreSQL 포트는 `localhost:5432`다. preview compose의 포트 `5433`을 쓰려면 `TEST_DB_PORT=5433`처럼 명시해야 한다.
- DB 생성 권한 또는 포트 충돌이 의심되면 `docker compose logs --tail 100 postgres`를 먼저 확인한다.

다른 테스트 DB를 사용할 때:

```bash
cd backend
TEST_DB_HOST=localhost TEST_DB_PORT=5432 TEST_DB_NAME=aise_test bash scripts/setup_test_db.sh
```

확인 필요:

- 로컬/CI에서 테스트 DB를 Docker Compose로 띄우는지, 별도 PostgreSQL 인스턴스를 쓰는지 확인 필요.
- CI에서 DB 생성 권한을 어떤 계정에 부여하는지 확인 필요.

### 2. Backend 전체 테스트

```bash
cd backend
uv sync
uv run pytest
```

테스트 종류:

| 종류 | 대표 파일 | 검증하는 흐름 |
| --- | --- | --- |
| API/router 테스트 | `backend/tests/test_project.py`, `backend/tests/test_agents_router.py`, `backend/tests/test_section.py` | FastAPI router, request/response schema, DB 저장 결과 |
| Service 테스트 | `backend/tests/test_artifact_svc.py`, `backend/tests/test_query_rewriter.py`, `backend/tests/test_text_chunker.py` | service 함수의 상태 전이, 텍스트 처리, artifact workflow |
| Agent 테스트 | `backend/tests/test_agent.py`, `backend/tests/test_general_chat.py`, `backend/tests/test_srs_generator_agent.py`, `backend/tests/test_testcase_generator_agent.py` | agent registry, supervisor routing, LLM 호출 stub, 산출물 생성 흐름 |
| Orchestration/RAG 테스트 | `backend/tests/test_orchestration.py`, `backend/tests/test_retrieval_gate.py`, `backend/tests/test_rag_isolation.py` | LangGraph 흐름, retrieval gate, project_id 기반 RAG 격리 |
| Review/HITL 테스트 | `backend/tests/test_review.py`, `backend/tests/test_hitl_interrupt.py` | 리뷰 결과 생성, Human-in-the-loop interrupt 처리 |

성공 기준:

- `uv run pytest`가 exit code `0`으로 종료한다.
- 테스트 시작 전에 `conftest.py`의 `_verify_test_db_ready` fixture가 테스트 DB 접속에 성공한다.
- 각 테스트 뒤 `conftest.py`의 cleanup 로직이 프로젝트, 요구사항, artifact, 세션, 지식 문서 테이블 데이터를 정리한다.

실패 시 확인 지점:

- `Test database is not initialised` 메시지가 나오면 `cd backend && bash scripts/setup_test_db.sh`를 다시 실행한다.
- DB 관련 traceback이면 `backend/tests/conftest.py`의 `TEST_DATABASE_URL`, `CLEANUP_TABLES`, 최근 Alembic migration 파일을 함께 확인한다.
- API assertion 실패는 해당 테스트 파일의 endpoint와 `backend/src/routers`, `backend/src/services`, `backend/src/models`, `backend/src/schemas/api`를 같이 추적한다.
- Agent/RAG 실패는 `backend/src/agents`, `backend/src/orchestration`, `backend/src/services/rag_svc.py`, `backend/src/services/llm_svc.py`를 먼저 확인한다.

### 3. Backend 부분 테스트와 커버리지

변경 범위가 좁을 때는 관련 테스트만 먼저 재현하고, 최종 제출 전 전체 테스트를 실행한다.

```bash
cd backend
uv run pytest tests/test_project.py
uv run pytest tests/test_orchestration.py -k retrieval
uv run pytest --cov=src --cov-report=term-missing --cov-report=html
```

성공 기준:

- 부분 테스트는 변경한 기능과 직접 관련된 실패를 빠르게 재현하거나 해결하는 용도다.
- 최종 성공 기준은 관련 부분 테스트와 `uv run pytest` 전체 통과다.
- coverage HTML 리포트는 기본적으로 `backend/htmlcov`에 생성된다.

확인 필요:

- 목표 커버리지 수치, CI 업로드 위치, 커버리지 미달 시 배포 차단 여부는 확인 필요.
- hotfix 상황에서 부분 테스트만으로 배포를 허용하는 기준은 확인 필요.

### 4. Frontend 정적 검증과 build

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm lint
pnpm format:check
BACKEND_URL=http://backend:8081 pnpm build
```

테스트 종류:

| 종류 | 명령 | 검증하는 내용 |
| --- | --- | --- |
| 의존성 재현성 | `pnpm install --frozen-lockfile` | `pnpm-lock.yaml` 기준 설치가 재현되는지 확인 |
| Lint | `pnpm lint` | ESLint와 Next.js/TypeScript 규칙 위반 확인 |
| Format check | `pnpm format:check` | Prettier 포맷 이탈 확인 |
| Production build | `BACKEND_URL=http://backend:8081 pnpm build` | Next.js build, route compilation, `/api/*` rewrite 대상 env 사용 |

성공 기준:

- 각 명령이 exit code `0`으로 종료한다.
- `pnpm build`가 `.next` build 산출물을 생성한다.
- `frontend/next.config.ts`의 rewrite가 `BACKEND_URL`을 기준으로 설정되므로 build 또는 smoke check 시 대상 URL을 명시한다.

실패 시 확인 지점:

- lint/format 실패는 출력된 파일 경로와 rule 이름을 기준으로 수정한다.
- build 실패는 Next.js가 출력한 page, component, type error, env 관련 메시지를 먼저 확인한다.
- package manager 오류가 나면 `frontend/package.json`의 `packageManager: pnpm@9.15.0`, `preinstall: npx only-allow pnpm`, `frontend/pnpm-lock.yaml`을 확인한다.

확인 필요:

- `frontend/package.json`에는 `test`, `vitest`, `jest`, `playwright` script가 없다. frontend 단위 테스트 또는 E2E 테스트 도입 여부와 공식 실행 명령은 확인 필요.
- `frontend/Dockerfile`은 `npm ci`와 `npm run build`를 사용하지만 저장소 정책은 pnpm으로 선언되어 있다. Docker build의 패키지 매니저 표준은 확인 필요.

### 5. Smoke check

서비스가 실제로 기동한 뒤에는 API 직접 접근과 frontend rewrite를 나누어 확인한다.

```bash
docker compose up -d --build
docker compose ps
curl -s http://localhost:8081/api/v1/sample/health
curl -s http://localhost:8081/docs
curl -s http://localhost:4000/api/v1/sample/health
curl -I http://localhost:4000
```

preview compose를 확인할 때:

```bash
docker compose -f docker-compose.preview.yml up -d --build
docker compose -f docker-compose.preview.yml ps
curl -s http://localhost:8181/docs
curl -s http://localhost:4100/api/v1/sample/health
```

성공 기준:

- compose service가 `running` 또는 `healthy` 상태다.
- backend 직접 API가 응답한다.
- frontend host의 `/api/v1/sample/health` 요청이 Next.js rewrite를 거쳐 backend로 전달된다.
- frontend root가 HTTP 응답을 반환한다.

실패 시 확인 지점:

- backend 직접 API 실패: `docker compose logs --tail 200 backend`, `backend/Dockerfile`, `backend/src/main.py`, `backend/src/routers/sample.py`
- frontend rewrite 실패: `docker compose logs --tail 200 frontend`, `frontend/next.config.ts`, compose의 `BACKEND_URL`
- DB 연결 실패: `docker compose logs --tail 100 postgres`, `backend/src/core/database.py`, `backend/alembic/versions`
- MinIO 또는 문서 업로드 실패: `docker compose logs --tail 100 minio`, `backend/src/services/storage_svc.py`

확인 필요:

- 운영 환경의 공식 health check URL, `/docs` 공개 여부, 리버스 프록시/TLS 경유 smoke check 주소는 확인 필요.
- sample API를 운영 health check로 사용해도 되는지 확인 필요.

## 변경 유형별 권장 테스트

| 변경 유형 | 우선 실행 명령 | 추가 확인 파일 | 성공 기준 | 실패 시 먼저 볼 곳 |
| --- | --- | --- | --- | --- |
| DB model 또는 migration 변경 | `cd backend && uv run alembic upgrade head`, `uv run pytest` | `backend/src/models`, `backend/alembic/versions`, `backend/tests/conftest.py` | migration 적용 후 전체 테스트 통과 | Alembic revision, FK cleanup 순서, DB URL |
| API router/schema 변경 | `cd backend && uv run pytest tests/test_project.py`, 이후 `uv run pytest` | `backend/src/routers`, `backend/src/schemas/api`, `frontend/src/services` | API response 계약과 frontend service 호출이 일치 | 실패한 endpoint, Pydantic schema, service return |
| Agent/LLM 흐름 변경 | `cd backend && uv run pytest tests/test_agent.py tests/test_orchestration.py` | `backend/src/agents`, `backend/src/orchestration`, `backend/src/services/llm_svc.py` | supervisor routing과 agent output state가 기대값과 일치 | tool_call/tool_result event, mocked LLM response |
| RAG/지식 문서 변경 | `cd backend && uv run pytest tests/test_rag_isolation.py tests/test_retrieval_gate.py` | `backend/src/services/rag_svc.py`, `backend/src/services/knowledge_svc.py`, `backend/src/services/embedding_svc.py` | project_id 격리와 retrieval gate 조건 유지 | project_id filter, inactive document 처리, embedding stub |
| Artifact workflow 변경 | `cd backend && uv run pytest tests/test_artifact_svc.py` | `backend/src/services/artifact_svc.py`, `backend/src/models/artifact.py`, `frontend/src/components/artifacts` | dirty/staged/clean 상태 전이와 PR 흐름 유지 | 상태 전이 조건, current_version/open_pr FK |
| Frontend UI/service 변경 | `cd frontend && pnpm lint && pnpm format:check && pnpm build` | `frontend/src/app`, `frontend/src/components`, `frontend/src/services`, `frontend/src/stores` | 정적 검증과 production build 통과 | ESLint rule, TypeScript 오류, API base path |
| Compose/Docker 변경 | `docker compose config`, `docker compose up -d --build`, smoke check | `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | compose 구문 통과, 컨테이너 기동, API/frontend 응답 | env_file, port, build arg, startup log |

## 유지보수 포인트

- 신규 backend 테이블을 추가하면 `backend/tests/conftest.py`의 `CLEANUP_TABLES`에 FK 의존 순서를 반영해야 테스트 간 데이터가 섞이지 않는다.
- 신규 Alembic migration을 추가하면 테스트 DB 준비 스크립트로 `aise_test`에도 적용되는지 확인한다.
- LLM 호출 경로는 실제 외부 API를 직접 호출하지 않도록 테스트에서 stub 또는 mock 패턴을 유지한다.
- frontend에 테스트 runner를 도입하면 `frontend/package.json` scripts, 이 문서, `docs/README.md`, `docs/deployment-ops.md`의 검증 명령을 함께 갱신한다.
- 배포 게이트가 정해지면 `확인 필요`로 남긴 CI/CD 테스트 기준을 실제 명령과 승인 기준으로 바꾼다.

## 확인 필요

- CI/CD 파이프라인 파일이 저장소에서 확인되지 않는다. 어떤 테스트가 PR/merge/deploy 필수 게이트인지 확인 필요.
- frontend 단위 테스트, 통합 테스트, E2E 테스트 실행 명령은 저장소에서 확인되지 않는다.
- backend lint, typecheck, format 표준 도구는 `backend/pyproject.toml`에서 확인되지 않는다.
- 테스트용 secret, 외부 LLM key, object storage endpoint를 CI에서 어떻게 주입하는지 확인 필요.
- 운영 smoke check URL, `/docs` 접근 정책, 장애 대응 기준, 테스트 실패 시 배포 중단/rollback 기준은 확인 필요.
