# AISE 2.0 — 개발 가이드

---

## 1. 서버 실행 방법

### 실행
```bash
./start-dev.sh
```

이 스크립트를 실행하면 아래 순서로 동작합니다:

1. **기존 프로세스 정리** — 포트 8081(Backend), 3000(Frontend)에 떠있는 프로세스를 자동 종료
2. **PostgreSQL 시작** — `docker-compose.yml`을 통해 Docker 컨테이너로 실행, 준비될 때까지 대기
3. **Backend 의존성 동기화** — `uv sync`로 Python 패키지 설치/업데이트
4. **Backend 시작** — FastAPI 서버 (`http://서버IP:8081`), 코드 변경 시 자동 리로드
5. **Frontend 의존성 확인** — `node_modules`가 없으면 `npm install` 자동 실행
6. **Frontend 시작** — Next.js 서버 (`http://서버IP:3000`)

### 실행 후 접속 주소

| 서비스 | URL | 설명 |
|--------|-----|------|
| Frontend | `http://서버IP:3000` | 웹 애플리케이션 |
| Backend | `http://서버IP:8081` | API 서버 |
| Swagger | `http://서버IP:8081/docs` | API 문서 (자동 생성) |
| PostgreSQL | `서버IP:5432` | DB (user: aise / pw: aise1234 / db: aise) |

### 종료
- `Ctrl+C` — Backend + Frontend 동시 종료
- PostgreSQL은 계속 실행됨. 종료하려면: `docker compose down`

---

## 2. 최상위 폴더/파일 구조

```
aise2.0/
├── CLAUDE.md              # AI 에이전트(Claude Code)에게 주는 프로젝트 지침서
├── PLAN.md                # 전체 작업 계획 (Phase 1~6 체크리스트)
├── PROGRESS.md            # 진행 상황 추적 (날짜별 작업 로그)
├── docker-compose.yml     # PostgreSQL 실행 설정
├── start-dev.sh           # 개발 서버 원클릭 시작 스크립트
├── docs/                  # 프로젝트 문서
│   ├── requirements/      #   시스템 요구사항 정의서 (FR-PF, FR-RQ, FR-TC)
│   ├── interface.md       #   Backend ↔ Frontend API 인터페이스 정의
│   └── info.md            #   이 문서 (개발 가이드)
├── references/            # 기술 조사 결과 (날짜_주제.md 형식)
├── backend/               # FastAPI 백엔드
├── frontend/              # Next.js 프론트엔드
├── legacy/                # aise 1.0 레거시 코드 (참조용)
│   └── aise1.0/
├── .claude/               # Claude Code 설정 및 커맨드 스킬
└── .gitlab/               # GitLab MR 템플릿
```

---

## 3. Frontend / Backend 폴더 구조

### Backend (`backend/src/`)

| 폴더 | 역할 |
|------|------|
| `main.py` | FastAPI 앱 엔트리포인트 |
| `core/` | 공통 설정 — CORS, 예외처리, 로깅(Loguru) |
| `middleware/` | 요청/응답 로깅 미들웨어 |
| `routers/` | API 엔드포인트 정의. `dev/`에 개발용 API 포함 |
| `schemas/api/` | Pydantic 스키마 — API 요청/응답 구조 정의 |
| `schemas/llm/` | LLM 출력 구조 정의 (Structured Output용) |
| `models/` | DB 모델 (SQLAlchemy) |
| `services/` | 비즈니스 로직 + 단순 LLM API 호출 (정제, Review 등) |
| `integrations/` | 외부 시스템 연동 — Jira, Polarion, Confluence (Import/Export) |
| `agents/` | Deep Agents 워크플로우 — 복잡한 생성 작업 (SRS, TC, Design) |
| `prompts/` | LLM 프롬프트 템플릿 (assist/, review/, srs/, design/, testcase/) |
| `utils/` | 유틸리티 — 파서, 포맷 변환기 등 |

### Frontend (`frontend/src/`)

| 폴더 | 역할 |
|------|------|
| `app/` | Next.js App Router. Route Group 구조: `(auth)` 인증, `(main)` 메인 |
| `app/(auth)/` | 인증 레이아웃 (로그인 등) |
| `app/(main)/` | 메인 레이아웃 — `dashboard/`, `project/`, `chat/`, `workflow/` |
| `components/` | UI 컴포넌트 — `chat/`, `layout/`, `overlay/`, `ui/`, `shared/` |
| `hooks/` | 커스텀 React 훅 (useResize, useMediaQuery 등) |
| `stores/` | Zustand 상태관리 (chat, panel, overlay) |
| `config/` | 네비게이션 등 설정 |
| `lib/` | 유틸리티 (cn 헬퍼, 폰트 설정) |
| `types/` | TypeScript 타입 정의 |

---

## 4. Claude Code 커맨드 스킬

Claude Code에서 `/스킬명` 으로 호출할 수 있는 자동화 커맨드입니다.

### 프로젝트 관리

| 커맨드 | 사용법 | 설명 |
|--------|--------|------|
| `/sync` | `/sync` | 작업 시작 시 PLAN.md + PROGRESS.md를 읽고 현재 상황 브리핑 |
| `/plan` | `/plan` 또는 `/plan update` | 작업 계획 확인 또는 완료 항목 체크 |
| `/progress` | `/progress` 또는 `/progress 작업내용` | 진행 상황 확인 또는 작업 로그 추가 |

### Git / 코드 관리

| 커맨드 | 사용법 | 설명 |
|--------|--------|------|
| `/branch` | `/branch feat/project-crud` | main 최신화 후 feature 브랜치 생성 |
| `/mr` | `/mr` 또는 `/mr 커밋메시지` | commit + push + GitLab MR 자동 생성 |

### 개발 도구

| 커맨드 | 사용법 | 설명 |
|--------|--------|------|
| `/api` | `/api project` | 지정한 리소스의 라우터, 스키마, 서비스 스캐폴딩 생성 |
| `/prompt` | `/prompt create assist-refine` | LLM 프롬프트 작성 또는 개선 |
| `/req` | `/req FR-RQ-01-02` 또는 `/req Review` | 요구사항 ID 조회 또는 키워드 검색 |
| `/update-docs` | `/update-docs` | 프로젝트 구조 변경을 감지하여 docs/info.md 자동 업데이트 |

### 조사 / 참조

| 커맨드 | 사용법 | 설명 |
|--------|--------|------|
| `/research` | `/research Azure Responses API` | 주제 조사 후 references/에 저장 |
| `/ref` | `/ref testcase` | legacy 코드 + references에서 키워드 검색 |

### Deep Agents / LangChain 스킬 (AI 에이전트 코딩 참조용)

> 이 스킬들은 사용자가 직접 호출하는 것이 아니라, Claude Code가 LangChain/LangGraph/Deep Agents 코드를 작성할 때 **자동으로 참조**하는 가이드입니다.

| 스킬 | 역할 | AISE 2.0 활용 시점 |
|------|------|-------------------|
| `framework-selection` | LangChain vs LangGraph vs Deep Agents 선택 가이드 | 아키텍처 결정 시 |
| `langchain-dependencies` | 패키지 버전/설치 가이드 | 의존성 추가 시 |
| `langchain-fundamentals` | `@tool`, structured output, 에이전트 생성 | AI 어시스트, Review 구현 시 |
| `langchain-middleware` | 승인 워크플로우, 커스텀 미들웨어 | Review 수락/거절 흐름 구현 시 |
| `langchain-rag` | RAG 파이프라인 (문서 로딩/분할/임베딩/검색) | Import/Classification 구현 시 |
| `langgraph-fundamentals` | StateGraph, 노드, 에지, 스트리밍 | SRS/TC 생성 파이프라인 구현 시 |
| `langgraph-persistence` | 체크포인터, thread 관리, 상태 저장 | Chat 인터페이스 (UCD/TC Chat) 구현 시 |
| `langgraph-human-in-the-loop` | interrupt/resume 패턴, 승인 워크플로우 | Review 승인 흐름 구현 시 |
| `deep-agents-core` | Deep Agents 하네스 아키텍처, SKILL.md 포맷 | SRS/TC/Design 에이전트 구현 시 |
| `deep-agents-memory` | 메모리 백엔드 (State/Store/Filesystem) | 대화 이력, 세션 관리 구현 시 |
| `deep-agents-orchestration` | 서브에이전트, TodoList, 작업 계획 | 복잡한 생성 파이프라인 구현 시 |

### 작업 흐름 예시

> 아래는 Claude Code에게 지시하는 방식입니다.
> Claude Code 채팅창에서 `/스킬명`을 입력하면 AI 에이전트가 자동으로 수행합니다.

```
/sync                              ← 에이전트가 현재 상황 브리핑
/branch feat/project-crud          ← 에이전트가 main pull + 브랜치 생성
/req FR-PF-02                      ← 에이전트가 관련 요구사항 검색
/api project                       ← 에이전트가 API 스캐폴딩 코드 생성
(에이전트가 코드 작업 수행...)
/mr                                ← 에이전트가 commit + push + MR 생성
```

---

## 5. 작업 수행 가이드

### 작업 시작 전

1. **PLAN.md 확인** — 현재 Phase에서 할 일 확인
2. **PROGRESS.md 확인** — 다른 사람이 이미 진행한 작업 확인
3. **docs/interface.md 참고** — API 구조와 JSON 형식 확인
4. **docs/requirements/ 참고** — 구현할 기능의 요구사항 ID 확인

### 브랜치 규칙

```
main (보호됨, 직접 push 금지)
  ├── feat/project-crud        ← 기능 개발
  ├── feat/requirement-api     ← 기능 개발
  ├── fix/login-redirect       ← 버그 수정
  └── refactor/schema-cleanup  ← 리팩토링
```

- **반드시 feature 브랜치에서 작업** → MR → 리뷰 → merge
- MR 생성 시 push option 사용:
  ```bash
  git push origin HEAD \
    -o merge_request.create \
    -o merge_request.target=main \
    -o merge_request.title="feat: 기능 설명" \
    -o merge_request.description="관련 요구사항: FR-XX-XX-XX"
  ```

### Backend 개발 시

1. **요구사항 확인** → `docs/requirements/`에서 FR-ID 확인
2. **interface.md 확인** → API 엔드포인트, 요청/응답 JSON 확인
3. **스키마 확인** → `backend/src/schemas/api/`에 이미 Pydantic 스키마 정의됨
4. **코드 작성** → router → service → (필요 시) agent/prompt
5. **테스트** → Swagger UI (`http://서버IP:8081/docs`)에서 직접 테스트

### Frontend 개발 시

1. **interface.md 확인** → 호출할 API 엔드포인트, JSON 구조 확인
2. **Backend Swagger 확인** → `http://서버IP:8081/docs`에서 실제 API 동작 확인
3. **dev API 활용** → `POST /api/dev/chat`으로 LLM 연동 테스트 가능
4. **컴포넌트 개발** → `src/components/`에 도메인별 폴더 생성

### 주요 문서 위치

| 문서 | 위치 | 용도 |
|------|------|------|
| 요구사항 정의 | `docs/requirements/` | 무엇을 만들어야 하는지 |
| API 인터페이스 | `docs/interface.md` | Backend ↔ Frontend 계약 |
| 작업 계획 | `PLAN.md` | 무엇을 언제 하는지 |
| 진행 상황 | `PROGRESS.md` | 무엇이 완료되었는지 |
| 기술 조사 | `references/` | 기술 결정의 근거 |
| 레거시 참고 | `legacy/aise1.0/` | aise 1.0 구현 참고 |
