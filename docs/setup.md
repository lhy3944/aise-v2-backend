# Setup

이 문서는 처음 저장소를 받는 개발자가 로컬 실행 환경을 맞출 때 필요한 런타임과 버전 요구사항을 정리한다. 버전은 코드와 설정 파일에서 확인 가능한 값만 확정값으로 적고, 저장소에서 확인되지 않는 항목은 `확인 필요`로 표시한다.

## 관련 파일

| 파일 | 확인한 내용 |
| --- | --- |
| `backend/pyproject.toml` | 백엔드 Python 요구 버전, Python 패키지 의존성, pytest 설정 |
| `backend/uv.lock` | 백엔드 의존성 잠금 파일 |
| `backend/Dockerfile` | 백엔드 컨테이너 Python 이미지, `uv` 사용, 실행 포트 |
| `backend/tests/conftest.py` | pytest 테스트 DB URL, 테스트 DB 준비 실패 시 안내 문구, 테스트 후 테이블 정리 방식 |
| `backend/scripts/setup_test_db.py` | `aise_test` 테스트 DB 생성 및 Alembic 마이그레이션 적용 명령 |
| `backend/scripts/setup_test_db.sh` | Python 테스트 DB 준비 스크립트의 shell wrapper |
| `frontend/package.json` | 프론트엔드 Node 요구 버전, pnpm 버전, Next.js/React 버전, npm scripts |
| `frontend/pnpm-lock.yaml` | 프론트엔드 의존성 잠금 파일 |
| `frontend/Dockerfile` | 프론트엔드 컨테이너 Node 이미지, standalone 빌드, 실행 포트 |
| `docker-compose.yml` | 로컬/기본 Docker 서비스와 PostgreSQL, MinIO, Redis 이미지 |
| `docker-compose.preview.yml` | preview 환경 Docker 서비스와 포트 분리 |
| `start-local.sh` | 로컬 개발 서버 실행 포트와 `uv`, `npm`, `npx next dev` 사용 |
| `start-dev.sh` | 로컬 개발 서버 실행 포트와 `uv`, `pnpm`, `pnpm exec next dev` 사용 |
| `.env.prod.example` | 운영용 예시 환경변수 |
| `.env.preview.example` | preview용 예시 환경변수 |

## 실행 환경 관련 코드/설정 경로 상세

처음 환경을 구성할 때는 아래 경로를 기준으로 "어떤 명령이 어디에서 정의되는지"를 확인한다. 저장소 루트에 백엔드와 프론트엔드가 함께 있지만, 의존성 설치, 실행, 환경변수 주입 지점이 서로 다르므로 경로를 구분해서 보는 것이 좋다.

| 범위 | 관련 파일 경로 | 확인할 내용 |
| --- | --- | --- |
| 루트 실행 스크립트 | `start-dev.sh`, `start-local.sh` | 로컬 개발 서버 포트, 백엔드/프론트엔드 동시 실행 순서, 의존성 설치 명령, `BACKEND_URL` 주입 여부 |
| 기본 Docker 실행 | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | 기본 compose 서비스, 포트 매핑, 컨테이너 빌드 방식, backend entrypoint의 Alembic 실행, frontend standalone 실행 |
| Preview Docker 실행 | `docker-compose.preview.yml`, `deploy/preview.sh` | preview 포트 분리, preview compose 파일, preview 전용 `.env.preview` 주입 |
| 운영 배포 스크립트 | `deploy.sh`, `.env.prod.example` | 기본 운영 compose 실행 순서, `HOST_IP` 사용, 운영 예시 환경변수 |
| 백엔드 패키지/테스트 설정 | `backend/pyproject.toml`, `backend/uv.lock`, `backend/tests/conftest.py` | Python 버전, 의존성, pytest 설정, 테스트 DB URL, 테스트 데이터 정리 방식 |
| 백엔드 앱 진입점 | `backend/src/main.py`, `backend/src/core/database.py`, `backend/alembic/env.py`, `backend/alembic/versions/` | FastAPI 앱 로딩, `.env` 로딩, DB URL 사용 위치, Alembic 마이그레이션 경로 |
| 백엔드 외부 서비스 설정 | `backend/src/services/storage_svc.py`, `backend/src/services/llm_svc.py`, `backend/src/services/embedding_svc.py`, `backend/src/orchestration/graph.py`, `backend/src/orchestration/retrieval_gate.py` | MinIO, LLM, 임베딩, LangGraph checkpointer, RAG gate 관련 환경변수 |
| 테스트 DB 준비 | `backend/scripts/setup_test_db.py`, `backend/scripts/setup_test_db.sh` | `aise_test` 생성, `TEST_DB_*` 변수, Alembic 적용 명령 |
| 프론트엔드 패키지/검증 설정 | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/eslint.config.mjs`, `frontend/next.config.ts`, `frontend/tsconfig.json`, `frontend/postcss.config.mjs` | Node/pnpm 버전, npm scripts, lint 설정, Next.js rewrites, TypeScript/PostCSS 설정 |
| 프론트엔드 API 연결 | `frontend/src/lib/api.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `frontend/src/services/knowledge-service.ts`, `frontend/src/services/agent-service.ts`, `frontend/src/services/artifact-record-service.ts` | `NEXT_PUBLIC_API_URL`, `BACKEND_URL`, `/api` rewrite, SSE 프록시 사용 지점 |
| 문서화된 운영 참고 | `docs/deployment-ops.md`, `docs/architecture.md`, `docs/maintenance.md` | 환경 구성 이후 배포, 아키텍처, 유지보수 흐름을 이어서 확인할 문서 |

코드에서 확인되지 않은 서버 계정, 클라우드 리소스, CI/CD 파이프라인, 운영 장애 대응 기준은 이 문서의 각 섹션에서 `확인 필요`로 표시한다.

## 필수 런타임 및 버전

| 구분 | 요구사항 | 근거 | 비고 |
| --- | --- | --- | --- |
| Python | `>=3.14` | `backend/pyproject.toml`의 `requires-python` | Docker 이미지는 `python:3.14-rc-slim`을 사용한다. Python 3.14 정식/RC 사용 여부는 팀 기준 `확인 필요`. |
| Python 패키지 관리자 | `uv` | `backend/Dockerfile`, `start-local.sh`, `start-dev.sh` | Dockerfile은 `pip install uv` 후 `uv sync --frozen --no-dev`를 실행한다. 로컬 스크립트도 `uv sync`, `uv run`을 사용한다. |
| Backend ASGI 서버 | `uvicorn` | `backend/Dockerfile`, `start-local.sh`, `start-dev.sh` | 컨테이너는 `uvicorn src.main:app --host 0.0.0.0 --port 8081`로 실행한다. |
| Node.js | `>=20` | `frontend/package.json`의 `engines.node`, `frontend/Dockerfile` | Docker 이미지는 `node:20-alpine`을 사용한다. |
| Frontend 패키지 관리자 | `pnpm@9.15.0` | `frontend/package.json`의 `packageManager`, `frontend/pnpm-lock.yaml` | `preinstall`에서 `npx only-allow pnpm`을 강제한다. |
| Next.js | `16.1.6` | `frontend/package.json` | `output: 'standalone'` 설정으로 컨테이너 실행 파일을 생성한다. |
| React | `19.2.3` | `frontend/package.json` | `react`, `react-dom` 모두 `19.2.3`이다. |
| TypeScript | `^5.9.3` | `frontend/package.json` | 프론트엔드 개발 의존성이다. |
| Docker | 버전 `확인 필요` | `docker-compose.yml`, `docker-compose.preview.yml`, `deploy.sh`, `deploy/preview.sh` | Compose 기반 실행이 제공되지만 Docker Engine/Compose 최소 버전은 저장소에 명시되어 있지 않다. |
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | `docker-compose.yml`, `docker-compose.preview.yml` | 기본 DB 컨테이너 이미지다. 백엔드는 SQLAlchemy asyncpg URL을 사용한다. |
| Redis | `redis:7-alpine` | `docker-compose.yml` | 기본 compose에는 포함되어 있고 preview compose에는 포함되어 있지 않다. preview의 Redis 사용 여부는 `확인 필요`. |
| MinIO | `minio/minio:latest` | `docker-compose.yml`, `docker-compose.preview.yml` | `latest` 태그라 정확한 버전 고정은 `확인 필요`. |

## 신규 개발자 로컬 구성 체크리스트

처음 저장소를 받은 개발자는 아래 순서대로 진행하면 된다. 각 단계는 코드에서 확인되는 설정 파일을 기준으로 작성했으며, 계정/비밀값/운영 기준처럼 저장소에 없는 정보는 `확인 필요`로 남긴다.

| 순서 | 단계 | 실행 명령 | 완료 기준 | 근거 파일 |
| --- | --- | --- | --- | --- |
| 1 | 필수 도구 확인 | `python --version`, `uv --version`, `node --version`, `pnpm --version`, `docker --version`, `docker compose version` | Python `>=3.14`, Node `>=20`, pnpm `9.15.0` 확인. uv와 Docker 최소 버전은 `확인 필요` | `backend/pyproject.toml`, `frontend/package.json`, `docker-compose.yml` |
| 2 | pnpm 준비 | `corepack enable && corepack prepare pnpm@9.15.0 --activate` 또는 `npm install -g pnpm@9.15.0` | `pnpm --version`이 `9.15.0`을 반환 | `frontend/package.json` |
| 3 | 환경 파일 준비 | `cp .env.prod.example .env.prod`, `cp .env.prod.example backend/.env` | 루트 Docker용 `.env.prod`와 로컬 백엔드용 `backend/.env`가 존재 | `.env.prod.example`, `backend/src/main.py`, `docker-compose.yml` |
| 4 | 외부 서비스 시작 | `docker compose up -d postgres minio redis` | PostgreSQL, MinIO, Redis 컨테이너가 실행 중 | `docker-compose.yml` |
| 5 | 백엔드 의존성 설치 | `cd backend && uv sync` | `uv.lock` 기준 의존성 설치 완료 | `backend/pyproject.toml`, `backend/uv.lock` |
| 6 | DB 스키마 초기화 | `cd backend && uv run alembic upgrade head` | Alembic migration이 최신 revision까지 적용 | `backend/alembic/env.py`, `backend/alembic/versions/` |
| 7 | 프론트엔드 의존성 설치 | `cd frontend && pnpm install` | `frontend/node_modules` 생성, pnpm lock 기준 설치 완료 | `frontend/package.json`, `frontend/pnpm-lock.yaml` |
| 8 | 개발 서버 실행 | `./start-dev.sh` 또는 아래의 backend/frontend 개별 실행 명령 | backend `9999` 또는 지정 포트, frontend `3009` 응답 | `start-dev.sh`, `start-local.sh`, `frontend/next.config.ts` |
| 9 | 초기 smoke check | `curl -s http://localhost:9999/api/v1/sample/health`, `curl -I http://localhost:3009` | health API가 성공 응답을 반환하고 frontend가 HTTP 응답 헤더를 반환 | `backend/src/routers/sample.py`, `frontend/src/app/(main)/page.tsx` |

이 체크리스트에서 가장 자주 막히는 지점은 환경 파일, PostgreSQL migration, 프론트엔드 패키지 매니저다. `.env.prod.example`은 LLM 키가 비어 있으므로 sample API, 프로젝트 목록, Swagger UI 같은 기본 동작은 확인할 수 있지만 채팅/생성/임베딩 기능은 실제 Azure OpenAI 또는 OpenAI 키 없이는 실패할 수 있다. 실제 키 발급 위치, 팀별 Secret 보관 방식, 개발자 개인 키 사용 가능 여부는 `확인 필요`다.

## 패키지 매니저와 의존성 설치

이 저장소는 백엔드와 프론트엔드가 서로 다른 패키지 매니저를 사용한다. 루트 디렉터리에서 한 번에 모든 의존성을 설치하는 workspace 설정은 코드에서 확인되지 않는다. 처음 환경을 구성할 때는 백엔드와 프론트엔드 디렉터리로 각각 이동해 설치해야 한다.

## 로컬 개발 서버 빠른 실행 명령

처음 실행할 때는 저장소 루트에서 환경 파일과 외부 서비스를 먼저 준비한 뒤 backend/frontend 개발 서버를 시작한다. 코드에서 확인되는 로컬 개발 실행 경로는 `start-dev.sh`, `start-local.sh`, 그리고 backend/frontend 개별 실행 명령이다.

### 권장 로컬 실행 경로: `start-dev.sh`

`start-dev.sh`는 `uv sync`로 백엔드 의존성을 동기화하고, `frontend/node_modules`가 없으면 `pnpm install`을 실행한 뒤 backend와 frontend를 함께 띄운다. 이 스크립트의 PostgreSQL 시작 코드는 주석 처리되어 있으므로 DB, MinIO, Redis는 별도 compose 서비스로 먼저 실행한다.

```bash
# 1. 루트에서 로컬 환경 파일 준비
cp .env.prod.example .env.prod
cp .env.prod.example backend/.env

# 2. 외부 서비스 실행
docker compose up -d postgres minio redis

# 3. DB 마이그레이션 적용
cd backend
uv sync
uv run alembic upgrade head
cd ..

# 4. backend/frontend 개발 서버 실행
./start-dev.sh
```

`start-dev.sh` 기준 접속 주소는 다음과 같다.

| 대상 | 주소 | 근거 |
| --- | --- | --- |
| Backend | `http://localhost:9999` | `start-dev.sh`의 `BACKEND_PORT=9999` |
| Swagger UI | `http://localhost:9999/docs` | FastAPI 기본 문서 경로 |
| Frontend | `http://localhost:3009` | `start-dev.sh`의 `FRONTEND_PORT=3009` |
| PostgreSQL | `localhost:5432` | `docker-compose.yml` postgres port |
| MinIO Console | `http://localhost:9001` | `docker-compose.yml` minio console port |
| Redis | `localhost:6379` | `docker-compose.yml` redis port |

실행 후 기본 동작은 다음 명령으로 확인한다.

```bash
curl -s http://localhost:9999/api/v1/sample/health
curl -s http://localhost:9999/api/v1/projects
curl -I http://localhost:3009
```

### 대체 로컬 실행 경로: `start-local.sh`

`start-local.sh`는 backend를 `8082`, frontend를 `3009`에서 실행하고, frontend 프로세스에 `BACKEND_URL=http://localhost:8082`를 주입한다.

```bash
docker compose up -d postgres minio redis
./start-local.sh
```

확인 명령은 다음과 같다.

```bash
curl -s http://localhost:8082/api/v1/sample/health
curl -s http://localhost:8082/api/v1/projects
curl -I http://localhost:3009
```

주의: `start-local.sh`는 `frontend/node_modules`가 없을 때 `npm install`을 실행하지만, `frontend/package.json`은 `pnpm@9.15.0`과 `preinstall: npx only-allow pnpm`을 지정한다. 이 불일치 때문에 최초 실행에서 의존성 설치가 실패할 수 있으며, 팀 표준 스크립트로 계속 유지할지는 `확인 필요`다.

### backend/frontend 개별 실행

스크립트 대신 터미널을 나누어 직접 실행하려면 다음 순서를 사용한다. 이 방식은 backend 포트와 frontend의 `BACKEND_URL`을 명시적으로 맞출 수 있어 디버깅할 때 가장 투명하다.

```bash
# 터미널 1: 외부 서비스
docker compose up -d postgres minio redis

# 터미널 2: backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --port=8082 --reload --host 0.0.0.0

# 터미널 3: frontend
cd frontend
pnpm install
BACKEND_URL=http://localhost:8082 pnpm dev --hostname 0.0.0.0 --port 3009
```

브라우저에서는 `http://localhost:3009`에 접속한다. 일부 클라이언트 서비스가 `NEXT_PUBLIC_API_URL`을 읽으므로 브라우저에서 백엔드를 직접 호출하는 흐름을 테스트할 때는 frontend 실행 전에 `NEXT_PUBLIC_API_URL=http://localhost:8082`도 함께 지정한다.

### Docker compose로 애플리케이션 전체 실행

컨테이너로 전체 애플리케이션을 실행하려면 다음 명령을 사용한다.

```bash
cp .env.prod.example .env.prod
docker compose up -d --build
docker compose ps
```

기본 접속 주소는 `http://localhost:4000` frontend, `http://localhost:8081` backend, `http://localhost:8081/docs` Swagger UI다. 단, `frontend/Dockerfile`은 `npm ci`를 사용하지만 저장소에는 `package-lock.json`이 없고 프론트엔드 패키지 정책은 pnpm으로 고정되어 있어 현재 Docker frontend 빌드 성공 여부는 `확인 필요`다.

### 최초 설치 명령어

저장소를 처음 받은 뒤 프로젝트 의존성만 먼저 설치하려면 루트 디렉터리에서 아래 순서대로 실행한다. 백엔드는 `backend/uv.lock`, 프론트엔드는 `frontend/pnpm-lock.yaml`을 기준으로 설치된다.

```bash
# 1. 백엔드 Python 의존성 설치
cd backend
uv sync

# 2. 루트로 돌아온 뒤 프론트엔드 Node 의존성 설치
cd ../frontend
corepack enable
corepack prepare pnpm@9.15.0 --activate
pnpm install
```

이미 `pnpm@9.15.0`이 설치되어 있다면 `corepack enable`과 `corepack prepare ...` 단계는 생략할 수 있다. 반대로 Corepack을 사용하지 않는 팀 표준이 있다면 pnpm 설치 방식은 `확인 필요`이며, 아래처럼 전역 설치 후 `pnpm install`을 실행한다.

```bash
cd frontend
npm install -g pnpm@9.15.0
pnpm install
```

| 영역 | 패키지 매니저 | 잠금 파일 | 설치 명령 | 근거 |
| --- | --- | --- | --- | --- |
| Backend | `uv` | `backend/uv.lock` | `cd backend && uv sync` | `backend/Dockerfile`, `start-dev.sh`, `start-local.sh` |
| Frontend | `pnpm@9.15.0` | `frontend/pnpm-lock.yaml` | `cd frontend && pnpm install` | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `start-dev.sh` |
| Docker backend build | `uv` | `backend/uv.lock` | `uv sync --frozen --no-dev` | `backend/Dockerfile` |
| Docker frontend build | `npm` 사용으로 작성됨 | `package-lock.json` 필요하나 저장소에 없음 | `npm ci` | `frontend/Dockerfile`; pnpm 정책과 불일치하므로 `확인 필요` |

### 백엔드 의존성 설치

백엔드는 `backend/pyproject.toml`과 `backend/uv.lock`을 기준으로 의존성을 동기화한다. 개발 환경에서는 테스트 의존성까지 필요하므로 기본 명령은 `uv sync`다.

```bash
cd backend
uv sync
```

Docker 이미지에서는 런타임 의존성만 설치하기 위해 `uv sync --frozen --no-dev --no-install-project` 후 소스 복사 뒤 `uv sync --frozen --no-dev`를 한 번 더 실행한다. 따라서 Docker 빌드에서 의존성 버전은 `backend/uv.lock`에 고정된 상태를 기준으로 재현된다.

```bash
cd backend
uv sync --frozen --no-dev
```

설치 후 백엔드 의존성이 정상인지 빠르게 확인하려면 다음 명령을 사용한다.

```bash
cd backend
uv run pytest
uv run alembic upgrade head
```

### 프론트엔드 의존성 설치

프론트엔드는 `frontend/package.json`의 `packageManager`가 `pnpm@9.15.0`으로 지정되어 있고, `preinstall` 스크립트가 `npx only-allow pnpm`으로 pnpm 사용을 강제한다. 따라서 로컬 개발 환경의 공식 설치 명령은 `pnpm install`이다.

```bash
cd frontend
pnpm install
```

Node.js는 `frontend/package.json`의 `engines.node` 기준으로 `>=20`이 필요하다. pnpm 자체 설치 방식은 저장소에 고정되어 있지 않으므로, Node.js 20 환경에서 Corepack을 사용할지 전역 설치를 사용할지는 팀 표준 `확인 필요`다. 일반적인 준비 명령은 다음 중 하나다.

```bash
corepack enable
corepack prepare pnpm@9.15.0 --activate
```

또는

```bash
npm install -g pnpm@9.15.0
```

설치 후 프론트엔드 의존성이 정상인지 빠르게 확인하려면 다음 명령을 사용한다.

```bash
cd frontend
pnpm lint
pnpm build
```

## 테스트 실행 및 결과 확인

이 저장소에서 코드로 확인되는 자동 검증 경로는 백엔드 `pytest`, 프론트엔드 ESLint/Prettier/Next.js build, 그리고 실행 중인 로컬 서버를 대상으로 하는 HTTP smoke check다. 프론트엔드 단위 테스트 러너(`vitest`, `jest`, `playwright`)와 전용 `pnpm test` 스크립트는 `frontend/package.json`에서 확인되지 않으므로 `확인 필요`다.

### 백엔드 테스트 DB 준비

백엔드 pytest는 `backend/tests/conftest.py` 기준으로 `postgresql+asyncpg://aise:aise1234@localhost:5432/aise_test` 테스트 DB를 사용한다. 테스트 DB는 자동 생성되지 않으며, 최초 1회 또는 DB를 삭제한 뒤에는 준비 스크립트를 먼저 실행해야 한다.

```bash
# 루트 디렉터리에서 PostgreSQL 컨테이너 실행
docker compose up -d postgres

# 테스트 DB 생성 및 Alembic 마이그레이션 적용
cd backend
uv sync
bash scripts/setup_test_db.sh
```

`backend/scripts/setup_test_db.py`는 기본값으로 `TEST_DB_NAME=aise_test`, `TEST_DB_USER=aise`, `TEST_DB_PASSWORD=aise1234`, `TEST_DB_HOST=localhost`, `TEST_DB_PORT=5432`를 사용한다. 다른 DB 포트나 계정을 쓰는 환경에서는 아래처럼 환경변수를 명시한다.

```bash
cd backend
TEST_DB_HOST=localhost TEST_DB_PORT=5432 TEST_DB_NAME=aise_test bash scripts/setup_test_db.sh
```

정상 준비 여부는 스크립트 출력의 마지막 줄에서 `Done. Test DB ready: postgresql+asyncpg://.../aise_test` 메시지로 확인한다. 테스트 DB가 없으면 pytest 시작 시 `Test database is not initialised. Run ./backend/scripts/setup_test_db.sh once, then retry pytest.` 안내와 함께 종료된다.

### 백엔드 pytest 실행

전체 백엔드 테스트는 다음 명령으로 실행한다.

```bash
cd backend
uv run pytest
```

테스트 파일이 많을 때는 대상 파일 또는 테스트 함수를 좁혀 실행한다.

```bash
cd backend
uv run pytest tests/test_project.py
uv run pytest tests/test_orchestration.py -k retrieval
uv run pytest tests/test_agent.py::test_create_agent
```

커버리지 플러그인은 `backend/pyproject.toml`의 개발 의존성에 포함되어 있으므로 다음 명령으로 터미널 커버리지 요약과 HTML 리포트를 생성할 수 있다.

```bash
cd backend
uv run pytest --cov=src --cov-report=term-missing --cov-report=html
```

결과 확인 기준은 다음과 같다.

| 확인 항목 | 정상 기준 | 실패 시 먼저 볼 내용 |
| --- | --- | --- |
| pytest 종료 코드 | `0` | 실패한 테스트 이름, traceback, fixture 에러 |
| 테스트 DB 준비 | `Done. Test DB ready: .../aise_test` 출력 후 pytest 실행 | PostgreSQL 컨테이너 상태, `TEST_DB_*` 환경변수, Alembic 실패 로그 |
| 전체 테스트 요약 | `passed`만 있거나 의도된 `skipped`가 명시됨 | `failed`, `error`, `xfailed`/`xpassed` 요약 |
| 커버리지 HTML | `backend/htmlcov/index.html` 생성 | `pytest-cov` 설치 여부, `uv sync` 실행 여부 |

테스트 후 데이터는 `backend/tests/conftest.py`의 `CLEANUP_TABLES` 순서에 따라 각 테스트 fixture 종료 시 삭제된다. 특정 테스트가 DB 상태에 의존해 실패하면 이전 테스트의 잔여 데이터보다 fixture override, Alembic 스키마, 비동기 세션 처리부터 확인한다.

### 린트 실행 및 결과 확인

현재 코드에서 확인되는 공식 린트 명령은 프론트엔드 `frontend/package.json`의 `lint` 스크립트다. 이 스크립트는 `eslint`를 실행하며, 설정은 `frontend/eslint.config.mjs`에서 Next.js Core Web Vitals와 TypeScript 규칙을 불러온다.

```bash
cd frontend
pnpm install
pnpm lint
```

린트 결과는 터미널 출력과 프로세스 종료 코드로 확인한다.

| 영역 | 명령 | 정상 기준 | 실패 시 확인할 내용 | 근거 |
| --- | --- | --- | --- | --- |
| Frontend ESLint | `cd frontend && pnpm lint` | ESLint error 없이 종료 코드 `0` | 출력된 파일 경로, 줄/열 번호, rule 이름, `frontend/eslint.config.mjs`의 Next.js/TypeScript 규칙 | `frontend/package.json`, `frontend/eslint.config.mjs` |
| Backend lint | `확인 필요` | `확인 필요` | `backend/pyproject.toml`에 Ruff, Black, mypy, pyright 등 린트/타입체크 도구와 스크립트가 없다. 팀 표준 명령 확정 필요 | `backend/pyproject.toml` |

프론트엔드 린트 실패 시 출력 예시는 보통 `파일경로:줄:열`, 문제 설명, rule 이름 순서로 표시된다. 수정 후에는 같은 명령을 다시 실행해 종료 코드가 `0`인지 확인한다.

```bash
cd frontend
pnpm lint
echo $?
```

`echo $?`가 `0`이면 직전 `pnpm lint`가 성공한 것이다. `1` 이상의 값이면 린트 오류 또는 실행 환경 문제로 실패한 것이므로, 터미널에 표시된 첫 번째 오류부터 수정한다. CI/CD에서 이 명령을 품질 게이트로 사용하는지 여부는 저장소에서 확인되지 않으므로 `확인 필요`다.

### 프론트엔드 정적 검증 및 빌드

프론트엔드는 `frontend/package.json`에 전용 테스트 스크립트가 없으므로, 현재 코드에서 확인되는 기본 검증 명령은 lint, format check, production build다.

```bash
cd frontend
pnpm install
pnpm lint
pnpm format:check
pnpm build
```

결과 확인 기준은 다음과 같다.

| 명령 | 정상 기준 | 산출물/확인 위치 |
| --- | --- | --- |
| `pnpm lint` | ESLint error 없이 종료 코드 `0` | 터미널 출력 |
| `pnpm format:check` | Prettier가 `All matched files use Prettier code style!`로 종료 | 터미널 출력 |
| `pnpm build` | Next.js build 성공, 종료 코드 `0` | `frontend/.next/` |

`pnpm test`, 브라우저 E2E, Storybook, 시각 회귀 테스트, Playwright 설정 파일은 코드에서 확인되지 않는다. 도입 여부와 팀의 품질 게이트 기준은 `확인 필요`다.

### 빌드 실행 및 결과 확인 명령어

처음 빌드를 확인할 때는 로컬 프론트엔드 production build, 백엔드 컨테이너 build, 전체 compose build를 분리해서 확인한다. 백엔드는 Python 애플리케이션 자체에 별도 compile/build 스크립트가 없고, Docker 이미지 빌드가 코드에서 확인되는 빌드 경로다. 프론트엔드는 `frontend/package.json`의 `build` 스크립트가 `next build`를 실행한다.

빌드 산출물은 아래 순서로 확인한다. 각 명령은 저장소 루트에서 시작한다고 가정한다.

| 대상 | 빌드 명령 | 산출물 확인 명령 | 정상 기준 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| Frontend 로컬 Next.js build | `cd frontend && pnpm install --frozen-lockfile && BACKEND_URL=http://backend:8081 pnpm build` | `cd frontend && test -d .next && find .next -maxdepth 2 -type d \( -name standalone -o -name static \) -print` | `.next`, `.next/standalone`, `.next/static`이 생성된다. | `frontend/package.json`, `frontend/next.config.ts` | 운영/preview별 `BACKEND_URL` 표준 값 확인 필요 |
| Frontend standalone server 파일 | 위와 동일 | `cd frontend && test -f .next/standalone/server.js && ls -lh .next/standalone/server.js` | Docker runner가 실행할 `server.js`가 존재한다. | `frontend/Dockerfile`, `frontend/next.config.ts` | `output: 'standalone'` 변경 시 Dockerfile도 함께 수정 필요 |
| Backend Docker image | `docker build -t aise2-backend:local ./backend` | `docker image inspect aise2-backend:local --format '{{.Id}} {{json .Config.ExposedPorts}} {{json .Config.Cmd}}'` | 이미지 ID, `8081/tcp`, `/app/entrypoint.sh` CMD가 확인된다. | `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock` | Python `3.14-rc-slim` 운영 사용 여부 확인 필요 |
| Backend image 내부 의존성 | 위와 동일 | `docker run --rm --entrypoint sh aise2-backend:local -lc 'test -x /app/.venv/bin/uvicorn && test -x /app/.venv/bin/alembic && echo ok'` | `ok`가 출력되어 runner 이미지 안의 런타임 명령이 존재한다. | `backend/Dockerfile` | 컨테이너 실행 정책과 보안 스캔 기준 확인 필요 |
| Frontend Docker image | `docker build -t aise2-frontend:local ./frontend` | `docker image inspect aise2-frontend:local --format '{{.Id}} {{json .Config.ExposedPorts}} {{json .Config.Cmd}}'` | 이미지 ID, `3000/tcp`, `node server.js` CMD가 확인된다. | `frontend/Dockerfile`, `frontend/package.json`, `frontend/next.config.ts` | `npm ci`와 pnpm lock 정책 불일치 확인 필요 |
| Frontend image 내부 산출물 | 위와 동일 | `docker run --rm --entrypoint sh aise2-frontend:local -lc 'test -f /app/server.js && test -d /app/.next/static && echo ok'` | `ok`가 출력되어 standalone 서버와 static asset이 runner 이미지에 복사되어 있다. | `frontend/Dockerfile` | Dockerfile을 pnpm 기반으로 고칠지 확인 필요 |
| 기본 compose build | `cp .env.prod.example .env.prod && docker compose build` | `docker compose images && docker compose config --services` | `backend`, `frontend` 이미지와 `postgres`, `minio`, `redis`, `backend`, `frontend` 서비스가 확인된다. | `docker-compose.yml` | 이 compose가 실제 production인지 staging인지 확인 필요 |
| Preview compose build | `cp .env.preview.example .env.preview && docker compose -f docker-compose.preview.yml build` | `docker compose -f docker-compose.preview.yml images && docker compose -f docker-compose.preview.yml config --services` | preview용 backend/frontend 이미지와 `postgres`, `minio`, `backend`, `frontend` 서비스가 확인된다. | `docker-compose.preview.yml` | preview Redis 필요 여부와 preview 전용 image tag 정책 확인 필요 |

주의: `docker run --entrypoint sh ...` 명령은 이미지 내부 파일 존재를 확인하기 위한 산출물 검사다. backend 기본 CMD를 그대로 실행하면 entrypoint가 `alembic upgrade head`를 수행하므로, DB 없이 이미지 산출물만 확인할 때는 위처럼 entrypoint를 바꿔 실행한다.

#### 프론트엔드 production build

```bash
cd frontend
pnpm install
pnpm build
echo $?
test -d .next && echo "frontend build output exists: .next"
```

결과 확인 기준은 다음과 같다.

| 확인 항목 | 정상 기준 | 근거 |
| --- | --- | --- |
| `pnpm build` 종료 코드 | `echo $?`가 `0` | `frontend/package.json`의 `build: next build` |
| Next.js 산출물 | `frontend/.next/` 디렉터리 생성 | Next.js production build 기본 산출물 |
| standalone 산출물 | Docker 빌드 성공 시 `frontend/.next/standalone` 필요 | `frontend/Dockerfile`이 `.next/standalone`을 runner 이미지로 복사 |

`frontend/next.config.ts`에서 `output: 'standalone'`이 유지되어야 Docker runner stage가 필요한 파일을 복사할 수 있다. `pnpm build`는 성공했지만 Docker frontend build가 실패하면 `frontend/Dockerfile`의 패키지 매니저 불일치(`npm ci`와 pnpm 정책)를 먼저 확인한다.

#### 백엔드 Docker 이미지 build

```bash
docker build -t aise2-backend:local ./backend
echo $?
docker image inspect aise2-backend:local --format '{{.Id}} {{.Config.ExposedPorts}}'
```

결과 확인 기준은 다음과 같다.

| 확인 항목 | 정상 기준 | 근거 |
| --- | --- | --- |
| `docker build` 종료 코드 | `echo $?`가 `0` | `backend/Dockerfile` |
| Python 의존성 설치 | build 로그에서 `uv sync --frozen --no-dev` 성공 | `backend/Dockerfile` |
| 노출 포트 | inspect 결과에 `8081/tcp` 포함 | `backend/Dockerfile`의 `EXPOSE 8081` |

이미지를 실행해 진입점까지 확인하려면 PostgreSQL이 먼저 필요하다. 로컬 기본 compose의 DB를 띄운 뒤 backend 컨테이너를 같은 네트워크에서 실행하거나, 더 단순하게 아래 `docker compose up -d --build backend` 경로를 사용한다.

#### 프론트엔드 Docker 이미지 build

현재 `frontend/Dockerfile`은 `npm ci`를 실행하지만 저장소에는 `package-lock.json`이 없고 `frontend/package.json`은 `preinstall`에서 pnpm 사용을 강제한다. 따라서 아래 명령은 Dockerfile의 현재 상태를 검증하기 위한 명령이며, 실패하면 코드와 문서 기준으로는 `확인 필요` 항목이다.

```bash
docker build -t aise2-frontend:local ./frontend
echo $?
docker image inspect aise2-frontend:local --format '{{.Id}} {{.Config.ExposedPorts}}'
```

결과 확인 기준은 다음과 같다.

| 확인 항목 | 정상 기준 | 실패 시 판단 |
| --- | --- | --- |
| `docker build` 종료 코드 | `echo $?`가 `0` | `npm ci`가 lock 파일 부재로 실패하면 Dockerfile 패키지 매니저 정리 `확인 필요` |
| 노출 포트 | inspect 결과에 `3000/tcp` 포함 | `frontend/Dockerfile`의 `EXPOSE 3000`과 비교 |
| standalone 복사 | build 로그에서 `.next/standalone` 복사 성공 | `next.config.ts`의 `output: 'standalone'` 유지 여부 확인 |

#### 전체 compose build 및 실행 확인

전체 애플리케이션 이미지와 의존 서비스를 함께 확인하려면 루트에서 다음 명령을 실행한다.

```bash
cp .env.prod.example .env.prod
docker compose build
echo $?
docker compose up -d
docker compose ps
curl -s http://localhost:8081/api/v1/sample/health
curl -I http://localhost:4000
```

결과 확인 기준은 다음과 같다.

| 확인 항목 | 정상 기준 | 실패 시 먼저 볼 내용 |
| --- | --- | --- |
| `docker compose build` | 종료 코드 `0` | frontend build 실패 시 `frontend/Dockerfile`, backend build 실패 시 `backend/Dockerfile` |
| `docker compose ps` | postgres, minio, redis, backend, frontend가 `running` 또는 `healthy` | `docker compose logs <서비스명>` |
| backend smoke check | health API가 성공 JSON 반환 | DB 연결, Alembic 로그, `backend/src/routers/sample.py` |
| frontend smoke check | `curl -I`가 HTTP 응답 헤더 반환 | frontend 로그, `BACKEND_URL`, `frontend/next.config.ts` |

빌드 산출물을 정리하려면 개발 환경에서만 다음 명령을 사용한다.

```bash
docker compose down
docker image rm aise2-backend:local aise2-frontend:local
```

볼륨까지 삭제하는 `docker compose down -v`는 DB, MinIO, Redis 데이터를 함께 삭제하므로 초기화가 필요한 개발 환경에서만 사용한다.

### 로컬 서버 smoke check

개발 서버 또는 Docker compose로 애플리케이션을 띄운 뒤에는 아래 명령으로 API와 프론트엔드 응답을 확인한다. 포트는 실행 경로에 따라 다르다.

```bash
# start-dev.sh 기준
curl -s http://localhost:9999/api/v1/sample/health
curl -s http://localhost:9999/api/v1/projects
curl -I http://localhost:3009

# start-local.sh 기준
curl -s http://localhost:8082/api/v1/sample/health
curl -s http://localhost:8082/api/v1/projects
curl -I http://localhost:3009

# docker compose up -d --build 기준
curl -s http://localhost:8081/api/v1/sample/health
curl -I http://localhost:4000
docker compose ps
```

정상 기준은 backend health API가 성공 응답을 반환하고, frontend `curl -I`가 `200`, `307`, `308` 등 Next.js가 의도한 HTTP 응답을 반환하며, `docker compose ps`에서 대상 서비스가 `Up` 상태인 것이다. 배포 환경의 공식 smoke test 시나리오와 장애 대응 기준은 코드에서 확인되지 않으므로 `확인 필요`다.

### 스크립트와 Dockerfile의 설치 명령 차이

`start-dev.sh`는 프론트엔드 `node_modules`가 없을 때 `pnpm install`을 실행하므로 `frontend/package.json`의 패키지 매니저 정책과 일치한다. 반면 `start-local.sh`는 `npm install`, `frontend/Dockerfile`은 `npm ci`를 사용한다. 저장소에는 `package-lock.json`이 없고 `preinstall`에서 pnpm을 강제하므로, 두 경로의 실제 성공 여부와 의도된 표준 명령은 `확인 필요`다.

## 백엔드 환경

백엔드는 FastAPI 애플리케이션이며 진입점은 `backend/src/main.py`의 `src.main:app`이다. `backend/src/main.py`에서 `load_dotenv()`를 호출하므로 백엔드 실행 디렉터리의 `.env` 값을 읽을 수 있다.

주요 백엔드 의존성은 `backend/pyproject.toml`에서 확인된다.

| 영역 | 주요 패키지 |
| --- | --- |
| API 서버 | `fastapi[standard]`, `uvicorn` |
| DB/마이그레이션 | `sqlalchemy`, `asyncpg`, `psycopg2-binary`, `psycopg[binary,pool]`, `alembic`, `pgvector` |
| LLM/오케스트레이션 | `openai`, `litellm`, `langgraph`, `langgraph-checkpoint-postgres` |
| 저장소/문서 처리 | `minio`, `pymupdf`, `python-docx`, `python-pptx`, `openpyxl`, `tiktoken` |
| 캐시/상태 | `redis` |
| 테스트 | `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` |

백엔드 기본 포트는 실행 방식에 따라 다르다.

| 실행 방식 | 백엔드 포트 | 근거 |
| --- | --- | --- |
| Docker 기본 compose | 호스트 `8081` -> 컨테이너 `8081` | `docker-compose.yml` |
| Docker preview compose | 호스트 `8181` -> 컨테이너 `8081` | `docker-compose.preview.yml` |
| `start-local.sh` | `8082` | `start-local.sh` |
| `start-dev.sh` | `9999` | `start-dev.sh` |

## 프론트엔드 환경

프론트엔드는 Next.js App Router 기반 애플리케이션이다. `frontend/next.config.ts`에서 `/api/:path*` 요청을 `BACKEND_URL`로 rewrite한다. 브라우저 직접 호출이 필요한 코드는 `NEXT_PUBLIC_API_URL`을 사용하며, 기본값은 빈 문자열이다.

주요 프론트엔드 버전은 `frontend/package.json` 기준이다.

| 항목 | 버전 |
| --- | --- |
| Next.js | `16.1.6` |
| React | `19.2.3` |
| React DOM | `19.2.3` |
| TypeScript | `^5.9.3` |
| Tailwind CSS | `^4` |
| ESLint | `^9` |

프론트엔드 기본 포트도 실행 방식에 따라 다르다.

| 실행 방식 | 프론트엔드 포트 | 근거 |
| --- | --- | --- |
| Docker 기본 compose | 호스트 `4000` -> 컨테이너 `3000` | `docker-compose.yml` |
| Docker preview compose | 호스트 `4100` -> 컨테이너 `3000` | `docker-compose.preview.yml` |
| `start-local.sh` | `3009` | `start-local.sh` |
| `start-dev.sh` | `3009` | `start-dev.sh` |

주의: `frontend/package.json`은 pnpm을 강제하고 `frontend/pnpm-lock.yaml`이 존재하지만, `frontend/Dockerfile`은 `COPY package*.json ./` 후 `npm ci`를 실행한다. 저장소에는 `package-lock.json`이 없으므로 현재 Dockerfile 빌드 가능 여부는 `확인 필요`다.

## 로컬 실행에 필요한 외부 서비스

| 서비스 | 기본 이미지/주소 | 기본 포트 | 용도 |
| --- | --- | --- | --- |
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | `5432` | 애플리케이션 영속 데이터와 Alembic 마이그레이션 대상 |
| MinIO | `minio/minio:latest` | API `9000`, Console `9001` | 지식 문서 등 객체 저장소 |
| Redis | `redis:7-alpine` | `6379` | LangGraph state cache 및 향후 Celery broker 용도로 주석에 명시 |

Preview compose는 PostgreSQL을 `5433`, MinIO를 `9100/9101`, 백엔드를 `8181`, 프론트엔드를 `4100`으로 분리한다. Preview compose에는 Redis 서비스가 없지만 `.env.preview.example`에는 `REDIS_URL=redis://localhost:6380/0`가 있다. preview Redis 실행 방식은 `확인 필요`다.

## 환경변수

환경변수는 실행 방식에 따라 읽는 위치가 다르다. 백엔드는 `backend/src/main.py`에서 `load_dotenv()`를 호출하므로 백엔드 프로세스의 현재 작업 디렉터리에 있는 `.env`를 읽는다. Docker compose 실행은 루트의 `.env.prod` 또는 `.env.preview`를 `env_file`로 백엔드 컨테이너에 주입하고, compose 파일의 `environment` 항목이 일부 값을 다시 덮어쓴다. 프론트엔드는 `BACKEND_URL`을 서버 사이드 rewrite와 SSE 프록시에 사용하고, `NEXT_PUBLIC_API_URL`은 브라우저 번들에 포함되는 공개 값이다.

### 설정 파일 준비

루트에는 예시 파일만 있고 실제 비밀값 파일은 저장소에 포함되어 있지 않다. 로컬 Docker 기본 환경은 `.env.prod.example`을 복사해 `.env.prod`를 만들고, preview 환경은 `.env.preview.example`을 복사해 `.env.preview`를 만든다.

```bash
cp .env.prod.example .env.prod
cp .env.preview.example .env.preview
```

백엔드를 Docker가 아닌 로컬 프로세스로 실행할 때는 `cd backend && uv run uvicorn ...` 형태로 실행하므로 `backend/.env`를 별도로 두는 편이 가장 명확하다. 루트 예시 파일을 그대로 복사해도 되지만, 로컬 포트에 맞춰 DB와 MinIO 주소를 점검해야 한다.

```bash
cp .env.prod.example backend/.env
```

주의: `.env.prod`, `.env.preview`, `backend/.env`에는 API 키와 스토리지 비밀번호가 들어갈 수 있으므로 Git에 커밋하지 않는다. 루트 `.gitignore`는 `.env`, `.env.*`를 무시하고, `frontend/.gitignore`는 프론트엔드 `.env*`를 무시한다.

### 백엔드 애플리케이션 변수

| 변수 | 필수 여부 | 사용처 | 기본값/예시 | 설정 방법과 확인 상태 |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | DB 사용 시 필수 | `backend/src/core/database.py`, `backend/alembic/env.py` | `postgresql+asyncpg://aise:aise1234@localhost:5432/aise` | 로컬 프로세스와 Alembic에서 사용한다. Docker 기본/preview compose는 컨테이너 내부 주소 `postgres:5432`로 덮어쓴다. 운영 DB 계정과 주소는 `확인 필요`. |
| `LANGGRAPH_CHECKPOINT_URL` | 선택 | `backend/src/orchestration/graph.py`, `.env.*.example` | `postgresql://aise:aise1234@localhost:5432/aise`, preview는 `localhost:5433` | 설정하지 않으면 `MemorySaver`를 사용한다. 설정하면 PostgreSQL checkpointer를 초기화한다. `postgresql+asyncpg://`가 아니라 psycopg가 읽는 `postgresql://` 형식이 예시 기준이다. 운영 지속성 정책은 `확인 필요`. |
| `REDIS_URL` | 현재 코드 직접 사용처 확인 안 됨 | `.env.*.example`, `docker-compose.yml` backend 환경 | 기본 `redis://localhost:6379/0`, preview 예시 `redis://localhost:6380/0`, Docker 기본은 `redis://redis:6379/0` | 기본 compose에는 Redis 서비스가 있으나 검색한 애플리케이션 코드에서는 직접 `REDIS_URL`을 읽지 않는다. preview compose에는 Redis 서비스가 없어 실제 필요 여부와 실행 방식은 `확인 필요`. |
| `ENVIRONMENT` | 선택 | `backend/src/core/logging.py`, compose | 코드 기본 `local`, compose 기본 `prod`, preview `preview` | `prod`, `production`, `staging`이면 개발 모드가 아니며 그 외 값은 개발 모드로 간주된다. Docker compose가 환경별로 주입한다. |
| `LOG_LEVEL` | 선택 | `backend/src/core/logging.py` | 개발 모드 `DEBUG`, 그 외 `INFO` | 필요 시 `.env`에 `LOG_LEVEL=INFO`처럼 지정한다. 로그는 `backend/var/logs/app.log`, `backend/var/logs/app.json` 기준으로 생성된다. 운영 로그 수집 방식은 `확인 필요`. |
| `CORS_ORIGINS` | 프론트/백엔드 origin이 다르면 필요 | `backend/src/core/cors.py`, compose | 코드 기본 `http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001` | 쉼표로 구분한다. Docker 기본은 `http://${HOST_IP:-localhost}:4000`, preview는 `https://preview.devbanjang.cloud,http://localhost:4100`을 주입한다. 운영 origin 최종 목록은 `확인 필요`. |
| `CORS_ORIGIN_REGEX` | 선택 | `backend/src/core/cors.py` | localhost, 사설 IP, `*.devbanjang.cloud` 허용 regex | 기본 regex로 대부분의 로컬/preview 주소를 허용한다. 보안 정책상 regex를 좁혀야 하는지는 `확인 필요`. |
| `RAG_GATE_ENABLED` | 선택 | `backend/src/orchestration/retrieval_gate.py` | `true` | 지식 검색 선별 게이트를 끌 때 `false` 계열 값을 사용한다. 코드의 bool 파서는 `1`, `true`, `yes`, `on`만 참으로 본다. |
| `RAG_GATE_TOP_K` | 선택 | `backend/src/orchestration/retrieval_gate.py` | `5` | RAG 게이트가 검색할 상위 문서 수다. 정수 변환 실패 시 기본값을 사용하고 경고 로그를 남긴다. |
| `RAG_GATE_THRESHOLD` | 선택 | `backend/src/orchestration/retrieval_gate.py` | `0.35` | RAG 게이트 통과 유사도 기준이다. float 변환 실패 시 기본값을 사용하고 경고 로그를 남긴다. |

### LLM 및 임베딩 변수

| 변수 | 필수 여부 | 사용처 | 기본값/예시 | 설정 방법과 확인 상태 |
| --- | --- | --- | --- | --- |
| `LLM_PROVIDER` | LLM 기능 사용 시 필요 | `backend/src/services/llm_svc.py`, `.env.*.example` | `azure` | `azure`면 Azure OpenAI 변수 세트를 사용하고, `openai`면 `OPENAI_API_KEY`를 사용한다. 팀의 기본 provider 정책은 `확인 필요`. |
| `SRS_API_KEY`, `SRS_ENDPOINT` | `LLM_PROVIDER=azure`에서 SRS/요구사항/SRS 생성 기능 사용 시 필수 | `backend/src/services/llm_svc.py`, `backend/src/routers/dev/chat.py` | 예시 파일은 빈 값 | Azure SRS 클라이언트 키와 endpoint다. 실제 비밀값과 Azure 리소스는 `확인 필요`. |
| `TC_API_KEY`, `TC_ENDPOINT` | `LLM_PROVIDER=azure`에서 테스트케이스 생성 기능 사용 시 필수 | `backend/src/services/llm_svc.py` | 예시 파일은 빈 값 | Azure TC 클라이언트 키와 endpoint다. 실제 비밀값과 Azure 리소스는 `확인 필요`. |
| `SRS_MODEL` | 선택 | `backend/src/services/llm_svc.py` | `gpt-5.2` | Azure SRS 배포명으로 사용된다. 실제 배포명은 `확인 필요`. |
| `TC_MODEL` | 선택 | `backend/src/services/llm_svc.py` | `gpt-5.2` | Azure TC 배포명으로 사용된다. 실제 배포명은 `확인 필요`. |
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai`에서 필수 | `backend/src/services/llm_svc.py`, `.env.*.example` | 예시 파일은 빈 값 | OpenAI provider 또는 OpenAI 임베딩 클라이언트 사용 시 필요하다. 실제 키는 `확인 필요`. |
| `OPENAI_MODEL` | 선택 | `backend/src/services/llm_svc.py`, `.env.*.example` | `gpt-4o` | `LLM_PROVIDER=openai`일 때 기본 채팅 모델이다. |
| `OPENAI_EMBEDDING_MODEL` | 선택 | `backend/src/services/embedding_svc.py` | `text-embedding-3-small` | OpenAI provider에서 임베딩 모델로 사용된다. |
| `AZURE_EMBEDDING_MODEL` | 선택 | `backend/src/services/embedding_svc.py` | `text-embedding-3-large` | Azure provider에서 임베딩 배포명/모델명으로 사용된다. 실제 Azure 배포명은 `확인 필요`. |

### MinIO 및 객체 저장소 변수

| 변수 | 필수 여부 | 사용처 | 기본값/예시 | 설정 방법과 확인 상태 |
| --- | --- | --- | --- | --- |
| `MINIO_ENDPOINT` | 파일 업로드/다운로드 사용 시 필요 | `backend/src/services/storage_svc.py`, compose backend 환경 | 코드 기본 `localhost:9000`, Docker는 `minio:9000` | 로컬 프로세스는 호스트 포트, Docker backend는 compose 서비스명 `minio:9000`을 사용한다. 운영 endpoint는 `확인 필요`. |
| `MINIO_ACCESS_KEY` | 파일 업로드/다운로드 사용 시 필요 | `backend/src/services/storage_svc.py`, compose backend 환경 | 코드 기본 `aise` | Docker compose에서는 `MINIO_ROOT_USER` 값으로 backend에 주입한다. 운영 계정은 `확인 필요`. |
| `MINIO_SECRET_KEY` | 파일 업로드/다운로드 사용 시 필요 | `backend/src/services/storage_svc.py`, compose backend 환경 | 코드 기본 `aise1234` | Docker compose에서는 `MINIO_ROOT_PASSWORD` 값으로 backend에 주입한다. 운영 비밀값은 `확인 필요`. |
| `MINIO_BUCKET` | 선택 | `backend/src/services/storage_svc.py`, compose backend 환경 | `aise-knowledge` | 버킷이 없으면 `storage_svc.ensure_bucket()`이 생성한다. 운영 버킷 정책, 백업, 암호화는 `확인 필요`. |

### 프론트엔드 변수

| 변수 | 필수 여부 | 사용처 | 기본값/예시 | 설정 방법과 확인 상태 |
| --- | --- | --- | --- | --- |
| `BACKEND_URL` | 프론트엔드 서버가 백엔드로 프록시할 때 필요 | `frontend/next.config.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, compose frontend 환경 | `http://localhost:8081` | Next.js rewrite와 Agent Chat SSE 프록시의 서버 사이드 대상이다. Docker compose는 `http://backend:8081`을 주입한다. `start-local.sh`는 `http://localhost:8082`로 실행한다. |
| `NEXT_PUBLIC_API_URL` | 브라우저에서 백엔드에 직접 호출할 때 필요 | `frontend/src/lib/api.ts`, `frontend/src/services/knowledge-service.ts`, `frontend/src/services/agent-service.ts`, `frontend/src/services/artifact-record-service.ts`, `frontend/Dockerfile` | 빈 문자열 또는 `http://localhost:8081` | 빈 문자열이면 같은 origin의 `/api`로 요청하고 Next.js rewrite가 백엔드로 전달한다. 직접 호출하려면 빌드/실행 전에 `NEXT_PUBLIC_API_URL=http://localhost:8081`처럼 지정한다. `NEXT_PUBLIC_*` 값은 브라우저에 노출되므로 비밀값을 넣지 않는다. |

### Docker compose 치환 변수

| 변수 | 사용처 | 기본값/예시 | 설정 방법과 확인 상태 |
| --- | --- | --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `docker-compose.yml`, `docker-compose.preview.yml`의 postgres와 backend DB URL | `aise`, `aise1234`, `aise` | 루트 `.env` 또는 쉘 환경으로 compose 치환에 사용된다. `.env.prod`/`.env.preview`는 backend `env_file`이며 compose 치환 파일과 역할이 다르므로 혼동하지 않는다. 운영 DB 계정은 `확인 필요`. |
| `POSTGRES_PORT` | `docker-compose.yml` | `5432` | 기본 compose 호스트 DB 포트를 바꿀 때 사용한다. preview compose는 `5433`으로 고정되어 있다. |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | `docker-compose.yml`, `docker-compose.preview.yml`의 MinIO와 backend MinIO 접속 정보 | `aise`, `aise1234` | MinIO root 계정이자 backend의 `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`로 주입된다. 운영 비밀값은 `확인 필요`. |
| `MINIO_PORT`, `MINIO_CONSOLE_PORT` | `docker-compose.yml` | `9000`, `9001` | 기본 compose 호스트 MinIO 포트를 바꿀 때 사용한다. preview compose는 `9100`, `9101`로 고정되어 있다. |
| `REDIS_PORT` | `docker-compose.yml` | `6379` | 기본 compose Redis 호스트 포트다. preview Redis 포트/서비스는 `확인 필요`. |
| `HOST_IP` | `docker-compose.yml`, `deploy.sh`, `deploy/preview.sh` | `localhost` 또는 `hostname -I` 결과 | Docker 기본 compose의 `CORS_ORIGINS`와 배포 스크립트 출력 주소에 사용된다. 서버의 고정 IP/도메인 매핑은 `확인 필요`. |

### 테스트 DB 변수

`backend/scripts/setup_test_db.py`는 pytest용 DB 생성과 Alembic 적용을 위해 별도 변수를 읽는다. 모두 선택값이며 기본 compose의 PostgreSQL 계정과 포트에 맞춰져 있다.

| 변수 | 사용처 | 기본값 |
| --- | --- | --- |
| `TEST_DB_NAME` | `backend/scripts/setup_test_db.py` | `aise_test` |
| `TEST_DB_USER` | `backend/scripts/setup_test_db.py` | `aise` |
| `TEST_DB_PASSWORD` | `backend/scripts/setup_test_db.py` | `aise1234` |
| `TEST_DB_HOST` | `backend/scripts/setup_test_db.py` | `localhost` |
| `TEST_DB_PORT` | `backend/scripts/setup_test_db.py` | `5432` |

테스트 DB를 처음 준비할 때는 다음 명령을 사용한다.

```bash
cd backend
uv run python scripts/setup_test_db.py
```

### 미확인 또는 향후 변수

`.env.prod.example`에는 Langfuse 관련 주석(`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)이 있지만, 현재 검색한 애플리케이션 코드에서 직접 읽는 위치는 확인되지 않았다. `MIGRATION_PLAN.md`에는 Phase 4 관측성 계획으로 언급되어 있으므로 실제 도입 여부, 자체 호스팅 주소, 키 발급 절차는 `확인 필요`다.

## 로컬 실행 및 초기 동작 확인 절차

처음 실행하는 개발자는 먼저 PostgreSQL, MinIO, Redis 같은 외부 서비스를 준비한 뒤 backend와 frontend를 띄우는 순서로 접근한다. `docker-compose.yml`에는 전체 서비스가 정의되어 있어 한 번에 실행할 수 있지만, 현재 `frontend/Dockerfile`은 `npm ci`를 사용하고 저장소에는 `package-lock.json`이 없으며 `frontend/package.json`은 pnpm을 강제한다. 따라서 Docker 전체 빌드가 실패하면 로컬 프로세스 실행 경로를 사용하고, Dockerfile의 패키지 매니저 정리는 `확인 필요`로 남긴다.

### 1. 사전 준비 확인

루트 디렉터리에서 다음 명령으로 필수 도구가 설치되어 있는지 확인한다.

```bash
python --version
uv --version
node --version
pnpm --version
docker --version
docker compose version
```

확인 기준은 `backend/pyproject.toml`, `backend/Dockerfile`, `frontend/package.json`, `frontend/Dockerfile`에 근거한다.

| 도구 | 기대 기준 | 확인 방법 |
| --- | --- | --- |
| Python | `>=3.14` | `python --version` |
| uv | 버전 `확인 필요` | `uv --version` |
| Node.js | `>=20` | `node --version` |
| pnpm | `9.15.0` | `pnpm --version` |
| Docker/Compose | 최소 버전 `확인 필요` | `docker --version`, `docker compose version` |

pnpm이 없으면 Node.js 20 환경에서 다음 중 하나로 준비한다.

```bash
corepack enable
corepack prepare pnpm@9.15.0 --activate
```

또는

```bash
npm install -g pnpm@9.15.0
```

### 2. 환경 파일 준비

Docker compose 기본 환경은 루트의 `.env.prod`를 backend 컨테이너 `env_file`로 읽는다. 저장소에는 예시 파일만 있으므로 처음 실행 전 복사한다.

```bash
cp .env.prod.example .env.prod
```

로컬 프로세스로 backend를 실행할 때는 `cd backend` 상태에서 `uvicorn`이 실행되고 `backend/src/main.py`가 `load_dotenv()`를 호출하므로, backend 작업 디렉터리의 `.env`를 준비한다.

```bash
cp .env.prod.example backend/.env
```

`.env.prod.example`에는 LLM API 키와 Azure/OpenAI endpoint 예시가 빈 값으로 남아 있다. 프로젝트 목록 조회, sample health check, Swagger UI 접근 같은 기본 동작은 DB만 있으면 확인할 수 있지만, 채팅/생성/임베딩/지식 검색 등 LLM 의존 기능은 실제 키와 endpoint 없이는 정상 완료되지 않을 수 있다. 실제 키 발급, 보관 위치, 운영/개발 분리 기준은 `확인 필요`다.

### 3. Docker compose로 전체 실행

루트 디렉터리에서 전체 서비스를 빌드하고 시작한다.

```bash
docker compose up -d --build
docker compose ps
```

기본 접속 주소는 `docker-compose.yml` 기준으로 다음과 같다.

| 대상 | 주소 | 근거 |
| --- | --- | --- |
| Frontend | `http://localhost:4000` | `docker-compose.yml` frontend `4000:3000` |
| Backend | `http://localhost:8081` | `docker-compose.yml` backend `8081:8081` |
| Swagger UI | `http://localhost:8081/docs` | FastAPI 기본 문서 경로 |
| PostgreSQL | `localhost:5432` | `docker-compose.yml` postgres port |
| MinIO API | `http://localhost:9000` | `docker-compose.yml` minio port |
| MinIO Console | `http://localhost:9001` | `docker-compose.yml` minio console port |
| Redis | `localhost:6379` | `docker-compose.yml` redis port |

컨테이너가 모두 올라온 뒤 다음 순서로 초기 동작을 확인한다.

```bash
docker compose ps
curl -s http://localhost:8081/api/v1/sample/health
curl -s http://localhost:8081/api/v1/sample/
curl -s http://localhost:8081/api/v1/projects
curl -I http://localhost:4000
```

기대 결과는 다음과 같다.

| 확인 항목 | 기대 결과 | 실패 시 먼저 볼 곳 |
| --- | --- | --- |
| `docker compose ps` | postgres, minio, redis, backend, frontend가 running 또는 healthy | `docker compose logs <서비스명>` |
| sample health | `{"status":"ok"}` | `backend/src/routers/sample.py`, backend 로그 |
| sample API | `{"message":"Hello, Sample API!"}` | `backend/src/main.py` 라우터 등록 |
| 프로젝트 목록 | `{"projects":[...]}` 형태의 JSON | DB 연결, Alembic migration, `backend/src/routers/project.py` |
| 프론트엔드 | HTTP `200` 계열 응답 | frontend 로그, `frontend/next.config.ts` rewrite 설정 |

주의: frontend 이미지 빌드 단계에서 `npm ci`가 `package-lock.json` 부재로 실패하면 `docker compose up -d postgres minio redis`로 외부 서비스만 띄운 뒤, 아래 로컬 프로세스 실행 절차로 frontend/backend를 실행한다. `frontend/Dockerfile`을 pnpm 기반으로 고칠지, npm lock 파일을 도입할지는 `확인 필요`다.

DB 마이그레이션 상태를 직접 확인하려면 backend 컨테이너 안에서 Alembic 현재 revision을 조회한다.

```bash
docker compose exec backend alembic current
```

로그 확인과 종료 명령은 다음과 같다.

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
```

볼륨까지 삭제해 완전히 초기화하려면 다음 명령을 사용한다. 이 명령은 PostgreSQL, MinIO, Redis 로컬 데이터를 삭제하므로 필요한 데이터가 없는 개발 환경에서만 실행한다.

```bash
docker compose down -v
```

### 4. 로컬 프로세스 실행: backend/frontend만 직접 실행

Docker compose 전체 실행 대신 backend와 frontend를 로컬 프로세스로 띄우려면 외부 서비스부터 준비한다. 기본 compose의 인프라 서비스만 사용하는 방법은 다음과 같다.

```bash
docker compose up -d postgres minio redis
docker compose ps
```

PostgreSQL 준비 상태를 확인한다.

```bash
docker compose exec -T postgres pg_isready -U aise -d aise
```

backend DB 스키마를 적용한다.

```bash
cd backend
uv sync
uv run alembic upgrade head
```

backend를 실행한다. `start-local.sh`와 맞추려면 `8082`, Docker 기본 포트와 맞추려면 `8081`을 사용한다.

```bash
cd backend
uv run uvicorn src.main:app --port=8082 --reload --host 0.0.0.0
```

다른 터미널에서 frontend를 실행한다. `BACKEND_URL`은 `frontend/next.config.ts`의 `/api/:path*` rewrite와 `frontend/src/app/api/v1/agent/chat/route.ts`의 SSE 프록시 대상이다.

```bash
cd frontend
pnpm install
BACKEND_URL=http://localhost:8082 pnpm dev --hostname 0.0.0.0 --port 3009
```

초기 동작은 다음 명령으로 확인한다.

```bash
curl -s http://localhost:8082/api/v1/sample/health
curl -s http://localhost:8082/api/v1/projects
curl -I http://localhost:3009
```

브라우저에서는 `http://localhost:3009`에 접속한다. 프론트엔드가 같은 origin의 `/api/*`로 호출하면 Next.js dev server가 `BACKEND_URL`로 프록시한다. 일부 클라이언트 서비스는 `NEXT_PUBLIC_API_URL`을 읽으므로 직접 백엔드 호출로 테스트해야 하는 경우에는 frontend 실행 전에 다음처럼 지정한다.

```bash
NEXT_PUBLIC_API_URL=http://localhost:8082 BACKEND_URL=http://localhost:8082 pnpm dev --hostname 0.0.0.0 --port 3009
```

### 5. 스크립트로 로컬 개발 서버 실행

루트에는 로컬 실행 편의 스크립트가 두 개 있다.

```bash
./start-dev.sh
```

`start-dev.sh`는 backend를 `9999`, frontend를 `3009`에서 실행한다. backend는 `uv sync` 후 `uv run uvicorn src.main:app --port=9999 --reload --host 0.0.0.0`으로 시작하고, frontend는 `pnpm exec next dev --hostname 0.0.0.0 --port 3009`로 시작한다. PostgreSQL 시작 로직은 주석 처리되어 있으므로 DB, MinIO, Redis는 별도로 준비해야 한다.

```bash
docker compose up -d postgres minio redis
./start-dev.sh
```

초기 확인 명령은 다음과 같다.

```bash
curl -s http://localhost:9999/api/v1/sample/health
curl -s http://localhost:9999/api/v1/projects
curl -I http://localhost:3009
```

다른 스크립트는 다음과 같다.

```bash
./start-local.sh
```

`start-local.sh`는 backend를 `8082`, frontend를 `3009`에서 실행하고 frontend에 `BACKEND_URL=http://localhost:8082`를 주입한다. 다만 `frontend/package.json`은 `pnpm@9.15.0`과 `preinstall: npx only-allow pnpm`을 지정하는데, `start-local.sh`는 `node_modules`가 없을 때 `npm install`을 실행한다. 저장소 정책과 불일치하므로 `start-local.sh`를 처음 실행할 때 의존성 설치가 실패할 수 있으며, 의도된 표준 실행 스크립트는 `확인 필요`다.

### 6. Preview compose 실행

preview 환경 구성을 로컬에서 확인하려면 별도 compose 파일을 사용한다.

```bash
cp .env.preview.example .env.preview
docker compose -f docker-compose.preview.yml up -d --build
docker compose -f docker-compose.preview.yml ps
```

Preview 접속 주소는 `docker-compose.preview.yml` 기준으로 다음과 같다.

| 대상 | 주소 |
| --- | --- |
| Frontend | `http://localhost:4100` |
| Backend | `http://localhost:8181` |
| Swagger UI | `http://localhost:8181/docs` |
| PostgreSQL | `localhost:5433` |
| MinIO API | `http://localhost:9100` |
| MinIO Console | `http://localhost:9101` |

초기 확인 명령은 다음과 같다.

```bash
curl -s http://localhost:8181/api/v1/sample/health
curl -s http://localhost:8181/api/v1/projects
curl -I http://localhost:4100
```

`.env.preview.example`에는 `REDIS_URL=redis://localhost:6380/0`가 있지만 `docker-compose.preview.yml`에는 Redis 서비스가 없다. preview 환경에서 Redis가 필요한지, 별도 Redis를 어떤 주소로 띄우는지는 `확인 필요`다.

### 7. 개발 중 개별 검증 명령어

backend 변경 후에는 다음 명령으로 단위 테스트와 마이그레이션 적용 여부를 확인한다.

```bash
cd backend
uv sync
uv run pytest
uv run alembic upgrade head
```

frontend 변경 후에는 다음 명령으로 lint와 production build를 확인한다.

```bash
cd frontend
pnpm install
pnpm lint
pnpm build
```

## 구성 흐름

1. Python, `uv`, Node.js, pnpm, Docker/Compose를 설치한다.
2. 저장소 루트에서 `.env.prod.example` 또는 `.env.preview.example`을 참고해 실행 환경용 env 파일을 준비한다.
3. Docker 기반 실행이면 `docker compose up -d --build`로 PostgreSQL, MinIO, Redis, backend, frontend를 함께 올린다.
4. 로컬 프로세스 기반 실행이면 PostgreSQL, MinIO, Redis를 먼저 준비한 뒤 `start-local.sh` 또는 `start-dev.sh`로 backend/frontend를 띄운다.
5. 백엔드는 시작 시 Docker entrypoint에서 `alembic upgrade head`를 먼저 실행하고, 실패하면 `alembic stamp head`를 시도한 뒤 서버를 시작한다.
6. 프론트엔드는 `/api/*` 요청을 `BACKEND_URL`로 rewrite하거나, 일부 클라이언트 서비스에서 `NEXT_PUBLIC_API_URL`을 기준으로 API를 호출한다.

## 유지보수 포인트

- Python 요구 버전은 `backend/pyproject.toml`과 `backend/Dockerfile`이 함께 바뀌어야 한다.
- 프론트엔드 패키지 매니저는 `frontend/package.json`의 `packageManager`, `preinstall`, `frontend/pnpm-lock.yaml`, `frontend/Dockerfile`이 일관되어야 한다.
- compose 포트를 변경하면 `CORS_ORIGINS`, `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, 문서의 접속 주소도 함께 갱신해야 한다.
- DB 스키마 변경 후에는 Alembic revision과 `uv run alembic upgrade head` 검증이 필요하다.
- MinIO `latest` 태그는 재빌드 시 런타임이 바뀔 수 있으므로 운영 안정성이 필요하면 고정 태그 전환을 검토해야 한다.
- preview 환경은 기본 compose와 포트/볼륨이 분리되어 있으므로 운영 데이터와 preview 데이터를 혼동하지 않아야 한다.

## 변경 영향 범위

| 변경 대상 | 영향받는 파일/문서 | 같이 확인할 내용 |
| --- | --- | --- |
| Python 또는 backend 의존성 | `backend/pyproject.toml`, `backend/uv.lock`, `backend/Dockerfile`, `backend/README.md`, 이 문서의 `필수 런타임 및 버전` | 로컬 `uv sync`, Docker build, `uv run pytest`, Python 3.14 RC 운영 사용 여부 |
| Node/pnpm 또는 frontend 의존성 | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/Dockerfile`, `start-dev.sh`, `start-local.sh` | pnpm 강제 정책과 Dockerfile `npm ci` 불일치, `pnpm lint`, `pnpm build` |
| 로컬 실행 포트와 API URL | `start-dev.sh`, `start-local.sh`, `frontend/next.config.ts`, `docker-compose.yml`, `docker-compose.preview.yml`, `backend/src/core/cors.py` | CORS origin, `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, smoke check 주소 |
| DB/MinIO/Redis 실행 방식 | `docker-compose.yml`, `docker-compose.preview.yml`, `.env.prod.example`, `.env.preview.example`, `backend/src/core/database.py`, `backend/src/services/storage_svc.py` | volume 보존, preview Redis 구성, MinIO bucket/credential, 운영 백업/복구 `확인 필요` 항목 |
| 테스트 또는 검증 명령 | `backend/pyproject.toml`, `backend/tests`, `frontend/package.json`, `frontend/eslint.config.mjs`, `frontend/tsconfig.json` | README와 `maintenance.md`의 공통 명령 색인, CI/CD 필수 게이트 확인 필요 항목 |

## 확인 필요

아래 항목은 실행 환경 구성 과정에서 신입 개발자가 막히기 쉬운 지점이지만, 저장소의 코드와 설정만으로는 최종 기준을 확정할 수 없다. 문서의 앞 섹션에는 코드로 확인되는 현재 상태를 적었고, 이 섹션에는 팀 또는 운영 담당자에게 별도로 확인해야 할 항목만 분리했다.

| 구분 | 확인 필요 항목 | 코드에서 확인한 근거 | 확인 후 반영할 위치 |
| --- | --- | --- | --- |
| 런타임 버전 | 팀 표준 Python 3.14 배포판이 정식 릴리스인지, `backend/Dockerfile`의 `python:3.14-rc-slim`을 계속 사용할지 확인 필요 | `backend/pyproject.toml`은 `requires-python >=3.14`, `backend/Dockerfile`은 `python:3.14-rc-slim` 사용 | 이 문서의 `필수 런타임 및 버전`, `backend/Dockerfile`, `backend/README.md` |
| Docker 도구 | Docker Engine 및 Docker Compose 최소 지원 버전 확인 필요 | `docker-compose.yml`, `docker-compose.preview.yml`, `deploy.sh`, `deploy/preview.sh`는 Compose 사용만 확인되고 최소 버전은 명시하지 않음 | 이 문서의 `필수 런타임 및 버전`, `로컬 실행 및 초기 동작 확인 절차` |
| 프론트엔드 패키지 매니저 | `frontend/Dockerfile`의 `npm ci`와 저장소의 pnpm 정책 불일치 해결 방향 확인 필요 | `frontend/package.json`은 `packageManager: pnpm@9.15.0`과 `preinstall: npx only-allow pnpm`을 지정하지만, `frontend/Dockerfile`은 `npm ci` 실행 | `frontend/Dockerfile`, 이 문서의 Docker build 절차 |
| 로컬 실행 스크립트 | `start-local.sh`의 `npm install`과 pnpm 정책 불일치 해결 방향 확인 필요 | `start-local.sh`는 `node_modules`가 없으면 `npm install`을 실행하고, `start-dev.sh`는 `pnpm install`을 실행 | `start-local.sh`, 이 문서의 `대체 로컬 실행 경로` |
| pnpm 설치 방식 | Corepack을 표준으로 사용할지, 전역 `npm install -g pnpm@9.15.0`을 사용할지 확인 필요 | `frontend/package.json`은 pnpm 버전만 고정하고 설치 방식은 정의하지 않음 | 이 문서의 `최초 설치 명령어`, 온보딩 체크리스트 |
| 서버와 네트워크 | 운영/preview 서버의 실제 호스트, 도메인, 고정 IP, 방화벽, 사내망/VPN 접근 방식 확인 필요 | compose와 배포 스크립트는 `HOST_IP`, `preview.devbanjang.cloud`, 로컬 포트를 언급하지만 실제 서버 계정과 네트워크 정책은 없음 | `docs/deployment-ops.md`, 이 문서의 접속 주소와 `CORS_ORIGINS` 설명 |
| 클라우드/외부 계정 | Azure OpenAI, OpenAI, MinIO 운영 계정, 클라우드 프로젝트/리소스 소유자 확인 필요 | `.env.prod.example`, `.env.preview.example`에는 키와 endpoint가 빈 값이고, 코드에는 발급 절차가 없음 | 비밀값 관리 문서, 이 문서의 `환경변수`, `docs/deployment-ops.md` |
| LLM 설정 | 실제 `LLM_PROVIDER`, Azure OpenAI 배포명, `SRS_MODEL`, `TC_MODEL`, 임베딩 배포명 확인 필요 | `backend/src/services/llm_svc.py`, `backend/src/services/embedding_svc.py`는 변수 사용 방식과 기본값만 제공 | `.env.*`, 이 문서의 `LLM 및 임베딩 변수` |
| 데이터 저장소 | 운영 MinIO bucket 생성 정책, 데이터 보존 기간, 백업/복구, 암호화, 접근 권한 확인 필요 | `backend/src/services/storage_svc.py`는 bucket 없으면 생성하지만 운영 정책은 없음 | `docs/deployment-ops.md`, `docs/maintenance.md`, 이 문서의 MinIO 변수 |
| Redis 구성 | preview Redis 실행 방식과 실제 필요 여부 확인 필요 | 기본 compose에는 Redis가 있으나 `docker-compose.preview.yml`에는 Redis 서비스가 없고 `.env.preview.example`에는 `REDIS_URL=redis://localhost:6380/0`만 있음 | `docker-compose.preview.yml`, `.env.preview.example`, 이 문서의 Preview 절차 |
| 테스트 게이트 | 프론트엔드 단위 테스트, E2E, Storybook, 시각 회귀 테스트 도입 여부와 필수 검증 기준 확인 필요 | `frontend/package.json`에는 `pnpm test`, Playwright/Vitest/Jest/Storybook 스크립트가 없음 | 이 문서의 `테스트 실행 및 결과 확인`, `docs/maintenance.md` |
| 백엔드 정적 검증 | 백엔드 lint, formatter, type check 표준 명령 확인 필요 | `backend/pyproject.toml`에는 Ruff, Black, mypy, pyright 등 도구 설정과 스크립트가 없음 | 이 문서의 `린트 실행 및 결과 확인`, CI/CD 문서 |
| CI/CD 절차 | 어떤 브랜치와 이벤트에서 lint/test/build/deploy가 실행되는지, 실패 시 담당자가 누구인지 확인 필요 | 저장소에서 CI/CD workflow 파일 또는 파이프라인 정의를 확인하지 못함 | `docs/deployment-ops.md`, 프로젝트 운영 Runbook |
| 장애 대응 기준 | 로컬/preview/운영 smoke check 실패, DB 마이그레이션 실패, LLM API 실패, MinIO 업로드 실패 시 공식 대응 기준 확인 필요 | 코드에는 로그와 일부 fallback이 있지만 장애 등급, 알림 채널, 복구 목표, on-call 기준은 없음 | `docs/deployment-ops.md`, `docs/maintenance.md`, 운영 Runbook |
| 관측성 | Langfuse 또는 다른 로그/메트릭/트레이싱 도구를 실제로 사용할지 확인 필요 | `.env.prod.example`의 Langfuse 변수는 주석이고, 현재 검색한 애플리케이션 코드에서 직접 읽는 위치가 없음 | `.env.*`, `docs/deployment-ops.md`, `docs/maintenance.md` |

위 항목을 확인한 뒤에는 이 문서만 수정하지 말고 관련 실행 스크립트, Dockerfile, compose 파일, 배포·운영 문서도 함께 갱신해야 한다. 특히 패키지 매니저, 포트, 환경변수, CORS, 비밀값 이름은 문서와 코드가 달라지면 신규 개발자의 최초 실행 실패로 바로 이어진다.
