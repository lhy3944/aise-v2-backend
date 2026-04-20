# AISE 2.0 API Interface

> Backend(FastAPI) ↔ Frontend(Next.js) 통신 인터페이스 정의
> Base URL: `/api/v1`
> 인증: SSO(Keycloak) 통과 후 user_id를 헤더 또는 세션에서 가져옴 (별도 토큰 없음)

---

## 1. 사용자 (Auth)

### `GET /api/v1/users/me`
> SSO 로그인 후 현재 사용자 정보 조회 (FR-PF-01)

**Response:**
```json
{
  "user_id": "hong.gildong",
  "user_name": "홍길동",
  "email": "hong.gildong@company.com",
  "department": "공학연구소"
}
```

### `GET /api/v1/users/me/activity`
> 최근 활동 이력 조회 (FR-PF-04-02)

**Response:**
```json
{
  "recent_projects": [
    {
      "project_id": "proj-001",
      "project_name": "로봇 제어 시스템",
      "last_accessed_at": "2026-03-27T10:30:00Z"
    }
  ]
}
```

---

## 2. 프로젝트 (Project)

### `GET /api/v1/projects`
> 사용자가 참여한 프로젝트 목록 조회 (FR-PF-02-08, FR-PF-02-09)

**Response:**
```json
{
  "projects": [
    {
      "project_id": "proj-001",
      "name": "로봇 제어 시스템",
      "description": "산업용 로봇 제어 소프트웨어",
      "domain": "robotics",
      "product_type": "embedded",
      "modules": ["requirements", "design", "testcase"],
      "member_count": 3,
      "status": "active",
      "created_at": "2026-03-20T09:00:00Z",
      "updated_at": "2026-03-27T10:30:00Z"
    }
  ]
}
```

### `POST /api/v1/projects`
> 프로젝트 생성 (FR-PF-02-01, FR-PF-02-02, FR-PF-02-03)

**Request:**
```json
{
  "name": "로봇 제어 시스템",
  "description": "산업용 로봇 제어 소프트웨어",
  "domain": "robotics",
  "product_type": "embedded",
  "modules": ["requirements", "design", "testcase"]
}
```
- `modules`: `["requirements", "design", "testcase"]` 중 선택
  - All = `["requirements", "design", "testcase"]`
  - Requirements Only = `["requirements"]`
  - Requirements+Design = `["requirements", "design"]`
  - Requirements+Testcase = `["requirements", "testcase"]`
  - Testcase Only = `["testcase"]`

**Response:**
```json
{
  "project_id": "proj-001",
  "name": "로봇 제어 시스템",
  "description": "산업용 로봇 제어 소프트웨어",
  "domain": "robotics",
  "product_type": "embedded",
  "modules": ["requirements", "design", "testcase"],
  "created_at": "2026-03-27T09:00:00Z"
}
```

### `GET /api/v1/projects/{project_id}`
> 프로젝트 상세 조회

### `PUT /api/v1/projects/{project_id}`
> 프로젝트 수정 (FR-PF-02-06, FR-PF-02-05)

**Request:**
```json
{
  "name": "로봇 제어 시스템 v2",
  "description": "수정된 설명",
  "modules": ["requirements", "design", "testcase"]
}
```

### `DELETE /api/v1/projects/{project_id}`
> 프로젝트 삭제 (FR-PF-02-07)

---

## 3. 멤버 (Member)

### `GET /api/v1/projects/{project_id}/members`
> 프로젝트 멤버 목록 조회 (FR-PF-03-06)

**Response:**
```json
{
  "members": [
    {
      "user_id": "hong.gildong",
      "user_name": "홍길동",
      "email": "hong.gildong@company.com",
      "role": "owner"
    }
  ]
}
```

### `POST /api/v1/projects/{project_id}/members`
> 멤버 초대 (FR-PF-03-01, FR-PF-03-02)

**Request:**
```json
{
  "email": "kim.chulsu@company.com",
  "role": "editor"
}
```
- `role`: `"owner"` | `"editor"` | `"viewer"` ※ 향후 `"reviewer"` 확장 가능

### `PUT /api/v1/projects/{project_id}/members/{user_id}`
> 멤버 역할 변경 (FR-PF-03-04)

**Request:**
```json
{
  "role": "editor"
}
```

### `DELETE /api/v1/projects/{project_id}/members/{user_id}`
> 멤버 제거 (FR-PF-03-05)

---

## 4. 요구사항 (Requirement)

### `GET /api/v1/projects/{project_id}/requirements`
> 요구사항 목록 조회

**Query Parameters:**
- `type`: `"fr"` | `"qa"` | `"constraints"` | `"other"` (선택, 없으면 전체)

**Response:**
```json
{
  "requirements": [
    {
      "requirement_id": "req-001",
      "display_id": "FR-001",
      "order_index": 0,
      "type": "fr",
      "original_text": "로봇 중앙 버튼클릭하면 멈춤",
      "refined_text": "로봇의 중앙 버튼을 클릭하면 자동으로 멈춰야 합니다.",
      "is_selected": true,
      "status": "draft",
      "created_at": "2026-03-27T09:00:00Z",
      "updated_at": "2026-03-27T09:05:00Z"
    }
  ]
}
```

### `POST /api/v1/projects/{project_id}/requirements`
> 요구사항 생성 (FR-RQ-01-01)

**Request:**
```json
{
  "type": "fr",
  "original_text": "로봇 중앙 버튼클릭하면 멈춤"
}
```
- `type`: `"fr"` | `"qa"` | `"constraints"` | `"other"`

### `PUT /api/v1/projects/{project_id}/requirements/{requirement_id}`
> 요구사항 수정 (FR-RQ-01-04~06)

**Request:**
```json
{
  "original_text": "수정된 내용",
  "refined_text": "수정된 정제 내용",
  "is_selected": true
}
```

### `DELETE /api/v1/projects/{project_id}/requirements/{requirement_id}`
> 요구사항 삭제

### `PUT /api/v1/projects/{project_id}/requirements/reorder`
> 요구사항 순서 변경 — 드래그 앤 드롭 (FR-RQ-01-21)

**Request:**
```json
{
  "ordered_ids": ["req-003", "req-001", "req-002"]
}
```
- `ordered_ids`: 변경된 순서대로 요구사항 ID 배열. 해당 타입 내 전체 ID를 포함해야 함.

**Response:**
```json
{
  "updated_count": 3
}
```

### `PUT /api/v1/projects/{project_id}/requirements/selection`
> 요구사항 일괄 선택/해제 (FR-RQ-01-07)

**Request:**
```json
{
  "requirement_ids": ["req-001", "req-002", "req-003"],
  "is_selected": true
}
```

### `POST /api/v1/projects/{project_id}/requirements/save`
> 요구사항 저장 (FR-RQ-01-08) — 현재 상태를 버전으로 저장

**Response:**
```json
{
  "version": 1,
  "saved_count": 5,
  "saved_at": "2026-03-27T10:00:00Z"
}
```

---

## 5. AI 어시스트 (Assist)

### `POST /api/v1/projects/{project_id}/assist/refine`
> 자연어 → 요구사항 문장 정제 (FR-RQ-01-02)

**Request:**
```json
{
  "text": "로봇 중앙 버튼클릭하면 멈춤",
  "type": "fr"
}
```

**Response:**
```json
{
  "original_text": "로봇 중앙 버튼클릭하면 멈춤",
  "refined_text": "로봇의 중앙 버튼을 클릭하면 자동으로 멈춰야 합니다.",
  "type": "fr"
}
```

### `POST /api/v1/projects/{project_id}/assist/suggest`
> 누락 요구사항 제안 / 보완 제안

**Request:**
```json
{
  "requirement_ids": ["req-001", "req-002"]
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "type": "qa",
      "text": "로봇 정지 명령의 응답 시간은 100ms 이내여야 합니다.",
      "reason": "FR req-001에 대응하는 성능 요구사항이 누락되어 있습니다."
    }
  ]
}
```

### `POST /api/v1/projects/{project_id}/assist/chat`
> 대화 모드 — 자유 대화를 통해 요구사항을 탐색적으로 정의 (FR-RQ-01-04~06)

**Request:**
```json
{
  "message": "우리 시스템은 로봇을 제어하는 시스템인데, 비상 정지 기능이 필요해요",
  "history": [
    { "role": "user", "content": "이전 메시지" },
    { "role": "assistant", "content": "이전 응답" }
  ]
}
```

**Response:**
```json
{
  "reply": "비상 정지 기능에 대해 몇 가지 요구사항을 정리해볼게요...",
  "extracted_requirements": [
    {
      "type": "fr",
      "text": "시스템은 비상 정지 버튼을 누르면 100ms 이내에 모든 동작을 중단해야 한다.",
      "reason": "사용자가 언급한 비상 정지 기능에서 추출"
    }
  ]
}
```
- `extracted_requirements`: 대화에서 추출된 요구사항 (없으면 빈 배열)
- `type`: `"fr"` | `"qa"` | `"constraints"` | `"other"`

---

## 6. Review

### `POST /api/v1/projects/{project_id}/review/requirements`
> 요구사항 Review (FR-RQ-02-01~04, FR-RQ-02-08, FR-RQ-02-13)
>
> - Include(`is_selected=true`)된 요구사항의 ID를 전달하여 리뷰 수행
> - v1: **충돌(conflict) + 중복(duplicate) 검출** + 간단 해결 힌트 제공
> - 리뷰 결과는 자동으로 DB에 저장 (프로젝트당 최신 1건 유지)

**Request:**
```json
{
  "requirement_ids": ["req-001", "req-002", "req-003"]
}
```

**Response:**
```json
{
  "review_id": "rv-001",
  "issues": [
    {
      "issue_id": "issue-001",
      "type": "conflict",
      "description": "FR-001과 FR-003이 충돌합니다. 정지 시간 100ms와 200ms가 모순됩니다.",
      "related_requirements": ["FR-001", "FR-003"],
      "hint": "두 요구사항의 정지 시간을 통일하거나 우선순위를 명시하세요."
    },
    {
      "issue_id": "issue-002",
      "type": "duplicate",
      "description": "FR-001과 FR-004가 동일한 내용입니다.",
      "related_requirements": ["FR-001", "FR-004"],
      "hint": "중복 요구사항 중 하나를 삭제하거나 통합하세요."
    }
  ],
  "summary": {
    "total_issues": 2,
    "conflicts": 1,
    "duplicates": 1,
    "ready_for_next": true,
    "feedback": "충돌 1건이 검출되었습니다. 해결을 권장하지만 다음 단계 진행은 가능합니다."
  }
}
```
- `type`: v1은 `"conflict"` | `"duplicate"` 사용 (추후 `"ambiguity"` 확장 예정)
- `hint`: 간단한 해결 방향 1줄
- `ready_for_next`: 충돌 유무와 관계없이 `true` (v1은 경고만, 차단 안 함)

### `GET /api/v1/projects/{project_id}/review/results/latest`
> 마지막 리뷰 결과 조회 (FR-RQ-02-14)
>
> 저장된 마지막 리뷰 결과를 반환. 리뷰 이력이 없으면 404.
> ※ v1에서는 API만 제공, UI는 추후 필요 시 제공

**Response:**
```json
{
  "review_id": "rv-001",
  "created_at": "2026-03-31T10:00:00Z",
  "reviewed_requirement_ids": ["req-uuid-001", "req-uuid-002", "req-uuid-003"],
  "issues": [
    {
      "issue_id": "issue-001",
      "type": "conflict",
      "description": "FR-001과 FR-003이 충돌합니다.",
      "related_requirements": ["FR-001", "FR-003"],
      "hint": "정지 시간을 통일하세요."
    }
  ],
  "summary": {
    "total_issues": 1,
    "conflicts": 1,
    "duplicates": 0,
    "ready_for_next": true,
    "feedback": "충돌 1건이 검출되었습니다."
  }
}
```

> **추후 확장 예정 (v1에서 미사용)**
> - `POST /review/suggestions/{issue_id}/accept` — 수정 제안 수락
> - `POST /review/suggestions/{issue_id}/reject` — 수정 제안 거절
> - 모호성(ambiguity), 누락(missing) 검출
> - severity(critical/minor), quality_score(0~100)

### `POST /api/v1/projects/{project_id}/review/usecase-diagram`
> Use Case Diagram Review (FR-RQ-02-05)

### `POST /api/v1/projects/{project_id}/review/usecase-spec`
> Use Case Specification Review (FR-RQ-02-06)

### `POST /api/v1/projects/{project_id}/review/testcases`
> TestCase Review (FR-TC-04)

**Response:**
```json
{
  "issues": [
    {
      "issue_id": "issue-001",
      "type": "duplicate",
      "description": "TC-003과 TC-005가 중복됩니다.",
      "related_testcases": ["tc-003", "tc-005"]
    }
  ],
  "coverage": {
    "total_requirements": 10,
    "covered_requirements": 8,
    "coverage_rate": 80.0,
    "uncovered_requirements": ["req-007", "req-009"]
  }
}
```

---

## 7. Glossary (용어정의)

### `GET /api/v1/projects/{project_id}/glossary`
> 용어 목록 조회 (FR-RQ-01-13)

**Response:**
```json
{
  "glossary": [
    {
      "glossary_id": "gls-001",
      "term": "EMS",
      "definition": "Emergency Stop - 비상 정지 기능",
      "product_group": "robotics"
    }
  ]
}
```

### `POST /api/v1/projects/{project_id}/glossary`
> 용어 추가 (FR-RQ-01-13)

**Request:**
```json
{
  "term": "EMS",
  "definition": "Emergency Stop - 비상 정지 기능",
  "product_group": "robotics"
}
```

### `PUT /api/v1/projects/{project_id}/glossary/{glossary_id}`
> 용어 수정

### `DELETE /api/v1/projects/{project_id}/glossary/{glossary_id}`
> 용어 삭제

### `POST /api/v1/projects/{project_id}/glossary/generate`
> Glossary 초안 자동 생성 (FR-RQ-01-15)

**Response:**
```json
{
  "generated_glossary": [
    {
      "term": "EMS",
      "definition": "Emergency Stop - 비상 정지 기능",
      "product_group": "robotics"
    }
  ]
}
```

---

## 8. Import / Export (공통)

### `POST /api/v1/projects/{project_id}/import/file`
> 파일 업로드 (FR-PF-05-01)

**Request:** `multipart/form-data`
- `file`: 업로드 파일 (PDF, Word, Excel, PPT, Markdown)

**Response:**
```json
{
  "import_id": "imp-001",
  "filename": "요구사항정의서.pdf",
  "file_type": "pdf",
  "status": "uploaded",
  "uploaded_at": "2026-03-27T09:00:00Z"
}
```

### `POST /api/v1/projects/{project_id}/import/jira`
> Jira에서 데이터 가져오기 (FR-PF-05-02)

**Request:**
```json
{
  "jira_project": "ROBOT",
  "ticket_ids": ["ROBOT-101", "ROBOT-102"]
}
```

### `POST /api/v1/projects/{project_id}/import/polarion`
> Polarion에서 데이터 가져오기 (FR-PF-05-03)

**Request:**
```json
{
  "project": "RobotControl",
  "work_item_ids": ["WI-001", "WI-002"]
}
```

### `POST /api/v1/projects/{project_id}/import/{import_id}/parse`
> 업로드된 문서 파싱 + 미리보기 (FR-PF-05-02, FR-PF-05-03)

**Response:**
```json
{
  "import_id": "imp-001",
  "parsed": {
    "total_pages": 40,
    "sections": [
      { "title": "1. Introduction", "page_range": "1-3", "content_preview": "..." },
      { "title": "2. System Overview", "page_range": "4-8", "content_preview": "..." }
    ],
    "tables_count": 5,
    "images_count": 3
  },
  "status": "parsed"
}
```

### `POST /api/v1/projects/{project_id}/classify`
> Import된 문서를 FR/QA/Constraints/Other로 분류 — 2-pass 방식 (FR-RQ-06)

**Request:**
```json
{
  "import_ids": ["imp-001", "imp-002"]
}
```

**Response (SSE stream):** 진행 상태를 실시간으로 전송
```
event: progress
data: {"phase": "structure_analysis", "progress": 100, "message": "1차 분석 완료: 12개 섹션 식별"}

event: progress
data: {"phase": "section_extraction", "progress": 45, "current_section": "3. Functional Requirements", "message": "2차 분석 중 (5/12 섹션)"}

event: complete
data: { ... classification result ... }
```

**Response (최종 결과):**
```json
{
  "classification_id": "cls-001",
  "classified": {
    "fr": [
      { "text": "로봇의 중앙 버튼을 클릭하면 멈춰야 한다.", "confidence": 0.95, "source_section": "3. Functional Requirements" }
    ],
    "qa": [
      { "text": "정지 응답시간은 100ms 이내", "confidence": 0.88, "source_section": "4. Performance" }
    ],
    "constraints": [
      { "text": "IEC 61508 안전 표준을 준수해야 한다.", "confidence": 0.92, "source_section": "5. Constraints" }
    ],
    "other": [
      { "text": "본 시스템은 2025년 3분기 출시 예정이다.", "confidence": 0.85, "source_section": "1. Introduction", "category_hint": "일정" }
    ]
  },
  "duplicates": [
    { "items": ["fr[0]", "fr[3]"], "similarity": 0.92, "suggestion": "병합 권장" }
  ],
  "summary": {
    "total_extracted": 45,
    "fr_count": 20,
    "qa_count": 10,
    "constraints_count": 8,
    "other_count": 7,
    "low_confidence_count": 5
  }
}
```

### `POST /api/v1/projects/{project_id}/export`
> 산출물 내보내기 (FR-PF-05-05~08)

**Request:**
```json
{
  "target": "pdf",
  "artifact_type": "srs",
  "version": 1
}
```
- `target`: `"pdf"` | `"markdown"` | `"word"` | `"jira"` | `"polarion"`
- `artifact_type`: `"srs"` | `"requirements"` | `"usecase_diagram"` | `"usecase_spec"` | `"testcases"`

---

## 9. Use Case Diagram

### `GET /api/v1/projects/{project_id}/usecase-diagrams`
> Use Case Diagram 목록 조회

### `POST /api/v1/projects/{project_id}/usecase-diagrams/generate`
> Use Case Diagram 생성 (FR-RQ-03-01)

**Request:**
```json
{
  "requirement_ids": ["req-001", "req-002", "req-003"],
  "diagram_tool": "plantuml"
}
```
- `diagram_tool`: `"plantuml"` | `"mermaid"`

**Response:**
```json
{
  "diagram_id": "ucd-001",
  "code": "@startuml\nactor User\nUser --> (로봇 정지)\n@enduml",
  "diagram_tool": "plantuml",
  "source_requirements_version": 1,
  "is_outdated": false,
  "created_at": "2026-03-27T10:00:00Z"
}
```

### `PUT /api/v1/projects/{project_id}/usecase-diagrams/{diagram_id}`
> Use Case Diagram 코드 직접 수정 (FR-RQ-03-02)

**Request:**
```json
{
  "code": "@startuml\nactor User\nUser --> (로봇 정지)\nUser --> (로봇 시작)\n@enduml"
}
```

### `POST /api/v1/projects/{project_id}/usecase-diagrams/{diagram_id}/chat`
> LLM을 통한 Diagram 수정 (FR-RQ-03-03)

**Request:**
```json
{
  "message": "관리자 Actor를 추가해줘",
  "history": [
    { "role": "user", "content": "이전 메시지" },
    { "role": "assistant", "content": "이전 응답" }
  ]
}
```

**Response:**
```json
{
  "code": "@startuml\nactor User\nactor Admin\nUser --> (로봇 정지)\nAdmin --> (시스템 설정)\n@enduml",
  "message": "관리자(Admin) Actor와 시스템 설정 Use Case를 추가했습니다."
}
```

### `POST /api/v1/projects/{project_id}/usecase-diagrams/{diagram_id}/save`
> Use Case Diagram 저장 (FR-RQ-03-06)

**Response:**
```json
{
  "diagram_id": "ucd-001",
  "version": 1,
  "saved_at": "2026-03-27T10:30:00Z"
}
```

---

## 10. Use Case Specification

### `GET /api/v1/projects/{project_id}/usecase-specs`
> Use Case Specification 목록 조회

### `POST /api/v1/projects/{project_id}/usecase-specs/generate`
> Use Case Specification 생성 (FR-RQ-04-01~03)

**Request:**
```json
{
  "diagram_id": "ucd-001"
}
```

**Response:**
```json
{
  "specifications": [
    {
      "spec_id": "ucs-001",
      "use_case_name": "로봇 정지",
      "candidates": [
        {
          "candidate_id": "cand-001",
          "description": "사용자가 중앙 버튼을 눌러 로봇을 정지시키는 Use Case",
          "actors": ["User"],
          "preconditions": ["로봇이 작동 중이어야 한다."],
          "steps": [
            "사용자가 로봇 제어 패널에 접근한다.",
            "중앙 정지 버튼을 클릭한다.",
            "시스템이 정지 명령을 전달한다.",
            "로봇이 현재 동작을 중단한다."
          ],
          "exceptions": ["버튼 고장 시 비상 정지 시스템이 작동한다."],
          "postconditions": ["로봇이 정지 상태이다."]
        }
      ]
    }
  ],
  "source_diagram_version": 1
}
```

### `PUT /api/v1/projects/{project_id}/usecase-specs/{spec_id}`
> Use Case Specification 수정/선택 (FR-RQ-04-02, FR-RQ-04-05)

**Request:**
```json
{
  "selected_candidate_id": "cand-001"
}
```

### `DELETE /api/v1/projects/{project_id}/usecase-specs/{spec_id}`
> Use Case Specification 삭제

---

## 11. TestCase

### `GET /api/v1/projects/{project_id}/testcases`
> TestCase 목록 조회

**Response:**
```json
{
  "testcases": [
    {
      "testcase_id": "tc-001",
      "summary": "중앙 버튼 클릭 시 로봇 정지 확인",
      "source_requirement_id": "req-001",
      "steps": [
        { "step": "로봇을 작동 상태로 전환", "data": "", "expected_result": "로봇이 작동 중" },
        { "step": "중앙 버튼 클릭", "data": "", "expected_result": "로봇이 정지됨" }
      ],
      "technique": "equivalence_partitioning",
      "platform": "jira",
      "is_selected": true,
      "created_at": "2026-03-27T10:00:00Z"
    }
  ]
}
```

### `POST /api/v1/projects/{project_id}/testcases/generate`
> 연동 모드 TC 생성 (FR-TC-03)

**Request:**
```json
{
  "requirement_ids": ["req-001", "req-002"],
  "techniques": ["equivalence_partitioning", "boundary_value"],
  "platform": "jira"
}
```
- `techniques`: `"equivalence_partitioning"` | `"boundary_value"` | 기타 (FR-TC-01-01~02)
- `platform`: `"jira"` | `"polarion"` (FR-TC-01-04)

**Response:**
```json
{
  "testcases": [
    {
      "testcase_id": "tc-001",
      "summary": "중앙 버튼 클릭 시 로봇 정지 확인",
      "source_requirement_id": "req-001",
      "steps": [
        { "step": "로봇을 작동 상태로 전환", "data": "", "expected_result": "로봇이 작동 중" },
        { "step": "중앙 버튼 클릭", "data": "", "expected_result": "로봇이 정지됨" }
      ],
      "technique": "equivalence_partitioning",
      "platform": "jira"
    }
  ],
  "requirement_mapping": {
    "req-001": ["tc-001", "tc-002"],
    "req-002": ["tc-003"]
  }
}
```

### `POST /api/v1/testcases/generate-standalone`
> 독립 모드 TC 생성 (FR-TC-02)

**Request:**
```json
{
  "content": "로봇의 중앙 버튼을 클릭하면 멈춰야 합니다.",
  "techniques": ["equivalence_partitioning", "boundary_value"],
  "platform": "jira"
}
```

**Response:**
```json
{
  "classified": {
    "fr": ["로봇의 중앙 버튼을 클릭하면 멈춰야 합니다."],
    "qa": [],
    "constraints": []
  },
  "testcases": [
    {
      "testcase_id": "tc-tmp-001",
      "summary": "중앙 버튼 클릭 시 로봇 정지 확인",
      "source_type": "fr",
      "source_text": "로봇의 중앙 버튼을 클릭하면 멈춰야 합니다.",
      "steps": [
        { "step": "로봇을 작동 상태로 전환", "data": "", "expected_result": "로봇이 작동 중" },
        { "step": "중앙 버튼 클릭", "data": "", "expected_result": "로봇이 정지됨" }
      ],
      "technique": "equivalence_partitioning",
      "platform": "jira"
    }
  ]
}
```

### `PUT /api/v1/projects/{project_id}/testcases/{testcase_id}`
> TestCase 수정 (FR-TC-01-05)

### `DELETE /api/v1/projects/{project_id}/testcases/{testcase_id}`
> TestCase 삭제

### `POST /api/v1/projects/{project_id}/testcases/chat`
> Chat으로 TC 수정 (FR-TC-01-07)

**Request:**
```json
{
  "message": "tc-001에 비상 정지 시나리오를 3개 더 만들어줘",
  "history": [
    { "role": "user", "content": "이전 메시지" },
    { "role": "assistant", "content": "이전 응답" }
  ]
}
```

### `PUT /api/v1/projects/{project_id}/testcases/selection`
> TC 일괄 선택/해제 (FR-TC-01-06)

**Request:**
```json
{
  "testcase_ids": ["tc-001", "tc-002"],
  "is_selected": true
}
```

### `POST /api/v1/projects/{project_id}/testcases/export`
> TC 내보내기 (FR-TC-05)

**Request:**
```json
{
  "testcase_ids": ["tc-001", "tc-002"],
  "format": "jira"
}
```
- `format`: `"jira"` | `"polarion"` | `"excel"` | `"markdown"`

---

## 12. SRS 생성

### `POST /api/v1/projects/{project_id}/srs/generate`
> SRS 문서 생성

**Request:**
```json
{
  "requirement_version": 1
}
```

**Response:**
```json
{
  "srs_id": "srs-001",
  "version": 1,
  "sections": [
    {
      "title": "1. Introduction",
      "content": "..."
    },
    {
      "title": "2. Functional Requirements",
      "content": "..."
    }
  ],
  "source_requirements_version": 1,
  "generated_at": "2026-03-27T11:00:00Z"
}
```

### `GET /api/v1/projects/{project_id}/srs`
> SRS 문서 조회

### `GET /api/v1/projects/{project_id}/srs/{srs_id}`
> SRS 문서 상세 조회

### `POST /api/v1/projects/{project_id}/srs/{srs_id}/review`
> SRS Review 요청 (FR-RQ-08)

**Response:**
```json
{
  "review_id": "rev-001",
  "srs_id": "srs-001",
  "issues": [
    {
      "issue_id": "issue-001",
      "section": "3. Functional Requirements",
      "type": "completeness",
      "severity": "high",
      "description": "로봇 정지 후 재시작 시나리오에 대한 요구사항이 누락되어 있습니다.",
      "suggestion": {
        "text": "시스템은 정지 상태에서 재시작 명령을 받으면 안전 점검 후 동작을 재개해야 한다."
      }
    }
  ],
  "summary": {
    "completeness_score": 75,
    "consistency_score": 90,
    "clarity_score": 85,
    "total_issues": 5,
    "high_severity": 2,
    "medium_severity": 2,
    "low_severity": 1
  }
}
```

### `POST /api/v1/projects/{project_id}/srs/{srs_id}/review/{review_id}/apply`
> SRS Review 수정 제안 수락/거절 (FR-RQ-08-04)

**Request:**
```json
{
  "decisions": [
    { "issue_id": "issue-001", "action": "accept" },
    { "issue_id": "issue-002", "action": "reject" },
    { "issue_id": "issue-003", "action": "modify", "modified_text": "사용자가 직접 수정한 내용" }
  ]
}
```

### `POST /api/v1/projects/{project_id}/srs/{srs_id}/regenerate`
> Review 반영 후 SRS 재생성 (FR-RQ-08-05)

---

## 13. 버전 관리

### `GET /api/v1/projects/{project_id}/versions`
> 전체 버전 이력 조회 (FR-RQ-07-04)

**Query Parameters:**
- `artifact_type`: `"requirements"` | `"usecase_diagram"` | `"usecase_spec"` | `"srs"` | `"testcases"`

**Response:**
```json
{
  "versions": [
    {
      "version": 2,
      "artifact_type": "requirements",
      "created_by": "hong.gildong",
      "created_at": "2026-03-27T11:00:00Z"
    },
    {
      "version": 1,
      "artifact_type": "requirements",
      "created_by": "hong.gildong",
      "created_at": "2026-03-27T09:00:00Z"
    }
  ]
}
```

### `GET /api/v1/projects/{project_id}/versions/{version}/diff`
> 두 버전 비교 (FR-RQ-07-03)

**Query Parameters:**
- `compare_with`: 비교할 버전 번호

### `POST /api/v1/projects/{project_id}/versions/{version}/restore`
> 이전 버전으로 복원 (FR-RQ-07-05)

---

## 14. 설정 (Settings)

### `GET /api/v1/users/settings`
> 사용자 개인 설정 조회

**Response:**
```json
{
  "jira_pat": "***masked***",
  "confluence_pat": "***masked***",
  "notification_enabled": true
}
```

### `PUT /api/v1/users/settings`
> 사용자 개인 설정 수정 (FR-PF-06-04~05)

**Request:**
```json
{
  "jira_pat": "new-pat-token",
  "confluence_pat": "new-confluence-pat"
}
```

### `GET /api/v1/projects/{project_id}/settings`
> 프로젝트 설정 조회

**Response:**
```json
{
  "llm_model": "gpt-4",
  "language": "ko",
  "export_format": "pdf",
  "diagram_tool": "plantuml",
  "polarion_pat": "***masked***"
}
```

### `PUT /api/v1/projects/{project_id}/settings`
> 프로젝트 설정 수정 (FR-PF-06-01~03, FR-PF-06-06)

**Request:**
```json
{
  "llm_model": "gpt-4",
  "language": "ko",
  "export_format": "pdf",
  "diagram_tool": "plantuml"
}
```

---

## 15. 알림 (Notification)

### `GET /api/v1/notifications`
> 알림 목록 조회 (FR-PF-07-04)

**Response:**
```json
{
  "notifications": [
    {
      "notification_id": "noti-001",
      "type": "review_request",
      "message": "홍길동님이 요구사항 Review를 요청했습니다.",
      "project_id": "proj-001",
      "is_read": false,
      "created_at": "2026-03-27T10:00:00Z"
    }
  ],
  "unread_count": 3
}
```

### `PUT /api/v1/notifications/{notification_id}/read`
> 알림 읽음 처리

---

## 공통 에러 응답

모든 API의 에러 응답은 아래 형식을 따릅니다:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "프로젝트를 찾을 수 없습니다.",
    "detail": "project_id: proj-999"
  }
}
```

| HTTP Status | code | 설명 |
|-------------|------|------|
| 400 | `BAD_REQUEST` | 잘못된 요청 |
| 401 | `UNAUTHORIZED` | 인증 실패 (SSO 세션 만료) |
| 403 | `FORBIDDEN` | 권한 없음 |
| 404 | `NOT_FOUND` | 리소스 없음 |
| 422 | `VALIDATION_ERROR` | 입력값 검증 실패 |
| 500 | `INTERNAL_ERROR` | 서버 내부 에러 |
