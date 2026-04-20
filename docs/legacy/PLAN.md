# AISE 2.0 - 작업 계획 (PLAN)

> 진행 상황: `PROGRESS.md`

---

## Phase 1: MVP — 프로젝트 + 요구사항 + AI 어시스트 ✅ 완료

> 핵심 가치: "요구사항을 입력하면 AI가 정제/보완해주는" 기본 루프 완성
> ※ Phase 2에서 Record 기반으로 전환됨. 기존 Requirements/Assist 코드는 레퍼런스로 보존.

<details>
<summary>Phase 1 상세 (접기)</summary>

### 1.1 인프라 / 기반

- [x] PostgreSQL DB 연결 설정 (SQLAlchemy + asyncpg)
- [x] DB 마이그레이션 설정 (Alembic)
- [x] Azure OpenAI 연동 서비스 (`services/llm_svc.py`) — Responses API 기반
- [x] Frontend API 클라이언트 설정 (Backend 연동)

### 1.2 프로젝트 관리 (FR-PF-02)

- [x] DB 모델: Project
- [x] API: Project CRUD (`/api/v1/projects`)
- [x] API: 프로젝트 설정 (`/api/v1/projects/{id}/settings`)
- [x] API: 모듈 선택
- [x] Frontend: 프로젝트 목록/생성/수정/삭제

### 1.3 요구사항 관리 (FR-RQ-01) → Phase 2에서 Record로 대체

- [x] Requirement CRUD + 넘버링 + 순서 변경 + 테이블 뷰
- [x] 섹션(그룹핑) CRUD + 드래그 앤 드롭

### 1.4~1.5 AI 어시스트 → Phase 3에서 Agent Chat으로 대체

- [x] 구조화 모드 (Refine, Suggest)
- [x] 대화 모드 (Chat + 요구사항 추출)

### 1.6 Glossary → Phase 2에서 확장

- [x] Glossary CRUD + AI 자동 생성

### 1.7 Knowledge Repository → Phase 2에서 확장

- [x] Backend: pgvector + MinIO + RAG Chat API
- [x] Frontend: API 연동 (Phase 2.1에서 처리)

### 1.8 Frontend 구조 재설계

- [x] /agent 라우트 + ArtifactPanel + RequirementsArtifact

</details>

---

## Phase 2: 프로젝트 기반 — 지식 저장소 + 용어 사전 + 섹션 관리 + 준비도

> 핵심 가치: "Agent 실행 전 프로젝트 기반 데이터를 준비하는" 단계 완성
> 의존성: Phase 1 인프라 (DB, MinIO, LLM) 활용

### 2.1 지식 저장소 강화 (3-1)

#### 2.1.1 Backend — DB 모델 확장

- [x] KnowledgeDocument에 `is_active` (Boolean, default=true) 필드 추가
- [x] KnowledgeDocument 상태값 정리: uploading→pending, processing, ready→completed, error→failed
- [x] Alembic 마이그레이션 생성 + 양쪽 DB 적용

#### 2.1.2 Backend — API 확장

- [x] `PATCH /documents/{id}/toggle` — 활성화/비활성화 토글
- [x] 문서 목록 조회 시 `is_active` 필드 포함
- [x] 업로드 시 중복 파일 감지 (동일 project + 동일 파일명) → 409 응답 + 클라이언트에서 덮어쓰기 확인
- [x] 문서 미리보기 API: `GET /documents/{id}/preview` — 첫 N줄 또는 첫 페이지 텍스트 반환
- [x] 지원 포맷 제한: txt, md, pdf (기존 docx/pptx/xlsx는 추후 확장)

#### 2.1.3 Frontend — ProjectKnowledgeTab API 연동

- [x] Mock 데이터 → 실제 API 호출로 교체 (목록, 업로드, 삭제)
- [x] 문서별 상태 표시: pending / processing / completed / failed (아이콘 + 텍스트)
- [x] 활성화/비활성화 토글 스위치 UI
- [x] 중복 업로드 시 확인 다이얼로그 ("덮어쓰기 하시겠습니까?")
- [x] 문서 클릭 시 미리보기 패널/모달 (원문 텍스트 표시)
- [x] 실패 문서: 에러 메시지 표시 + 재업로드 버튼

### 2.2 용어 사전 확장 (3-2)

#### 2.2.1 Backend — DB 모델 확장

- [x] GlossaryItem에 필드 추가:
  - `source_document_id` (UUID FK → KnowledgeDocument, nullable, SET NULL)
  - `synonyms` (ARRAY(String), default=[])
  - `abbreviations` (ARRAY(String), default=[])
  - `section_tags` (ARRAY(String), default=[])
  - `is_auto_extracted` (Boolean, default=false) — AI 추출 여부
  - `is_approved` (Boolean, default=false) — 사용자 승인 여부
  - `created_at`, `updated_at` (DateTime)
- [x] Alembic 마이그레이션

#### 2.2.2 Backend — API 확장

- [x] `POST /glossary/extract` — **지식 문서 기반** 용어 후보 추출 (기존 generate는 요구사항 기반)
  - 활성 지식 문서의 chunk를 컨텍스트로 사용
  - 추출 결과: term, definition, source_document_id, synonyms, abbreviations
  - DB 저장 없이 후보 목록 반환 (사용자 검토 후 저장)
- [x] `POST /glossary/approve` — 선택한 후보 일괄 승인 저장
- [x] `PUT /glossary/{id}` 확장 — synonyms, abbreviations, section_tags 수정 지원
- [x] 프롬프트: 지식 문서 기반 용어 추출 프롬프트 작성
- [x] 재추출 시 기존 수동 편집 항목(`is_auto_extracted=false`) 보존 로직

#### 2.2.3 Frontend — 용어 사전 UI 개선

- [x] 용어 목록에 출처 문서, 동의어, 약어, 섹션 태그 컬럼 표시
- [x] AI 추출 버튼 → 후보 목록 표시 → 체크박스 선택 → 승인 저장
- [x] 수동 추가 시 동의어/약어/섹션 태그 입력 필드
- [x] 승인 상태 뱃지 (승인됨 / 미승인)

### 2.3 섹션 관리 재설계 (3-3)

#### 2.3.1 Backend — DB 모델 재설계

- [x] RequirementSection 확장 (또는 새 Section 모델):
  - `description` (Text, nullable) — 섹션 설명/목적
  - `output_format_hint` (Text, nullable) — 출력 형식 힌트
  - `is_required` (Boolean, default=false) — 필수 여부
  - `is_default` (Boolean, default=false) — 기본 제공 섹션 여부
  - `is_active` (Boolean, default=true) — 활성화 상태
  - `type` 필드 제거 또는 자유 문자열로 변경 (FR/QA/Constraints 고정 → 자유 섹션명)
- [x] Alembic 마이그레이션
- [x] 프로젝트 생성 시 기본 5종 섹션 자동 생성:
  - Overview (필수, 삭제불가)
  - Functional Requirements (필수, 삭제불가)
  - Quality Attributes (필수, 삭제불가)
  - Constraints (필수, 삭제불가)
  - Interfaces (필수, 삭제불가)

#### 2.3.2 Backend — API 수정

- [x] 섹션 삭제 시 `is_default=true`이면 400 에러 (비활성화만 허용)
- [x] `PATCH /sections/{id}/toggle` — 활성화/비활성화 토글
- [x] `POST /sections/extract` — 지식 문서 기반 섹션 후보 AI 추출
  - 활성 지식 문서 분석 → 추가 섹션 후보 제안
  - 사용자 검토 후 저장
- [x] 섹션 목록 조회 시 `is_active`, `is_default`, `is_required` 포함
- [x] 프롬프트: 지식 문서 기반 섹션 추출 프롬프트 작성

#### 2.3.3 Frontend — 섹션 관리 UI

- [x] 프로젝트 상세 내 섹션 관리 탭/페이지
- [x] 기본 섹션 5종: 삭제 버튼 비활성, 비활성화 토글만 표시
- [x] 커스텀 섹션 추가: 이름, 설명, 출력 형식 힌트, 필수 여부 입력
- [x] AI 섹션 추출 버튼 → 후보 목록 → 선택 저장
- [x] 드래그 앤 드롭 순서 변경 (SRS 출력 순서 반영)
- [x] 섹션별 설명/출력 형식 힌트 인라인 편집

### 2.4 프로젝트 준비도 (3-4)

#### 2.4.1 Backend — API

- [x] `GET /projects/{id}/readiness` — 준비도 조회
  - `knowledge_count`: 활성 지식 문서 수 (completed 상태)
  - `glossary_approved_count`: 승인된 용어 수
  - `active_section_count`: 활성 섹션 수
  - `is_ready`: 최소 기준 충족 여부 (문서 ≥1, 용어 ≥1, 섹션 ≥1)
  - 각 항목별 상태 (sufficient / insufficient)

#### 2.4.2 Frontend — 준비도 UI

- [x] 프로젝트 상세 페이지에 준비도 카드 표시
- [x] 각 항목 클릭 시 해당 탭(지식/용어/섹션)으로 이동
- [x] 미비 항목 시각적 강조 (경고 아이콘 + 색상)
- [x] Agent 진입 시점에도 준비도 미니뷰 표시 (좌패널)

---

## Phase 3: Agent 코어 — 레이아웃 + 레코드 추출

> 핵심 가치: "지식 문서에서 AI가 섹션별 레코드를 추출하는" 핵심 워크플로우 완성
> 의존성: Phase 2 (지식 문서, 섹션, 용어 사전이 준비된 상태)

### 3.1 Record 데이터 모델 (4-3 기반)

#### 3.1.1 Backend — DB 모델

- [x] `Record` 모델 신규 생성:
  - `id` (UUID PK)
  - `project_id` (FK → Project)
  - `section_id` (FK → Section)
  - `content` (Text) — 레코드 본문
  - `display_id` (String) — 자동 넘버링 (예: OVR-001, FR-001)
  - `source_document_id` (FK → KnowledgeDocument, nullable)
  - `source_location` (String, nullable) — 원문 위치 (페이지, 줄 번호 등)
  - `confidence_score` (Float, nullable) — AI 추출 신뢰도 (0.0~1.0)
  - `status` (String) — draft / approved / excluded
  - `is_auto_extracted` (Boolean, default=false)
  - `order_index` (Integer)
  - `created_at`, `updated_at` (DateTime)
- [x] Alembic 마이그레이션

#### 3.1.2 Backend — Record CRUD API

- [x] `GET /projects/{id}/records` — 레코드 목록 (섹션별 그룹핑, 섹션 필터 지원)
- [x] `POST /projects/{id}/records` — 레코드 수동 추가 (사용자 직접 작성)
- [x] `PUT /projects/{id}/records/{record_id}` — 레코드 수정
- [x] `DELETE /projects/{id}/records/{record_id}` — 레코드 삭제
- [x] `PATCH /projects/{id}/records/{record_id}/status` — 상태 변경 (approved/excluded)
- [x] `PUT /projects/{id}/records/reorder` — 순서 변경

### 3.2 레코드 추출 Agent (4-3)

#### 3.2.1 Backend — 추출 API

- [x] `POST /projects/{id}/records/extract` — 전체 레코드 추출 시작
  - 활성 지식 문서 + 활성 섹션 + 승인된 용어 사전을 컨텍스트로 사용
  - 섹션별로 지식 문서 내용을 분석하여 레코드 추출
  - 결과: Record 목록 (content, section_id, source_document_id, source_location, confidence_score)
  - DB 저장 없이 후보 반환 → 사용자 검토 후 승인
- [x] `POST /projects/{id}/records/extract-section` — 특정 섹션만 재추출
  - 기존 해당 섹션 레코드는 유지, 새 후보만 추가 제안
- [x] `POST /projects/{id}/records/approve` — 선택한 추출 후보 일괄 승인 저장

#### 3.2.2 프롬프트

- [x] 레코드 추출 프롬프트 작성:
  - 입력: 지식 문서 텍스트 + 섹션 목록(이름/설명/출력 형식) + 용어 사전
  - 출력: 섹션별 레코드 목록 + 원문 출처 + 신뢰도
  - 규칙: 원문에 없는 내용 생성 금지, 출처 반드시 명시
- [x] 섹션별 재추출 프롬프트 (특정 섹션 집중)

### 3.3 Agent 레이아웃 재설계 (4-1)

#### 3.3.1 Frontend — 좌패널 재구성

- [x] 프로젝트 선택 드롭다운 (현재 프로젝트 표시 + 전환)
- [x] 준비도 미니뷰 (문서/용어/섹션 각각 아이콘+숫자, 클릭 시 프로젝트 상세로 이동)
- [x] 대화 스레드 리스트 (기존 유지)

#### 3.3.2 Frontend — 우패널 재구성

- [x] ArtifactPanel 탭 변경: Requirements → **Records** 탭, SRS 탭 유지
  - Design, TestCase 탭은 추후 Phase용으로 placeholder 유지
- [x] Records 탭: 섹션별 그룹핑 레코드 목록
  - 섹션 필터 (드롭다운 또는 탭)
  - 레코드 카드: ID, 섹션, 내용, 출처(문서명+위치), 신뢰도 뱃지
  - 인라인 편집 / 삭제 / 제외 처리
  - 수동 레코드 추가 버튼
- [x] 원문 출처 클릭 → 지식 문서 미리보기 모달 (해당 위치 하이라이트)

#### 3.3.3 Frontend — 패널 비율 조정

- [x] 기본 비율: 좌 2 / 중앙 4 / 우 4 로 변경
- [x] 현재 프로젝트 컨텍스트를 상단에 항상 표시

### 3.4 액션 카드 + 채팅 연동 (4-2, 4-5)

#### 3.4.1 Frontend — 액션 카드

- [x] 초기 화면에 워크플로우 진입 액션 카드 표시:
  - "레코드 추출 시작" — 항상 표시, 준비도 미충족 시 비활성
  - "SRS 문서 생성" — 추출된 레코드 있을 때 활성
  - "용어집 검토" — 미승인 용어 있을 때 활성
  - "SRS 재생성" — 기존 SRS 버전 있을 때 활성
- [x] 프로젝트 준비도에 따라 카드 활성/비활성 처리
- [x] 카드 클릭 시 해당 워크플로우 시작 (채팅에 시스템 메시지 + API 호출)

#### 3.4.2 채팅 ↔ 우패널 연동

- [x] 에이전트 작업 완료 시 채팅에 결과 요약 메시지 + 해당 탭 이동 버튼
- [x] 우패널에서 레코드 수정 시 채팅에 변경 로그 자동 기록
- [x] 우패널 탭은 에이전트 작업 완료 시 자동 전환
- [x] 채팅에서 "FR 섹션 다시 추출해줘" → 부분 재추출 트리거

### 3.5 채팅 UI 개선

#### 3.5.1 구조화 블록 파싱 + 렌더링

- [x] `[CLARIFY]` 블록 파싱 → ClarifyQuestion 카드 렌더링
- [ ] `[REQUIREMENTS]` 블록 파싱 → ExtractedRequirements 카드 렌더링
- [ ] `[GENERATE_SRS]` 블록 파싱 → GenerateSrsProposal 카드 렌더링

#### 3.5.2 CLARIFY 답변 전송

- [ ] ClarifyQuestion에서 답변 선택 후 → 사용자 메시지로 자동 전송
  - `onAnswer(answer)` → `useChatStore.addMessage()` + `streamAgentChat()` 호출
  - 답변 전송 후 에이전트가 다음 단계 진행

#### 3.5.3 코드블록 overflow 수정

- [x] MessageResponse에 `overflow-hidden` 추가 → 코드블록 영역 내부 스크롤

### 3.6 다중 세션 + URL 라우팅

> 세션별 URL 라우팅 + 백엔드 DB 저장 + 다중 세션 동시 스트리밍

#### 3.6.1 Backend — 세션 모델 + API

- [x] `Session`, `SessionMessage` DB 모델 (PostgreSQL)
- [x] Alembic 마이그레이션 (sessions, session_messages 테이블)
- [x] Session CRUD API (`/api/v1/sessions`)
- [x] Agent Chat session_id 기반으로 변경 (history[] 제거, DB에서 로드)
- [x] 메시지 자동 저장 (user 메시지 → 스트리밍 전, assistant 메시지 → 스트리밍 완료 후)
- [x] 첫 메시지 시 세션 제목 자동 설정

#### 3.6.2 Frontend — URL 라우팅 + 스토어

- [x] `/agent` (새 대화), `/agent/[sessionId]` (특정 세션) 라우팅
- [x] 세션 API 서비스 (`session-service.ts`)
- [x] Chat Store 리팩터링: Thread 기반 → Session 기반
  - `sessionMessages: Record<string, ChatMessage[]>` (서버 캐시)
  - `streamingSessionIds: Set<string>` (세션별 독립 스트리밍)
  - localStorage persist 제거 (서버가 source of truth)

#### 3.6.3 Frontend — 컴포넌트

- [x] ChatArea: sessionId props, 서버 메시지 로드, 첫 메시지 시 세션 생성 + URL 변경
- [x] SessionList: 서버 기반 세션 목록 (ThreadList 대체)
- [x] LeftSidebar: SessionList 사용, "새 대화" → `/agent` 네비게이션
- [x] MobileBottomDrawer: SessionList 사용

---

## Phase 4: SRS 생성 + 내보내기

> 핵심 가치: "승인된 레코드 → SRS 문서 생성" 파이프라인 완성
> 의존성: Phase 3 (레코드 추출 완료 상태)

### 4.1 SRS 생성 (4-4)

#### 4.1.1 Backend — DB 모델

- [ ] `SrsDocument` 모델:
  - `id` (UUID PK)
  - `project_id` (FK → Project)
  - `version` (Integer) — 생성 버전
  - `content` (Text) — Markdown 형태 SRS 본문
  - `status` (String) — generating / completed / failed
  - `based_on_records` (JSON) — 기반 레코드 ID 목록 (추적성)
  - `based_on_documents` (JSON) — 기반 지식 문서 목록
  - `created_at` (DateTime)
- [ ] `SrsSection` 모델 (SRS 내 섹션별 분리):
  - `id`, `srs_document_id`, `section_id`, `content`, `order_index`
- [ ] Alembic 마이그레이션

#### 4.1.2 Backend — API

- [ ] `POST /projects/{id}/srs/generate` — SRS 생성 시작
  - 승인된(approved) 레코드 + 용어 사전 기반
  - 섹션 순서대로 문서 구성
- [ ] `GET /projects/{id}/srs` — SRS 목록 (버전별)
- [ ] `GET /projects/{id}/srs/{srs_id}` — SRS 상세 조회
- [ ] `PUT /projects/{id}/srs/{srs_id}/sections/{section_id}` — SRS 섹션 인라인 편집
- [ ] `POST /projects/{id}/srs/{srs_id}/regenerate` — SRS 재생성

#### 4.1.3 프롬프트

- [ ] SRS 생성 프롬프트 (IEEE 830 기반, 섹션별 레코드 → 문서 챕터)
- [ ] SRS 내 원본 레코드 참조 마킹 (Traceability)

#### 4.1.4 Frontend — SRS 탭

- [ ] SRS 렌더링 (Markdown → HTML, 섹션별 구분)
- [ ] 각 항목에서 원본 레코드 및 출처 문서 링크 (클릭 시 이동)
- [ ] 인라인 편집 지원 (섹션별 편집 모드)
- [ ] 생성 이력: 버전 목록 + 기반 문서 정보

### 4.2 내보내기

- [ ] API: `POST /projects/{id}/srs/{srs_id}/export` — md, pdf 지원
- [ ] Frontend: Export 버튼 + 형식 선택 UI

---

## Phase 5: TestCase 생성 (추후 상세화)

> 핵심 가치: "레코드/SRS 기반 TC 자동 생성"

- [ ] TC 모델 + CRUD
- [ ] TC 생성 Agent (레코드 기반)
- [ ] TC Review
- [ ] TC Export

---

## Phase 6: 버전관리 + 추적성 (추후 상세화)

> 핵심 가치: "산출물 간 연결 + 변경 시 영향 파악"

- [ ] 레코드 → SRS → TC 간 추적성 매트릭스
- [ ] SRS 버전 간 diff 표시
- [ ] 지식 문서 변경 시 outdated 알림

---

## Phase 7: 멤버 관리 + SSO + 플랫폼 완성 (추후 상세화)

- [ ] SSO(Keycloak) 연동
- [ ] 멤버 관리 (Owner/Editor/Viewer)
- [ ] 알림 시스템
- [ ] 대시보드

---

## Phase 우선순위 요약

| Phase    | 내용                                         | 핵심 가치                 |
| -------- | -------------------------------------------- | ------------------------- |
| **1** ✅ | 프로젝트 + 요구사항 + AI 어시스트 + Glossary | 기본 루프 완성 (레퍼런스) |
| **2** 🔜 | 지식 저장소 + 용어 사전 + 섹션 관리 + 준비도 | 프로젝트 기반 데이터 준비 |
| **3**    | Agent 레이아웃 + 레코드 추출 + 액션 카드     | 핵심 워크플로우 완성      |
| **4**    | SRS 생성 + 내보내기                          | SRS 파이프라인 완성       |
| **5**    | TestCase 생성                                | TC 파이프라인 완성        |
| **6**    | 버전관리 + 추적성                            | 산출물 관리 완성          |
| **7**    | 멤버 관리 + SSO + 플랫폼                     | 팀 협업 완성              |

---

## 품질 리팩토링 (2026-04-16)

- [x] Record API 입력 타입 정리 (UUID) + 잘못된 ID 422 조기 검증
- [x] Record 서비스 리팩토링 (섹션 소속 검증, 일괄 승인 채번/순번 배치 계산)
- [x] Agent/Knowledge 스키마 mutable 기본값 제거 (`default_factory` 적용)
- [x] Record/Agent 테스트 추가 + 테스트 DB cleanup 로직 안정화
- [x] Requirement/Section API 입력 타입 정리 (UUID) + 잘못된 ID 422 조기 검증
- [x] Requirement `section_id=""` 하위 호환 유지 (`None` 정규화 validator)
- [x] Requirement/Section reorder·selection 서비스 UUID 처리 리팩토링
- [x] Requirement/Section 테스트 보강 + 전체 테스트 재검증
- [x] Requirement/Section/Record 부분 reorder 시 전체 order_index 일관성 보장 (충돌 방지)
- [x] Record source_document 프로젝트 소속 검증 추가 (교차 프로젝트 참조 차단)
- [x] Record 라우터 정적 경로(`/reorder`) 우선 매칭 버그 수정
- [x] Record approve 경로의 source_document 교차 프로젝트 참조 차단 검증 추가
- [x] 기본 섹션 보장 로직 개선 (부분 유실 시 누락 기본 섹션만 자동 복구)
- [x] Assist/Review 요청 ID 타입(UUID) 정규화 + invalid UUID 422 검증 일원화
- [x] Glossary source_document 프로젝트 소속 검증 추가 (create/approve)
- [x] Session 생성 시 프로젝트 존재 검증 추가

---

## 성능 최적화 백로그

### 채팅 메시지 가상화 (Virtualization)

> 현재 상태: 모든 메시지를 한 번에 렌더링. 일반적인 수십 턴 세션에서는 문제없음.
> 대비 시점: 세션당 100+ 턴 또는 코드블록/머메이드가 많은 긴 세션에서 체감 성능 저하 시.

**현재 보호 장치:**
- `MessageResponse`가 `memo`로 감싸져 있어 이전 메시지는 re-render 안 됨
- Shiki 토큰 캐시로 코드 하이라이팅 재계산 방지

**검토할 접근법:**
- [ ] `react-window` 또는 `@tanstack/virtual`로 뷰포트 밖 메시지를 언마운트
  - 주의: 턴 기반 레이아웃(min-height 고정)과의 호환성 검토 필요
  - 주의: 가변 높이 아이템(코드블록, 머메이드, 테이블) 측정 전략 필요
- [ ] 대안: 일정 턴 수 이상이면 과거 메시지를 접는 UI ("이전 대화 보기" 버튼)
  - 가상화보다 구현 단순, 턴 레이아웃 영향 없음
- [ ] Streamdown `memo` 비교 함수 최적화 (content + streaming만 비교 중, 충분한지 프로파일링)

---

## 미결 사항

- [ ] 레코드 신뢰도 스코어 임계값 기준 (몇 % 이하를 검토 필요로 표시할지)
- [ ] SRS 버전 간 diff 표시 방식
- [ ] 프로젝트 준비도 최소 기준 수치 (문서 N개 이상 등)
- [ ] 지식 문서 중복 업로드 정책 (덮어쓰기 vs 버전 구분) — 우선 덮어쓰기 확인으로 구현

## Last hotfix (2026-04-17)

- [x] Frontend chat streaming hotfix: keep Streamdown active during streaming, enable incomplete-markdown parsing, and batch token flush via requestAnimationFrame to prevent reverse/out-of-order rendering artifacts.
- [x] Code block horizontal scrollbar UX: keep horizontal scrolling but show scrollbar only on hover/focus for chat markdown and source markdown.
- [x] Code block scrollbar behavior tuned: keep fixed horizontal scrollbar height and fade thumb in/out on hover/focus (no layout jump).
- [x] Markdown visual refresh: added 3 style presets (`docs`, `github`, `dense`) and set docs preset as default for chat + source markdown renderers.
- [x] Added markdown theme preset setting with persistent storage (docs/github/dense), and applied transparent inner background style for code blocks.
- [x] Fixed markdown preset card clipping/alignment and code-block header alignment; removed inner code-block border.
- [x] Polished markdown preset card visual consistency with theme cards and refined code-block header separator/alignment with no shell shadow.

- [x] Added chat font-size preference (small/medium/large) and applied it to user/assistant messages in agent chat.
- [x] Refined code-block header layout: full-width bottom separator line, improved vertical alignment (language/actions), and increased Y padding.

- [x] Replaced assistant pre-response spinner with Wave Dots loading indicator.
- [x] Unified markdown outer borders (table/mermaid/code-block) with shared shell border tokens for consistent look.
- [x] Applied proportional markdown typography scaling (base + heading hierarchy) based on chat font-size preference.

- [x] Removed markdown table wrapper border layer (wrapper shell) while keeping table outer border style.

- [x] Moved streaming indicator to right edge of assistant message (replace Streamdown trailing caret with custom Wave Dots).
- [x] Restored current-turn top anchoring by preventing bottom auto-scroll override while latest user+assistant turn is active.
- [x] Enforced markdown table wrapper shell border removal with stronger selectors and Streamdown style override order.

- [x] Aligned code-block header language/actions on the same line by overriding Streamdown action wrapper positioning (absolute top row).
- [x] Mobile streaming UX hotfix: keep optimistic session state during `/agent -> /agent/[sessionId]` handoff so first-turn streaming stays visible without waiting for route hydration.
- [x] Mobile/new-session loading guard: show full-page loading only when there are no messages and no active stream, preventing spinner from masking token-by-token rendering.
- [x] Mobile token-drain hotfix: replace single-frame token flush with time-sliced drain (small chunk append loop) so coalesced SSE chunks still render progressively on mobile.
- [x] Desktop auto-follow hotfix: keep current-turn top anchoring on mobile only, while desktop restores streaming auto-scroll follow behavior.
- [x] Mobile conditional auto-follow: enable streaming auto-scroll follow on mobile when user is near bottom, while keeping top-anchoring when user is reading above.

## 2026-04-18 추가 작업: 백엔드 리팩토링 분석/하네스 설계
- [x] backend/src 전 파일/함수 인벤토리 재점검
- [x] 에이전트 일관성 이슈(P0/P1) 라인 기준 리뷰 정리
- [x] Harness/Structured Output/Tool Gateway 중심 Phase-1 설계 초안 문서화 (`REFECTORING.md`)
