# 프로젝트 규칙

## 설계 문서 우선순위
1. `DESIGN.md` — 백엔드 아키텍처 (최우선)
2. `FRONTEND_DESIGN.md` — 프론트엔드 설계
3. `MIGRATION_PLAN.md` — 이관 전략
4. `ANALYSIS.md` — 기존 자산 분석
5. `PROGRESS.md` — 진행 상황 (세션 간 인계)

## 재활용 원칙
- A등급(ANALYSIS.md에 명시) 코드는 불필요한 재작성 금지
- 기존 프로토타입의 `useChatStream`, `panel-store`, `lib/api` 등은 최대한 보존
- 기존 SSE 버퍼링 로직은 성능 튜닝된 자산 — 교체 시 사전 협의

## 추가 규칙
- Phase 순서 준수: DESIGN.md §12, FRONTEND_DESIGN.md §25 참조
- 에이전트 추가 시: `agents/base.py`의 BaseAgent 상속 + `@register_agent` 데코레이터
- 프롬프트는 `prompts/*.md`에 분리. 하드코딩 금지
- DB 스키마 변경은 반드시 Alembic 마이그레이션
- SSE 이벤트 추가 시 프론트 `types/agent-events.ts` 동시 업데이트
- 커밋 메시지는 Conventional Commits 형식 (feat/fix/refactor/docs/test)

## 자주 쓰는 명령어

### 백엔드
- 개발 서버: `cd backend && uvicorn src.main:app --reload`
- 테스트: `cd backend && pytest tests/ -v`
- 마이그레이션 생성: `cd backend && alembic revision --autogenerate -m "message"`
- 마이그레이션 적용: `cd backend && alembic upgrade head`

### 프론트엔드
- 개발 서버: `cd frontend && pnpm dev`
- 린트: `cd frontend && pnpm lint`
- 포맷: `cd frontend && pnpm format`
- 빌드: `cd frontend && pnpm build`

### 공통
- 전체 기동: `./start-dev.sh` (backend :9999, frontend :3009)
- 로컬 대체: `./start-local.sh` (backend :8082, frontend :3009)
- Docker: `docker-compose up`
- Preview 배포: `./deploy/preview.sh`

## 저장소 구조 (Phase 0 이관 완료)

```
aise-v2-backend/
├── DESIGN.md · FRONTEND_DESIGN.md · ANALYSIS.md · MIGRATION_PLAN.md · CLAUDE.md · PROGRESS.md
├── backend/          # FastAPI (프로토타입 이관, 96 passed 기준선)
├── frontend/         # Next.js 16 (프로토타입 이관, build 성공 기준선)
├── docker-compose.yml · docker-compose.preview.yml
├── .env.prod.example · .env.preview.example
├── deploy/ · deploy.sh · start-dev.sh · start-local.sh
├── .github/workflows/   # Preview/Prod VPS 배포 (secrets 설정 필요)
├── references/          # 과거 리서치 노트
├── docs/legacy/         # 프로토타입 원본 문서 (읽기 전용)
└── .prototype-ref/      # 프로토타입 clone (gitignore, 로컬 참고용)
```

## 기준선 (Phase 0)

- **Backend**: 96 passed in 23.63s (postgresql+asyncpg, Alembic 16 migrations)
- **Frontend**: `pnpm build` 성공 (Next.js 16.1.6 Turbopack)
- **Known gaps** (Phase 1에서 처리):
  - Frontend lint: 22 problems (8 errors, 14 warnings) — 프로토타입 동일 상태
  - Backend P0: `rag_svc` project_id 필터 누락, `agent_svc` 프롬프트 의존
  - LangGraph/LiteLLM/HITL 미도입 — MIGRATION_PLAN.md 참조
