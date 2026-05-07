# Deployment and Operations

이 문서는 AISE+ 코드베이스를 처음 보는 신입 개발자가 배포 관련 구성 파일과 스크립트를 코드 경로 기준으로 추적하기 위한 운영 문서이다. 현재 저장소에서 확인 가능한 내용만 정리하고, 서버/클라우드 계정, CI/CD, 비밀 관리, 장애 대응 기준처럼 코드로 확정할 수 없는 항목은 `확인 필요`로 표시한다.

## 배포 구성 개요

AISE+의 컨테이너 배포 구성은 Docker Compose 중심이다. 루트 `docker-compose.yml`은 기본 배포 구성을 정의하고, `docker-compose.preview.yml`은 master 환경과 포트/컨테이너/볼륨을 분리한 preview 구성을 정의한다. 백엔드와 프론트엔드는 각각 `backend/Dockerfile`, `frontend/Dockerfile`로 이미지가 빌드된다.

```mermaid
flowchart LR
    Operator[운영자 또는 배포 스크립트] --> Compose[Docker Compose]
    Compose --> Postgres[(postgres: pgvector/pgvector:pg16)]
    Compose --> MinIO[(minio: minio/minio)]
    Compose --> Redis[(redis: redis:7-alpine)]
    Compose --> Backend[backend: FastAPI container]
    Compose --> Frontend[frontend: Next.js container]

    Frontend -->|BACKEND_URL=http://backend:8081| Backend
    Backend -->|DATABASE_URL| Postgres
    Backend -->|MINIO_ENDPOINT=minio:9000| MinIO
    Backend -->|REDIS_URL| Redis
```

## 배포·운영 통합 흐름

아래 다이어그램은 저장소에서 확인되는 배포 실행 경로와 운영 점검 경로를 한 번에 연결한 것이다. `deploy.sh`는 기본 compose를 사용하고, `deploy/preview.sh`는 preview compose를 사용한다. 두 경로 모두 Docker Compose가 backend/frontend 이미지를 빌드하고 컨테이너를 시작하는 구조이며, backend 컨테이너는 시작 시 Alembic migration을 먼저 실행한 뒤 FastAPI 서버를 연다.

```mermaid
flowchart TD
    Start([배포 요청 또는 운영자 작업 시작])
    Start --> Choose{대상 환경 선택}

    Choose -->|기본 compose| ProdEnv[".env 및 .env.prod 준비"]
    Choose -->|preview compose| PreviewEnv[".env.preview 준비"]

    ProdEnv --> ProdScript["deploy.sh 또는 docker compose 명령 실행"]
    PreviewEnv --> PreviewScript["deploy/preview.sh 또는 preview compose 명령 실행"]

    ProdScript --> ProdCompose["docker-compose.yml"]
    PreviewScript --> PreviewCompose["docker-compose.preview.yml"]

    ProdCompose --> Build["backend/frontend 이미지 빌드"]
    PreviewCompose --> Build

    Build --> Infra["PostgreSQL, MinIO, Redis 구성 확인"]
    Infra --> BackendStart[backend 컨테이너 시작]
    BackendStart --> Migration["alembic upgrade head 실행"]
    Migration --> BackendRun["uvicorn src.main:app --port 8081"]
    Build --> FrontendStart[frontend 컨테이너 시작]
    FrontendStart --> Rewrite["Next.js /api/* rewrite"]
    Rewrite --> BackendRun

    BackendRun --> Smoke["배포 후 smoke check"]
    FrontendStart --> Smoke
    Smoke --> Status["docker compose ps 및 logs 확인"]
    Status --> Operate{운영 중 이상 징후?}

    Operate -->|아니오| Monitor[로그와 상태 지속 확인]
    Operate -->|예| Triage[장애 유형별 1차 점검]
    Triage --> Logs["backend/frontend/postgres/minio/redis 로그 확인"]
    Triage --> Data["DB migration, MinIO bucket, Redis 연결 확인"]
    Triage --> Config["환경 변수, CORS, BACKEND_URL 확인"]
    Logs --> NeedsConfirm["확인 필요: 장애 등급, on-call, 알림, 복구 승인 기준"]
    Data --> NeedsConfirm
    Config --> NeedsConfirm
```

운영자가 이 다이어그램을 따라갈 때 함께 확인해야 하는 코드 경로는 `deploy.sh`, `deploy/preview.sh`, `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/next.config.ts`이다. 실제 서버 접속 방법, 클라우드 계정, DNS/TLS, CI/CD 승인 절차, secret 저장소, 장애 등급과 에스컬레이션 기준은 저장소에서 확인되지 않으므로 모두 `확인 필요`이다.

## 운영 전제 조건

배포와 운영에 필요한 전제 조건은 아래 파일에서 확인된다. 실제 서버 계정, 클라우드 계정, 도메인/TLS, secret 주입 방식은 저장소에 없으므로 `확인 필요`로 둔다.

| 항목 | 코드에서 확인한 값 | 근거 파일 | 운영자가 준비할 것 | 확인 필요 |
| --- | --- | --- | --- | --- |
| 컨테이너 런타임 | Docker Compose 기반으로 `postgres`, `minio`, `redis`, `backend`, `frontend`를 기동한다. | `docker-compose.yml`, `docker-compose.preview.yml`, `deploy.sh`, `deploy/preview.sh` | Docker Engine과 Docker Compose v2가 설치된 호스트 | 실제 운영 호스트와 Docker 버전 표준 확인 필요 |
| Backend 런타임 | 이미지 빌드는 `python:3.14-rc-slim`, 프로젝트 요구 버전은 `requires-python = ">=3.14"`이다. | `backend/Dockerfile`, `backend/pyproject.toml` | Docker 빌드 환경 또는 로컬 개발 시 `uv`와 Python 3.14 이상 | Python 3.14 RC 이미지를 운영 표준으로 사용할지 확인 필요 |
| Frontend 런타임 | 이미지 빌드/실행은 `node:20-alpine`, 앱 엔진은 Node `>=20`, Next.js standalone 출력이다. | `frontend/Dockerfile`, `frontend/package.json`, `frontend/next.config.ts` | Docker 빌드 환경 또는 로컬 개발 시 Node 20 이상 | 운영 빌드에서 `pnpm`과 `npm ci` 중 어떤 패키지 매니저가 표준인지 확인 필요 |
| PostgreSQL | 기본/preview 모두 `pgvector/pgvector:pg16` 이미지를 사용하고 persistent volume을 붙인다. | `docker-compose.yml`, `docker-compose.preview.yml` | DB 데이터 볼륨, 백업/복구 절차, migration 검증 절차 | 백업 주기, 복구 RTO/RPO, migration 승인 절차 확인 필요 |
| MinIO | `minio/minio:latest` 이미지와 `/data` 볼륨을 사용한다. backend는 `MINIO_ENDPOINT=minio:9000`으로 접근한다. | `docker-compose.yml`, `docker-compose.preview.yml` | object storage 볼륨과 bucket 관리 기준 | 운영에서 MinIO를 그대로 쓸지 외부 object storage를 쓸지 확인 필요 |
| Redis | 기본 compose에는 `redis:7-alpine`이 있고 backend는 `REDIS_URL=redis://redis:6379/0`을 받는다. preview compose에는 Redis 서비스가 없다. | `docker-compose.yml`, `docker-compose.preview.yml`, `.env.preview.example` | LangGraph state cache 또는 향후 broker 용도에 맞는 Redis | preview의 `REDIS_URL=redis://localhost:6380/0` 대상과 Redis 필요 여부 확인 필요 |
| 외부 LLM API | `LLM_PROVIDER`, Azure/OpenAI API key와 endpoint 예시가 있다. | `.env.prod.example`, `.env.preview.example`, `backend/src/services/llm_svc.py` | API key, endpoint, model 정책, 비용/쿼터 관리 | 실제 provider, endpoint, secret 저장소, 장애 시 fallback 정책 확인 필요 |
| 네트워크/도메인 | 기본 frontend는 `4000`, backend는 `8081`; preview frontend는 `4100`, backend는 `8181`로 노출된다. preview 주석에는 `preview.devbanjang.cloud`가 있다. | `docker-compose.yml`, `docker-compose.preview.yml`, `deploy/preview.sh`, `frontend/next.config.ts` | DNS, TLS 종료, 리버스 프록시, 방화벽 포트 정책 | 실제 도메인, 인증서, 프록시 타임아웃, allowed origin 최종 목록 확인 필요 |

## 배포 관련 파일과 스크립트 목록

| 구분 | 경로 | 역할 | 코드에서 확인한 주요 내용 | 관련 명령어 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 기본 Docker Compose | `docker-compose.yml` | 기본 배포 후보 구성 파일 | `postgres`, `minio`, `redis`, `backend`, `frontend` 서비스를 정의한다. PostgreSQL은 `pgvector/pgvector:pg16`, Redis는 `redis:7-alpine`, MinIO는 `minio/minio:latest` 이미지를 사용한다. backend는 `./backend/Dockerfile`, frontend는 `./frontend/Dockerfile`로 빌드된다. | `docker compose up -d --build`, `docker compose ps`, `docker compose down` | 이 구성이 실제 production인지, staging인지, 사내 서버용 compose인지 확인 필요. |
| Preview Docker Compose | `docker-compose.preview.yml` | master와 분리된 preview 환경 구성 파일 | preview 포트는 frontend `4100:3000`, backend `8181:8081`, PostgreSQL `5433:5432`, MinIO `9100:9000`, MinIO console `9101:9001`이다. 컨테이너명과 볼륨도 `aise2_preview_*`, `preview_*`로 분리된다. Redis 서비스는 preview compose에 정의되어 있지 않다. | `docker compose -f docker-compose.preview.yml up -d --build`, `docker compose -f docker-compose.preview.yml down` | preview 도메인 `preview.devbanjang.cloud`의 DNS/TLS/리버스 프록시 설정은 확인 필요. preview에서 Redis가 필요한지 여부도 확인 필요. |
| 기본 배포 스크립트 | `deploy.sh` | 루트 compose 기반 전체 배포 또는 특정 서비스 재시작 | `.env` 파일 존재를 확인한 뒤, 서비스 인자가 없으면 `docker compose down`, `docker compose build --no-cache`, `docker compose up -d`를 순서대로 실행한다. 서비스명을 넘기면 `docker compose up -d --build "$SERVICE"`만 실행한다. 완료 후 frontend `:4000`, backend `:8081`, `docker compose ps`를 출력한다. | `./deploy.sh`, `./deploy.sh backend`, `./deploy.sh frontend` | 스크립트는 `.env.example`을 안내하지만 저장소에는 `.env.prod.example`, `.env.preview.example`만 확인된다. 실제 `.env` 생성 기준은 확인 필요. |
| Preview 배포 스크립트 | `deploy/preview.sh` | preview compose 기반 브랜치 배포와 preview 중지 | 인자가 브랜치명이면 `git fetch`, `git checkout`, `git pull` 후 `docker compose -f docker-compose.preview.yml up -d --build`를 실행한다. `--stop` 인자는 `docker compose -f docker-compose.preview.yml down`으로 preview를 중지한다. 완료 후 frontend `:4100`, backend `:8181`, Swagger `:8181/docs`, DB `:5433`을 출력한다. | `./deploy/preview.sh`, `./deploy/preview.sh feat/my-feature`, `./deploy/preview.sh --stop` | 운영 서버에서 이 스크립트를 누가 실행하는지, 브랜치 체크아웃 권한과 배포 승인 절차는 확인 필요. |
| Backend Dockerfile | `backend/Dockerfile` | FastAPI 백엔드 이미지 빌드/실행 정의 | `python:3.14-rc-slim` 기반 multi-stage build이다. builder에서 `uv sync --frozen --no-dev`로 의존성을 설치하고, runner에서 `/app/entrypoint.sh`를 실행한다. entrypoint는 `alembic upgrade head`를 먼저 시도하고 실패 시 `alembic stamp head`를 시도한 뒤 `uvicorn src.main:app --host 0.0.0.0 --port 8081`을 실행한다. | `docker compose build backend`, `docker compose up -d backend` | Python 3.14 RC 이미지를 운영에서 사용해도 되는지, Alembic 실패 후 stamp 처리 정책이 적절한지 확인 필요. |
| Frontend Dockerfile | `frontend/Dockerfile` | Next.js 프론트엔드 이미지 빌드/실행 정의 | `node:20-alpine` 기반 multi-stage build이다. builder에서 `NEXT_PUBLIC_API_URL`, `BACKEND_URL` build arg를 받아 `npm ci`, `npm run build`를 실행한다. runner는 standalone 출력물과 static 파일을 복사하고 `node server.js`로 `3000` 포트를 연다. | `docker compose build frontend`, `docker compose up -d frontend` | package manager는 `frontend/package.json`에서 `pnpm@9.15.0`로 지정되어 있으나 Dockerfile은 `npm ci`를 사용한다. 실제 운영 빌드 표준 패키지 매니저는 확인 필요. |
| Production 환경 예시 | `.env.prod.example` | backend 운영 후보 환경 변수 예시 | `LLM_PROVIDER`, Azure/OpenAI 키와 endpoint, `REDIS_URL`, `LANGGRAPH_CHECKPOINT_URL`, Langfuse 관련 주석이 있다. compose 기본 배포는 backend에 `.env.prod`를 `env_file`로 주입한다. | `cp .env.prod.example .env.prod` 후 값 입력, `docker compose up -d --build` | 실제 API 키, endpoint, Langfuse 사용 여부, secret 저장소와 주입 방식은 확인 필요. |
| Preview 환경 예시 | `.env.preview.example` | backend preview 환경 변수 예시 | Azure/OpenAI 키와 endpoint, `REDIS_URL=redis://localhost:6380/0`, `LANGGRAPH_CHECKPOINT_URL=postgresql://aise:aise1234@localhost:5433/aise`가 있다. preview compose는 backend에 `.env.preview`를 `env_file`로 주입한다. | `cp .env.preview.example .env.preview` 후 값 입력, `./deploy/preview.sh` | preview compose에 Redis가 없어 `REDIS_URL`의 실제 대상과 필요 여부는 확인 필요. |
| Next.js 배포/프록시 설정 | `frontend/next.config.ts` | standalone 빌드와 API rewrite 정의 | `output: 'standalone'`으로 Dockerfile runner가 standalone 서버를 실행할 수 있게 한다. `/api/:path*` 요청은 `BACKEND_URL` 기본값 `http://localhost:8081` 또는 환경 변수 값으로 rewrite된다. 허용 개발 origin으로 `dev.devbanjang.cloud`, `local-aise.lge.com`이 설정되어 있다. | `BACKEND_URL=http://backend:8081 npm run build`, `npm run start` | 운영 도메인, TLS 종료 지점, 프록시 타임아웃, allowed origin 최종 목록은 확인 필요. |
| 개발 서버 스크립트 | `start-dev.sh`, `start-local.sh` | 로컬 개발 실행 보조 | 두 스크립트 모두 backend와 frontend 개발 서버를 실행하고, 기존 포트 사용 프로세스를 종료한다. `start-dev.sh`는 backend `9999`, frontend `3009`를 사용하며 PostgreSQL compose 시작 부분은 주석 처리되어 있다. `start-local.sh`는 backend `8082`, frontend `3009`를 사용하고 frontend 실행 시 `BACKEND_URL=http://localhost:8082`를 주입한다. | `./start-dev.sh`, `./start-local.sh` | 로컬 개발 표준 스크립트가 둘 중 어느 것인지, 로컬 DB/MinIO/Redis 기동 표준은 확인 필요. |

## 운영 추적 경로 맵

배포 중 오류가 나거나 운영 설정을 변경할 때는 아래 순서로 파일을 추적한다. 이 표는 배포 스크립트와 compose 설정에서 시작해 실제 애플리케이션 코드가 환경변수와 연결 정보를 어떻게 소비하는지까지 연결한 경로 맵이다.

| 운영 관심사 | 먼저 볼 파일 | 이어서 볼 코드/설정 파일 | 확인할 내용 | 확인 필요 |
| --- | --- | --- | --- | --- |
| 기본 배포 진입점 | `deploy.sh` | `docker-compose.yml`, `.env.prod.example`, `backend/Dockerfile`, `frontend/Dockerfile` | `.env` 존재 검사, 전체 배포 시 `docker compose down` -> `build --no-cache` -> `up -d` 순서, backend/frontend 이미지 빌드 경로, 완료 후 노출 포트 출력 | 실제 production 배포가 이 스크립트인지, `.env`와 `.env.prod`의 역할 분리 기준 확인 필요 |
| Preview 배포 진입점 | `deploy/preview.sh` | `docker-compose.preview.yml`, `.env.preview.example`, `backend/Dockerfile`, `frontend/Dockerfile` | 브랜치 checkout/pull 후 preview compose `up -d --build`, `--stop` 중지 경로, preview 포트와 컨테이너명 | preview 배포 서버, DNS/TLS, 브랜치 배포 승인 절차 확인 필요 |
| Backend 컨테이너 시작 | `backend/Dockerfile` | `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions`, `backend/src/main.py` | entrypoint가 `alembic upgrade head`를 먼저 실행하고 실패 시 `alembic stamp head`를 시도한 뒤 `uvicorn src.main:app --host 0.0.0.0 --port 8081`을 실행한다. FastAPI 앱은 `src.main:app`에서 router, CORS, logging middleware를 등록한다. | migration 실패 후 stamp fallback을 운영에서 허용할지 확인 필요 |
| Frontend 컨테이너 시작 | `frontend/Dockerfile` | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/next.config.ts`, `docker-compose.yml`, `docker-compose.preview.yml` | Dockerfile은 `npm ci`와 `npm run build`를 실행하고 standalone 산출물을 `node server.js`로 구동한다. compose는 `BACKEND_URL=http://backend:8081`, `NEXT_PUBLIC_API_URL=""`를 build/runtime env로 넘긴다. | 저장소 package manager 선언은 pnpm이므로 Dockerfile의 npm 사용 표준 확인 필요 |
| API 프록시와 CORS | `frontend/next.config.ts` | `backend/src/core/cors.py`, `backend/src/main.py`, `docker-compose.yml`, `docker-compose.preview.yml` | frontend `/api/:path*` rewrite 대상은 `BACKEND_URL`이다. backend는 `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`를 읽어 `CORSMiddleware`를 등록한다. compose는 기본/preview별 origin 값을 주입한다. | 운영 도메인, HTTPS origin, reverse proxy timeout/buffering, SSE 지원 기준 확인 필요 |
| DB 연결과 migration | `docker-compose.yml`, `docker-compose.preview.yml` | `backend/src/core/database.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions`, `backend/scripts/setup_test_db.py` | backend 런타임 DB는 `DATABASE_URL`을 읽고 기본값은 localhost PostgreSQL이다. Docker 배포에서는 compose가 `postgres:5432` 기반 URL을 주입한다. Alembic migration 파일은 `backend/alembic/versions`에 누적된다. | 운영 DB 계정, 백업/복구, migration 승인과 rollback/downgrade 절차 확인 필요 |
| LangGraph checkpoint와 Redis | `docker-compose.yml`, `.env.prod.example`, `.env.preview.example` | `backend/src/orchestration/graph.py`, `backend/src/orchestration/supervisor.py`, `backend/src/orchestration/state.py` | 기본 compose는 `LANGGRAPH_CHECKPOINT_URL=postgresql://...@postgres:5432/...`, `REDIS_URL=redis://redis:6379/0`를 주입한다. preview 예시는 localhost 기반 값을 포함하지만 preview compose에는 Redis 서비스가 없다. | preview Redis 대상, checkpoint DB 분리 여부, 장애 시 state 복구 기준 확인 필요 |
| Object storage | `docker-compose.yml`, `docker-compose.preview.yml` | `backend/src/services/storage_svc.py`, `backend/src/services/knowledge_svc.py`, `backend/src/routers/knowledge.py` | compose는 `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`을 backend에 주입한다. `storage_svc.py`는 MinIO client를 lazy init하고 bucket 확인/생성, 업로드, 다운로드, 삭제를 수행한다. | 운영에서 MinIO를 그대로 쓸지 외부 object storage를 쓸지, bucket lifecycle과 백업 기준 확인 필요 |
| LLM credential과 생성 기능 | `.env.prod.example`, `.env.preview.example` | `backend/src/services/llm_svc.py`, `backend/src/agents`, `backend/src/orchestration/supervisor.py`, `backend/src/prompts` | env 예시는 `LLM_PROVIDER`, Azure/OpenAI API key, endpoint, model 값을 제공한다. 생성 기능은 backend service/agent/orchestration 계층에서 LLM service를 경유한다. | 실제 provider, 모델 승인 기준, quota/cost, fallback 정책, secret rotation 확인 필요 |
| 로그와 장애 조사 | `backend/src/core/logging.py` | `backend/src/middleware/logging_middleware.py`, `backend/src/core/exceptions.py`, `backend/src/main.py`, `docker-compose.yml` | Loguru가 stderr와 `var/logs/app.log`, `var/logs/app.json`에 로그를 남긴다. middleware는 request_id, method/path, status, 처리 시간을 기록한다. Docker compose에는 backend 로그 디렉터리 volume mount가 없다. | 중앙 로그 수집, 로그 보존, alert rule, 장애 등급과 on-call 기준 확인 필요 |
| 테스트와 배포 전 검증 | `backend/pyproject.toml`, `frontend/package.json` | `backend/tests`, `backend/scripts/setup_test_db.sh`, `backend/scripts/setup_test_db.py`, `frontend/eslint.config.mjs`, `frontend/tsconfig.json` | backend는 `uv run pytest`, frontend는 `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build`로 검증할 수 있다. 테스트 DB 준비 스크립트는 `backend/scripts`에 있다. | CI/CD에서 어떤 검증을 필수 게이트로 삼는지 확인 필요 |
| 로컬/개발 실행과 배포 차이 | `start-dev.sh`, `start-local.sh` | `frontend/docker-compose.yml`, `frontend/README.md`, `backend/README.md`, `docker-compose.yml` | 로컬 스크립트는 backend/frontend dev server를 직접 띄우고 포트가 배포 compose와 다르다. 루트 compose는 인프라와 앱 컨테이너를 함께 띄운다. | 팀 표준 로컬 실행 방식과 로컬 DB/MinIO/Redis 기동 방식 확인 필요 |
| CI/CD와 외부 인프라 | 저장소 전체에서 확인된 배포 파일: `deploy.sh`, `deploy/preview.sh`, `docker-compose.yml`, `docker-compose.preview.yml` | 현재 워크트리에서 `.github/workflows`, `Jenkinsfile`, `.gitlab-ci.yml`, Terraform/Kubernetes manifest는 확인되지 않는다. | 저장소 기준으로는 수동 Docker Compose 배포 흐름만 문서화할 수 있다. | 실제 CI/CD, 클라우드 계정, IaC, secret manager, 릴리스 승인자는 확인 필요 |

## 환경 변수 정리

Compose와 예시 env 파일이 주입하는 주요 환경 변수는 다음과 같다. 실제 값은 secret이므로 문서에 기록하지 않는다.

| 변수 | 사용 위치 | 코드에서 확인한 기본값 또는 예시 | 설명 | 확인 필요 |
| --- | --- | --- | --- | --- |
| `POSTGRES_USER` | `docker-compose.yml`, `docker-compose.preview.yml` | `aise` | PostgreSQL 사용자와 backend DB URL 조합에 사용된다. | 운영 계정명과 권한 범위 확인 필요 |
| `POSTGRES_PASSWORD` | `docker-compose.yml`, `docker-compose.preview.yml` | `aise1234` | PostgreSQL password와 backend DB URL 조합에 사용된다. | 운영 secret 값과 저장소 외부 주입 방식 확인 필요 |
| `POSTGRES_DB` | `docker-compose.yml`, `docker-compose.preview.yml` | `aise` | PostgreSQL database 이름이다. | 운영 DB 이름 확인 필요 |
| `POSTGRES_PORT` | `docker-compose.yml` | `5432` | 기본 compose의 호스트 DB 포트 override에 사용된다. | 운영 포트 정책 확인 필요 |
| `MINIO_ROOT_USER` | `docker-compose.yml`, `docker-compose.preview.yml` | `aise` | MinIO root user와 backend access key로 사용된다. | 운영 access key 관리 방식 확인 필요 |
| `MINIO_ROOT_PASSWORD` | `docker-compose.yml`, `docker-compose.preview.yml` | `aise1234` | MinIO root password와 backend secret key로 사용된다. | 운영 secret 값과 회전 정책 확인 필요 |
| `MINIO_BUCKET` | `docker-compose.yml`, `docker-compose.preview.yml` | `aise-knowledge` | backend가 문서/지식 저장소 bucket으로 사용할 값이다. | bucket 생성 자동화 여부 확인 필요 |
| `DATABASE_URL` | backend container environment | `postgresql+asyncpg://...@postgres:5432/...` | SQLAlchemy asyncpg 기반 애플리케이션 DB 연결 문자열이다. | 외부 DB 사용 시 connection string 표준 확인 필요 |
| `LANGGRAPH_CHECKPOINT_URL` | `docker-compose.yml`, `.env.prod.example`, `.env.preview.example` | 기본 compose는 `postgresql://...@postgres:5432/...`, 예시는 localhost URL | LangGraph checkpoint용 sync psycopg URL이다. `+asyncpg`를 쓰지 않는다고 예시에 명시되어 있다. | preview compose가 이 값을 직접 override하지 않으므로 `.env.preview` 값이 컨테이너 내부에서 유효한지 확인 필요 |
| `REDIS_URL` | `docker-compose.yml`, `.env.prod.example`, `.env.preview.example` | 기본 compose는 `redis://redis:6379/0`, prod 예시는 localhost 6379, preview 예시는 localhost 6380 | LangGraph state cache와 향후 Celery broker 용도로 주석 처리되어 있다. | preview Redis 대상과 운영 Redis 구성 확인 필요 |
| `ENVIRONMENT` | backend container environment | 기본 `${ENVIRONMENT:-prod}`, preview `preview` | backend 실행 환경 구분값이다. | 운영 환경명 표준 확인 필요 |
| `CORS_ORIGINS` | backend container environment | 기본 `http://${HOST_IP:-localhost}:4000`, preview `https://preview.devbanjang.cloud,http://localhost:4100` | FastAPI CORS 허용 origin에 사용된다. | 실제 도메인, HTTPS origin, 사내망 origin 최종 목록 확인 필요 |
| `BACKEND_URL` | frontend build arg/runtime env, `frontend/next.config.ts` | compose에서는 `http://backend:8081`, next.config 기본값은 `http://localhost:8081` | Next.js `/api/:path*` rewrite 대상이다. | 리버스 프록시 사용 시 서버 사이드 접근 URL 확인 필요 |
| `NEXT_PUBLIC_API_URL` | frontend Docker build arg | compose에서는 빈 문자열 | 브라우저 공개 API URL로 빌드 타임에 주입된다. 현재 compose는 같은 origin `/api/*` 프록시를 쓰도록 빈 값이다. | 공개 API URL을 쓸 배포인지 확인 필요 |
| `LLM_PROVIDER` | `.env.prod.example`, `.env.preview.example` | `azure` | LLM provider 선택값이다. | 실제 운영 provider와 fallback 정책 확인 필요 |
| `SRS_API_KEY`, `SRS_ENDPOINT`, `TC_API_KEY`, `TC_ENDPOINT` | `.env.prod.example`, `.env.preview.example` | 빈 값 | Azure OpenAI 계열 API credential/endpoint로 보인다. | 실제 키, endpoint, 권한, rotation 정책 확인 필요 |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | `.env.prod.example`, `.env.preview.example` | `OPENAI_MODEL=gpt-4o` | Azure 미사용 시 OpenAI credential/model 예시이다. | 실제 사용 여부와 모델 승인 기준 확인 필요 |
| `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | `.env.prod.example` 주석 | 주석 처리 | Phase 4 observability 후보로 주석만 있다. | Langfuse 도입 여부와 호스트 확인 필요 |

주의: `docker-compose.yml`의 backend는 `env_file: .env.prod`를 읽지만, `deploy.sh`는 실행 전에 `.env` 파일 존재를 검사하고 `HOST_IP`를 `.env`에서 읽는다. 따라서 스크립트 기반 배포를 쓰려면 `.env`와 `.env.prod`의 역할을 운영 표준으로 정리해야 한다. 현재 저장소에는 `.env.example`이 없으므로 `deploy.sh` 안내 문구의 기준 파일도 확인 필요이다.

## 운영 환경 반영 흐름

운영 환경 값은 한 곳에서만 주입되지 않는다. 신입 개발자는 배포 전에 `.env`, `.env.prod`, `.env.preview`, compose의 `environment`, frontend Docker build arg, Next.js rewrite 설정이 각각 어느 시점에 반영되는지 구분해야 한다.

```mermaid
flowchart TD
    EnvFile[".env / .env.prod / .env.preview 작성"] --> ComposeConfig["docker compose config로 env 치환 확인"]
    ComposeConfig --> BuildArgs["frontend build args: NEXT_PUBLIC_API_URL, BACKEND_URL"]
    ComposeConfig --> BackendEnv["backend env_file + environment"]
    ComposeConfig --> InfraEnv["PostgreSQL/MinIO/Redis environment"]

    BuildArgs --> FrontendBuild["frontend Docker build: npm ci, npm run build"]
    FrontendBuild --> NextStandalone["Next.js standalone server.js"]
    BackendEnv --> BackendStart["backend container start"]
    InfraEnv --> InfraStart["postgres/minio/redis container start"]

    InfraStart --> BackendStart
    BackendStart --> Migration["alembic upgrade head"]
    Migration --> Uvicorn["uvicorn src.main:app:8081"]
    NextStandalone --> Rewrite["/api/* rewrite -> BACKEND_URL"]
    Rewrite --> Uvicorn

    Uvicorn --> Verify["배포 후 env/API/log 검증"]
    Rewrite --> Verify
```

### 환경 반영 단계별 절차

| 단계 | 수행할 일 | 반영 시점 | 확인 명령어 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 1 | 기본 배포용 `.env.prod`를 `.env.prod.example`에서 만들고 secret 값을 채운다. | backend 컨테이너가 시작될 때 `env_file`로 읽는다. | `docker compose config | sed -n '/backend:/,/frontend:/p'` | `.env.prod.example`, `docker-compose.yml` | 실제 secret 저장소, 값 편집 권한, rotation 절차 확인 필요. |
| 2 | `deploy.sh`를 쓸 경우 별도 `.env` 파일과 `HOST_IP` 값을 준비한다. | `deploy.sh` 실행 초기에 파일 존재와 완료 메시지 URL에 사용된다. | `test -f .env && grep '^HOST_IP=' .env` | `deploy.sh` | `.env.example`이 저장소에 없으므로 `.env` 작성 기준 확인 필요. |
| 3 | preview 배포용 `.env.preview`를 `.env.preview.example`에서 만든다. | preview backend 컨테이너가 시작될 때 `env_file`로 읽는다. | `docker compose -f docker-compose.preview.yml config | sed -n '/backend:/,/frontend:/p'` | `.env.preview.example`, `docker-compose.preview.yml` | preview Redis 대상, LangGraph checkpoint URL, 실제 preview secret 확인 필요. |
| 4 | compose의 DB/MinIO/Redis 기본값 override가 필요한지 확인한다. | compose가 컨테이너를 생성할 때 `environment`, port, volume에 반영된다. | `docker compose config`, `docker compose -f docker-compose.preview.yml config` | `docker-compose.yml`, `docker-compose.preview.yml` | 운영 DB/MinIO 계정과 포트 정책 확인 필요. |
| 5 | frontend API 프록시 값을 확인한다. | Docker build arg는 `next build` 시점에, runtime `BACKEND_URL`은 standalone 서버 실행 시점에 반영된다. | `docker compose config | grep -A8 'frontend:'`, `curl http://localhost:4000/api/v1/sample/` | `frontend/Dockerfile`, `frontend/next.config.ts`, `docker-compose.yml` | 실제 reverse proxy/DNS/TLS 환경에서 `BACKEND_URL`을 어떤 값으로 둘지 확인 필요. |
| 6 | 환경 값 변경 후 대상 컨테이너를 재생성한다. | 이미 실행 중인 컨테이너에는 env 변경이 자동 반영되지 않는다. | `docker compose up -d --build backend frontend`, preview는 `docker compose -f docker-compose.preview.yml up -d --build` | `deploy.sh`, `deploy/preview.sh`, compose 파일 | 운영에서 전체 재배포와 서비스 단독 재시작 중 무엇을 허용하는지 확인 필요. |
| 7 | 반영 후 컨테이너 내부 값을 필요한 범위에서만 확인한다. | 컨테이너 재생성 이후 런타임 환경에 반영된다. | `docker compose exec backend sh -lc 'env | grep -E "ENVIRONMENT|DATABASE_URL|MINIO_ENDPOINT|REDIS_URL|LLM_PROVIDER" | sort'` | `docker-compose.yml`, `.env.prod.example`, `.env.preview.example` | secret 전체 출력은 운영 보안 정책에 따라 금지될 수 있으므로 확인 방식 확정 필요. |

주의: secret이 포함될 수 있는 `env`, `docker compose config`, 로그 출력 결과를 이슈나 문서에 그대로 붙이면 안 된다. 현재 저장소에는 secret 마스킹, secret manager, 감사 로그 정책이 없으므로 운영 담당자 확인 전까지는 모두 `확인 필요`로 둔다.

### 운영 환경별 반영 요약

| 환경 | 배포 진입점 | env 파일 | 포트와 URL | 반영 확인 명령어 | 코드에서 확인한 한계 |
| --- | --- | --- | --- | --- | --- |
| 기본 compose | `docker compose up -d --build` 또는 `./deploy.sh` | backend는 `.env.prod`, `deploy.sh`는 `.env`도 요구 | frontend `4000`, backend `8081`, DB `${POSTGRES_PORT:-5432}`, MinIO `${MINIO_PORT:-9000}`, Redis `${REDIS_PORT:-6379}` | `docker compose config`, `docker compose ps`, `curl http://localhost:4000/api/v1/sample/` | 실제 production 여부, `.env`와 `.env.prod` 역할, 무중단 배포 여부 확인 필요 |
| preview compose | `./deploy/preview.sh` 또는 `docker compose -f docker-compose.preview.yml up -d --build` | backend는 `.env.preview` | frontend `4100`, backend `8181`, DB `5433`, MinIO `9100/9101` | `docker compose -f docker-compose.preview.yml config`, `curl http://localhost:4100/api/v1/sample/` | DNS/TLS, reverse proxy, Redis 대상, preview 데이터 보존 기준 확인 필요 |
| 로컬 개발 | `./start-local.sh`, `./start-dev.sh`, 또는 backend/frontend 수동 실행 | 스크립트별 명시 env와 로컬 shell env | `start-local.sh`: backend `8082`, frontend `3009`; `start-dev.sh`: backend `9999`, frontend `3009` | `curl http://localhost:8082/docs`, `curl http://localhost:3009/api/v1/sample/` | 로컬 DB/MinIO/Redis 기동 표준과 팀 표준 스크립트 확인 필요 |

## 배포 후 검증 체크리스트

배포가 성공했다는 기준은 컨테이너가 떠 있는 것만으로 충분하지 않다. 최소한 compose 상태, backend migration/startup 로그, backend 직접 API, frontend rewrite, 주요 인프라 연결을 순서대로 확인한다.

### 기본 compose 배포 후 검증

| 순서 | 검증 대상 | 명령어 | 기대 결과 | 실패 시 먼저 볼 파일/로그 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 1 | 서비스 상태 | `docker compose ps` | `postgres`, `redis`, `backend`, `frontend`가 실행 중이고 PostgreSQL/Redis healthcheck가 healthy 상태이다. | `docker-compose.yml`, `docker compose logs --tail 200 <service>` | backend/frontend/MinIO healthcheck 추가 여부 확인 필요 |
| 2 | backend 시작 로그 | `docker compose logs --tail 200 backend` | `Running Alembic migrations`, `Starting server`, Uvicorn startup 로그를 확인한다. | `backend/Dockerfile`, `backend/alembic/versions`, `backend/src/main.py` | migration 실패 후 `stamp head` 허용 여부 확인 필요 |
| 3 | DB 연결 | `docker compose exec postgres pg_isready -U aise` | `accepting connections` 응답을 확인한다. | `docker-compose.yml`, `backend/src/core/database.py` | 운영 DB 계정명과 권한, 외부 DB 사용 여부 확인 필요 |
| 4 | Redis 연결 | `docker compose exec redis redis-cli ping` | `PONG` 응답을 확인한다. | `docker-compose.yml`, `.env.prod.example` | Redis 장애 시 서비스 영향 범위 확인 필요 |
| 5 | backend 문서 엔드포인트 | `curl -I http://localhost:8081/docs` | HTTP 200 또는 FastAPI docs 응답을 확인한다. | `backend/src/main.py`, `backend/Dockerfile` | 운영에서 `/docs` 공개 허용 여부 확인 필요 |
| 6 | backend API smoke | `curl http://localhost:8081/api/v1/sample/` | sample router 응답을 확인한다. | `backend/src/routers/sample.py`, `backend/src/main.py` | sample API를 공식 health check로 쓸지 확인 필요 |
| 7 | frontend 페이지 | `curl -I http://localhost:4000` | Next.js frontend가 HTTP 응답을 반환한다. | `frontend/Dockerfile`, `frontend/next.config.ts` | 실제 도메인/TLS 기준 URL 확인 필요 |
| 8 | frontend API rewrite | `curl http://localhost:4000/api/v1/sample/` | frontend를 경유해 backend sample API 응답을 받는다. | `frontend/next.config.ts`, `docker-compose.yml`, `docker compose logs --tail 100 frontend` | reverse proxy timeout/buffering과 SSE 지원 확인 필요 |
| 9 | MinIO 상태 | `docker compose logs --tail 100 minio` | MinIO server가 시작되어 있고 credential/bucket 관련 오류가 없다. | `docker-compose.yml`, `backend/src/services/storage_svc.py` | bucket lifecycle, 백업, 외부 object storage 전환 여부 확인 필요 |
| 10 | 오류 로그 | `docker compose logs --since 10m backend frontend` | 배포 직후 반복 예외, rewrite 오류, env 누락 오류가 없다. | `backend/src/core/logging.py`, `backend/src/core/exceptions.py`, `frontend/next.config.ts` | 중앙 로그/알림 기준 확인 필요 |

### Preview 배포 후 검증

| 순서 | 검증 대상 | 명령어 | 기대 결과 | 실패 시 먼저 볼 파일/로그 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 1 | preview 서비스 상태 | `docker compose -f docker-compose.preview.yml ps` | preview 컨테이너가 실행 중이고 PostgreSQL healthcheck가 healthy 상태이다. | `docker-compose.preview.yml` | 기본 compose와 같은 Docker daemon에서 동시 운영 시 컨테이너명 충돌 여부 확인 필요 |
| 2 | preview backend 로그 | `docker compose -f docker-compose.preview.yml logs --tail 200 backend` | migration과 Uvicorn startup 로그를 확인한다. | `backend/Dockerfile`, `docker-compose.preview.yml` | preview migration 실패 처리 기준 확인 필요 |
| 3 | preview backend docs | `curl -I http://localhost:8181/docs` | preview backend가 HTTP 응답을 반환한다. | `deploy/preview.sh`, `docker-compose.preview.yml` | `preview.devbanjang.cloud` 기준 외부 접근 URL 확인 필요 |
| 4 | preview frontend | `curl -I http://localhost:4100` | preview frontend가 HTTP 응답을 반환한다. | `frontend/Dockerfile`, `docker-compose.preview.yml` | DNS/TLS/reverse proxy 설정 확인 필요 |
| 5 | preview rewrite | `curl http://localhost:4100/api/v1/sample/` | preview frontend를 경유해 backend sample API 응답을 받는다. | `frontend/next.config.ts`, `docker-compose.preview.yml` | reverse proxy가 있는 경우 외부 URL 기준 smoke check 확인 필요 |
| 6 | preview MinIO | `docker compose -f docker-compose.preview.yml logs --tail 100 minio` | MinIO server 시작 오류가 없다. | `docker-compose.preview.yml`, `backend/src/services/storage_svc.py` | preview object 데이터 보존/삭제 기준 확인 필요 |
| 7 | preview Redis 관련 오류 | `docker compose -f docker-compose.preview.yml logs --tail 200 backend | grep -i redis || true` | Redis 오류가 반복되지 않는지 확인한다. | `.env.preview.example`, `docker-compose.preview.yml` | preview compose에는 Redis 서비스가 없으므로 Redis 필요 여부 확인 필요 |

검증 실패 시에는 마지막으로 변경한 축을 기준으로 되돌아간다. env 변경 직후 실패하면 `docker compose config`와 컨테이너 내부 env를 확인하고, 이미지 빌드 변경 직후 실패하면 `docker compose build <service>` 로그를 확인하며, DB model/migration 변경 직후 실패하면 `backend/alembic/versions`와 backend startup 로그를 먼저 확인한다.

## 장애·오류 대응 기준과 점검 순서

운영 장애는 "사용자 영향 범위 확인 -> 최근 변경 확인 -> 서비스 상태 확인 -> 로그와 설정 확인 -> 데이터/외부 의존성 확인 -> 복구 또는 에스컬레이션" 순서로 좁힌다. 현재 저장소에는 장애 등급, 온콜, 알림, 고객 공지, 롤백 승인 기준이 정의되어 있지 않으므로 운영 판단이 필요한 항목은 모두 `확인 필요`로 둔다.

### 1차 판단 기준

| 판단 축 | 먼저 확인할 것 | 명령어 또는 위치 | 코드에서 확인한 기준 | 확인 필요 |
| --- | --- | --- | --- | --- |
| 사용자 영향 | frontend 접속, backend API, Agent SSE 중 어느 경로가 실패하는지 분리한다. | `curl -I http://localhost:4000`, `curl http://localhost:4000/api/v1/sample/`, `curl -I http://localhost:8081/docs` | frontend는 `4000`, backend는 `8081`, API rewrite는 `frontend/next.config.ts`의 `BACKEND_URL`을 따른다. | 실제 운영 도메인/TLS 기준 health URL과 장애 등급 기준 확인 필요 |
| 최근 변경 | 마지막 배포 대상, 브랜치, env 변경, migration 변경을 확인한다. | `git log --oneline -5`, `git diff --name-only HEAD~1..HEAD`, `docker compose ps` | 배포 스크립트는 `deploy.sh`, preview는 `deploy/preview.sh`이고 backend 시작 시 Alembic을 실행한다. | 운영 배포 이력 저장 위치, 승인자, rollback commit/tag 기준 확인 필요 |
| 서비스 상태 | 컨테이너가 running/healthy인지 확인한다. | `docker compose ps`, preview는 `docker compose -f docker-compose.preview.yml ps` | PostgreSQL과 Redis에는 healthcheck가 있고 backend는 이 둘의 healthy 이후 시작된다. preview에는 Redis 서비스가 없다. | frontend/backend/MinIO 공식 healthcheck 추가 여부 확인 필요 |
| 로그 | Docker stdout/stderr와 backend 파일 로그를 함께 본다. | `docker compose logs --since 30m backend frontend`, `docker compose exec backend sh -lc 'tail -n 200 var/logs/app.log'`, `docker compose exec backend sh -lc 'tail -n 200 var/logs/app.json'` | `backend/src/core/logging.py`가 stderr, `var/logs/app.log`, `var/logs/app.json`에 남기고 요청 로그는 request_id를 포함한다. | 중앙 로그 수집 위치, 보존 기간, request_id 검색 방식 확인 필요 |
| 설정 | compose env 치환, `.env.prod`, `.env.preview`, CORS, rewrite를 확인한다. | `docker compose config`, `docker compose exec backend sh -lc 'env | grep -E "ENVIRONMENT|DATABASE_URL|MINIO_ENDPOINT|REDIS_URL|LLM_PROVIDER|CORS_ORIGINS"'` | backend는 `.env.prod`/`.env.preview`와 compose `environment`를 함께 읽고 frontend는 `BACKEND_URL`을 사용한다. | secret 출력 금지 정책과 운영 env 조회 권한 확인 필요 |
| 데이터 의존성 | PostgreSQL migration, MinIO, Redis 또는 checkpoint 상태를 확인한다. | `docker compose exec postgres pg_isready -U aise`, `docker compose logs --tail 100 minio`, `docker compose exec redis redis-cli ping` | DB/MinIO/Redis는 compose 서비스로 정의되고, backend는 PostgreSQL/MinIO/Redis 관련 env를 받는다. | 백업/복구, Redis 장애 영향, MinIO lifecycle 확인 필요 |
| 외부 의존성 | LLM provider, API key, endpoint, quota/content filter 오류를 확인한다. | `docker compose logs --since 30m backend | grep -Ei "openai|azure|llm|quota|rate|content|timeout|401|403|429|500" || true` | LLM 호출은 `backend/src/services/llm_svc.py`와 `.env.*.example`의 provider/key/endpoint에 의존한다. | 실제 provider, quota, fallback, 비용 알림 기준 확인 필요 |

### 증상별 점검 순서

| 증상 | 점검 순서 | 관련 로그와 설정 위치 | 우선 복구 또는 다음 조치 | 확인 필요 |
| --- | --- | --- | --- | --- |
| 배포 직후 backend 컨테이너가 재시작됨 | `docker compose ps backend` -> `docker compose logs --tail 300 backend` -> migration 로그에서 `Running Alembic migrations`, `stamp head`, traceback 확인 -> `DATABASE_URL`과 PostgreSQL healthcheck 확인 | `backend/Dockerfile`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions`, `backend/src/core/database.py`, `.env.prod.example` | DB 연결 문제면 env와 compose service name을 수정하고 재기동한다. migration 실패면 데이터 손상 가능성이 있어 임의 `stamp head`를 운영에서 허용하지 말고 담당자 확인 후 진행한다. | migration 실패 시 rollback/downgrade, 백업 복구, `stamp head` 허용 기준 확인 필요 |
| frontend는 뜨지만 API가 404/502/500 | frontend `/api/v1/sample/` curl -> backend 직접 `/api/v1/sample/` curl -> `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, Next.js rewrite 확인 -> backend CORS와 router 로그 확인 | `frontend/next.config.ts`, `frontend/src/lib/api.ts`, `docker-compose.yml`, `docker-compose.preview.yml`, `backend/src/core/cors.py`, `backend/src/main.py` | rewrite 대상이 잘못되었으면 frontend 컨테이너를 rebuild/recreate한다. backend 직접 호출도 실패하면 backend 로그 기준으로 API 오류를 추적한다. | reverse proxy, TLS, allowed origin, 외부 URL smoke 기준 확인 필요 |
| Agent 채팅/SSE가 끊기거나 지연됨 | frontend SSE route handler 로그와 backend `/api/v1/agent/chat` 로그 확인 -> `docker compose logs --since 30m backend frontend` -> 프록시 buffering/timeout 가능성 분리 -> LangGraph checkpoint URL과 LLM 오류 확인 | `frontend/src/app/api/v1/agent/chat/route.ts`, `backend/src/routers/agent.py`, `backend/src/orchestration/graph.py`, `backend/src/schemas/events.py`, `docs/events.md`, `.env.prod.example` | 로컬/compose 내부에서 backend 직접 호출이 정상인데 외부 도메인에서만 끊기면 reverse proxy 설정 문제로 본다. LLM timeout/429는 provider 정책 확인 후 재시도/안내가 필요하다. | SSE buffering 비활성화, idle timeout, 재연결, LLM fallback 정책 확인 필요 |
| 문서 업로드 또는 RAG 처리 실패 | MinIO 로그와 backend error 로그 확인 -> 지식 문서 상태가 `failed`인지 확인 -> parser/embedding/RAG service 변경 여부 확인 -> bucket/env 확인 | `backend/src/services/storage_svc.py`, `backend/src/services/knowledge_svc.py`, `backend/src/services/document_processor.py`, `backend/src/services/embedding_svc.py`, `backend/src/services/rag_svc.py`, `backend/src/models/knowledge.py`, `MINIO_*` env | MinIO 연결 오류는 endpoint/key/bucket부터 확인한다. 처리 실패 데이터는 DB와 object storage 정합성을 같이 확인하고 한쪽만 삭제하지 않는다. | 업로드 제한, 악성 파일 검사, MinIO 백업/lifecycle, 재처리 운영 절차 확인 필요 |
| LLM 생성 기능만 실패 | backend 로그에서 provider/auth/rate/content filter 오류 확인 -> `.env.prod`/`.env.preview`의 provider/key/endpoint/model 확인 -> prompt/schema 변경 이력 확인 | `backend/src/services/llm_svc.py`, `backend/src/prompts`, `backend/src/agents`, `backend/src/services/srs_svc.py`, `backend/src/services/design_svc.py`, `backend/src/services/testcase_svc.py`, `.env.*.example` | key 누락/권한 문제면 secret 주입을 복구한다. content filter 또는 schema parse 실패면 사용자 입력과 prompt 변경을 함께 확인한다. | 실제 API key, deployment name, quota, 비용 한도, provider fallback 확인 필요 |
| DB 관련 API가 느리거나 실패 | PostgreSQL healthcheck와 로그 확인 -> backend request_id 기준 느린 API 확인 -> 최근 migration/index/vector 변경 확인 -> connection string과 SSL 설정 확인 | `backend/src/core/database.py`, `backend/src/models`, `backend/alembic/versions`, `docker-compose.yml`, `backend/src/middleware/logging_middleware.py` | migration 직후면 schema/index 누락을 먼저 본다. 운영 DB TLS가 필요한 경우 현재 `connect_args={"ssl": False}` 기본값과 충돌할 수 있다. | 운영 DB 모니터링, slow query 기준, pgvector index/vacuum/analyze 정책 확인 필요 |
| preview만 실패 | preview compose 상태와 포트 확인 -> `.env.preview` 값 확인 -> Redis 관련 오류 검색 -> 컨테이너명 충돌 여부 확인 | `docker-compose.preview.yml`, `deploy/preview.sh`, `.env.preview.example`, `docker compose -f docker-compose.preview.yml logs --tail 200 backend` | preview compose에는 Redis 서비스가 없으므로 Redis 오류가 반복되면 실제 필요 여부와 대상 URL을 확인한다. 기본 compose와 같은 daemon에서 컨테이너명 충돌 가능성도 확인한다. | preview 서버, DNS/TLS, Redis 대상, 데이터 보존/삭제 기준 확인 필요 |

### 로그와 설정 위치 요약

| 구분 | 위치 | 확인할 내용 | 주의사항 |
| --- | --- | --- | --- |
| Docker 서비스 로그 | `docker compose logs --tail 200 <service>`, preview는 `docker compose -f docker-compose.preview.yml logs --tail 200 <service>` | 컨테이너 시작 실패, build/runtime 오류, backend migration, frontend server, PostgreSQL/MinIO/Redis 오류 | secret이나 request body가 포함될 수 있으므로 외부 공유 전 마스킹한다. |
| Backend 파일 로그 | 컨테이너 내부 `var/logs/app.log`, `var/logs/app.json` | Loguru request_id, path, status, 처리 시간, AppException, unhandled exception | compose에는 `var/logs` volume mount가 없어 컨테이너 교체 시 파일 보존 여부가 약하다. 중앙 로그 수집은 확인 필요다. |
| Backend 로깅 설정 | `backend/src/core/logging.py`, `backend/src/middleware/logging_middleware.py`, `backend/src/core/exceptions.py` | `LOG_LEVEL`, `ENVIRONMENT`, 파일 rotation/retention, request_id, 예외 응답 | `diagnose`는 prod/staging이 아니면 활성화된다. 운영 환경명 설정 오류 시 민감 정보 노출 가능성을 확인한다. |
| Backend env와 인프라 설정 | `.env.prod.example`, `.env.preview.example`, `docker-compose.yml`, `docker-compose.preview.yml` | `DATABASE_URL`, `LANGGRAPH_CHECKPOINT_URL`, `REDIS_URL`, `MINIO_*`, `CORS_ORIGINS`, `LLM_PROVIDER` | 실제 secret 값과 secret manager는 저장소에 없다. 운영 값은 `확인 필요`다. |
| Frontend API 설정 | `frontend/next.config.ts`, `frontend/src/lib/api.ts`, `frontend/src/app/api/v1/agent/chat/route.ts`, `frontend/Dockerfile` | `/api/*` rewrite, `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, SSE proxy | Next.js rewrite와 SSE route handler 경로가 다르므로 일반 API와 채팅 스트리밍을 분리해서 점검한다. |
| 데이터/스토리지 설정 | `backend/src/core/database.py`, `backend/alembic`, `backend/src/services/storage_svc.py`, `backend/src/services/document_processor.py`, `docker-compose.yml` | DB SSL/URL, migration history, MinIO endpoint/bucket, 문서 처리 상태 | DB와 object storage 중 한쪽만 조작하면 정합성이 깨질 수 있다. |

## 배포 후 런타임 동작 흐름

배포 명령이 성공한 뒤 애플리케이션은 "인프라 컨테이너 준비 -> backend migration/server 시작 -> frontend standalone server 시작 -> 사용자 요청 처리" 순서로 동작한다. 이 흐름은 `docker-compose.yml`, `docker-compose.preview.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/next.config.ts`, `backend/src/main.py`에서 확인할 수 있다.

```mermaid
sequenceDiagram
    participant User as 사용자 브라우저
    participant FE as Next.js frontend
    participant BE as FastAPI backend
    participant DB as PostgreSQL pgvector
    participant Obj as MinIO
    participant Cache as Redis
    participant LLM as Azure/OpenAI API

    Note over FE,BE: Docker Compose가 컨테이너를 시작한 뒤의 런타임 흐름
    BE->>DB: alembic upgrade head
    BE->>BE: src.main:app 로드, router/CORS/logging 등록
    FE->>FE: node server.js로 standalone 서버 시작
    User->>FE: 화면 접속 및 /api/* 요청
    FE->>BE: Next.js rewrite, BACKEND_URL 대상 프록시
    BE->>DB: SQLAlchemy async session으로 업무 데이터 조회/저장
    BE->>Obj: 지식 문서 파일 업로드/다운로드/삭제
    BE->>Cache: REDIS_URL 기반 state/cache 접근
    BE->>LLM: 생성/검토/에이전트 기능 호출
    BE-->>FE: JSON 또는 streaming 응답
    FE-->>User: 화면 갱신
```

### 런타임별 시작 동작

| 런타임 | 시작 시점 동작 | 배포 후 확인 명령어 | 관련 파일 | 유지보수 포인트 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| PostgreSQL/pgvector | compose가 `pgvector/pgvector:pg16` 컨테이너와 named volume을 준비하고 healthcheck를 수행한다. | `docker compose ps postgres`, `docker compose exec postgres pg_isready -U aise` | `docker-compose.yml`, `docker-compose.preview.yml` | Alembic migration 전후 schema와 데이터 보존을 확인한다. | 운영 백업, 복구, RTO/RPO, migration 승인 절차 확인 필요 |
| MinIO | compose가 `minio/minio:latest`를 `server /data --console-address ":9001"`로 실행한다. backend 서비스는 lazy init 시 bucket 존재 여부를 확인하고 없으면 생성한다. | `docker compose logs --tail 100 minio`, `curl http://localhost:9001` | `docker-compose.yml`, `docker-compose.preview.yml`, `backend/src/services/storage_svc.py` | bucket 이름, access key, object 삭제 로직을 데이터 보존 정책과 맞춘다. | 운영 object storage가 MinIO인지 외부 S3 호환 서비스인지 확인 필요 |
| Redis | 기본 compose에서 `redis:7-alpine`이 appendonly 모드로 실행되고 healthcheck를 가진다. backend에는 `REDIS_URL=redis://redis:6379/0`이 주입된다. | `docker compose ps redis`, `docker compose exec redis redis-cli ping` | `docker-compose.yml`, `.env.prod.example`, `.env.preview.example` | state/cache 장애 시 backend 로그와 Redis 연결 문자열을 함께 확인한다. | preview compose에는 Redis 서비스가 없어 preview Redis 대상 확인 필요 |
| Backend/FastAPI | 컨테이너 entrypoint가 `alembic upgrade head`를 실행하고 실패 시 `alembic stamp head`를 시도한 뒤 `uvicorn src.main:app --host 0.0.0.0 --port 8081`을 실행한다. | `docker compose logs --tail 200 backend`, `curl http://localhost:8081/docs` | `backend/Dockerfile`, `backend/src/main.py`, `backend/alembic/versions` | 시작 로그에서 migration 결과와 router 로딩 오류를 먼저 확인한다. | `stamp head` fallback을 운영에서 허용할지 확인 필요 |
| Frontend/Next.js | Docker runner가 `.next/standalone` 산출물을 `node server.js`로 실행하고, `/api/:path*`는 `BACKEND_URL`로 rewrite한다. | `docker compose logs --tail 100 frontend`, `curl -I http://localhost:4000`, `curl http://localhost:4000/api/v1/sample/` | `frontend/Dockerfile`, `frontend/next.config.ts`, `docker-compose.yml` | `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, reverse proxy 경로가 같은 API 경로를 가리키는지 확인한다. | Dockerfile의 `npm ci`와 저장소의 pnpm 정책 불일치 확인 필요 |
| 외부 LLM API | backend의 생성/검토/에이전트 기능에서 `LLM_PROVIDER`에 따라 Azure 또는 OpenAI credential과 endpoint를 사용한다. | `docker compose exec backend sh -lc 'grep \"LLM\\|Azure\\|OPENAI\" var/logs/app.log | tail -n 50'` | `.env.prod.example`, `.env.preview.example`, `backend/src/services/llm_svc.py`, `backend/src/agents`, `backend/src/prompts` | key 누락, endpoint 오류, content filter, quota 오류를 구분해서 본다. | 실제 provider, model, quota, fallback, 비용 관리 기준 확인 필요 |

### 배포 후 사용자 요청 처리 흐름

1. 사용자는 frontend 포트로 접속한다.
   - 기본 compose: `http://<host>:4000`
   - preview compose: `http://<host>:4100` 또는 reverse proxy가 있다면 `https://preview.devbanjang.cloud`
   - 근거 파일: `docker-compose.yml`, `docker-compose.preview.yml`, `deploy.sh`, `deploy/preview.sh`
2. Next.js frontend는 브라우저 화면을 제공하고 API 요청을 `/api/*` 경로로 보낸다.
   - 근거 파일: `frontend/src/lib/api.ts`, `frontend/src/services/*`, `frontend/next.config.ts`
   - `NEXT_PUBLIC_API_URL`이 빈 값이면 같은 origin의 `/api/*`를 사용한다.
3. Next.js rewrite가 `/api/:path*` 요청을 `BACKEND_URL`로 프록시한다.
   - 기본/preview compose의 frontend `BACKEND_URL`은 `http://backend:8081`이다.
   - 근거 파일: `frontend/next.config.ts`, `docker-compose.yml`, `docker-compose.preview.yml`
   - 확인 명령: `curl http://localhost:4000/api/v1/sample/`, preview는 `curl http://localhost:4100/api/v1/sample/`
4. FastAPI backend는 CORS, logging middleware, router를 거쳐 요청을 처리한다.
   - 근거 파일: `backend/src/main.py`, `backend/src/core/cors.py`, `backend/src/middleware/logging_middleware.py`, `backend/src/routers`
   - 확인 명령: `curl http://localhost:8081/docs`, `docker compose logs --tail 200 backend`
5. 업무 데이터는 PostgreSQL에 저장되고, 파일/지식 문서는 MinIO에 저장된다.
   - DB 근거 파일: `backend/src/core/database.py`, `backend/src/models`, `backend/alembic/versions`
   - MinIO 근거 파일: `backend/src/services/storage_svc.py`, `backend/src/services/knowledge_svc.py`, `backend/src/routers/knowledge.py`
6. 생성형 기능은 backend agent/service 계층에서 LLM provider로 외부 API를 호출한다.
   - 근거 파일: `backend/src/services/llm_svc.py`, `backend/src/agents`, `backend/src/orchestration`, `backend/src/prompts`
   - 확인 필요: 실제 API key, endpoint, model, quota, fallback 정책은 저장소에 없다.
7. 장애 조사 시에는 같은 요청 흐름을 역순으로 따라간다.
   - frontend 화면/API rewrite 문제: `docker compose logs --tail 100 frontend`, `curl http://localhost:4000/api/v1/sample/`
   - backend 오류: `docker compose logs --since 30m backend`, `docker compose exec backend sh -lc 'tail -n 200 var/logs/app.log'`
   - DB/MinIO/Redis 오류: 각 compose 서비스 상태와 로그 확인
   - 확인 필요: 장애 등급, 알림 채널, on-call, 고객 공지 기준은 저장소에서 확인되지 않는다.

## 기본 배포 흐름

코드에서 확인되는 기본 배포 흐름은 `deploy.sh`와 `docker-compose.yml` 기준으로 다음과 같다.

```mermaid
sequenceDiagram
    participant Op as 운영자
    participant Script as deploy.sh
    participant Compose as Docker Compose
    participant Backend as backend container
    participant Frontend as frontend container
    participant DB as PostgreSQL

    Op->>Script: ./deploy.sh 또는 ./deploy.sh backend
    Script->>Script: .env 존재 확인
    alt 전체 배포
        Script->>Compose: docker compose down
        Script->>Compose: docker compose build --no-cache
        Script->>Compose: docker compose up -d
    else 특정 서비스 재시작
        Script->>Compose: docker compose up -d --build SERVICE
    end
    Compose->>DB: postgres healthcheck 대기
    Compose->>Backend: backend 시작
    Backend->>DB: alembic upgrade head
    Backend->>Backend: uvicorn src.main:app --port 8081
    Compose->>Frontend: frontend 시작
    Frontend->>Backend: BACKEND_URL=http://backend:8081
    Script->>Compose: docker compose ps
```

### 기본 배포 단계별 절차

1. 배포 호스트에서 저장소 루트로 이동한다.
   - 근거 파일: `deploy.sh`
   - 실행 예: `cd <repo-root>`
   - 확인 필요: 실제 운영 서버 접속 방법, 배포 계정, 작업 디렉터리 표준은 저장소에 없다.
2. `deploy.sh`가 `.env` 존재 여부를 검사한다.
   - 근거 파일: `deploy.sh`
   - 스크립트는 `.env`가 없으면 종료하고 `.env.example` 복사를 안내한다.
   - 확인 필요: 저장소에는 `.env.example`이 없고 `.env.prod.example`, `.env.preview.example`만 있으므로 실제 `.env`와 `.env.prod`를 어떻게 나누어 관리하는지 확인해야 한다.
3. `HOST_IP`를 `.env`에서 읽어 완료 메시지의 접속 URL에 사용한다.
   - 근거 파일: `deploy.sh`
   - 실행 로직: `grep HOST_IP .env 2>/dev/null | cut -d= -f2`
   - 확인 필요: 운영에서 `HOST_IP`를 직접 관리할지, DNS/리버스 프록시 주소를 쓸지 확인해야 한다.
4. 서비스 인자 없이 실행하면 전체 배포를 수행한다.
   - 근거 파일: `deploy.sh`
   - 실행 순서: `docker compose down` -> `docker compose build --no-cache` -> `docker compose up -d`
   - 의미: 기존 compose 서비스를 내린 뒤 backend/frontend 이미지를 캐시 없이 다시 빌드하고 모든 서비스를 백그라운드로 시작한다.
   - 확인 필요: 무중단 배포가 아니므로 운영 트래픽이 있는 환경에서 허용되는지 확인해야 한다.
5. 서비스명을 인자로 넘기면 해당 서비스만 재시작한다.
   - 근거 파일: `deploy.sh`
   - 실행 예: `./deploy.sh backend`, `./deploy.sh frontend`
   - 실행 로직: `docker compose up -d --build "$SERVICE"`
   - 확인 필요: backend 단독 재시작 시 migration 자동 실행 영향과 frontend/backend 버전 호환성 검증 기준은 저장소에 없다.
6. Docker Compose가 인프라 서비스를 먼저 준비한다.
   - 근거 파일: `docker-compose.yml`
   - PostgreSQL은 `pgvector/pgvector:pg16`, Redis는 `redis:7-alpine`, MinIO는 `minio/minio:latest`를 사용한다.
   - `backend`는 `postgres`와 `redis`의 healthcheck가 healthy가 된 뒤 시작된다.
   - 확인 필요: MinIO에는 compose healthcheck가 없고 bucket 생성 자동화도 확인되지 않는다.
7. backend 컨테이너가 시작하면서 DB migration과 FastAPI 서버 실행을 수행한다.
   - 근거 파일: `backend/Dockerfile`
   - 실행 순서: `alembic upgrade head` -> 실패 시 `alembic stamp head` 시도 -> `uvicorn src.main:app --host 0.0.0.0 --port 8081`
   - 확인 필요: migration 실패 후 `stamp head`로 계속 진행하는 정책이 운영에서 허용되는지 확인해야 한다.
8. frontend 컨테이너가 Next.js standalone 서버를 실행한다.
   - 근거 파일: `frontend/Dockerfile`, `frontend/next.config.ts`, `docker-compose.yml`
   - 빌드 시 `BACKEND_URL=http://backend:8081`, `NEXT_PUBLIC_API_URL=""`가 전달된다.
   - 런타임은 `node server.js`이며 컨테이너 내부 `3000` 포트를 호스트 `4000`에 노출한다.
   - 브라우저의 `/api/*` 요청은 Next.js rewrite를 통해 backend의 `/api/*`로 전달된다.
9. 배포 완료 후 `docker compose ps`로 상태를 출력한다.
   - 근거 파일: `deploy.sh`
   - 기본 접속 URL: frontend `http://<HOST_IP 또는 localhost>:4000`, backend `http://<HOST_IP 또는 localhost>:8081`
   - 추가 검증 예: `curl http://localhost:8081/docs`, `docker compose logs -f backend`

### 기본 배포 구성의 서비스별 포트

| 서비스 | 컨테이너명 | 내부 포트 | 호스트 포트 | 근거 파일 |
| --- | --- | --- | --- | --- |
| PostgreSQL | `aise2_preview_postgres` | `5432` | `${POSTGRES_PORT:-5432}` | `docker-compose.yml` |
| MinIO API | `aise2_minio` | `9000` | `${MINIO_PORT:-9000}` | `docker-compose.yml` |
| MinIO Console | `aise2_minio` | `9001` | `${MINIO_CONSOLE_PORT:-9001}` | `docker-compose.yml` |
| Redis | `aise2_redis` | `6379` | `${REDIS_PORT:-6379}` | `docker-compose.yml` |
| Backend | `aise2_backend` | `8081` | `8081` | `docker-compose.yml`, `backend/Dockerfile` |
| Frontend | `aise2_frontend` | `3000` | `4000` | `docker-compose.yml`, `frontend/Dockerfile` |

주의: 기본 compose의 PostgreSQL 컨테이너명이 `aise2_preview_postgres`로 되어 있어 이름만 보면 preview와 혼동될 수 있다. 실제 preview compose도 같은 이름을 사용하므로, 두 compose를 같은 Docker daemon에서 동시에 실행할 때 컨테이너명 충돌 가능성이 있는지 확인 필요이다.

## Preview 배포 흐름

Preview 배포는 `deploy/preview.sh`와 `docker-compose.preview.yml` 기준으로 동작한다.

```mermaid
sequenceDiagram
    participant Op as 운영자
    participant Script as deploy/preview.sh
    participant Git as Git
    participant Compose as Docker Compose preview

    Op->>Script: ./deploy/preview.sh [branch]
    Script->>Script: ROOT_DIR로 이동
    alt branch 인자 있음
        Script->>Git: git fetch origin branch
        Script->>Git: git checkout branch
        Script->>Git: git pull origin branch
    end
    Script->>Script: HOST_IP 계산 및 export
    Script->>Compose: docker compose -f docker-compose.preview.yml up -d --build
    Compose-->>Script: preview 컨테이너 실행
    Script-->>Op: Frontend :4100, Backend :8181, Swagger :8181/docs 출력
```

### Preview 배포 단계별 절차

1. preview 배포 스크립트를 저장소 어느 위치에서 실행해도 스크립트가 저장소 루트로 이동한다.
   - 근거 파일: `deploy/preview.sh`
   - 실행 로직: `ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"`, `cd "$ROOT_DIR"`
2. `--stop` 인자를 넘기면 preview 서비스를 중지한다.
   - 근거 파일: `deploy/preview.sh`
   - 실행 명령: `docker compose -f docker-compose.preview.yml down`
   - 확인 필요: volume을 삭제하지 않으므로 preview DB/MinIO 데이터 보존 정책은 별도 확인이 필요하다.
3. 배포 모드에서는 브랜치를 결정한다.
   - 근거 파일: `deploy/preview.sh`
   - 브랜치 인자가 없으면 `git branch --show-current` 결과를 사용한다.
   - 브랜치 인자가 있으면 `git fetch origin "$BRANCH"`, `git checkout "$BRANCH"`, `git pull origin "$BRANCH"`를 순서대로 실행한다.
   - 확인 필요: 배포 서버에서 직접 branch checkout/pull을 수행하는 방식의 승인 절차와 권한 관리는 저장소에 없다.
4. `HOST_IP`를 호스트 네트워크에서 계산해 export한다.
   - 근거 파일: `deploy/preview.sh`
   - 실행 로직: `hostname -I | awk '{print $1}'`
   - 확인 필요: preview 공개 주소가 compose 주석의 `preview.devbanjang.cloud`인지, 스크립트가 출력하는 IP 기반 URL인지 운영 표준 확인이 필요하다.
5. preview compose를 build/up 한다.
   - 근거 파일: `deploy/preview.sh`, `docker-compose.preview.yml`
   - 실행 명령: `docker compose -f docker-compose.preview.yml up -d --build`
   - 실행 결과: backend는 호스트 `8181`, frontend는 호스트 `4100`, PostgreSQL은 호스트 `5433`, MinIO API는 호스트 `9100`, MinIO console은 호스트 `9101`로 노출된다.
6. preview backend는 PostgreSQL healthcheck 이후 시작된다.
   - 근거 파일: `docker-compose.preview.yml`, `backend/Dockerfile`
   - backend는 `.env.preview`를 읽고 `DATABASE_URL`은 compose 내부 `postgres:5432`를 사용한다.
   - 확인 필요: preview compose에는 Redis 서비스가 없지만 `.env.preview.example`에는 `REDIS_URL=redis://localhost:6380/0`이 있으므로 Redis 사용 여부와 실제 대상 확인이 필요하다.
7. preview frontend는 같은 origin API 프록시 패턴을 사용한다.
   - 근거 파일: `docker-compose.preview.yml`, `frontend/next.config.ts`
   - `NEXT_PUBLIC_API_URL`은 빈 값이고 `BACKEND_URL=http://backend:8081`로 빌드/실행된다.
   - compose 주석은 브라우저가 `https://preview.devbanjang.cloud/api/*`로 요청하고 Next.js rewrite가 컨테이너 내부 backend로 프록시한다고 설명한다.
   - 확인 필요: TLS 종료, DNS, 리버스 프록시 설정 파일은 저장소에 없다.
8. 스크립트가 preview 접속 정보를 출력한다.
   - 근거 파일: `deploy/preview.sh`
   - 출력 대상: frontend `http://$HOST_IP:4100`, backend `http://$HOST_IP:8181`, Swagger `http://$HOST_IP:8181/docs`, DB `$HOST_IP:5433`
   - 추가 검증 예: `curl http://localhost:8181/docs`, `docker compose -f docker-compose.preview.yml logs -f backend`

### Preview 구성의 서비스별 포트

| 서비스 | 컨테이너명 | 내부 포트 | 호스트 포트 | 근거 파일 |
| --- | --- | --- | --- | --- |
| PostgreSQL | `aise2_preview_postgres` | `5432` | `5433` | `docker-compose.preview.yml` |
| MinIO API | `aise2_preview_minio` | `9000` | `9100` | `docker-compose.preview.yml` |
| MinIO Console | `aise2_preview_minio` | `9001` | `9101` | `docker-compose.preview.yml` |
| Backend | `aise2_preview_backend` | `8081` | `8181` | `docker-compose.preview.yml` |
| Frontend | `aise2_preview_frontend` | `3000` | `4100` | `docker-compose.preview.yml` |

## 실행 및 검증 명령어

이 섹션은 신입 개발자가 로컬 개발 서버, 컨테이너 기반 실행, 배포 스크립트, 상태 점검 명령을 구분해서 사용할 수 있도록 명령어와 목적을 함께 정리한다. 명령어는 저장소 루트에서 실행하는 것을 기본으로 한다.

### 빌드 및 배포 준비 명령어

배포 전에 아래 명령어로 환경 파일, compose 구문, backend migration/test, frontend build, Docker 이미지 빌드를 순서대로 확인한다. 코드에서 확인 가능한 준비 절차만 정리했으며, 실제 secret 값과 운영 승인 절차는 저장소에 없으므로 `확인 필요`로 둔다.

| 단계 | 명령어 | 목적 | 코드에서 확인한 동작 또는 근거 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 1 | `cp .env.prod.example .env.prod` | 기본 compose의 backend `env_file` 준비 | `docker-compose.yml`의 backend 서비스가 `.env.prod`를 읽는다. 예시 파일에는 `LLM_PROVIDER`, Azure/OpenAI key/endpoint, `REDIS_URL`, `LANGGRAPH_CHECKPOINT_URL` 항목이 있다. | `.env.prod.example`, `docker-compose.yml` | 실제 API key, endpoint, secret 저장소, 값 주입 방식은 확인 필요. |
| 2 | `cp .env.preview.example .env.preview` | preview compose의 backend `env_file` 준비 | `docker-compose.preview.yml`의 backend 서비스가 `.env.preview`를 읽는다. preview 예시는 LLM env와 `REDIS_URL`, `LANGGRAPH_CHECKPOINT_URL`을 포함한다. | `.env.preview.example`, `docker-compose.preview.yml` | preview compose에는 Redis 서비스가 없으므로 `REDIS_URL` 대상과 필요 여부 확인 필요. |
| 3 | `vi .env.prod` 또는 `vi .env.preview` | 배포 대상 환경에 맞는 secret/env 값을 채운다. | compose가 일부 DB/MinIO 값은 기본값으로 조합하지만, LLM credential과 외부 endpoint는 예시 파일에 빈 값으로 남아 있다. | `.env.prod.example`, `.env.preview.example`, `backend/src/services/llm_svc.py` | 운영 secret을 어떤 도구로 편집/배포할지, git에 기록하지 않는 절차 확인 필요. |
| 4 | `docker compose config` | 기본 compose 구문과 env 치환 결과를 배포 전에 검증한다. | 기본 compose는 PostgreSQL, MinIO, Redis, backend, frontend 서비스를 정의하고 backend/frontend build context를 참조한다. | `docker-compose.yml` | 이 compose가 production, staging, 또는 서버 단일 배포용인지 확인 필요. |
| 5 | `docker compose -f docker-compose.preview.yml config` | preview compose 구문과 env 치환 결과를 검증한다. | preview compose는 기본 compose와 포트/볼륨/컨테이너명을 분리하려고 구성되어 있다. | `docker-compose.preview.yml` | 기본 compose와 preview compose를 같은 Docker daemon에서 동시에 올릴 때 컨테이너명 충돌 여부 확인 필요. |
| 6 | `cd backend && uv sync --frozen` | backend 의존성 lockfile 기준 설치 가능 여부를 확인한다. | backend Dockerfile도 `uv sync --frozen --no-dev`와 `uv sync --frozen --no-dev`를 사용해 `uv.lock` 기준으로 설치한다. | `backend/pyproject.toml`, `backend/uv.lock`, `backend/Dockerfile` | 운영 빌드 환경에서 Python `3.14`와 `uv` 사용이 표준인지 확인 필요. |
| 7 | `cd backend && uv run alembic upgrade head` | 배포 전 DB migration 적용 가능성을 확인한다. | backend 컨테이너 entrypoint가 시작 시 `alembic upgrade head`를 먼저 실행한다. 실패하면 `alembic stamp head`를 시도하고 계속 진행한다. | `backend/Dockerfile`, `backend/alembic.ini`, `backend/alembic/versions` | 운영 DB에 직접 적용하기 전 staging 검증, 백업, rollback/downgrade 절차 확인 필요. |
| 8 | `cd backend && uv run pytest` | backend 테스트를 배포 전 실행한다. | `backend/pyproject.toml`에 pytest dev dependency와 `asyncio_mode = "auto"`가 정의되어 있다. | `backend/pyproject.toml`, `backend/tests` | CI에서 자동 실행되는지, 운영 배포 승인 기준에 포함되는지 확인 필요. |
| 9 | `cd frontend && pnpm install --frozen-lockfile` | frontend 의존성 lockfile 기준 설치 가능 여부를 확인한다. | `frontend/package.json`은 `packageManager: pnpm@9.15.0`과 `preinstall: npx only-allow pnpm`을 선언하고 `frontend/pnpm-lock.yaml`이 존재한다. | `frontend/package.json`, `frontend/pnpm-lock.yaml` | Dockerfile은 `npm ci`를 사용하므로 실제 운영 이미지 빌드가 pnpm lockfile과 일치하는지 확인 필요. |
| 10 | `cd frontend && pnpm lint` | frontend 정적 검사를 배포 전 실행한다. | `frontend/package.json`의 `lint` script가 `eslint`를 실행한다. | `frontend/package.json` | lint failure를 배포 차단 조건으로 삼는지 확인 필요. |
| 11 | `cd frontend && BACKEND_URL=http://backend:8081 pnpm build` | frontend production build를 로컬에서 사전 검증한다. | `frontend/package.json`의 `build` script는 `next build`이고, `frontend/next.config.ts`는 `/api/*` rewrite 대상에 `BACKEND_URL`을 사용한다. Docker compose도 frontend build arg로 `BACKEND_URL=http://backend:8081`을 전달한다. | `frontend/package.json`, `frontend/next.config.ts`, `docker-compose.yml` | 실제 운영 도메인/리버스 프록시 구조에서 `BACKEND_URL`을 어떤 값으로 둘지 확인 필요. |
| 12 | `docker compose build backend` | backend Docker 이미지 빌드를 단독으로 검증한다. | `backend/Dockerfile`은 `python:3.14-rc-slim` 기반 multi-stage build로 `uv sync --frozen --no-dev`를 수행한다. | `backend/Dockerfile`, `docker-compose.yml` | Python 3.14 RC 기반 이미지를 운영에서 허용할지 확인 필요. |
| 13 | `docker compose build frontend` | frontend Docker 이미지 빌드를 단독으로 검증한다. | `frontend/Dockerfile`은 `node:20-alpine` 기반으로 `npm ci`, `npm run build`, Next.js standalone 복사를 수행한다. | `frontend/Dockerfile`, `docker-compose.yml` | 저장소에는 `pnpm-lock.yaml`은 있으나 `package-lock.json`은 확인되지 않아 `npm ci` 성공 여부와 패키지 매니저 표준 확인 필요. |
| 14 | `docker compose build --no-cache` | 기본 compose의 backend/frontend 이미지를 캐시 없이 새로 빌드한다. | `deploy.sh`의 전체 배포 경로가 `docker compose build --no-cache`를 실행한다. | `deploy.sh`, `docker-compose.yml` | 빌드 시간이 길어질 수 있으므로 운영 배포 시간대와 캐시 정책 확인 필요. |
| 15 | `docker compose -f docker-compose.preview.yml build` | preview 이미지 빌드를 배포 실행 전에 확인한다. | preview compose도 backend/frontend build context를 사용한다. preview 배포 스크립트는 `up -d --build`로 빌드와 실행을 한 번에 수행한다. | `docker-compose.preview.yml`, `deploy/preview.sh` | preview 전용 image tag 또는 build cache 정책은 확인 필요. |
| 16 | `chmod +x deploy.sh deploy/preview.sh start-local.sh start-dev.sh` | 스크립트를 직접 실행할 수 있는 권한을 보장한다. | 루트 배포와 preview 배포는 각각 `./deploy.sh`, `./deploy/preview.sh` 형태로 문서화되어 있다. | `deploy.sh`, `deploy/preview.sh`, `start-local.sh`, `start-dev.sh` | 배포 서버에서 파일 권한이 git checkout 후 유지되는지 확인 필요. |

준비 명령 실행 시 특히 아래 불일치를 먼저 확인해야 한다.

- `deploy.sh`는 `.env` 파일 존재를 검사하고 `.env.example` 복사를 안내하지만, 현재 저장소에서 확인되는 예시 파일은 `.env.prod.example`, `.env.preview.example`이다. 스크립트 기반 기본 배포 전에 `.env`와 `.env.prod`의 역할 분리가 확인 필요이다.
- `frontend/package.json`은 pnpm 사용을 강제하고 `pnpm-lock.yaml`이 존재하지만, `frontend/Dockerfile`은 `npm ci`를 실행한다. 현재 파일 구성만 보면 Docker 빌드 재현성과 패키지 매니저 표준이 확인 필요이다.
- backend Docker 이미지는 `python:3.14-rc-slim`을 사용하고 프로젝트도 `requires-python = ">=3.14"`이다. Python 3.14 RC 이미지를 운영 표준으로 사용할지 확인 필요이다.

### 린트, 타입체크, 포맷 검증 명령어

배포 전 품질 검증 명령은 frontend 중심으로 스크립트가 정의되어 있다. backend는 현재 `backend/pyproject.toml`에 pytest 설정만 있고 ruff, mypy, black, pyright 같은 린트/타입체크/포맷 도구 설정이 확인되지 않는다. 따라서 backend 정적 검증 표준은 `확인 필요`로 표시하고, 코드에서 실행 근거가 있는 명령만 아래에 정리한다.

| 대상 | 명령어 | 목적 | 코드에서 확인한 근거 | 실패 시 확인할 것 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| Frontend lint | `cd frontend && pnpm lint` | Next.js, React, TypeScript 코드의 ESLint 위반과 정적 오류를 확인한다. | `frontend/package.json`의 `lint` script는 `eslint`를 실행한다. `frontend/eslint.config.mjs`가 Next.js Core Web Vitals와 TypeScript 설정을 사용한다. | ESLint가 출력한 파일 경로, rule 이름, line/column을 기준으로 수정한 뒤 같은 명령을 재실행한다. | CI/CD에서 lint 실패를 배포 차단 조건으로 삼는지 확인 필요. |
| Frontend typecheck | `cd frontend && pnpm exec tsc --noEmit` | TypeScript 타입 오류를 Next.js 빌드 전 별도로 확인한다. | `frontend/package.json` dev dependency에 `typescript`가 있고 `frontend/tsconfig.json`이 존재한다. 별도 `typecheck` script는 없다. | 타입 오류가 발생한 `frontend/src` 경로와 import alias, component props, API response type을 확인한다. | `typecheck` script를 `package.json`에 추가할지, CI에서 별도 단계로 둘지 확인 필요. |
| Frontend format check | `cd frontend && pnpm format:check` | Prettier 포맷 이탈 여부를 파일 수정 없이 검사한다. | `frontend/package.json`의 `format:check` script는 `prettier --check "src/**/*.{ts,tsx,css,json}"`를 실행한다. | 포맷이 맞지 않는 파일 목록을 확인하고 `pnpm format`으로 정리하거나 수동 수정한다. | 포맷 검사를 배포 전 필수 단계로 운영하는지 확인 필요. |
| Frontend format write | `cd frontend && pnpm format` | `src` 하위 TypeScript, CSS, JSON 파일을 Prettier 기준으로 자동 정리한다. | `frontend/package.json`의 `format` script는 `prettier --write "src/**/*.{ts,tsx,css,json}"`를 실행한다. | 자동 포맷 후 `git diff`로 의도하지 않은 대량 변경이 없는지 확인하고 `pnpm format:check`를 재실행한다. | 저장 시 자동 포맷, pre-commit hook, 팀 포맷 적용 시점은 확인 필요. |
| Frontend production build | `cd frontend && BACKEND_URL=http://backend:8081 pnpm build` | Next.js production build, route compilation, 서버/클라이언트 번들 생성, `/api/*` rewrite 설정을 함께 검증한다. | `frontend/package.json`의 `build` script는 `next build`이고 `frontend/next.config.ts`는 `BACKEND_URL`을 API rewrite 대상으로 사용한다. | 빌드 오류의 route, server/client component 경계, env 사용 위치, rewrite 대상 값을 확인한다. | 운영/preview 환경별 `BACKEND_URL` 표준 값 확인 필요. |
| Backend lint | `확인 필요` | Python 코드 스타일과 정적 오류를 배포 전 검사하는 표준 명령이 필요하다. | `backend/pyproject.toml`에 ruff, flake8, pylint 같은 lint dependency나 tool 설정이 확인되지 않는다. | 도구를 도입하기 전에는 pytest와 코드 리뷰로 보완해야 한다. | 사용할 린터, rule set, 배포 차단 기준 확인 필요. |
| Backend typecheck | `확인 필요` | FastAPI schema, service, agent, orchestration 계층의 타입 오류를 정적으로 확인하는 표준 명령이 필요하다. | `backend/pyproject.toml`에 mypy, pyright 같은 type checker dependency나 tool 설정이 확인되지 않는다. | 도구를 도입하기 전에는 pytest와 런타임 smoke check로 보완해야 한다. | mypy/pyright 도입 여부와 타입 엄격도 기준 확인 필요. |
| Backend format | `확인 필요` | Python 코드 포맷을 일관되게 맞추는 표준 명령이 필요하다. | `backend/pyproject.toml`에 black, ruff format, isort 같은 formatter dependency나 tool 설정이 확인되지 않는다. | 포맷 도구가 정해지기 전에는 변경 범위를 작게 유지하고 리뷰에서 스타일 이탈을 확인한다. | formatter 종류, line length, import 정렬 기준, pre-commit 적용 여부 확인 필요. |
| Backend syntax smoke | `cd backend && uv run python -m compileall src tests` | 별도 린터가 없는 상태에서 Python 문법 오류와 import-time 이전의 기본 컴파일 오류를 빠르게 확인한다. | Python 표준 라이브러리 `compileall`을 사용하며, backend 소스는 `backend/src`, 테스트는 `backend/tests`에 있다. | 컴파일 실패 파일과 line number를 확인하고 문법 오류를 수정한다. | 이 명령을 공식 배포 전 검증 단계로 채택할지 확인 필요. |

권장 실행 순서는 다음과 같다.

```bash
cd frontend && pnpm lint
cd frontend && pnpm exec tsc --noEmit
cd frontend && pnpm format:check
cd frontend && BACKEND_URL=http://backend:8081 pnpm build

cd backend && uv run python -m compileall src tests
cd backend && uv run pytest
```

주의: frontend는 `packageManager: pnpm@9.15.0`과 `preinstall: npx only-allow pnpm`을 선언하지만 `frontend/Dockerfile`은 `npm ci`와 `npm run build`를 사용한다. 검증 명령은 저장소의 lockfile과 package manager 선언을 기준으로 pnpm을 사용하도록 정리했으며, Docker 이미지 빌드 경로의 npm 사용은 운영 표준 확인이 필요하다.

### 테스트 실행 명령어와 목적

배포 전 테스트는 backend pytest, frontend 정적 검증, production build, 실행 중인 서비스 smoke check로 나누어 본다. 저장소에서 확인되는 CI/CD 파이프라인 파일은 없으므로, 어떤 명령을 필수 배포 게이트로 삼는지는 `확인 필요`이다.

| 구분 | 명령어 | 목적 | 코드에서 확인한 동작 또는 근거 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| 테스트 DB 인프라 준비 | `docker compose up -d postgres` | backend pytest가 사용할 PostgreSQL을 로컬 compose로 기동한다. | 테스트 fixture는 `localhost:5432/aise_test`에 접속한다. 기본 compose의 PostgreSQL은 호스트 `5432`를 노출한다. | `docker-compose.yml`, `backend/tests/conftest.py` | 로컬/CI 테스트 DB를 compose로 띄우는지, 별도 DB를 쓰는지 확인 필요. |
| 테스트 DB 생성 및 migration | `cd backend && bash scripts/setup_test_db.sh` | `aise_test` 테스트 DB를 만들고 Alembic migration을 적용한다. | wrapper가 `uv run python scripts/setup_test_db.py`를 실행한다. Python 스크립트는 `TEST_DB_*` 환경변수 기본값을 사용하고 `uv run alembic upgrade head`를 수행한다. | `backend/scripts/setup_test_db.sh`, `backend/scripts/setup_test_db.py`, `backend/alembic` | 테스트 DB 생성 권한과 CI에서의 DB 초기화 절차 확인 필요. |
| 테스트 DB 포트/이름 override | `cd backend && TEST_DB_HOST=localhost TEST_DB_PORT=5432 TEST_DB_NAME=aise_test bash scripts/setup_test_db.sh` | 기본 포트와 다른 DB를 사용할 때 테스트 DB 준비 대상을 명시한다. | `setup_test_db.py`가 `TEST_DB_NAME`, `TEST_DB_USER`, `TEST_DB_PASSWORD`, `TEST_DB_HOST`, `TEST_DB_PORT`를 읽는다. | `backend/scripts/setup_test_db.py` | 팀별 로컬 DB 포트, preview DB 포트 `5433`을 테스트에 사용할지 확인 필요. |
| backend 전체 테스트 | `cd backend && uv run pytest` | FastAPI router, service, agent, orchestration, artifact 관련 pytest 전체를 실행한다. | `backend/pyproject.toml`에 pytest, pytest-asyncio, pytest-cov가 dev dependency로 있고 `asyncio_mode = "auto"`가 설정되어 있다. | `backend/pyproject.toml`, `backend/tests` | 배포 전 전체 pytest 통과를 필수 조건으로 삼는지 확인 필요. |
| backend 특정 테스트 | `cd backend && uv run pytest tests/test_project.py` | 변경 범위가 좁을 때 관련 테스트 파일만 빠르게 확인한다. | `backend/tests` 아래에 router/service/agent/orchestration 단위의 pytest 파일이 분리되어 있다. | `backend/tests/test_project.py`, `backend/tests/test_orchestration.py`, `backend/tests/test_agent.py` | 특정 테스트만 통과해도 배포를 허용하는 기준은 확인 필요. |
| backend 테스트 함수 필터 | `cd backend && uv run pytest tests/test_orchestration.py -k retrieval` | 실패 재현이나 특정 기능 검증을 위해 테스트명을 필터링한다. | pytest의 `-k` 필터를 사용할 수 있고 orchestration/retrieval 관련 테스트 파일이 있다. | `backend/tests/test_orchestration.py`, `backend/tests/test_retrieval_gate.py` | 운영 hotfix에서 최소 테스트 범위를 어디까지 허용할지 확인 필요. |
| backend 커버리지 | `cd backend && uv run pytest --cov=src --cov-report=term-missing --cov-report=html` | 변경 후 누락된 backend 코드 경로를 확인하고 HTML 커버리지 리포트를 만든다. | `pytest-cov`가 dev dependency로 선언되어 있다. HTML 리포트는 기본적으로 `backend/htmlcov`에 생성된다. | `backend/pyproject.toml` | 목표 커버리지 수치와 CI 업로드 위치는 확인 필요. |
| frontend 의존성 검증 | `cd frontend && pnpm install --frozen-lockfile` | frontend lockfile 기준 설치가 재현되는지 확인한다. | `frontend/package.json`은 `packageManager: pnpm@9.15.0`과 `preinstall: npx only-allow pnpm`을 선언하고 `pnpm-lock.yaml`이 있다. | `frontend/package.json`, `frontend/pnpm-lock.yaml` | Dockerfile은 `npm ci`를 사용하므로 운영 이미지 빌드의 패키지 매니저 표준 확인 필요. |
| frontend lint | `cd frontend && pnpm lint` | Next.js/TypeScript ESLint 규칙으로 정적 오류를 확인한다. | `frontend/package.json`의 `lint` script는 `eslint`를 실행하고, `frontend/eslint.config.mjs`가 Next.js Core Web Vitals와 TypeScript 설정을 불러온다. | `frontend/package.json`, `frontend/eslint.config.mjs` | lint 실패를 배포 차단 조건으로 삼는지 확인 필요. |
| frontend format check | `cd frontend && pnpm format:check` | Prettier 포맷 이탈 여부를 배포 전에 확인한다. | `frontend/package.json`의 `format:check` script가 `prettier --check "src/**/*.{ts,tsx,css,json}"`을 실행한다. | `frontend/package.json` | 포맷 검사를 CI 필수 단계로 운영하는지 확인 필요. |
| frontend production build | `cd frontend && BACKEND_URL=http://backend:8081 pnpm build` | Next.js production build와 `/api/*` rewrite 설정을 검증한다. | `build` script는 `next build`이고 `frontend/next.config.ts`는 `BACKEND_URL`로 API rewrite 대상을 정한다. compose도 frontend build arg로 `BACKEND_URL=http://backend:8081`을 전달한다. | `frontend/package.json`, `frontend/next.config.ts`, `docker-compose.yml` | 실제 운영/preview에서 `BACKEND_URL`을 어떤 값으로 둘지 확인 필요. |
| frontend 전용 단위/E2E 테스트 | `확인 필요` | 전용 frontend test runner가 있는지 확인한다. | `frontend/package.json`에는 `test`, `vitest`, `jest`, `playwright` 스크립트가 확인되지 않는다. | `frontend/package.json` | frontend 단위 테스트 또는 E2E 테스트 도입 여부와 실행 명령 확인 필요. |
| Docker compose 구문 검증 | `docker compose config` | 테스트 후 배포 전에 기본 compose의 env 치환과 YAML 구문을 확인한다. | 기본 compose는 PostgreSQL, MinIO, Redis, backend, frontend와 build context를 정의한다. | `docker-compose.yml` | 이 검증을 배포 전 필수 단계로 운영하는지 확인 필요. |
| Preview compose 구문 검증 | `docker compose -f docker-compose.preview.yml config` | preview compose의 env 치환, 포트, 볼륨 구성을 확인한다. | preview compose는 기본 compose와 다른 포트와 볼륨명을 사용한다. | `docker-compose.preview.yml` | preview compose의 Redis 누락과 container_name 충돌 가능성 검토 기준 확인 필요. |
| 기본 환경 smoke check | `curl http://localhost:8081/docs` | backend가 기동했고 FastAPI 문서 엔드포인트가 열리는지 확인한다. | backend Docker entrypoint는 `uvicorn src.main:app --host 0.0.0.0 --port 8081`을 실행한다. | `backend/Dockerfile`, `backend/src/main.py`, `docker-compose.yml` | `/docs` 접근 허용을 운영에서도 유지할지 확인 필요. |
| 기본 API smoke check | `curl http://localhost:8081/api/v1/sample/` | 배포 후 backend sample router 응답을 확인한다. | 상태 점검 예시로 문서화된 sample API이며 router 파일이 존재한다. | `backend/src/routers/sample.py`, `backend/src/main.py` | sample API를 운영 health check로 사용할지 확인 필요. |
| frontend rewrite smoke check | `curl http://localhost:4000/api/v1/sample/` | frontend를 경유한 `/api/*` rewrite가 backend로 연결되는지 확인한다. | Next.js 설정이 `/api/:path*`를 `BACKEND_URL`로 rewrite한다. 기본 compose frontend는 호스트 `4000`에 노출된다. | `frontend/next.config.ts`, `docker-compose.yml` | 리버스 프록시/TLS 환경의 smoke check URL은 확인 필요. |
| preview smoke check | `curl http://localhost:8181/docs` 및 `curl http://localhost:4100/api/v1/sample/` | preview backend와 frontend rewrite 경로를 확인한다. | preview compose는 backend `8181`, frontend `4100`을 호스트에 노출한다. | `docker-compose.preview.yml`, `deploy/preview.sh` | `preview.devbanjang.cloud` 기준의 실제 smoke check URL과 인증서 상태 확인 필요. |

테스트 실패 시 우선순위는 다음과 같다.

1. backend pytest가 DB 연결 오류로 실패하면 `docker compose ps postgres`, `docker compose logs --tail 100 postgres`, `cd backend && bash scripts/setup_test_db.sh` 순서로 테스트 DB 상태를 먼저 확인한다.
2. backend 테스트가 특정 API 또는 service assertion에서 실패하면 실패한 테스트 파일명과 traceback을 기준으로 `backend/src/routers`, `backend/src/services`, `backend/src/agents`, `backend/src/orchestration` 중 관련 구현을 추적한다.
3. frontend lint/format/build가 실패하면 터미널에 표시된 파일 경로, 줄/열, rule 또는 Next.js build 오류를 먼저 수정한 뒤 같은 명령을 재실행한다.
4. smoke check가 실패하면 `docker compose ps`, `docker compose logs --tail 200 backend`, `docker compose logs --tail 200 frontend`로 컨테이너 상태와 rewrite 대상 `BACKEND_URL`을 함께 확인한다.

### 로컬 개발 서버 실행

| 명령어 | 목적 | 실행되는 서버와 포트 | 코드에서 확인한 동작 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| `./start-local.sh` | 로컬 개발용 backend/frontend를 한 번에 실행한다. | Backend `8082`, Swagger `8082/docs`, Frontend `3009` | `8082`, `3009` 포트를 점유한 기존 프로세스를 `lsof`로 찾아 종료한다. backend는 `uv sync` 후 `uv run uvicorn src.main:app --reload --host 0.0.0.0 --port=8082 --log-level debug`로 실행한다. frontend는 `BACKEND_URL=http://localhost:8082 npx next dev --hostname 0.0.0.0 --port 3009`로 실행한다. | `start-local.sh` | 로컬 표준 스크립트가 `start-local.sh`인지 `start-dev.sh`인지 확인 필요. PostgreSQL/MinIO/Redis는 이 스크립트가 자동 기동하지 않는다. |
| `./start-dev.sh` | 다른 포트 조합의 개발 서버를 한 번에 실행한다. | Backend `9999`, Swagger `9999/docs`, Frontend `3009` | `9999`, `3009` 포트를 점유한 기존 프로세스를 종료한다. backend는 `uv sync` 후 `uv run uvicorn src.main:app --port=9999 --reload --host 0.0.0.0`로 실행한다. frontend는 `node_modules`가 없으면 `pnpm install` 후 `pnpm exec next dev --hostname 0.0.0.0 --port 3009`로 실행한다. PostgreSQL compose 기동 코드는 주석 처리되어 있다. | `start-dev.sh` | backend 포트가 `9999`라서 frontend의 `/api/*` rewrite 기본값 `http://localhost:8081`과 맞지 않을 수 있다. 실제 사용 시 `BACKEND_URL` 주입 기준 확인 필요. |
| `cd backend && uv run uvicorn src.main:app --port=8081 --reload --host 0.0.0.0` | backend만 수동으로 개발 실행한다. | Backend `8081`, Swagger `8081/docs` | FastAPI 앱 진입점 `src.main:app`을 reload 모드로 실행한다. backend README의 예시 명령이다. | `backend/README.md`, `backend/src/main.py` | 로컬 DB, MinIO, Redis, LLM env를 어떻게 준비할지 확인 필요. |
| `cd frontend && pnpm dev` | frontend만 수동으로 개발 실행한다. | Next.js 기본 `3000` | `frontend/package.json`의 `dev` script가 `next dev`를 실행한다. | `frontend/package.json` | API rewrite 대상은 `frontend/next.config.ts`의 `BACKEND_URL` 기본값 `http://localhost:8081` 또는 실행 환경 변수에 의존한다. |
| `cd frontend && BACKEND_URL=http://localhost:8082 pnpm dev` | frontend 개발 서버가 `start-local.sh`로 띄운 backend `8082`를 바라보게 실행한다. | Frontend 기본 `3000`, API rewrite 대상 `8082` | Next.js rewrite가 `/api/:path*`를 `BACKEND_URL` 값으로 프록시한다. | `frontend/next.config.ts`, `start-local.sh` | 팀 표준 frontend 포트가 `3000`인지 `3009`인지 확인 필요. |

개발 서버 스크립트 공통 주의사항:

- 두 스크립트 모두 Ctrl+C를 받으면 backend/frontend 프로세스를 종료한다. PostgreSQL은 별도 종료가 필요하다는 메시지를 출력한다.
- 두 스크립트 모두 로컬 PostgreSQL/MinIO/Redis를 자동으로 보장하지 않는다. `start-dev.sh`에는 PostgreSQL compose 시작 코드가 있으나 주석 처리되어 있다.
- `start-local.sh`는 frontend 의존성 설치에 `npm install`과 `npx next dev`를 사용하고, `start-dev.sh`는 `pnpm install`과 `pnpm exec next dev`를 사용한다. 반면 `frontend/package.json`은 `packageManager: pnpm@9.15.0`와 `preinstall: npx only-allow pnpm`을 선언하므로 실제 표준 패키지 매니저는 확인 필요이다.

### 컨테이너 기반 로컬/배포 실행

| 명령어 | 목적 | 실행되는 서비스 | 코드에서 확인한 동작 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- | --- |
| `docker compose up -d --build` | 기본 compose 전체 서비스를 빌드하고 백그라운드로 실행한다. | PostgreSQL `5432`, MinIO `9000/9001`, Redis `6379`, Backend `8081`, Frontend `4000` | backend/frontend 이미지를 빌드하고, backend는 PostgreSQL/Redis healthcheck 이후 시작한다. frontend는 backend에 의존한다. | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | 이 구성이 production인지 staging인지 로컬 통합 실행용인지 확인 필요. |
| `docker compose up -d postgres redis minio` | 애플리케이션은 로컬 프로세스로 띄우고 인프라만 compose로 실행한다. | PostgreSQL, Redis, MinIO | 기본 compose에 정의된 인프라 컨테이너와 named volume을 사용한다. | `docker-compose.yml` | backend 로컬 실행 시 `DATABASE_URL`, `REDIS_URL`, `MINIO_ENDPOINT`가 컨테이너 주소가 아닌 localhost 포트에 맞게 설정되어야 하는지 확인 필요. |
| `docker compose up -d --build backend` | backend 컨테이너만 빌드/재시작한다. | Backend `8081` | backend 이미지를 빌드하고 entrypoint에서 Alembic migration 후 Uvicorn을 실행한다. | `docker-compose.yml`, `backend/Dockerfile` | migration 자동 실행과 실패 시 `alembic stamp head` 정책 확인 필요. |
| `docker compose up -d --build frontend` | frontend 컨테이너만 빌드/재시작한다. | Frontend `4000` | Next.js standalone build를 실행하고 `node server.js`로 `3000`을 열어 호스트 `4000`에 노출한다. | `docker-compose.yml`, `frontend/Dockerfile`, `frontend/next.config.ts` | backend API schema와 frontend 빌드 버전 호환성 검증 기준 확인 필요. |
| `docker compose down` | 기본 compose 서비스를 중지하고 컨테이너 네트워크를 정리한다. | 기본 compose 서비스 전체 | named volume은 삭제하지 않는다. | `docker-compose.yml` | 운영 환경에서 중지 허용 시점과 데이터 volume 보존 정책 확인 필요. |

### 스크립트 기반 배포 실행

| 명령어 | 목적 | 코드에서 확인한 동작 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- |
| `./deploy.sh` | 기본 compose 전체 배포를 수행한다. | `.env` 존재를 검사한 뒤 `docker compose down`, `docker compose build --no-cache`, `docker compose up -d`를 순서대로 실행한다. 완료 후 frontend `4000`, backend `8081`, `docker compose ps`를 출력한다. | `deploy.sh`, `docker-compose.yml` | `.env`와 `.env.prod` 역할 분리, `.env.example` 부재, 무중단 배포 여부 확인 필요. |
| `./deploy.sh backend` | backend 서비스만 빌드/재시작한다. | `docker compose up -d --build backend`를 실행한다. | `deploy.sh`, `backend/Dockerfile` | migration 자동 실행 영향과 운영 승인 절차 확인 필요. |
| `./deploy.sh frontend` | frontend 서비스만 빌드/재시작한다. | `docker compose up -d --build frontend`를 실행한다. | `deploy.sh`, `frontend/Dockerfile` | frontend/backend 버전 호환성 확인 필요. |
| `./deploy/preview.sh` | 현재 브랜치를 preview compose로 배포한다. | 현재 브랜치를 읽고 `docker compose -f docker-compose.preview.yml up -d --build`를 실행한다. 완료 후 frontend `4100`, backend `8181`, Swagger `8181/docs`, DB `5433`을 출력한다. | `deploy/preview.sh`, `docker-compose.preview.yml` | preview 서버, DNS/TLS, Redis 구성 확인 필요. |
| `./deploy/preview.sh feat/my-feature` | 지정 브랜치를 checkout/pull한 뒤 preview로 배포한다. | `git fetch origin <branch>`, `git checkout <branch>`, `git pull origin <branch>` 후 preview compose를 build/up 한다. | `deploy/preview.sh` | 배포 서버에서 직접 git checkout을 수행하는 권한과 승인 절차 확인 필요. |
| `./deploy/preview.sh --stop` | preview 서비스를 중지한다. | `docker compose -f docker-compose.preview.yml down`을 실행한다. | `deploy/preview.sh`, `docker-compose.preview.yml` | preview volume과 데이터 보존/삭제 기준 확인 필요. |

### 구성 확인과 상태 점검

배포 구성 파일 자체를 확인하는 명령어:

```bash
docker compose config
docker compose -f docker-compose.preview.yml config
```

기본 compose 배포:

```bash
cp .env.prod.example .env.prod
# .env.prod 값 입력 필요
docker compose up -d --build
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

스크립트 기반 기본 배포:

```bash
# deploy.sh는 .env 파일을 요구한다. 실제 .env 작성 기준은 확인 필요.
./deploy.sh
./deploy.sh backend
./deploy.sh frontend
```

Preview 배포와 중지:

```bash
cp .env.preview.example .env.preview
# .env.preview 값 입력 필요
./deploy/preview.sh
./deploy/preview.sh feat/my-feature
./deploy/preview.sh --stop
```

컨테이너 내부 상태 확인:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec postgres pg_isready -U aise
docker compose exec redis redis-cli ping
```

Backend API 확인:

```bash
curl http://localhost:8081/docs
curl http://localhost:8081/api/v1/sample/
```

개발 서버 API 확인:

```bash
# start-local.sh 기준
curl http://localhost:8082/docs

# start-dev.sh 기준
curl http://localhost:9999/docs

# frontend dev server가 API rewrite를 정상 수행하는지 확인
curl http://localhost:3009/api/v1/sample/
```

Preview API 확인:

```bash
curl http://localhost:8181/docs
```

## 로그 운영

현재 저장소에서 확인되는 로그 체계는 backend 애플리케이션 로그와 Docker 컨테이너 stdout/stderr 로그 중심이다. 중앙 로그 수집기, APM, metrics exporter, alert rule은 코드에서 확인되지 않는다.

```mermaid
flowchart LR
    User[사용자 요청] --> Frontend[Next.js frontend]
    Frontend -->|/api/* rewrite| Backend[FastAPI backend]
    Backend --> Middleware[LoggingMiddleware]
    Middleware --> Stderr[container stderr]
    Middleware --> AppLog[var/logs/app.log]
    Middleware --> JsonLog[var/logs/app.json]
    Operator[운영자] --> DockerLogs[docker compose logs]
    DockerLogs --> Stderr
    Operator --> Exec[docker compose exec backend]
    Exec --> AppLog
    Exec --> JsonLog
```

| 로그 대상 | 확인 방법 | 코드에서 확인한 내용 | 근거 파일 | 한계와 확인 필요 |
| --- | --- | --- | --- | --- |
| Backend 컨테이너 로그 | `docker compose logs -f backend` | Loguru가 `sys.stderr` handler를 등록하므로 애플리케이션 로그가 Docker 로그로 노출된다. backend entrypoint의 Alembic/uvicorn 출력도 컨테이너 로그로 확인한다. | `backend/src/core/logging.py`, `backend/Dockerfile` | Docker 로그 드라이버, 로그 파일 크기 제한, 외부 수집 대상은 확인 필요. |
| Backend 파일 로그 | `docker compose exec backend sh -lc 'tail -n 200 var/logs/app.log'` | 텍스트 로그 파일은 `var/logs/app.log`에 기록된다. 매일 자정 rotation, 7일 retention이 설정되어 있다. | `backend/src/core/logging.py` | 컨테이너 내부 파일이므로 컨테이너 재생성 시 보존되지 않을 수 있다. 운영에서 volume mount 또는 중앙 수집을 할지 확인 필요. |
| Backend JSON 로그 | `docker compose exec backend sh -lc 'tail -n 200 var/logs/app.json'` | 구조화 로그는 `serialize=True`로 `var/logs/app.json`에 기록된다. 텍스트 로그와 동일하게 매일 rotation, 7일 retention이다. | `backend/src/core/logging.py` | JSON 로그를 어떤 수집 시스템에 적재할지 확인 필요. |
| 요청/응답 로그 | backend 로그에서 `Request:`와 `Response:` 검색 | 모든 요청에 8자리 `request_id`가 부여되고, method/path, status code, 처리 시간이 기록된다. | `backend/src/middleware/logging_middleware.py`, `backend/src/main.py` | frontend 사용자 화면에는 request_id가 노출되지 않는다. 사용자 문의와 로그를 연결하는 운영 절차는 확인 필요. |
| 애플리케이션 예외 | backend 로그에서 `AppException`, `Unhandled exception`, `Internal Server Error` 검색 | `AppException`은 warning과 지정 status code로 응답한다. 미처리 예외는 exception stack trace를 남기고 500 JSON 응답을 반환한다. | `backend/src/core/exceptions.py`, `backend/src/middleware/logging_middleware.py` | 500 발생 시 자동 알림, 장애 등급 분류, 에스컬레이션 기준은 확인 필요. |
| Frontend 컨테이너 로그 | `docker compose logs -f frontend` | frontend Docker runner는 Next.js standalone 서버를 `node server.js`로 실행한다. | `frontend/Dockerfile`, `frontend/next.config.ts` | frontend 애플리케이션 레벨 로깅/브라우저 에러 수집(Sentry 등)은 확인되지 않는다. |
| PostgreSQL/Redis/MinIO 로그 | `docker compose logs -f postgres`, `docker compose logs -f redis`, `docker compose logs -f minio` | 각 서비스는 compose 서비스로 실행되며 Docker 로그로 확인한다. PostgreSQL과 Redis에는 healthcheck가 있다. | `docker-compose.yml`, `docker-compose.preview.yml` | DB slow query, MinIO audit log, Redis persistence monitoring은 확인 필요. |

### 로그 확인 기본 절차

1. 장애 시 먼저 서비스 상태를 확인한다.
   - 기본 compose: `docker compose ps`
   - preview compose: `docker compose -f docker-compose.preview.yml ps`
2. 장애가 발생한 사용자의 대략적인 요청 시각과 API 경로를 기준으로 backend 로그를 좁힌다.
   - 예: `docker compose logs --since 30m backend`
   - request path 확인: `Request: GET /api/...`, `Request: POST /api/...`
3. 500 또는 기능 오류가 있으면 같은 request_id의 `Response:`와 예외 로그를 함께 확인한다.
   - 파일 로그 예: `docker compose exec backend sh -lc "grep '<request_id>' var/logs/app.log"`
   - JSON 로그 예: `docker compose exec backend sh -lc "grep '<request_id>' var/logs/app.json"`
4. 컨테이너 시작 실패나 재시작 반복이면 entrypoint 로그를 먼저 본다.
   - 예: `docker compose logs --tail 200 backend`
   - 확인 키워드: `Running Alembic migrations`, `WARNING: alembic upgrade failed`, `Starting server`
5. frontend 화면에서 API 오류만 보이면 frontend 로그와 backend 로그를 같이 본다.
   - frontend가 `/api/*`를 backend로 rewrite하므로 backend 컨테이너가 정상인지 함께 확인해야 한다.

주의: backend 파일 로그는 컨테이너 내부 `var/logs`에 생성된다. 현재 compose에는 이 경로를 호스트 volume으로 연결하는 설정이 없으므로, 컨테이너 교체 후에도 로그를 보존해야 하는 운영 환경이라면 volume mount 또는 중앙 로그 수집 구성이 필요하다. 해당 구성은 현재 코드에서 확인되지 않으므로 `확인 필요`이다.

## 장애 대응 Runbook

아래 절차는 저장소 구성과 코드에서 직접 확인 가능한 범위의 1차 대응이다. 서비스 복구 승인, 장애 등급, 고객 공지, on-call 에스컬레이션은 저장소에서 확인되지 않으므로 `확인 필요`로 둔다.

### 공통 1차 점검

```bash
docker compose ps
docker compose logs --tail 200 backend
docker compose logs --tail 200 frontend
docker compose logs --tail 200 postgres
docker compose logs --tail 200 minio
docker compose logs --tail 200 redis
```

Preview 환경에서는 모든 명령에 `-f docker-compose.preview.yml`을 붙인다.

```bash
docker compose -f docker-compose.preview.yml ps
docker compose -f docker-compose.preview.yml logs --tail 200 backend
docker compose -f docker-compose.preview.yml logs --tail 200 frontend
docker compose -f docker-compose.preview.yml logs --tail 200 postgres
docker compose -f docker-compose.preview.yml logs --tail 200 minio
```

### 장애 유형별 확인과 조치

| 증상 | 우선 확인 명령어 | 코드에서 확인 가능한 원인 후보 | 1차 조치 | 한계와 확인 필요 |
| --- | --- | --- | --- | --- |
| Backend가 기동하지 않음 | `docker compose logs --tail 200 backend` | entrypoint에서 `alembic upgrade head` 후 `uvicorn src.main:app --port 8081`을 실행한다. migration 실패 시 `alembic stamp head`를 시도하고 계속 진행한다. | Alembic 오류, DB 연결 오류, env 누락 메시지를 확인한다. 필요 시 `docker compose up -d --build backend`로 재빌드/재시작한다. | migration 실패 후 stamp로 진행하는 정책의 운영 허용 여부, DB rollback 절차 확인 필요. |
| Backend가 DB 연결 실패 | `docker compose ps postgres`, `docker compose exec postgres pg_isready -U aise`, `docker compose logs --tail 200 postgres` | backend는 `DATABASE_URL=postgresql+asyncpg://...@postgres:5432/...`를 사용하고 PostgreSQL healthcheck 이후 시작된다. | PostgreSQL healthcheck 상태와 credential/env 값을 확인한다. 기본 compose라면 `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` override 여부를 본다. | 운영 DB 백업/복구, 외부 DB 사용 여부, 계정 권한 정책 확인 필요. |
| Redis 연결 관련 오류 | `docker compose ps redis`, `docker compose exec redis redis-cli ping`, `docker compose logs --tail 200 redis` | 기본 compose에는 Redis가 있고 backend에 `REDIS_URL=redis://redis:6379/0`이 주입된다. preview compose에는 Redis 서비스가 없다. | 기본 compose에서는 Redis healthcheck와 `PONG` 응답을 확인한다. preview에서 Redis 오류가 나면 `.env.preview`의 `REDIS_URL` 대상과 Redis 필요 여부를 확인한다. | preview Redis 구성은 코드상 불일치 가능성이 있어 확인 필요. |
| MinIO 업로드/다운로드 실패 | `docker compose logs --tail 200 minio`, `docker compose exec backend sh -lc 'grep MinIO var/logs/app.log \| tail -n 50'` | backend는 `MINIO_ENDPOINT=minio:9000`, access/secret, bucket을 env로 받는다. `storage_svc`는 bucket 확인/생성, 업로드, 다운로드, 삭제 실패를 로그로 남기고 AppException을 발생시킨다. | MinIO 컨테이너 상태, credential, bucket 이름, backend 로그의 `MinIO` 오류를 확인한다. | MinIO 데이터 백업, bucket lifecycle, 외부 object storage 전환 여부 확인 필요. |
| API가 500을 반환 | `docker compose logs --since 30m backend`, `docker compose exec backend sh -lc 'grep \"Unhandled exception\\|Internal Server Error\" var/logs/app.log \| tail -n 50'` | `LoggingMiddleware`가 미처리 예외를 `logger.exception`으로 남기고 500 응답을 반환한다. | request path, request_id, stack trace를 기준으로 관련 router/service를 추적한다. 최근 배포가 있으면 해당 서비스만 `docker compose up -d --build backend`로 재시작 가능한지 판단한다. | 장애 등급, 고객 영향 판단, 자동 알림/대시보드가 없어 확인 필요. |
| LLM 호출 실패 또는 생성 기능 실패 | `docker compose exec backend sh -lc 'grep \"LLM\\|Azure\\|OPENAI\\|API_KEY\\|ENDPOINT\" var/logs/app.log \| tail -n 80'` | `llm_svc`는 Azure/OpenAI credential 누락, content filter, JSON 파싱 실패, streaming 실패 등을 AppException 또는 warning/error로 처리한다. | `.env.prod` 또는 `.env.preview`의 provider/API key/endpoint/model 설정을 확인하고, backend 컨테이너를 재시작해 env 반영 여부를 확인한다. | 실제 LLM provider, 쿼터/비용 제한, fallback 모델, provider 장애 시 운영 정책 확인 필요. |
| Frontend에서 API만 실패 | `docker compose logs --tail 200 frontend`, `curl http://localhost:8081/docs`, `curl http://localhost:4000/api/v1/sample/` | frontend는 `BACKEND_URL=http://backend:8081`로 `/api/*` rewrite를 수행한다. | backend 직접 접근과 frontend rewrite 경로를 각각 확인한다. preview는 포트를 `8181`, `4100`으로 바꿔 확인한다. | 리버스 프록시, TLS, 도메인, timeout 설정은 저장소에 없어 확인 필요. |
| Preview 배포 후 서비스 충돌 | `docker ps --format 'table {{.Names}}\\t{{.Ports}}'`, `docker compose -f docker-compose.preview.yml ps` | 기본 compose의 PostgreSQL 컨테이너명도 `aise2_preview_postgres`이고 preview compose도 같은 이름을 사용한다. | 같은 Docker daemon에서 기본/preview를 동시에 올릴 경우 컨테이너명 충돌 여부를 확인한다. 필요 시 compose 파일의 container_name 정책을 조정한다. | 어떤 환경에서 두 compose를 동시에 운영하는지 확인 필요. |
| 디스크 사용량 증가 | `docker system df`, `docker volume ls`, `docker compose exec backend sh -lc 'du -sh var/logs || true'` | PostgreSQL/MinIO/Redis는 named volume을 사용한다. backend 파일 로그는 7일 retention이나 컨테이너 내부에 있다. | 불필요한 preview 컨테이너와 이미지 정리를 검토하고, DB/MinIO volume 사용량을 확인한다. | 운영 데이터 보존, 이미지 정리 주기, 로그 보존 기준 확인 필요. |

### 재시작과 중지 절차

기본 compose에서 특정 서비스만 재시작:

```bash
./deploy.sh backend
./deploy.sh frontend
docker compose restart backend
docker compose restart frontend
```

기본 compose 전체 재배포:

```bash
./deploy.sh
```

Preview 재배포와 중지:

```bash
./deploy/preview.sh
./deploy/preview.sh --stop
```

주의: `./deploy.sh` 전체 배포는 `docker compose down`을 먼저 실행하므로 무중단 배포가 아니다. 운영 트래픽이 있는 환경에서 이 절차를 그대로 사용할 수 있는지는 `확인 필요`이다.

### 롤백 한계

저장소에는 이미지 태그 기반 release 관리, 이전 이미지 보존, DB migration downgrade runbook, 데이터 복구 runbook이 확인되지 않는다. 따라서 장애 상황에서의 안전한 롤백은 아래 항목이 확정되기 전까지 `확인 필요`이다.

- 어떤 git ref 또는 image tag를 안정 버전으로 볼지 확인 필요.
- Alembic migration 실패 또는 데이터 오류 발생 시 downgrade를 허용할지 확인 필요.
- PostgreSQL/MinIO volume을 언제, 어디에 백업하는지 확인 필요.
- rollback 중 frontend/backend/API schema 버전 호환성을 어떻게 검증하는지 확인 필요.

## 운영 유지보수 절차

정기 유지보수에서 코드로 확인 가능한 점검 항목은 compose 상태, persistent volume, DB migration, 환경 변수, frontend/backend build 설정이다.

| 주기 | 점검 항목 | 권장 확인 명령어 | 관련 파일 | 확인 필요 |
| --- | --- | --- | --- | --- |
| 배포 전 | compose 구문과 env 주입 확인 | `docker compose config`, `docker compose -f docker-compose.preview.yml config` | `docker-compose.yml`, `docker-compose.preview.yml`, `.env.prod.example`, `.env.preview.example` | 실제 secret 값은 저장소 외부에서 확인 필요. |
| 배포 전 | Alembic migration 확인 | `cd backend && uv run alembic upgrade head` | `backend/alembic`, `backend/Dockerfile` | 운영 DB에 적용하기 전 staging 검증 절차 확인 필요. |
| 배포 전 | backend 테스트 | `cd backend && uv run pytest` | `backend/tests`, `backend/pyproject.toml` | CI에서 자동 실행되는지 확인 필요. |
| 배포 전 | frontend 빌드/검사 | `cd frontend && pnpm lint`, `cd frontend && pnpm build` | `frontend/package.json`, `frontend/next.config.ts`, `frontend/Dockerfile` | Dockerfile은 `npm ci`를 사용하므로 pnpm lockfile과 npm lockfile 기준 확인 필요. |
| 운영 중 | 서비스 상태 | `docker compose ps`, `docker compose logs --tail 100 backend` | `docker-compose.yml` | healthcheck가 backend/frontend/MinIO에는 없어 추가 필요 여부 확인 필요. |
| 운영 중 | 저장소 사용량 | `docker system df`, `docker volume ls` | `docker-compose.yml`, `docker-compose.preview.yml` | volume 백업과 정리 기준 확인 필요. |
| 운영 중 | 로그 보존 | `docker compose exec backend sh -lc 'ls -lh var/logs'` | `backend/src/core/logging.py` | 중앙 로그 수집과 장기 보존 기준 확인 필요. |
| 장애 후 | 원인 분석 기록 | backend request_id, stack trace, 배포 git ref, env 변경 이력 수집 | `backend/src/middleware/logging_middleware.py`, `deploy.sh`, `deploy/preview.sh` | RCA 템플릿, 장애 등급, 재발 방지 이슈 관리 방식 확인 필요. |

## 확인 필요

이 섹션은 배포·운영 문서 안에서 추측하면 안 되는 항목만 따로 모은 목록이다. 아래 항목은 코드와 저장소 파일만으로 최종값, 책임자, 승인 절차를 확정할 수 없으므로 운영 담당자에게 확인하기 전까지 모두 `확인 필요` 상태로 유지한다.

- 서버/클라우드 계정: 실제 운영 서버, 접속 계정, bastion/VPN, 클라우드 리소스 소유자, 비용/권한 관리자는 확인 필요.
- CI/CD 절차: 자동 배포 파이프라인, 배포 브랜치/태그, 테스트 게이트, 승인자, 실패 알림, 배포 이력 저장 위치는 확인 필요.
- 환경변수와 secret: 운영/preview별 실제 env 값, API key, endpoint, model, secret 저장소, rotation 정책은 확인 필요.
- 장애 대응 기준: 장애 등급, on-call, 알림 채널, 고객 공지 기준, RCA/postmortem 템플릿은 확인 필요.
- 데이터와 롤백 정책: DB/Object 백업, RTO/RPO, migration 승인, downgrade/rollback 허용 기준은 확인 필요.

다음 항목은 배포 관련 코드에서 최종 정책이나 실제 계정을 확인할 수 없다. 신입 개발자는 아래 표를 운영 담당자에게 확인하기 전까지 해당 값을 추정해서 문서, 스크립트, `.env` 파일에 확정값처럼 기록하면 안 된다.

| 범주 | 항목 | 상태 | 코드에서 확인한 범위 | 코드에서 확인되지 않는 내용 |
| --- | --- | --- | --- | --- |
| 운영 서버 | 실제 운영 서버와 접속 방법 | 확인 필요 | `deploy.sh`와 `deploy/preview.sh`는 현재 checkout된 서버에서 Docker Compose를 실행하는 방식만 보여준다. | 서버 IP/도메인, SSH 계정, 작업 디렉터리, bastion/VPN 필요 여부, 배포 실행 권한자 |
| 클라우드/인프라 계정 | 클라우드 계정과 리소스 소유자 | 확인 필요 | 저장소에는 `docker-compose.yml`, `docker-compose.preview.yml` 기반 단일 호스트 실행 구성이 있다. | AWS/GCP/Azure 계정, 사내 VPS 소유 부서, Kubernetes/Terraform 등 외부 IaC 존재 여부, 비용/권한 관리자 |
| CI/CD | 자동 배포 파이프라인과 승인 절차 | 확인 필요 | 현재 워크트리에서 `.github/workflows`, GitLab CI, Jenkinsfile 같은 파이프라인 파일은 확인되지 않았다. 수동 스크립트는 `deploy.sh`, `deploy/preview.sh`만 확인된다. | 어떤 브랜치/태그가 배포되는지, 테스트 게이트, 승인자, secret 주입 방식, 실패 알림, 배포 이력 보관 위치 |
| 환경변수 | 운영/preview 환경변수 실제값 | 확인 필요 | `.env.prod.example`, `.env.preview.example`, compose의 `environment` 블록에 변수 이름과 일부 기본값이 있다. | 실제 `DATABASE_URL`, `POSTGRES_*`, `MINIO_*`, `REDIS_URL`, `CORS_ORIGINS`, `BACKEND_URL`, `LLM_PROVIDER`, API key/endpoint/model 값과 환경별 차이 |
| 비밀 관리 | secret 저장소와 회전 정책 | 확인 필요 | 예시 env 파일에는 credential 항목이 비어 있고, compose는 `.env.prod`, `.env.preview`를 읽는다. | Vault/SOPS/클라우드 secret manager/GitHub Secrets 사용 여부, 키 발급자, rotation 주기, 유출 대응 절차 |
| 네트워크 | TLS/도메인/리버스 프록시 | 확인 필요 | preview compose 주석과 `CORS_ORIGINS`에 `preview.devbanjang.cloud`가 언급되고, frontend/backend 포트는 compose에 정의되어 있다. | DNS 소유자, TLS 인증서 발급/갱신, Nginx/Caddy/로드밸런서 설정, SSE timeout/buffering 설정, 방화벽 정책 |
| 배포 방식 | 무중단 배포와 롤백 절차 | 확인 필요 | `deploy.sh` 전체 배포는 `docker compose down` 후 재빌드/재기동한다. 이미지 태그나 release manifest는 확인되지 않는다. | 무중단 배포 필요 여부, 안정 버전 기준, 이전 이미지 보존, frontend/backend 버전 호환 검증, rollback 명령과 승인자 |
| 데이터 운영 | DB/Object 백업과 복구 | 확인 필요 | PostgreSQL/MinIO/Redis named volume은 compose에 정의되어 있다. | 백업 주기, 저장 위치, retention, RTO/RPO, 복구 drill, migration 전 백업 강제 여부 |
| 장애 대응 | 장애 등급, 알림, on-call, 고객 공지 | 확인 필요 | backend request 로그와 예외 로그, Docker logs 확인 방법만 코드에서 확인된다. PostgreSQL/Redis healthcheck는 있으나 backend/frontend/MinIO healthcheck는 없다. | 장애 등급 기준, 대응 시간, 알림 채널, on-call 순번, 고객 공지 기준, postmortem/RCA 템플릿 |
| 관측성 | 로그/메트릭/트레이싱 수집 | 확인 필요 | `backend/src/core/logging.py`가 stderr와 컨테이너 내부 파일 로그를 남긴다. `.env.prod.example`에는 Langfuse 주석만 있다. | 중앙 로그 수집기, 메트릭 대시보드, alert rule, Langfuse/Sentry/Prometheus/Grafana 사용 여부와 접근 권한 |
| Migration | Alembic 운영 정책 | 확인 필요 | `backend/Dockerfile` entrypoint가 `alembic upgrade head` 실패 시 `alembic stamp head`를 시도한다. | 운영에서 stamp fallback을 허용할지, 실패 시 배포 중단 기준, downgrade 사용 여부, 데이터 migration 검증/승인 절차 |

## 유지보수 포인트

- compose 파일 변경 시 backend의 `DATABASE_URL`, `LANGGRAPH_CHECKPOINT_URL`, `REDIS_URL`, `MINIO_ENDPOINT`, frontend의 `BACKEND_URL`이 같은 네트워크/포트 기준으로 맞는지 함께 확인한다.
- preview와 기본 compose를 같은 서버에서 동시에 운영하려면 컨테이너명과 포트 충돌을 먼저 확인한다. 특히 기본 compose의 PostgreSQL 컨테이너명이 `aise2_preview_postgres`로 되어 있다.
- backend 이미지 시작 시 Alembic migration이 자동 실행된다. 모델과 migration을 변경한 배포는 DB 백업과 migration 검증 절차가 필요하지만, 현재 저장소에는 해당 runbook이 없다.
- frontend는 `output: 'standalone'`을 전제로 Dockerfile이 `.next/standalone`을 복사한다. Next.js 설정을 바꾸면 Dockerfile도 같이 검토해야 한다.
- `frontend/package.json`은 pnpm 사용을 강제하지만 `frontend/Dockerfile`은 npm을 사용한다. lockfile과 Docker 빌드 재현성이 맞는지 유지보수 시 확인해야 한다.
- `.env.prod.example`, `.env.preview.example`은 LLM provider와 API key 항목을 포함한다. 운영 secret은 문서나 git에 직접 기록하면 안 되며, 실제 주입 방식은 확인 필요이다.

## 배포 변경 영향 범위

| 변경 대상 | 영향받는 운영 흐름 | 관련 파일 | 유지보수 시 주의할 포인트 |
| --- | --- | --- | --- |
| compose service name, network, port | frontend/backend 통신, CORS, smoke check, 운영 방화벽 | `docker-compose.yml`, `docker-compose.preview.yml`, `frontend/next.config.ts`, `backend/src/core/cors.py`, `deploy.sh`, `deploy/preview.sh` | 포트만 바꿔도 `BACKEND_URL`, `CORS_ORIGINS`, 문서의 curl 주소, reverse proxy 설정이 같이 바뀐다. 운영 도메인/TLS는 확인 필요다. |
| backend Dockerfile 또는 entrypoint | migration 적용, 앱 시작, 로그 위치, health check | `backend/Dockerfile`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/src/main.py`, `backend/src/core/logging.py` | `alembic upgrade head` 실패 후 `stamp head`로 진행하는 현재 정책은 운영 허용 여부가 확인 필요다. |
| frontend Dockerfile 또는 Next.js build 설정 | standalone 산출물, `/api/*` rewrite, 정적 asset serving | `frontend/Dockerfile`, `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/next.config.ts` | pnpm 강제 정책과 Dockerfile `npm ci` 불일치가 있어 lockfile/패키지 매니저 기준을 먼저 확정해야 한다. |
| env_file 또는 secret 변수 | DB, MinIO, Redis, LLM provider, CORS, LangGraph checkpoint | `.env.prod.example`, `.env.preview.example`, `docker-compose.yml`, `docker-compose.preview.yml`, `backend/src/services/llm_svc.py`, `backend/src/services/storage_svc.py` | 실제 secret 값, 저장소, 회전 정책은 문서에 확정값처럼 쓰지 말고 `확인 필요`로 둔다. |
| DB/MinIO/Redis volume | 데이터 보존, 백업/복구, rollback, preview 격리 | `docker-compose.yml`, `docker-compose.preview.yml`, `backend/src/models/*.py`, `backend/src/services/storage_svc.py` | volume 이름 변경은 기존 데이터 접근에 직접 영향을 준다. 백업, 복구, retention, migration 전 snapshot 기준은 확인 필요다. |
| 배포 스크립트 또는 CI/CD | 배포 승인, 브랜치 checkout, 재시작 범위, rollback | `deploy.sh`, `deploy/preview.sh`, 저장소에 존재하는 CI/CD 설정 파일 또는 별도 운영 문서 | 현재 스크립트는 수동 compose 중심이고 무중단/롤백 정책이 확정되어 있지 않다. 자동 파이프라인과 승인자는 확인 필요다. |
