# AISE Developer Handoff Docs

## 개요

이 문서 세트는 AISE 코드베이스를 처음 인수받는 신입 개발자가 로컬 실행 환경, 시스템 아키텍처, 주요 기능 흐름, 배포·운영 방식, 유지보수 포인트를 순서대로 이해할 수 있도록 정리한 인수인계 자료이다.

문서의 1차 독자는 저장소 구조와 서비스 흐름을 아직 모르는 신규 백엔드·프론트엔드 개발자다. 각 문서는 코드와 설정 파일에서 확인 가능한 내용을 우선으로 설명하며, 저장소만으로 확정할 수 없는 서버 계정, 클라우드 계정, CI/CD 운영 절차, 환경변수 실제 값, 장애 대응 기준은 추측하지 않고 `확인 필요`로 표시한다.

## 문서 목차

처음 온보딩하는 개발자는 아래 순서대로 읽으면 로컬 실행에서 운영·유지보수까지 자연스럽게 이어진다. 이미 맡은 작업이 정해져 있다면 목적 열을 기준으로 필요한 문서부터 열어도 된다.

| 순서 | 문서 | 목적 |
| --- | --- | --- |
| 1 | [실행 환경 구성](./setup.md) | 로컬 실행 환경, 필수 런타임, 의존성 설치, 실행/검증 명령을 확인한다. |
| 2 | [시스템 아키텍처](./architecture.md) | Next.js 프론트엔드, FastAPI 백엔드, PostgreSQL/pgvector, MinIO, Redis, LLM 연동의 전체 구조와 요청 흐름을 파악한다. |
| 3 | [기능 흐름](./features.md) | 프로젝트, 지식 문서, RAG, 요구사항, 산출물, Agent/HITL 등 주요 기능별 사용자 흐름과 구현 파일을 추적한다. |
| 4 | [테스트](./testing.md) | 테스트 DB 준비, backend pytest, frontend 정적 검증/build, smoke check, 실패 시 확인 지점을 확인한다. |
| 5 | [배포·운영](./deployment-ops.md) | Docker Compose, 배포 스크립트, preview/prod 구성, 운영 점검 명령과 미확인 운영 항목을 확인한다. |
| 6 | [유지보수](./maintenance.md) | 변경 작업 시 먼저 볼 파일, 검증 방법, 장애 추적 순서, 장기 유지보수 주의점을 확인한다. |

## 권장 온보딩 경로

아래 순서는 저장소를 처음 받은 개발자가 문서를 읽으며 실제로 따라갈 수 있는 기본 경로다. 각 단계의 완료 기준을 만족하면 다음 단계로 넘어간다.

| 단계 | 읽을 문서 | 따라 할 일 | 완료 기준 |
| --- | --- | --- | --- |
| 1. 저장소와 실행 전제 파악 | [setup.md](./setup.md) | 필수 런타임, 패키지 매니저, `.env` 준비 방식, Docker Compose 의존 서비스를 확인한다. | 로컬에서 필요한 도구, 환경 파일, 외부 서비스 목록을 설명할 수 있다. |
| 2. 로컬 실행 | [setup.md](./setup.md) | `start-dev.sh`, `start-local.sh`, Docker Compose 실행 경로 중 현재 환경에 맞는 방식을 선택하고 smoke check 명령을 확인한다. | backend, frontend, PostgreSQL, Redis, MinIO 실행 방식과 기본 확인 URL을 알고 있다. |
| 3. 큰 구조 이해 | [architecture.md](./architecture.md) | Mermaid 다이어그램을 기준으로 브라우저 요청, Next.js rewrite, FastAPI router, DB/MinIO/Redis/LLM 연결 흐름을 추적한다. | 화면 요청이 어떤 백엔드 모듈과 저장소 의존성으로 이어지는지 큰 흐름을 설명할 수 있다. |
| 4. 담당 기능 추적 | [features.md](./features.md) | 프로젝트, 지식 문서, RAG, 요구사항, 산출물, Agent/HITL 중 맡은 기능의 화면, API, service, model 파일을 따라간다. | 기능 변경 시 먼저 열어야 할 프론트엔드/백엔드 파일과 검증 명령을 정리할 수 있다. |
| 5. 테스트 기준 확인 | [testing.md](./testing.md) | 테스트 DB 준비, backend pytest, frontend lint/format/build, smoke check 절차와 실패 시 확인 지점을 따라간다. | 변경 전후 어떤 테스트를 실행해야 하고, 실패하면 어떤 파일부터 확인할지 설명할 수 있다. |
| 6. 배포·운영 경계 확인 | [deployment-ops.md](./deployment-ops.md) | 기본 compose, preview compose, `deploy.sh`, 로그 확인, 장애 1차 점검 절차를 읽고 `확인 필요` 항목을 분리한다. | 코드로 확인 가능한 배포 흐름과 조직 확인이 필요한 운영 정보를 구분할 수 있다. |
| 7. 변경 작업 준비 | [maintenance.md](./maintenance.md) | 변경 유형별 체크리스트, 테스트 우선순위, 장애 추적 순서, 데이터/LLM/문서 처리 유지보수 포인트를 확인한다. | 작은 변경을 시작하기 전에 영향 범위, 검증 방법, 미확인 운영 리스크를 기록할 수 있다. |

처음 하루 안에 최소한 1~3단계를 완료하는 것을 권장한다. 실제 이슈를 배정받은 뒤에는 4단계에서 담당 기능을 좁히고 5단계의 테스트 기준을 확인한다. 변경 전에는 7단계의 체크리스트를 먼저 확인한다. 배포나 운영 작업을 맡는 경우에는 6단계를 먼저 끝낸 뒤 팀의 실제 계정, secret, 승인 절차를 별도로 확인해야 한다.

## 작업별 빠른 이동

- 실행 환경을 처음 구성하거나 로컬 명령을 확인해야 하면 [setup.md](./setup.md)를 먼저 본다.
- 서비스 경계, 요청 흐름, 데이터 저장소 연결 관계를 이해해야 하면 [architecture.md](./architecture.md)를 본다.
- 특정 화면이나 API가 어떤 기능 흐름에 속하는지 추적해야 하면 [features.md](./features.md)를 본다.
- 테스트 DB 준비, backend pytest, frontend 정적 검증, smoke check 절차를 확인해야 하면 [testing.md](./testing.md)를 본다.
- Docker Compose, 배포 스크립트, 운영 점검, 미확인 인프라 항목을 확인해야 하면 [deployment-ops.md](./deployment-ops.md)를 본다.
- 변경 전 영향 범위, 테스트 우선순위, 장애 추적 순서를 정리해야 하면 [maintenance.md](./maintenance.md)를 본다.

## 문서별 유지보수와 변경 영향 범위

신규 개발자는 변경을 시작하기 전에 아래 표로 어느 문서를 먼저 갱신해야 하는지 확인한다. 코드 변경과 문서 변경의 영향 범위가 다르면 코드 근거 파일을 우선 확인하고, 운영 계정/CI/CD/secret/장애 대응처럼 저장소에서 확인되지 않는 값은 `확인 필요`로 남긴다.

| 문서 | 유지보수 시 주의할 포인트 | 변경 영향 범위 |
| --- | --- | --- |
| [setup.md](./setup.md) | 런타임 버전, 패키지 매니저, 환경변수, 로컬 실행 스크립트가 실제 코드와 맞는지 확인한다. | `backend/pyproject.toml`, `backend/Dockerfile`, `frontend/package.json`, `frontend/Dockerfile`, `start-dev.sh`, `start-local.sh`, `docker-compose.yml` 변경 시 함께 갱신한다. |
| [architecture.md](./architecture.md) | Mermaid 다이어그램, 컴포넌트 책임, 요청/데이터 흐름이 router/service/model 구성과 어긋나지 않게 유지한다. | Next.js rewrite, FastAPI router, DB 모델, MinIO/RAG/Agent/LLM 연결 구조 변경 시 다이어그램과 흐름 설명을 같이 갱신한다. |
| [features.md](./features.md) | 사용자 기능 설명은 화면, 프론트엔드 service/store, 백엔드 API/service/model, 검증 명령을 한 묶음으로 관리한다. | 프로젝트, 지식 문서, 요구사항, Artifact, Agent/HITL 기능의 API 계약이나 상태 전이가 바뀌면 기능별 표와 유지보수 포인트를 같이 갱신한다. |
| [testing.md](./testing.md) | 테스트 실행 순서, 테스트 종류, 성공 기준, 실패 시 확인 지점이 실제 테스트 파일과 스크립트에 맞는지 유지한다. | `backend/tests`, `backend/scripts/setup_test_db.py`, `backend/pyproject.toml`, `frontend/package.json`, compose smoke check 경로가 바뀌면 함께 갱신한다. |
| [deployment-ops.md](./deployment-ops.md) | compose, Dockerfile, 배포 스크립트, 로그/장애 점검 절차는 실제 배포 파일과 일치해야 한다. | 포트, env_file, healthcheck, image build, preview/prod 구성이 바뀌면 배포 흐름 다이어그램, 명령어, `확인 필요` 항목을 같이 갱신한다. |
| [maintenance.md](./maintenance.md) | 변경 유형별 체크리스트와 테스트 우선순위가 현재 테스트 파일/운영 리스크와 맞는지 유지한다. | DB migration, API 계약, LLM 프롬프트, SSE 이벤트, Artifact lineage, 배포 설정 변경 시 영향 범위와 검증 기준을 이 문서에 먼저 반영한다. |

## 로컬 실행 빠른 명령

처음 실행할 때는 루트 디렉터리에서 인프라 서비스를 먼저 띄운 뒤 개발 서버를 시작한다. 상세한 환경변수와 실패 대응은 [setup.md](./setup.md)의 실행 환경 구성을 기준으로 확인한다.

```bash
# PostgreSQL, MinIO, Redis 실행
docker compose up -d postgres minio redis

# backend/frontend 개발 서버 실행
./start-dev.sh

# 기본 동작 확인
curl -s http://localhost:9999/api/v1/sample/health
curl -I http://localhost:3009
```

컨테이너로 전체 구성을 한 번에 확인하려면 다음 명령을 사용한다. 현재 `frontend/Dockerfile`은 `npm ci`를 사용하지만 저장소의 프론트엔드 패키지 정책은 pnpm이므로 Docker frontend build 성공 여부는 `확인 필요` 항목으로 남아 있다.

```bash
docker compose up -d --build
docker compose ps
curl -s http://localhost:8081/api/v1/sample/health
curl -I http://localhost:4000
```

## 공통 테스트 실행 빠른 명령

저장소에서 코드로 확인되는 테스트 실행 경로는 백엔드 `pytest`와 프론트엔드 정적 검증/빌드다. 백엔드 테스트 명령은 `backend/pyproject.toml`, `backend/tests/conftest.py`, `backend/scripts/setup_test_db.sh`에 근거하고, 프론트엔드 검증 명령은 `frontend/package.json`의 scripts에 근거한다.

```bash
# 백엔드 테스트 DB 준비 및 전체 테스트
docker compose up -d postgres
cd backend
bash scripts/setup_test_db.sh
uv sync
uv run pytest

# 백엔드 커버리지 확인이 필요할 때
uv run pytest --cov=src --cov-report=term-missing
```

```bash
# 프론트엔드 정적 검증과 프로덕션 빌드
cd ..
cd frontend
pnpm install
pnpm lint
pnpm format:check
pnpm build
```

확인 필요:

- `frontend/package.json`에는 `pnpm test`, `vitest`, `jest`, `playwright` 실행 스크립트가 확인되지 않는다. 프론트엔드 단위 테스트나 E2E 테스트를 필수로 실행하는지는 확인 필요다.
- 운영 CI/CD에서 어떤 테스트 명령을 필수 게이트로 사용하는지는 저장소만으로 확정할 수 없다. 배포 전 필수 테스트 목록, 승인자, 실패 시 중단 기준은 확인 필요다.

## 빌드 및 패키징 빠른 명령

빌드와 패키징은 프론트엔드 Next.js production build, 백엔드 Docker 이미지 build, 전체 Docker Compose build로 나누어 확인한다. Python 백엔드는 별도 wheel/package 산출 명령이 저장소에 정의되어 있지 않고, `backend/Dockerfile`의 `uv sync --frozen --no-dev` 기반 컨테이너 이미지가 코드에서 확인되는 패키징 경로다.

| 대상 | 명령 | 산출물/확인 기준 | 근거 파일 | 확인 필요 |
| --- | --- | --- | --- | --- |
| Frontend production build | `cd frontend && pnpm install --frozen-lockfile && pnpm build` | `frontend/.next/` 생성, standalone 설정 유지 | `frontend/package.json`, `frontend/next.config.ts`, `frontend/pnpm-lock.yaml` | 운영/preview별 `BACKEND_URL` 표준 값 |
| Backend Docker image | `docker build -t aise2-backend:local ./backend` | `8081/tcp`를 노출하는 backend 이미지 생성 | `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock` | Python 3.14 RC 이미지 운영 허용 여부 |
| Frontend Docker image | `docker build -t aise2-frontend:local ./frontend` | `3000/tcp`를 노출하는 Next.js standalone 이미지 생성 | `frontend/Dockerfile`, `frontend/package.json` | Dockerfile의 `npm ci`와 저장소 pnpm 정책 불일치 |
| 기본 compose package | `docker compose build` | backend/frontend 이미지를 compose 기준으로 빌드 | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | image registry/tag 정책 |
| Preview compose package | `docker compose -f docker-compose.preview.yml build` | preview 포트/환경 기준 이미지 빌드 | `docker-compose.preview.yml`, `deploy/preview.sh` | preview 전용 cache/tag 정책 |
| 배포 스크립트 package | `./deploy.sh` 또는 `./deploy.sh backend` | 전체 또는 단일 서비스를 build 후 기동 | `deploy.sh`, `docker-compose.yml` | `.env`와 `.env.prod` 역할 분리, 운영 승인 절차 |

자세한 실패 대응은 [setup.md](./setup.md)의 `빌드 실행 및 결과 확인 명령어`와 [deployment-ops.md](./deployment-ops.md)의 `빌드 및 배포 준비 명령어`를 따른다.

## 문서별 검증·점검 명령 색인

각 상세 문서는 결과 검증과 운영 점검에 필요한 명령을 문서 안에 포함한다. 처음 읽을 때는 아래 표의 명령 묶음을 먼저 확인하고, 실제 실행 전에는 각 문서의 `확인 필요` 항목도 함께 본다.

| 문서 | 명령 묶음 | 대표 명령 | 확인 기준 |
| --- | --- | --- | --- |
| [setup.md](./setup.md) | 로컬 실행, 의존성 설치, pytest, frontend lint/build, compose smoke check | `./start-dev.sh`, `uv run pytest`, `pnpm lint`, `docker compose up -d --build` | 개발 서버와 기본 API가 응답하고, 백엔드 테스트 및 프론트엔드 정적 검증이 통과한다. |
| [architecture.md](./architecture.md) | 런타임 연결 확인, 아키텍처 경계별 테스트, Docker 패키징 | `curl -s http://localhost:9999/api/v1/sample/health`, `uv run pytest tests/test_orchestration.py`, `docker build -t aise2-backend:local ./backend` | 브라우저, Next.js, FastAPI, DB/스토리지, Agent 경계가 문서의 흐름대로 연결된다. |
| [features.md](./features.md) | 기능별 pytest, Agent smoke, frontend lint/build | `uv run pytest tests/test_project.py`, `uv run python scripts/smoke_langgraph_chat.py`, `pnpm build` | 수정한 기능의 router/service/model/agent와 화면 계약이 함께 검증된다. |
| [testing.md](./testing.md) | 테스트 DB 준비, backend pytest, 부분 테스트, frontend 정적 검증/build, smoke check | `bash scripts/setup_test_db.sh`, `uv run pytest`, `pnpm lint`, `curl -s http://localhost:4000/api/v1/sample/health` | 테스트 종류별 성공 기준을 확인하고, 실패 시 DB/fixture/router/service/frontend rewrite 중 어디를 볼지 구분한다. |
| [deployment-ops.md](./deployment-ops.md) | 배포 전 config/build/test, 상태 점검, 로그 확인, smoke check | `docker compose config`, `docker compose ps`, `docker compose logs --tail 200 backend`, `curl http://localhost:4000/api/v1/sample/` | compose 구문, 이미지 빌드, 컨테이너 상태, backend 직접 접근, frontend rewrite 경로를 구분해 확인한다. |
| [maintenance.md](./maintenance.md) | 변경 유형별 테스트 우선순위, migration 검증, 장애 추적 명령 | `uv run alembic upgrade head`, `uv run pytest`, `docker compose logs backend`, `pnpm lint` | 변경 범위별 영향 파일과 테스트를 짝지어 확인하고, 장애 시 로그와 상태를 같은 순서로 추적한다. |

## 공통 사용 원칙

- 문서에 적힌 파일 경로는 해당 설명의 코드 근거다. 동작이 바뀌었는지 확인할 때는 먼저 표의 관련 파일을 열어 실제 구현을 확인한다.
- 실행과 검증은 문서의 명령어를 기준으로 하되, 운영 서버나 CI/CD에서 쓰는 최종 명령은 `확인 필요` 항목과 팀 운영 문서를 함께 확인한다.
- 아키텍처와 배포·운영 흐름은 Mermaid 다이어그램으로 제공한다. 다이어그램은 코드에서 확인한 구성 요소와 연결만 표현하며, 코드에서 확인되지 않는 DNS, TLS, 클라우드 네트워크, secret 저장소는 별도 확인 대상이다.
- 기능을 수정할 때는 `features.md`에서 사용자 흐름과 API 진입점을 찾고, `maintenance.md`에서 관련 검증 명령과 주의점을 확인한다.

## 빠른 확인 명령

문서 내용이 저장소에 반영되어 있는지 확인할 때는 루트 디렉터리에서 아래 명령을 사용할 수 있다.

```bash
rg --files docs
rg "확인 필요|Mermaid|mermaid|실행|검증|유지보수" docs
```

확인 필요:

- 이 README는 코드베이스 분석 결과를 읽는 길잡이 문서이며, 실제 조직의 온보딩 절차, 접근 권한 신청 절차, 배포 승인자, 장애 대응 연락망은 저장소에서 확인되지 않는다.
