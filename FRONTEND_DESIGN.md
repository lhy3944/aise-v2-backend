# FRONTEND_DESIGN.md — 프론트엔드 설계 문서

> **DESIGN.md 확장판** (섹션 16~24)
> Next.js 16 + shadcn + ai-elements + Tailwind 기반
> 기존 프로토타입(`aise-v2/frontend`)의 우수한 자산을 보존하며 신규 기능 통합

---

## 16. 프론트엔드 기술 스택 (확정)

### 16.1 기존 프로토타입에서 확정 사용 (변경 없음)

| 카테고리 | 라이브러리 | 비고 |
|---|---|---|
| **프레임워크** | Next.js 16.1 (App Router) + React 19 | React Compiler 활성화 |
| **UI 프리미티브** | shadcn/ui + radix-ui | Dialog, Dropdown, Tabs 등 |
| **AI UI 전용** | ai-elements (AI SDK) | 메시지 렌더링 패턴 |
| **스타일링** | Tailwind CSS 4 | 커스텀 컬러 체계 유지 |
| **상태 관리** | **Zustand 5** | `persist` 미들웨어 활용 |
| **데이터 페칭** | **SWR 2** + 커스텀 `lib/api.ts` | fetch 래퍼 구조 유지 |
| **폼** | react-hook-form + zod + @hookform/resolvers | |
| **드래그앤드롭** | @dnd-kit | 섹션 순서 변경 |
| **마크다운** | streamdown (streaming-aware) + react-markdown + remark-gfm | 스트리밍 렌더링 최적 |
| **테마** | next-themes | 다크/라이트 |
| **알림** | sonner | 토스트 |
| **아이콘** | lucide-react | |
| **애니메이션** | motion (framer-motion) | |
| **단축키** | cmdk | 커맨드 팔레트 |

### 16.2 신규 도입 또는 검토 대상

| 라이브러리 | 용도 | 결정 |
|---|---|---|
| **@microsoft/fetch-event-source** | SSE 개선 (POST 지원, 재연결) | ⭐ **도입 권장** — 현재 fetch 직접 구현 대비 에러 복구·헤더 지원 우수 |
| **TanStack Query v5** | SWR 대체 또는 병용 | 현 SWR 유지. 서버 mutation·optimistic update 필요 시 TanStack Query 병용 고려 |
| **react-diff-viewer-continued** | 문서 버전 diff 뷰 | ⭐ **도입** — §20.5 버전 관리용 |
| **monaco-editor** 또는 **@codemirror/view** | 인라인 산출물 편집 | 필요 시 검토 (초기는 Textarea + shadcn) |
| **reactflow** 또는 **@xyflow/react** | 영향도 분석 그래프 | §20.6 구현 시 도입 |
| **DayPicker 또는 date-fns** | 날짜 처리 | 필요 시 |

### 16.3 SSE 개선 결정

**현재**: `fetch` 직접 → ReadableStream 수동 파싱
**개선안**: `@microsoft/fetch-event-source` 도입

**이유**:
- POST 메서드 + 커스텀 헤더 지원 (EventSource 한계 극복)
- 자동 재연결 + 에러 복구
- `onopen` / `onmessage` / `onerror` / `onclose` 명확한 훅
- 기존 `useChatStream.ts`의 토큰 버퍼링 로직은 **그대로 유지**하고, SSE 파서만 교체

**마이그레이션 리스크 낮음** — `streamAgentChat` 내부 구현만 교체.

---

## 17. 정보 구조 (IA)

### 17.1 기존 IA (유지)

```
/ (ROOT)
├── /login, /signup                        # (auth) 그룹
├── /dashboard                             # 홈 (주요 지표)
├── /projects
│   ├── /                                  # 프로젝트 목록
│   └── /[id]                              # 프로젝트 상세
│       └── /requirements                  # 요구사항 상세 (서브페이지)
├── /agent
│   └── /[sessionId]                       # 대화 세션
└── /workflow                              # (예약 — 워크플로 관리)
```

### 17.2 신규 추가 라우트

```
/projects/[id]
├── /                                      # 기본 정보 탭
├── /knowledge                             # 지식 저장소 탭 (분리 권장)
├── /glossary                              # 용어 사전 탭 (분리 권장)
├── /sections                              # 섹션 탭 (분리 권장)
├── /artifacts                             # [신규] 산출물 허브
│   ├── /srs                               # SRS 버전 목록 + 에디터
│   ├── /design                            # 설계 문서
│   └── /testcases                         # TC 목록
└── /impact                                # [신규] 영향도 분석 대시보드
```

**결정 사유**: 현재 탭 전환이 쿼리스트링 또는 상태 기반이면 URL 공유·북마크가 어려움. 라우트 분리로 딥링크 가능.

### 17.3 내비게이션 구조

**유지**: 상단 탑바(Agent / Projects) + 프로젝트 내 탭 구조
**강화**: 프로젝트 내부에 세로 사이드바 서브네비 추가 고려 (탭 수가 늘어나면)

```
┌──────────────────────────────────────────────────┐
│  [AISE+] [Agent] [Projects]     🔍 🔔 ⋮ 🌙 👤   │  ← Top Bar (유지)
├──────────────────────────────────────────────────┤
│  ← 오브제로봇                         [에이전트 대화]│
│  [기본정보] [지식저장소] [용어사전] [섹션]           │
│  [산출물] [영향도]  ← 신규                         │
├──────────────────────────────────────────────────┤
│  (탭 콘텐츠)                                       │
└──────────────────────────────────────────────────┘
```

---

## 18. 기존 자산 재활용 맵

### 18.1 그대로 재사용 (변경 없음)

| 영역 | 컴포넌트/로직 | 재사용 이유 |
|---|---|---|
| **라우팅 구조** | `app/(main)/*` 전체 | IA 변경 최소 |
| **API 레이어** | `lib/api.ts` (`ApiError`, `api.get/post/...`) | 에러 핸들링 완성도 높음 |
| **인증 가드** | `app/(auth)`, 401 리다이렉트 | 동작 검증됨 |
| **Zustand stores** | `chat-store`, `panel-store`, `project-store`, `toast-store`, `ui-preference-store` | 이미 잘 설계됨 |
| **채팅 스트리밍 훅** | `useChatStream.ts` 전체 | 토큰 버퍼링·모바일 대응 등 고도화 완료 |
| **레이아웃 모드** | `LayoutMode` enum (WIDE/SPLIT/CLOSED) | **이미 제안한 3-모드 토글이 구현됨** |
| **프로젝트 리스트** | `projects/page.tsx`, 카드 컴포넌트 | 완성도 높음 |
| **프로젝트 생성 모달** | 모듈 선택(All/Req+Design/…) | 유지 |
| **지식 저장소 UI** | 업로드 + 텍스트 입력 + 청크 상태 | 유지 |
| **용어사전 테이블** | 검색 + AI 생성 + 수동 추가 | **제품 차별화 핵심** — 유지 |
| **섹션 관리** | 드래그 정렬 + 활성화 토글 | 유지 |
| **메시지 렌더링** | `MessageRenderer.tsx` (streamdown) | 최신 스트리밍 마크다운 |
| **커스텀 훅들** | `useResize`, `useChatScroll`, `useOverlay` 등 | 모두 유지 |

### 18.2 개선 필요 (일부 수정)

| 영역 | 현재 상태 | 개선 방향 |
|---|---|---|
| **HITL UI** | `ClarifyQuestion.tsx` (프롬프트 기반 액션 카드) | §19.2 — 백엔드 `interrupt()` 기반 구조화된 컴포넌트로 리팩토링 |
| **toolCall 표시** | `ChatMessage.toolCalls` 필드는 있으나 렌더링 최소 | §19.1 — **Collapsible Agent Invocation Card** 로 확장 |
| **산출물 탭** | `RecordsArtifact`, `SrsArtifact`(stub), `DesignArtifact`(stub), `TestCaseArtifact`(stub) | SRS/Design/TC 실구현 + 인라인 편집 |
| **세션 히스토리** | `SessionList.tsx` — 제목만 표시 | §19.8 — 에이전트 아이콘·턴수·생성 산출물 배지 추가 |
| **SSE 클라이언트** | fetch 직접 구현 | `@microsoft/fetch-event-source` 로 교체 |
| **`agent-service.ts`** | tool event 처리 | HITL interrupt / plan progress 이벤트 추가 파싱 |

### 18.3 신규 추가 필요 (프로토타입에 없음)

| # | 항목 | 위치 |
|---|---|---|
| N1 | **Agent Invocation Card** (인라인 collapse) | `components/chat/AgentInvocationCard.tsx` |
| N2 | **HITL 구조화 컴포넌트** (Clarify / Confirm / Decision) | `components/chat/hitl/*` |
| N3 | **Plan Progress Tracker** (인라인 진행 상태) | `components/chat/PlanProgress.tsx` |
| N4 | **SRS Editor** (섹션별 편집 + 재생성) | `components/artifacts/srs/*` |
| N5 | **TC Editor** (요구사항 연결) | `components/artifacts/testcase/*` |
| N6 | **Design Doc Editor** (UCD/UCS/SAD) | `components/artifacts/design/*` |
| N7 | **Version History** (diff 뷰어) | `components/artifacts/shared/VersionHistory.tsx` |
| N8 | **Impact Analysis** (영향도 그래프) | `components/impact/*` |
| N9 | **Artifact Hub** | `app/(main)/projects/[id]/artifacts/*` |
| N10 | **i18n 인프라** | `next-intl` 또는 `react-i18next` 추가 (Phase 후기) |

---

## 19. 핵심 유즈케이스별 화면 흐름 (10개)

각 유즈케이스는 **화면 → 사용자 액션 → API 호출 → 상태 변화 → 결과 UI** 순서로 기술.

### UC-01. 프로젝트 생성 & 초기 셋업

```
[프로젝트 목록] → [+ 프로젝트 생성] 클릭
   └ 모달: 이름·설명·도메인·제품유형·모듈(All/Req/Design/TC) 입력
   └ POST /projects → { project_id }
   └ 자동 이동: /projects/{id}  (기본 정보 탭)
[지식저장소 탭] → 파일 업로드 (드래그·드롭)
   └ POST /projects/{id}/documents (multipart)
   └ 백엔드 임베딩 시작 → SSE로 청크 진행률
   └ 청크 카운트 실시간 업데이트
[용어사전 탭] → [AI 생성] 클릭
   └ POST /projects/{id}/glossary/generate
   └ 에이전트가 지식 문서에서 용어 추출 → 테이블 갱신
[섹션 탭] → 기본 제공 섹션 확인 + 커스텀 섹션 추가
   └ POST /projects/{id}/sections
[에이전트 대화 버튼] → /agent (현재 프로젝트 컨텍스트 유지)
```

**상태 변화**: `useProjectStore.currentProject` 설정 → 전역 활용
**신규 고려**: 초기 셋업 가이드 위젯 (onboarding checklist)

### UC-02. 지식 기반 질의응답 (RAG)

```
[Agent 화면] → 프로젝트 선택 (사이드바 Combobox)
   └ useProjectStore.setCurrentProject
[중앙 입력창] → "오브제로봇 지식문서를 간단히 요약해줘" 입력
   └ POST /chat (SSE 시작)
   └ 서버: supervisor → knowledge_qa 에이전트 라우팅
[대화 영역] → 실시간 토큰 스트리밍
   └ useChatStream.onToken → appendToLastAssistant
[인용 표시] → SourceReference 컴포넌트
   └ 클릭 시 SourceViewerPanel 오픈 (우측 패널)
   └ 문서 청크 하이라이트 + 메타데이터
```

**신규 고려**: 답변 말미에 "더 깊이 분석" / "SRS로 발전시키기" 등 다음 액션 제안 칩

### UC-03. 요구사항 초안 생성

```
[Agent] → "이 프로젝트의 요구사항을 뽑아줘"
   └ 서버: supervisor → plan 수립
   └ Plan: [knowledge_qa → requirement]
[대화 영역] → Plan Progress Tracker 표시 (§20.3)
   └ Step 1: knowledge_qa  ⚙️ 실행 중
   └ Step 2: requirement   ⏸ 대기
[완료 후] → ExtractedRequirements 카드 스트림 출력
   └ Records 탭 자동 활성화 (setActiveTab + SPLIT 레이아웃)
   └ 카드별 [승인] [제외] 액션
```

**기존 자산**: `ExtractedRequirements.tsx`, `RecordsArtifact.tsx` 재활용
**개선점**: Plan 진행 상황 가시화 추가

### UC-04. SRS 전체 생성

```
[Agent] → "요구사항으로 SRS 문서 만들어줘"
   └ 서버: supervisor → 섹션 템플릿 조회 → srs_generator
   └ Plan: [requirement → srs_gen → critic]
[중앙] → Plan Progress + 토큰 스트리밍
[우측 산출물 패널] → SRS 탭 자동 전환
   └ 섹션별로 실시간 빌드업 (WebSocket/SSE)
[완료] → critic 에이전트 검토 결과 카드 출력
   └ "3개 요구사항 중복 감지" 등
   └ [자동 수정] [무시] [검토 요청]
```

**신규**: SrsArtifact 실구현 (§20.4)

### UC-05. SRS 섹션 재생성

```
[산출물 패널 > SRS] → 특정 섹션 (예: "Quality Attributes") 호버
   └ 섹션 우측 상단에 [⋮] 메뉴
   └ "AI로 재생성" 선택
[모달 또는 인라인] → 재생성 프롬프트 (선택적)
   └ "보안 요구사항을 더 강화해서" 등
   └ POST /artifacts/{id}/sections/{section_id}/regenerate
[산출물 패널] → 해당 섹션만 교체 (diff preview 옵션)
   └ [적용] [취소]
```

**핵심**: 대화 없이 산출물 자체에서 조작 가능 — 당신 지적 반영

### UC-06. 테스트케이스 일괄 생성

```
[Agent] → "승인된 요구사항으로 테스트케이스 만들어줘"
   └ 서버: testcase_generator 에이전트
   └ 요구사항 ↔ TC 자동 연결 (requirement_ids)
[산출물 패널] → Test Cases 탭
   └ 요구사항별 그룹핑 (FR-001 → TC-001, TC-002)
   └ TC 카드: 제목·선행조건·단계·기대결과
   └ 커버리지 뱃지: "FR-001: 3 TCs" / "FR-003: 0 TCs ⚠️"
```

**신규**: TestCaseArtifact 실구현

### UC-07. 모호한 요청 → HITL 응답 (개선 포인트)

```
[Agent] → "인증 기능 좀 추가해줘" (모호)
   └ 서버: supervisor → clarify 액션
   └ SSE: { type: "interrupt", data: { question, options, interrupt_id } }
[대화 영역] → ClarifyCard 인라인 렌더
   ┌─────────────────────────────────────┐
   │ 🤔 에이전트가 질문합니다              │
   │ 인증 방식을 명확히 해주세요             │
   │  ⚪ JWT 기반                         │
   │  ⚪ OAuth2 (Google/GitHub)          │
   │  ⚪ 세션 기반                         │
   │  ⚪ 직접 입력: [________]            │
   │           [응답 전송]                │
   └─────────────────────────────────────┘
[사용자 선택] → POST /chat/{session_id}/resume
   └ body: { interrupt_id, response: { choice: "OAuth2" } }
   └ 백엔드 그래프 재개 → 토큰 스트리밍 이어짐
[완료] → 동일 대화 내 다음 turn으로 자연스럽게 이어짐
```

**핵심 개선**: 프롬프트 기반 추론 → **백엔드 구조화 응답 + 프론트 전용 컴포넌트** (§20.2)

### UC-08. 요구사항 수정 → 영향도 → 연쇄 업데이트 (핵심 가치)

```
[산출물 > Records] → FR-003 편집 (인라인 또는 모달)
   └ PATCH /records/{id}
   └ 서버: critic 에이전트 자동 트리거 → 영향도 계산
[알림 토스트] → "FR-003 변경으로 SRS 2개 섹션, TC 4개 영향"
   └ [영향도 보기] 클릭
[영향도 분석 페이지] (§20.6) → 그래프 + 리스트
   ┌──────────────────────────────────┐
   │ FR-003 (변경)                     │
   │   └→ SRS.Functional Requirements │
   │   └→ TC-012, TC-013, TC-017      │
   │   └→ Design.UCD Section 2.1      │
   │                                   │
   │ [모두 자동 업데이트] [개별 선택]    │
   └──────────────────────────────────┘
[자동 업데이트 승인] → 각 항목 업데이트 → 버전 증분
   └ SRS v1.2 → v1.3, TCs 재생성
```

**신규**: §20.6 영향도 그래프 UI + 백엔드 `critic` 에이전트에 `calculate_impact` 도구

### UC-09. 산출물 수동 편집 + 에이전트 재검토

```
[산출물 > SRS] → 특정 섹션 편집 (인라인 Textarea 또는 에디터)
   └ PATCH /artifacts/{id} (디바운스 저장)
   └ 상단에 "마지막 저장: 방금 전 (수동 편집)"
[편집 종료 후] → [AI 재검토] 버튼
   └ POST /artifacts/{id}/review → critic 에이전트
   └ 대화에 새 turn 추가: "수동 편집된 SRS를 검토하겠습니다"
[결과] → AgentInvocationCard 렌더 + 개선 제안 리스트
```

### UC-10. 용어사전 AI 생성 + 수동 큐레이션

```
[용어사전] → [AI 생성] 버튼
   └ POST /projects/{id}/glossary/generate
   └ 에이전트: 지식문서 + 대화 이력 스캔 → 용어 후보
[테이블] → 상태별 행: "자동 추출" 뱃지
   └ 체크박스 선택 → [승인] [삭제]
[수동 추가] → [+ 추가] → 용어·정의·제품군 입력
```

**기존 자산**: 현 `용어사전` UI 유지. AI 생성 피드백 루프만 강화

---

## 20. 신규 화면 상세 설계

### 20.1 Agent Invocation Card (인라인 Collapse)

**위치**: `components/chat/AgentInvocationCard.tsx`

**동작**: `ChatMessage.toolCalls` 배열을 렌더. 에이전트 호출이 **대화 흐름의 자연스러운 일부**로 표현.

```
┌─ 💬 User: "요구사항으로 SRS 만들어줘" ──────────┐
└──────────────────────────────────────────────┘
┌─ 🤖 Assistant ────────────────────────────────┐
│                                                │
│  ┌─ 🔧 requirement_agent ⚙️ 실행 중 ─── ▼ ──┐ │
│  │ (접혔을 때는 이 한 줄만 표시)                 │ │
│  └─────────────────────────────────────────┘ │
│                                                │
│  ┌─ 🔧 srs_generator ✅ 완료 (2.3s) ──── ▶ ─┐ │
│  │ ▼ 펼침 시:                                │ │
│  │   Input: { records_count: 12 }           │ │
│  │   Output: SRS v1.0 생성 (5개 섹션)        │ │
│  │   [SRS 문서 보기 →]                       │ │
│  └─────────────────────────────────────────┘ │
│                                                │
│  요구사항 12개를 기반으로 SRS 문서를 생성했습니다.│
│  주요 섹션은 다음과 같습니다: ...                │
└──────────────────────────────────────────────┘
```

**컴포넌트 구조**:

```tsx
interface Props {
  toolCall: ToolCallData;
  onViewArtifact?: (artifactId: string) => void;
}

// 상태별 렌더
state === 'running':  스피너 + 경과 시간 카운터
state === 'completed': 체크 아이콘 + 실행 시간 + 산출물 링크
state === 'error':    에러 아이콘 + 재시도 버튼 (옵션)
```

**기존 코드 활용**:
- `ChatMessage.toolCalls` 필드 (이미 존재)
- `useChatStream`의 `onToolCall` / `onToolResult` 핸들러 (확장)

**백엔드 연동**: LangGraph `astream_events` → `on_tool_start` / `on_tool_end` 이벤트를 SSE로 전달

### 20.2 HITL 전용 컴포넌트 3종

**위치**: `components/chat/hitl/`

#### (a) ClarifyCard — 선택형 명확화

```tsx
interface ClarifyData {
  type: 'clarify';
  interrupt_id: string;
  question: string;
  options?: Array<{ value: string; label: string; description?: string }>;
  allow_custom: boolean;  // 자유 입력 허용 여부
}
```

```
┌─ 🤔 명확화 필요 ──────────────────────────────┐
│ 인증 방식을 명확히 해주세요                       │
│                                                │
│  ⚪ JWT 기반                                   │
│  ⚪ OAuth2 (Google/GitHub)                    │
│  ⚪ 세션 기반                                   │
│  ⚪ 기타 (직접 입력)                            │
│     [_____________________________]            │
│                                                │
│                          [응답]                │
└────────────────────────────────────────────────┘
```

#### (b) ConfirmCard — 승인형 확인

```tsx
interface ConfirmData {
  type: 'confirm';
  interrupt_id: string;
  title: string;
  description: string;
  impact?: Array<{ label: string; detail: string }>;  // "영향받는 TC: 8개"
  severity: 'info' | 'warning' | 'danger';
  actions: { approve: string; reject: string; modify?: string };
}
```

```
┌─ ⚠️ 확인이 필요합니다 ──────────────────────────┐
│ REQ-003~007 (5개)을 삭제하고 교체합니다           │
│                                                │
│ 영향받는 항목:                                   │
│  • TC-012, TC-013, TC-017 (3개)                │
│  • SRS.Functional Requirements 섹션             │
│                                                │
│ [자세히 보기]                                    │
│                                                │
│       [거부]  [수정 후 진행]  [승인]            │
└────────────────────────────────────────────────┘
```

#### (c) DecisionCard — 다중 선택형

```tsx
interface DecisionData {
  type: 'decision';
  interrupt_id: string;
  question: string;
  options: Array<{ id: string; label: string; default?: boolean }>;
  min_selection?: number;
  max_selection?: number;
}
```

사용 예: "어떤 비기능 요구사항을 포함할까요?" (체크박스 복수 선택)

#### 공통 동작

모든 HITL 카드는 `handleResume` 훅을 통해 `POST /chat/{session_id}/resume` 호출. 응답 후 카드가 **읽기 전용 상태로 고정** (되돌릴 수 없음 명시).

```tsx
const { handleResume, isResuming } = useHitlResume(sessionId);

<ClarifyCard
  data={data}
  onSubmit={(response) => handleResume(data.interrupt_id, response)}
  disabled={isResuming || hasResponded}
/>
```

### 20.3 Plan Progress Tracker (인라인)

**위치**: `components/chat/PlanProgress.tsx`

**동작**: Supervisor가 plan을 세운 경우 해당 turn 상단에 인라인으로 진행 상태 표시. Collapse 가능.

```
┌─ 📋 Plan: requirement → srs_gen → critic ─ ▼ ──┐
│  ✅ requirement_agent  │ 2.1s │ 12 records      │
│  ⚙️ srs_generator      │ 진행 중...              │
│  ⏸ critic              │ 대기 중                 │
│                                 [취소]          │
└────────────────────────────────────────────────┘
```

**데이터 모델**: `ChatMessage`에 `plan?: PlanStep[]` 추가

```tsx
interface PlanStep {
  agent: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  result_summary?: string;
}
```

**백엔드 이벤트**: SSE로 `plan_update` 이벤트 전달

```json
{ "event": "plan_update", "data": { "step": 1, "status": "running" } }
```

### 20.4 SRS Editor (산출물 패널 내장)

**위치**: `components/artifacts/srs/SrsEditor.tsx`

**레이아웃** (SPLIT 모드 우측 패널):

```
┌─ SRS v1.2 (draft) ───────────── [⋮] ─┐
│ [📝 편집] [📜 이력] [📥 내보내기] [🤖재생성]│
├─────────────────────────────────────────┤
│                                         │
│ 1. Overview                    [⋮][✏️] │
│    로봇 기반 AI 집사 시스템...            │
│                                         │
│ 2. Functional Requirements     [⋮][✏️] │
│    ┌──────────────────────────────┐   │
│    │ FR-001  승인                 │   │
│    │ 시스템은 사용자가 자연어로...    │   │
│    └──────────────────────────────┘   │
│    ┌──────────────────────────────┐   │
│    │ FR-002  승인                 │   │
│    └──────────────────────────────┘   │
│    [+ 요구사항 추가]                    │
│                                         │
│ 3. Quality Attributes          [⋮][✏️] │
│ ...                                     │
└─────────────────────────────────────────┘
```

**섹션 [⋮] 메뉴**: "AI로 재생성" / "수동 편집" / "비활성화" / "복사"
**섹션 [✏️]**: 직접 편집 모드 토글

**핵심 기능**:
- 섹션별 독립 저장 (디바운스 500ms)
- 요구사항 카드 클릭 → Records 탭에서 하이라이트 (양방향 연결)
- 편집 이력 로컬 저장 (뒤로가기 지원)
- "마지막 저장: 3초 전 (수동)" vs "(에이전트)" 구분 표시

### 20.5 Version History + Diff

**위치**: `components/artifacts/shared/VersionHistory.tsx`

```
┌─ 변경 이력 ──────────────────────── ✕ ──┐
│                                          │
│ ● v1.3 (현재) · 방금 전 · 🤖 critic     │
│   영향도 반영: FR-003 변경으로 자동 업데이트│
│   [diff 보기]                            │
│                                          │
│ ○ v1.2 · 2시간 전 · 👤 사용자 편집       │
│   Quality Attributes 섹션 수동 보강       │
│   [diff 보기] [이 버전으로 되돌리기]       │
│                                          │
│ ○ v1.1 · 어제 · 🤖 srs_generator        │
│ ○ v1.0 · 3일 전 · 🤖 최초 생성           │
│                                          │
└─────────────────────────────────────────┘
```

**diff 뷰어**: `react-diff-viewer-continued` 활용 (split view, syntax highlight)

**API**: `GET /artifacts/{id}/versions`, `GET /artifacts/{id}/versions/{v}/diff?against={v2}`

### 20.6 Impact Analysis (영향도 분석)

**위치**: `app/(main)/projects/[id]/impact/page.tsx` + `components/impact/*`

**두 가지 뷰**:

#### (a) 그래프 뷰 (reactflow)

```
       ┌──────────┐
       │  FR-003  │ (변경됨)
       └────┬─────┘
    ┌───────┼───────┐
    ▼       ▼       ▼
┌──────┐ ┌──────┐ ┌──────┐
│TC-012│ │TC-013│ │SRS §3│
└──────┘ └──────┘ └──────┘
   ⚠️       ⚠️       ✅ 최신
```

노드 클릭 → 우측 상세 패널

#### (b) 리스트 뷰 (테이블)

| 변경된 항목 | 영향받는 항목 | 타입 | 상태 | 액션 |
|---|---|---|---|---|
| FR-003 | TC-012 | TestCase | ⚠️ 업데이트 필요 | [재생성] |
| FR-003 | TC-013 | TestCase | ⚠️ 업데이트 필요 | [재생성] |
| FR-003 | SRS §3.2 | SRS Section | ✅ 최신 | - |

**일괄 액션**: "선택된 항목 모두 재생성" → plan 기반 배치 실행

**백엔드**: `GET /projects/{id}/impact?changed_ids=...` → 그래프 JSON
**계산 로직**: `requirement_ids` 관계 + `created_from_spec` 메타데이터 트래버스

### 20.7 강화된 Session List

**위치**: `components/chat/SessionItem.tsx` (현 98줄 → 확장)

```
┌─ 세션 히스토리 ────── 🔍 [____] ────┐
│                                     │
│ 📝 SRS 초안 작성                    │
│    🤖 srs_generator · 12턴 · 2시간전 │
│    📎 SRS v1.0  🔖 REQ-001~012      │
│    ────────────────────             │
│                                     │
│ 💬 로그인 요구사항 Q&A               │
│    🤖 knowledge_qa · 4턴 · 어제      │
│    ────────────────────             │
│                                     │
│ 🎯 [HITL 대기] OAuth 구현 논의        │
│    ⏸ 2일째 응답 대기                 │
│    [이어가기]                        │
│                                     │
└─────────────────────────────────────┘
```

**추가 메타데이터**: 주 에이전트, 턴 수, 생성된 산출물 링크, HITL 대기 상태

---

## 21. 컴포넌트 라이브러리 맵

### 21.1 shadcn/ui 활용 (기존 + 신규)

| 컴포넌트 | 용도 |
|---|---|
| **Dialog, Drawer** | 프로젝트 생성, 설정 (기존 `vaul` + radix) |
| **DropdownMenu** | 섹션 액션, 산출물 옵션 |
| **Popover** | 빠른 편집, 필터 |
| **Collapsible** | ⭐ AgentInvocationCard 기반 |
| **Tabs** | 프로젝트 탭, 산출물 탭 |
| **RadioGroup** | ClarifyCard 선택지 |
| **Checkbox** | DecisionCard, 일괄 선택 |
| **Progress** | Plan step indicator |
| **Badge** | 상태 뱃지 (FR/QA, approved 등) |
| **ScrollArea** | 대화 / 산출물 스크롤 |
| **Sheet** | 모바일 사이드바 |
| **Skeleton** | 로딩 상태 |
| **AlertDialog** | 파괴적 액션 확인 |
| **Resizable** | SPLIT 모드 드래그 리사이즈 (이미 useResize 있음) |

### 21.2 ai-elements 활용

| 컴포넌트 | 용도 |
|---|---|
| **Message, Reasoning** | 기본 메시지 렌더 |
| **Actions** | 메시지 하단 액션 (복사, 재생성) |
| **CodeBlock** | 코드 블록 |
| **Source** | 인용 출처 (SourceReference와 통합) |

### 21.3 신규 커스텀 컴포넌트 위계

```
components/
├── chat/
│   ├── AgentInvocationCard.tsx          [N1]
│   ├── PlanProgress.tsx                 [N3]
│   ├── hitl/
│   │   ├── ClarifyCard.tsx              [N2a]
│   │   ├── ConfirmCard.tsx              [N2b]
│   │   ├── DecisionCard.tsx             [N2c]
│   │   └── useHitlResume.ts
│   ├── SessionItem.tsx                  (개선)
│   └── [기존 유지: ChatArea, ChatInput, MessageRenderer ...]
├── artifacts/
│   ├── ArtifactPanel.tsx                (기존 유지)
│   ├── RecordsArtifact.tsx              (유지)
│   ├── srs/
│   │   ├── SrsEditor.tsx                [N4]
│   │   ├── SrsSection.tsx
│   │   └── SrsToolbar.tsx
│   ├── testcase/
│   │   ├── TestCaseList.tsx             [N5]
│   │   ├── TestCaseCard.tsx
│   │   └── CoverageBadge.tsx
│   ├── design/
│   │   └── DesignDoc.tsx                [N6]
│   └── shared/
│       ├── VersionHistory.tsx           [N7]
│       ├── DiffViewer.tsx
│       └── RegenerateDialog.tsx
├── impact/
│   ├── ImpactGraph.tsx                  [N8a] (reactflow)
│   └── ImpactList.tsx                   [N8b]
└── [기존 유지: projects/*, layout/*, overlay/* ...]
```

---

## 22. 상태 관리 전략

### 22.1 기존 Zustand stores (유지)

| Store | 역할 | 영속화 |
|---|---|---|
| `chat-store` | 메시지, 스트리밍 상태, 입력값 | ❌ (세션 휘발) |
| `panel-store` | 레이아웃 모드, 패널 너비 | ✅ `aise-panel` |
| `project-store` | 현재 프로젝트 | ❌ |
| `artifact-store` | 산출물 활성 탭 | ❌ |
| `record-store` | 레코드 후보, 갱신 트리거 | ❌ |
| `ui-preference-store` | 테마, 폰트 크기 | ✅ |
| `overlay-store` | 모달/시트 열림 상태 | ❌ |
| `search-store`, `suggestion-store`, `toast-store`, `readiness-store` | 각 용도 | ❌ |

### 22.2 신규 추가 store

| Store | 역할 | 영속화 |
|---|---|---|
| `hitl-store` | interrupt 큐, 응답 이력 | ❌ — 세션 종료 시 초기화 |
| `version-store` | 산출물 버전 캐시 | ❌ (SWR과 함께) |
| `impact-store` | 영향도 계산 결과 캐시 | ❌ |
| `i18n-store` | 언어 설정 | ✅ |

### 22.3 SWR 사용 기준

**SWR로 관리**: 서버 리소스 (projects, documents, glossary, sections, artifacts, versions)
**Zustand로 관리**: 클라이언트 UI 상태 (패널 레이아웃, 입력값, 스트리밍 버퍼)

**혼용 패턴** (기존 채팅에서 이미 사용):
```tsx
// SWR: 초기 세션 메시지 로드
const { data } = useSWR(`/sessions/${id}`, fetcher);

// Zustand: 스트리밍 중 실시간 메시지 갱신
useChatStore.addMessage(id, newMsg);
```

### 22.4 실시간 통신 전략

| 채널 | 용도 | 프로토콜 |
|---|---|---|
| **Chat SSE** | 토큰 스트리밍, tool_call, interrupt, plan_update | `@microsoft/fetch-event-source` (POST) |
| **Document indexing** | 임베딩 진행률 | SSE 또는 SWR polling (3초) |
| **Artifact updates** | 타 사용자/에이전트의 산출물 변경 | SWR refreshInterval (Phase 4+) |
| **Notifications** | 비동기 작업 완료 | SSE 별도 채널 또는 polling |

---

## 23. API ↔ 화면 매핑

백엔드 DESIGN.md §10 API 명세와 화면 연결.

### 23.1 대화

| API | 화면 | 컴포넌트/훅 |
|---|---|---|
| `POST /chat` | Agent 메인 | `useChatStream.sendMessage` |
| `POST /chat/{id}/resume` | HITL 카드 응답 | `useHitlResume` [신규] |
| `GET /chat/{id}` | 세션 로드 | `sessionService.get` |
| `DELETE /chat/{id}` | 세션 삭제 | `SessionItem` 메뉴 |
| `GET /chat?project_id={id}` | 세션 리스트 | `SessionList` |

### 23.2 프로젝트 / 지식

| API | 화면 | 상태 |
|---|---|---|
| `POST /projects` | 생성 모달 | 기존 유지 |
| `GET /projects` | 목록 페이지 | 기존 유지 |
| `POST /projects/{id}/documents` | 지식 저장소 탭 | 기존 유지 |
| `GET /projects/{id}/glossary` | 용어사전 탭 | 기존 유지 |
| `POST /projects/{id}/glossary/generate` | [AI 생성] 버튼 | 기존 유지 |
| `GET /projects/{id}/sections` | 섹션 탭 | 기존 유지 |

### 23.3 산출물 (신규 확장)

| API | 화면 | 신규 |
|---|---|---|
| `GET /projects/{id}/artifacts` | Artifact Hub | ⭐ |
| `GET /artifacts/{id}` | SRS/TC Editor | ⭐ |
| `PATCH /artifacts/{id}` | 수동 편집 저장 | ⭐ |
| `PATCH /artifacts/{id}/sections/{sid}` | 섹션별 저장 | ⭐ |
| `POST /artifacts/{id}/regenerate` | AI 재생성 | ⭐ |
| `POST /artifacts/{id}/sections/{sid}/regenerate` | 섹션별 재생성 | ⭐ |
| `GET /artifacts/{id}/versions` | Version History | ⭐ |
| `GET /artifacts/{id}/versions/{v}/diff` | Diff Viewer | ⭐ |
| `POST /artifacts/{id}/restore/{v}` | 이전 버전 복원 | ⭐ |

### 23.4 영향도 (신규)

| API | 화면 |
|---|---|
| `GET /projects/{id}/impact?changed_ids=...` | Impact Graph |
| `POST /projects/{id}/impact/apply` | 일괄 재생성 실행 |

### 23.5 에이전트 메타

| API | 화면 |
|---|---|
| `GET /agents` | 설정 또는 about 페이지 — 등록된 에이전트 소개 |

---

## 24. 반응형 · 접근성 · i18n

### 24.1 반응형 전략

기존 `panel-store`의 `setViewport` 로직 유지. 세 가지 브레이크포인트:
- **Mobile**: < 768px — 단일 패널, Sheet로 사이드바/산출물
- **Tablet**: 768-1023px — 사이드바 기본 닫힘
- **Desktop**: ≥ 1024px — 3-패널 모드 지원

**모바일에서의 신규 컴포넌트**:
- AgentInvocationCard: 완전 접힘 기본값
- HITL 카드: 전체 너비
- Plan Progress: 2-line 압축 모드
- SRS Editor: Sheet로 오픈

### 24.2 접근성 (a11y)

- shadcn/radix 컴포넌트 기본 a11y 보장
- 추가 고려:
  - HITL 카드: `role="alertdialog"`, `aria-labelledby`
  - AgentInvocationCard: `aria-expanded`, 키보드 펼침
  - 대화 영역: `aria-live="polite"` (스트리밍 공지)
  - 포커스 트랩: Dialog 내부
  - 다크모드 명도 대비 WCAG AA

### 24.3 다크/라이트 테마

기존 `next-themes` 유지. 커스텀 컬러 체계도 유지.
**추가 고려**: 산출물 diff 뷰어, 영향도 그래프의 다크 모드 변형

### 24.4 국제화 (i18n)

**Phase 4 도입** 권장. Phase 1~3은 한국어 우선.

**선택지**:
- `next-intl` — App Router 네이티브 통합 ⭐ 권장
- `react-i18next` — 성숙도 높음

**번역 대상 우선순위**:
1. UI 라벨, 버튼, 폼 라벨
2. 에러 메시지, 토스트
3. AI 생성 프롬프트 (백엔드 측 처리, 프론트는 locale 전달)
4. 도움말, 온보딩

---

## 25. 로드맵 조정 (프론트엔드 관점)

| Phase | 기간 | 프론트엔드 작업 |
|---|---|---|
| **Phase 1** (기반) | 1-2주 | 기존 프로토타입 코드를 새 구조로 이관, API 레이어/stores/layout 안정화, 단일 에이전트 대화 검증 |
| **Phase 2** (멀티 에이전트) | 2-3주 | **AgentInvocationCard**, **PlanProgress** 구현, Records/SRS/TC artifact 확장 |
| **Phase 3** (HITL) | 1-2주 | **HITL 3종 컴포넌트** + resume API 연동, SessionList 강화 |
| **Phase 4** (품질) | 지속 | Version History, Impact Analysis, SSE 개선, i18n 인프라 |
| **Phase 5** (운영) | 이후 | 모바일 최적화 마무리, 접근성 감사, A/B 테스트 UI |

---

## 26. 첫 실행 체크리스트 (Claude Code 착수 시)

### 26.1 분석 단계
- [ ] 기존 저장소 clone 및 `CLAUDE.md`, `PLAN.md`, `REFECTORING.md` 숙지
- [ ] 기존 `agent-service.ts` SSE 파싱 로직 상세 분석
- [ ] 기존 `MessageRenderer.tsx`의 렌더 분기 파악
- [ ] 기존 `RecordsArtifact.tsx`의 패턴을 SRS/TC로 확장할 템플릿 추출

### 26.2 기반 작업
- [ ] `@microsoft/fetch-event-source` 설치 및 SSE 클라이언트 교체
- [ ] 타입 정의: `ToolCallData` 확장, `PlanStep`, `HitlData` 추가
- [ ] `hitl-store`, `version-store` 신규 생성
- [ ] 백엔드 SSE 이벤트 스키마 확정 (token / tool_call / tool_result / plan_update / interrupt / done)

### 26.3 핵심 컴포넌트 순서
1. AgentInvocationCard (Phase 2 착수)
2. PlanProgress
3. ClarifyCard → ConfirmCard → DecisionCard
4. SrsEditor (RecordsArtifact 패턴 참조)
5. TestCaseList
6. VersionHistory + DiffViewer
7. ImpactGraph

---

**문서 버전**: v1.0
**관련 문서**: DESIGN.md (백엔드 통합본)
**다음 액션**: Claude Code에서 본 문서 + 백엔드 DESIGN.md 동시 참조하여 구현 착수
