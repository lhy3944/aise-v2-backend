# AISE 2.0

AI-powered Software Engineering 플랫폼 — 요구사항 관리, SRS/SAD 생성, TestCase 생성

## 프로젝트 개요

- aise1.0은 one-shot SRS 생성 방식 → 실무에서 쓸모없는 SRS 취급
- aise2.0은 AUTOSAD.ai를 참고하여 **단계별 생성 + AI 어시스트 + 반복 검토** 방식으로 개선
- 인증은 공학연구소 SSO(Keycloak + LDAP)를 통해 처리

## 시스템 범위

### 전체 파이프라인

```
Requirements (FR/QA/Constraints + Glossary)
    ↓  AI 어시스트 (정제/보완/제안) + Review
    ↓
  SRS 생성
    ↓
  Design 자동 생성 (Requirements 기반)
    - System Models (Use Case Diagram/Specifications, Interaction Diagrams, Conceptual Design)
    - Logical / Dynamic / Physical Models
    ↓
  SAD 생성
    ↓
  TestCase 생성 (Requirements 기반, 독립모드 지원)
```

### 프로젝트 모듈 선택

- **All** — Requirements + Design + Test Case 전부
- **Requirements Only** — 요구사항 관리 + SRS 생성만
- **Requirements + Design** — SRS/SAD 흐름
- **Requirements + Testcase** — SRS + TC 생성
- **Testcase Only** — TC 독립모드 (외부 문서 Import → 자동 분류 → TC 생성)

## 요구사항 문서

`docs/` 디렉토리에 문서가 정의되어 있음:

- `requirements/[Requirements] Platform.md` (FR-PF) — 인증, 프로젝트 관리, 멤버, 설정, Import/Export 등
- `requirements/[Requirements] SRS_system.md` (FR-RQ) — 요구사항 입력/Assist, Review, UCD, UCS, 버전관리, 추적성
- `requirements/[Requirements] TC_system.md` (FR-TC) — TC 생성(공통/독립모드/연동모드), Review, Export, 버전관리, 추적성
- `interface.md` — Backend ↔ Frontend API 인터페이스 정의 (전체 엔드포인트 + JSON 구조)

## 기술 스택

| 영역         | 기술                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------ |
| Backend      | FastAPI, Python 3.14, UV, Loguru, SQLAlchemy, asyncpg                                            |
| Frontend     | Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, Shadcn/ui, Zustand, Vercel AI SDK            |
| Database     | PostgreSQL 16 (Docker)                                                                           |
| LLM          | Azure OpenAI (GPT-5.2, Responses API)                                                            |
| AI Framework | 현재: 직접 API 호출 (Review, Assist 등) / 추후: Deep Agents (LangGraph 기반, SRS·TC·Design 생성) |
| 인증         | Keycloak SSO + LDAP                                                                              |
| 코드 검색    | ast-grep (`sg`) — AST 기반 구조 검색. 코드 패턴 검색 시 Grep 대신 사용                           |

## 데이터베이스

- **개발 DB**: `postgresql://aise:aise1234@localhost:5432/aise`
- **테스트 DB**: `postgresql://aise:aise1234@localhost:5432/aise_test`
- **주의**: 테스트는 반드시 `aise_test` DB를 사용해야 한다. `tests/conftest.py`의 `TEST_DATABASE_URL` 확인.
  - 테스트 실행 시 모든 테이블 데이터가 DELETE되므로, 개발 DB를 사용하면 데이터가 사라진다.
- **마이그레이션**: Alembic 사용. 새 마이그레이션 생성 후 **양쪽 DB 모두** 적용할 것:
  ```bash
  cd backend
  uv run alembic upgrade head                                                    # 개발 DB
  DATABASE_URL="postgresql+asyncpg://aise:aise1234@localhost:5432/aise_test" uv run alembic upgrade head  # 테스트 DB
  ```

## 디렉토리 구조

```
aise2.0/
├── CLAUDE.md
├── PLAN.md              # 작업 계획 (할 일 목록)
├── PROGRESS.md          # 진행 상황 추적 (작업 로그)
├── docs/                # 문서
│   └── requirements/    # 시스템 요구사항 정의서 (FR-PF, FR-RQ, FR-TC)
├── references/          # 조사/분석 결과 저장 (YYYY-MM-DD_주제.md)
├── docker-compose.yml   # PostgreSQL (pgvector) + MinIO (개발용)
├── start-dev.sh         # 개발 서버 시작 (DB + Backend + Frontend)
├── backend/             # FastAPI 백엔드
│   ├── pyproject.toml
│   ├── uv.lock
│   └── src/
│       ├── main.py
│       ├── core/        # 공통 설정 (CORS, 예외처리, 로깅)
│       ├── middleware/   # 미들웨어
│       ├── routers/     # API 라우터 (dev/ 포함)
│       ├── schemas/     # Pydantic 스키마 (api/, llm/)
│       ├── models/      # DB 모델 (SQLAlchemy)
│       ├── services/        # 비즈니스 로직 + 단순 API 호출
│       ├── integrations/   # 외부 시스템 연동 (Jira, Polarion, Confluence)
│       ├── agents/          # Deep Agents 워크플로우 (SRS/TC/Design)
│       ├── prompts/         # LLM 프롬프트 템플릿
│       └── utils/           # 유틸리티 (파서, 변환기)
├── frontend/            # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/         # App Router ((main)랜딩, (agent)채팅/워크플로우)
│   │   ├── components/  # UI 컴포넌트 (chat/, layout/, overlay/, ui/, shared/)
│   │   ├── hooks/       # 커스텀 훅 (useReview, useResize, useMediaQuery 등)
│   │   ├── stores/      # Zustand 상태관리 (chat, panel, overlay)
│   │   └── config/      # 네비게이션 등 설정
└── legacy/              # 레거시 코드 및 참조 구현체
    └── aise1.0/         # aise 1.0 구현체
```

## 핵심 설계 원칙

1. **자연어 입력 + AI 구조화** — 복잡한 폼 대신 자유로운 입력, AI가 정제
2. **짧은 피드백 루프** — AI 제안을 수락/거절하는 인터랙션이 빠르게 동작
3. **입력 품질 = 출력 품질** — 생성 전 Review를 통해 부실한 입력 방지
4. **확장 가능한 구조** — 모듈 선택 방식으로 SRS/Design/TC 독립 운영 가능

## Frontend 가이드라인

> **상세 규칙은 `frontend/CLAUDE.md` 참조** — 컴포넌트 패턴, 스타일링, 스토어, 오버레이, 폼 검증, Modal+Form, 애니메이션, 금지사항 등 모든 프론트엔드 구현 규칙이 정의되어 있다.

- **AI 인터랙션 UI** — `components/ui/ai-elements/` 컴포넌트 우선 사용. 새 AI 컴포넌트 필요 시 [ai-elements 공식 문서](https://ai-elements.dev) 조사 후 설치 또는 패턴에 맞춰 구현
- **기본 UI** — shadcn/ui. 새 컴포넌트는 `npx shadcn@latest add`
- **폼 검증** — react-hook-form + zod (HTML5 네이티브 검증 금지)
- **Modal + Form** — 액션 버튼은 Modal `footer` prop으로 분리, `form` 속성으로 연결

## Git 워크플로우

- **브랜치 전략**: GitHub Flow (main ← feature)
- **코드 관리**: GitLab, MR(Merge Request) 기반 — 사람이 리뷰 후 merge
- **feature 브랜치 네이밍**: `feat/기능명`, `fix/버그명` 등
- **MR 생성**: push 시 GitLab push option으로 자동 생성
  ```bash
  git push origin HEAD \
    -o merge_request.create \
    -o merge_request.target=main \
    -o merge_request.title="feat: 기능 설명" \
    -o merge_request.description="관련 요구사항: FR-XX-XX-XX"
  ```
- **주의**: main에 직접 push 금지. 반드시 feature 브랜치 → MR → 리뷰 → merge

## 개발 플로우 (개발 → 테스트 → 리뷰)

```
코드 작성 (subagent 병렬)
  → [자동] PostToolUse Hook: pytest 실행
    → 실패 시 agent가 수정
    → 통과 시 계속
  → [수동] 커밋 전: reviewer agent로 리뷰 (사용자 요청 시)
  → 커밋 + MR 생성
```

### Hook 설정 (`.claude/settings.json`)

- **PostToolUse**: 코드 수정(Edit/Write) 시 `uv run pytest tests/` 자동 실행

### 사용 가능한 Agent/Skill

- `test-runner` agent — 테스트 실행 + 실패 시 원인 분석/수정
- `reviewer` agent — 아키텍처/코드 품질 리뷰 (코드 수정 안 함)
- `/test-backend [module]` — 수동 테스트 실행 스킬

## 에이전트 협업 규칙

### 필수: 작업 시작 시

1. **반드시 PLAN.md와 PROGRESS.md를 먼저 읽을 것**
2. PLAN.md에서 다음 할 일을 확인하고, PROGRESS.md에서 현재 상태를 확인

### 필수: 작업 완료 시

1. PLAN.md에서 완료된 항목을 `[x]`로 체크
2. PROGRESS.md의 상태 테이블 업데이트 + 작업 로그에 날짜와 함께 기록

### 파일 역할

- **PLAN.md** — 전체 작업 계획 및 할 일 목록 (Phase별 체크리스트)
- **PROGRESS.md** — 진행 상황 추적 (상태 테이블 + 날짜별 작업 로그)
