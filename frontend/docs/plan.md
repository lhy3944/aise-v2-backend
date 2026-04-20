# Frontend Plan

> 여러 개발자(2-3명)가 일관된 결과물을 만들기 위한 공통 인프라 정비 계획.
> 기능 개발은 이 공통 작업이 완료된 후 착수한다.

---

## Phase 1: 코드 품질 인프라

> 목표: 코드 스타일/포맷이 자동으로 통일되도록 도구 설정

- [x] **Prettier 설정** — `.prettierrc`, `.prettierignore` 구성
  - singleQuote, trailingComma, tabWidth 등 팀 표준 결정
  - `package.json`에 format 스크립트 추가
- [x] **ESLint 규칙 강화** — 현재 Next.js 기본 → AISE+ 맞춤 규칙 추가
  - import 순서 정렬 (`eslint-plugin-import`)
  - 미사용 변수/import 경고 → 에러로 승격
  - React Hooks 규칙 강화
- [x] **에디터 설정 통일** — `.vscode/settings.json` 공유
  - 저장 시 자동 포맷 (formatOnSave)
  - ESLint 자동 수정 (codeActionsOnSave)
- [x] **기존 코드 일괄 포맷팅** — Prettier 적용 후 전체 포맷 + 단일 커밋

---

## Phase 2: 디자인 시스템 정비

> 목표: AISE+ 디자인 토큰 기반으로 일관된 UI 구현

- [x] **디자인 토큰 정리** — `globals.css` 토큰 체계 검증 및 누락 토큰 보완
  - 현재 토큰이 모든 UI 케이스를 커버하는지 점검
  - 하드코딩된 색상/간격이 있으면 토큰으로 전환
- [x] **shadcn/ui 테마 적용 검증** — 기존 shadcn 컴포넌트에 AISE+ 토큰이 올바르게 적용되는지 점검
  - Button, Badge, Input, Select 등 주요 컴포넌트 확인
  - 필요시 shadcn 컴포넌트 CSS 변수 오버라이드
- [x] **공통 스타일 유틸 정리** — 자주 쓰이는 Tailwind 패턴을 문서화
  - 카드 스타일, 구분선, 섹션 간격 등 반복 패턴

---

## Phase 3: 공통 컴포넌트 표준화

> 목표: 도메인 개발 시 재사용할 공통 컴포넌트 세트 완성

### 3-1. Toast/알림 시스템
- [x] Toast 컴포넌트 도입 (sonner 또는 react-hot-toast)
- [x] 성공/에러/경고/정보 4가지 타입 표준화
- [x] API 응답 연동 패턴 문서화 (성공 시 toast, 에러 시 toast)

### 3-2. 폼 컴포넌트 표준화
- [x] Input, Textarea, Select, Checkbox 스타일 통일 점검
- [x] 폼 유효성 검증 패턴 결정 (react-hook-form + zod)
- [x] 공통 FormField 래퍼 (라벨 + 입력 + 에러 메시지) 필요 여부 검토
- [x] 폼 사용 예시 문서화

### 3-3. 테이블/리스트 패턴
- [x] 데이터 테이블 기본 구조 결정 (shadcn Table 기반)
- [x] 정렬, 페이지네이션, 빈 상태 표현 패턴 통일
- [x] 리스트/카드 토글 뷰 패턴 표준화 (ProjectCard/ProjectListItem 기반)

---

## Phase 4: API 연동 표준화

> 목표: API 호출 방식, 에러 처리, 로딩 상태를 통일

- [x] **API 클라이언트 정비** — `lib/api.ts` 기반 표준 패턴 확립
  - 공통 에러 처리 (401 → 로그인 리다이렉트, 500 → 에러 토스트)
  - 요청/응답 타입 정의 패턴
  - 인증 토큰 자동 첨부
- [x] **데이터 페칭 패턴 결정**
  - SWR / React Query / 직접 fetch 중 표준 선택
  - 로딩/에러/빈상태 처리 표준 패턴
  - 낙관적 업데이트 패턴 (필요 시)
- [x] **API 연동 예시 문서화** — 표준 패턴을 보여주는 레퍼런스 코드

---

## Phase 5: 가이드 문서 보강

> 목표: 신규 개발자 온보딩 및 기존 개발자 참조용 문서 완성

- [x] `frontend/docs/guides/code-conventions.md` 업데이트
  - Phase 1 결과 반영 (Prettier, ESLint 규칙)
- [x] `frontend/docs/guides/component-patterns.md` 업데이트
  - Phase 3 결과 반영 (Toast, 폼, 테이블 패턴)
- [x] `frontend/docs/guides/design-tokens.md` 업데이트
  - Phase 2 결과 반영 (토큰 체계 최종본)
- [x] `frontend/docs/guides/api-patterns.md` 신규 작성
  - Phase 4 결과 반영 (API 연동 표준)

---

## 우선순위 요약

| Phase | 영역 | 긴급도 | 이유 |
|-------|------|--------|------|
| 1 | 코드 품질 인프라 | **높음** | 모든 작업의 기반, PR diff 노이즈 제거 |
| 2 | 디자인 시스템 | **높음** | UI 일관성의 근본, 하드코딩 방지 |
| 3 | 공통 컴포넌트 | **높음** | 기능 개발 시 즉시 필요 |
| 4 | API 연동 | **높음** | 백엔드 연동 시 즉시 필요 |
| 5 | 가이드 문서 | **중간** | 각 Phase 완료 시 점진적 업데이트 |
