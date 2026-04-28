# PLAN — 산출물 통합 + Lineage 추적 시스템

> **상태**: ✅ Phase A~G + 후속 #1 #2 완료 (2026-04-28). 후속 #3 의사결정 대기.
> **선행 문서**: DESIGN.md, FRONTEND_DESIGN.md, MIGRATION_PLAN.md §4.1, PROGRESS.md
> **관련 메모리**: `~/.claude/projects/.../memory/followup_workspace_generic.md`

---

## 0. 진행 상황 스냅샷 (2026-04-28)

### 완료
- **Phase A** Frontend Staging 인프라 제네릭화 ✅
- **Phase B** TestCase staging 합류 ✅
- **Phase C** SRS artifact 마이그레이션 + staging ✅
- **Phase D** DESIGN agent + UI 활성화 ✅
- **Phase E** Lineage 컬럼 + 저장 로직 ✅
- **Phase F** Impact API + Stale UI ✅
- **Phase G** Auto-regenerate (impact_svc.apply_regeneration + ImpactPanel) ✅
- **후속 #1** Project soft delete + MinIO `delete_prefix` cleanup ✅
- **후속 #2** record version 히스토리 UI (RecordVersionsModal + DiffViewer 재사용) ✅

### 다음 (의사결정 대기)
- **후속 #3** Stale 알림 / 영향도 모달 UI 재설계 — 사용자 피드백 반영 필요.
  PROGRESS.md `[P1] Stale 알림 ... ` 섹션에 옵션 정리됨.
  권장 조합: (A) 각 artifact 화면 헤더 inline alert + (α) 카드 형태 모달
  본문 + (현재) stale > 0 시에만 노출. 추정 ~150 LOC.

### 추가 후속 (시간 여유 시)
- legacy `srs_documents/srs_sections` drop (안정화 2 release 후)
- 다중 SRS/DESIGN 지원
- branch/fork 모델, conflict resolution UI

---

## 1. 목표

모든 artifact 타입(`record / srs / design / testcase`)이 **동일한 git-like 버전 관리 워크플로우**를 거치도록 통합하고, **레코드 변경 → 산출물 변경**의 인과 관계를 **버전 단위로 추적**할 수 있는 시스템을 구축한다.

### 사용자 요구사항 (원문)

> "프로젝트별로 추출된 레코드를 기반으로 산출물을 생성할 때, 정확히 버전관리가 되어야 하고, 변경점이 관리가 되어야 해. 어떤 레코드를 수정해서, 어떻게 산출물이 변경이 되었는지가 추적이 가능한 구조가 핵심이야."

### 결과적으로 가능해야 하는 시나리오

1. record `REC-003` 편집 → unstaged → stage → PR → merge (모든 타입 동일 흐름)
2. SRS, DESIGN, TC도 동일하게 unstaged → stage → PR → merge
3. SRS v1.3 화면에서 "이 버전은 record A/B/C(각 v2/v1/v3) 기반으로 만들어졌다" 즉시 확인
4. record `REC-003` v2→v3 merge 직후 → 영향받는 SRS §3.2, TC-012/013/017 화면에 **stale 배지** 자동 표시
5. "변경 영향도 보기" 클릭 → 영향받는 산출물 그래프 + 일괄 재생성 옵션

---

## 2. 현재 상태 (조사 결과 종합)

| 영역 | record | srs | design | testcase |
|---|---|---|---|---|
| Artifact 테이블 등록 | ✅ | ❌ (별도 srs_documents 테이블) | ✅ (enum만, row 없음) | ✅ |
| Backend 통합 라우터 사용 | ✅ | ❌ (별도 `PUT /srs/.../sections/{sid}`) | ✅ | ✅ |
| Frontend staging 워크플로우 | ✅ | ❌ | — (placeholder) | ❌ (직접 update) |
| 산출물 생성 agent | (추출 agent) | ✅ `srs_generator` | ❌ 미구현 | ✅ `tc_generator` (추정) |
| based_on 메타데이터 저장 | — | ✅ `SrsDocument.based_on_records` | — | ❌ |

### 4가지 핵심 갭 (사용자 요구사항을 막는 것)

- **G1**: `ArtifactVersion.source_artifact_ids` 컬럼 부재 → 버전별 lineage 미명시
- **G2**: TC ← SRS lineage가 추상적 (`ArtifactDependency`만)
- **G3**: 영향도 조회 API 미구현 (`GET /projects/{id}/impact?changed_ids=...`)
- **G4**: stale 마킹 / 자동 재생성 메커니즘 부재

---

## 3. 7단계 Phase 구성

```
Phase A. Frontend 제네릭화                      [인프라]
  └─ Phase B. TC staging 합류                   [도메인 통합]
  └─ Phase C. SRS 마이그레이션 + staging        [도메인 통합 + 백필]
  └─ Phase D. DESIGN agent + UI 활성화          [도메인 통합]
─────────────────────────────────────────────────
  Phase E. Lineage 컬럼 + agent 저장 로직       [추적성]
  └─ Phase F. Impact API + Stale UI             [영향도]
  └─ Phase G. Auto-regenerate + Critic 도구     [자동화]
```

**의존성**: A → {B, C, D} (병렬 가능) → E → F → G

---

## Phase A — Frontend Staging 인프라 제네릭화

### 목적
`staging-store`와 `ChangesWorkspaceModal`의 record-specific 결합 제거. 새 artifact 타입 추가 전 베이스라인 확보. record만 존재해도 100% 동등 동작.

### 변경 파일

| 파일 | 라인 | 변경 |
|---|---|---|
| `frontend/src/stores/staging-store.ts` | 18-23 | `ArtifactDraft` 인터페이스 — `content: string` → `content: JsonObject`, `originalContent: JsonObject`, `artifactKind: ArtifactKind`, `displayLabel?: string` 추가 |
| `frontend/src/stores/staging-store.ts` | 188 | persist key `aise-staging` → `aise-staging-v2` (기존 stale draft 폐기) |
| `frontend/src/components/artifacts/workspace/StagedChangesTray.tsx` | 290-329 | `DraftRow.content/originalContent`를 호출자 변환 책임으로 위임 (`contentPreview/originalPreview: string` props) |
| `frontend/src/components/artifacts/workspace/ChangesWorkspaceModal.tsx` | 36, 60-67 | record 사전 fetch 제거. drafts의 `displayLabel`로 라벨 결정 |
| `frontend/src/components/artifacts/workspace/ChangesWorkspaceModal.tsx` | 104-134 | `submitPullRequest` 단순화 — `draft.content` 그대로 PATCH (artifact_type별 분기 제거) |
| `frontend/src/components/artifacts/workspace/changePreview.ts` | 신규 | `previewContent(kind, content)` builder map (record/srs/design/testcase 케이스) |
| `frontend/src/components/artifacts/workspace/PullRequestCreateForm.tsx` | 24-28 | `StagedChangeSummary.contentPreview: string` 유지 (호출자가 builder 사용) |
| `frontend/src/components/artifacts/ArtifactRecordsPanel.tsx` | 207-250 | `setArtifactDraft` 호출 시 record 전체 dict 전달 + `displayLabel: record.display_id` |

### DB 마이그레이션
없음.

### 위험 / 완화
- sessionStorage stale draft → persist key bump으로 강제 reset
- amber/blue 테두리 + line-through diff가 객체화로 깨짐 → preview string으로 비교

### 롤백
단일 commit으로 묶어 git revert 1번이면 회복.

### 테스트
- staging-store unit test (새 schema)
- record E2E: 편집 → stage → PR → merge 회귀 통과
- ChangesWorkspaceModal Storybook snapshot

### 추정 LOC: ~150

---

## Phase B — TestCase staging 합류

### 목적
TC 편집 시 staging-store 경유. backend 무변경 (이미 제네릭).

### 변경 파일

| 파일 | 라인 | 변경 |
|---|---|---|
| `frontend/src/components/artifacts/TestCaseArtifact.tsx` | 24, 102-139 | `artifactService.update()` 직접 호출 제거 → `useStagingStore.setDraft()` |
| `frontend/src/components/artifacts/TestCaseArtifact.tsx` | 41-79 | `refreshNonce` 패턴으로 list 갱신 |
| `frontend/src/components/artifacts/TestCaseArtifact.tsx` | 174-318 | unstaged dot indicator + WorkspaceStatusBar mount |
| `frontend/src/stores/artifact-record-store.ts` (선택) | — | 일반화된 `useArtifactRefreshStore<ArtifactKind>` 검토 |

### DB 마이그레이션
없음.

### 위험 / 완화
- TC content shape (steps, priority, type) → previewContent에서 title 한 줄 요약
- 409 (staged 중 편집): record와 동일 한계, 토스트 표시

### 롤백
TC editor만 git revert. 데이터 영향 없음.

### 테스트
- TestCaseArtifact: 편집 → stage → PR → merge → list refresh
- 409 케이스 토스트 표시 확인

### 추정 LOC: ~120

---

## Phase C — SRS artifact 마이그레이션 + staging 합류

### 목적
SRS 데이터를 `srs_documents/srs_sections` → `artifacts + artifact_versions` 로 백필. 별도 라우터 deprecate. 모든 데이터 보존.

### C.1 데이터 모델 결정

**옵션 A 채택**: SRS 문서 전체를 하나의 artifact (`artifact_type='srs'`)로, content payload는 sections 배열.

```json
{
  "sections": [
    {"section_id": "...", "title": "1. 서론", "content": "...", "order_index": 0}
  ],
  "based_on_records": {"artifact_ids": ["uuid1", "uuid2"]},
  "based_on_documents": {"documents": [...]}
}
```

**근거**:
- ARTIFACT_TYPES enum 변경 불필요
- 사용자가 "SRS 1건"을 PR/diff/merge 단위로 인식 (직관적)
- `SrsDocument.version` ↔ `ArtifactVersion.version_number` 1:1 매핑

### C.2 Alembic 마이그레이션 (신규)

**파일**: `backend/alembic/versions/{rev}_backfill_srs_to_artifacts.py`
**템플릿**: `c6e3d4f50607_backfill_records_to_artifacts.py` 참조

**알고리즘**:
1. 멱등성: `SELECT COUNT(*) FROM artifacts WHERE artifact_type='srs'` > 0이면 skip
2. 모든 `srs_documents` (status='completed')을 project_id로 그룹화
3. 프로젝트당 1개의 `Artifact(artifact_type='srs')` row 생성, `display_id='SRS-001'`
4. 각 SrsDocument → ArtifactVersion 1개 (`version_number = SrsDocument.version`, snapshot = sections payload)
5. `current_version_id = max(version_number) ArtifactVersion.id`, `working_status='clean'`
6. **legacy 테이블 drop 금지** (Phase 종료 후 별도 PR)

**downgrade**: `DELETE FROM artifact_versions WHERE artifact_id IN (...) ; DELETE FROM artifacts WHERE artifact_type='srs'`

### C.3 Backend 변경

| 파일 | 라인 | 변경 |
|---|---|---|
| `backend/src/services/srs_svc.py` | 48-167 | `generate_srs`가 Artifact + ArtifactVersion에 INSERT (dual-write 생략, 단방향 전환) |
| `backend/src/services/srs_svc.py` | 26-45 | `_to_response`가 Artifact.content에서 sections 읽도록 변경 |
| `backend/src/services/srs_svc.py` | 170-194 | `list_srs/get_srs`도 artifact 테이블 사용. SrsDocumentResponse 호환 형태로 변환 |
| `backend/src/services/srs_svc.py` | 197-232 | `update_srs_section` **삭제** — `artifact_svc.update_working_copy`로 대체 |
| `backend/src/routers/srs.py` | 48-57 | `PUT /{srs_id}/sections/{section_id}` **제거** |
| `backend/src/routers/srs.py` | 22-46 | `generate/list/get/regenerate` 호환 유지 (frontend 일부가 호출) |
| `backend/src/agents/srs_generator.py` | 62-89 | 응답 dict 시그니처 유지. `srs_id`는 `Artifact.id`로 의미 변경 |
| `backend/src/services/testcase_svc.py` | 96-216 | `SrsDocument` join 제거 → Artifact + ArtifactVersion에서 sections 추출. **TC 생성 입력은 SRS clean version만** (dirty/staged 제외) |

### C.4 Frontend 변경

| 파일 | 라인 | 변경 |
|---|---|---|
| `frontend/src/components/artifacts/SrsArtifact.tsx` | 25, 145-179 | `srsService.updateSection()` 제거 → staging-store setDraft. content는 sections 전체 snapshot |
| `frontend/src/components/artifacts/SrsArtifact.tsx` | 87-179 | unstaged dot + WorkspaceStatusBar mount |
| `frontend/src/components/artifacts/SrsArtifact.tsx` | 233-276 | version selector → ArtifactVersion 목록 (`artifactService.listVersions()`) |
| `frontend/src/services/srs-service.ts` | 18-19 | `updateSection` 메서드 제거 |

### 데이터 보존 보장 (CRITICAL)

1. **백업 권고**: 운영 DB `pg_dump` 후 마이그레이션 (PROGRESS.md에 명시)
2. **Dry-run 스크립트**: `backend/scripts/srs_backfill_dryrun.py` (신규) — INSERT 없이 변환 결과만 로깅
3. **트랜잭션**: project 단위 savepoint
4. legacy `srs_documents/srs_sections` **drop 금지** (호환 기간 유지)

### 위험 / 완화

| 위험 | 완화 |
|---|---|
| `SrsDocument.content`(합본) vs `SrsSection.content`(섹션별) sync 불일치 | SrsSection을 source of truth로 백필 (실 편집 대상이었음) |
| `testcase_svc.py` SrsDocument 의존 | 동일 PR에서 함께 변경 + integration test |
| `srs_id` 의미 변화 (SrsDocument.id → Artifact.id) | UUID 호환, frontend 영향 없음 확인 |
| `ck_artifacts_clean_requires_version` CHECK 위반 | `c6e3d4f50607` 의 INSERT-then-UPDATE 2-step 패턴 차용 |
| version 체인 parent_version_id | v1.parent=NULL, v2.parent=v1.id 순차 채번 |

### 롤백
- DB: `alembic downgrade` (legacy 테이블 보존되므로 즉시 복원)
- Code: git revert. **단, 마이그레이션 후 신규 SRS는 legacy table에 없음** → revert 시 사라진 것처럼 보임. **운영 cutover 전 staging 충분 검증 필수**

### 테스트
- Backend: `tests/test_srs_generator_agent.py` 보강, artifact_svc srs 시나리오 추가
- Migration: srs_documents fixture가 있는 테스트 DB upgrade 후 data parity 검증
- Frontend: SRS 편집 → tray 표시 → PR → merge → version selector에 새 version 등장

### 추정 LOC: ~500 (마이그레이션 + 양쪽 변경)

---

## Phase D — DESIGN agent + UI 활성화

### 목적
backend는 이미 artifact 통합되어 있음. **Agent 구현 + Frontend UI**만 추가.

### 변경 파일

| 파일 | 라인 | 변경 |
|---|---|---|
| `backend/src/agents/design_generator.py` | 신규 | `srs_generator.py`를 템플릿으로 — SRS 섹션 입력 → 설계 산출물 생성. content payload는 sections 또는 markdown |
| `backend/src/services/design_svc.py` | 신규 | `generate_design()`, `list/get` (SRS와 동일 패턴, 단 artifact 테이블 사용) |
| `backend/src/routers/artifact.py` 또는 신규 | — | `POST /api/v1/projects/{pid}/design/generate` (SRS와 대칭) |
| `backend/src/prompts/design/generator.md` | 신규 | LLM 프롬프트 (SRS 프롬프트 패턴) |
| `frontend/src/components/artifacts/DesignArtifact.tsx` | 1-17 (placeholder 교체) | SrsArtifact 패턴 — list/edit/staging-store 통합 |
| `frontend/src/services/design-service.ts` | 신규 | `list/get/generate/regenerate` (srs-service 패턴) |

### DB 마이그레이션
없음 (artifact_type='design' 이미 enum 등록됨).

### 위험 / 완화
- design content payload schema 미정 → SRS와 동일하게 sections 배열로 통일
- agent 프롬프트 품질 → SRS와 동일 단계의 LLM 호출, 후속 튜닝 영역

### 롤백
신규 파일이 대부분 → 파일 삭제 + DesignArtifact 원복.

### 테스트
- agent unit test (mock LLM)
- DesignArtifact: 생성 → 편집 → stage → PR → merge

### 추정 LOC: ~400

---

## Phase E — Lineage 컬럼 + 저장 로직 (G1, G2 해결)

### 목적
`ArtifactVersion`에 **버전별 source_artifact_ids** 컬럼 추가. 모든 산출물 생성 agent가 입력 artifact IDs를 기록.

### E.1 DB 마이그레이션 (신규)

**파일**: `backend/alembic/versions/{rev}_add_artifact_version_lineage.py`

```python
op.add_column(
    'artifact_versions',
    sa.Column('source_artifact_versions', sa.JSON, nullable=True),
)
op.create_index('ix_artifact_versions_source', 'artifact_versions',
                ['source_artifact_versions'], postgresql_using='gin')
```

**컬럼 schema**:
```json
{
  "record": [{"artifact_id": "uuid", "version_number": 3}],
  "srs": [{"artifact_id": "uuid", "version_number": 1, "section_id": "..."}],
  "design": [...]
}
```

> **중요**: `version_number`까지 포함. "어떤 버전의 record를 입력으로 썼는지" 명시 → record가 v3→v4가 되면 SRS의 source가 outdated 판정 가능.

### E.2 백필

기존 ArtifactVersion에 대한 best-effort 백필:
- SRS Artifact의 ArtifactVersion → `based_on_records`(srs_svc 또는 SrsDocument 메타)에서 record artifact IDs 읽어 변환. version_number는 머지 시점 기준 current_version_id 추정 (정확도 한계 있음)
- TC: SrsDocument 입력이 명시되어 있으면 그것을 source로
- 백필 실패 케이스는 `null` 허용

### E.3 Agent/Service 변경

| 파일 | 변경 |
|---|---|
| `backend/src/services/artifact_svc.py` `create_pr` (L370-445) | `source_artifact_versions` 인자 받아 ArtifactVersion 생성 시 함께 INSERT |
| `backend/src/services/srs_svc.py` `generate_srs` | input record_ids → 각 record의 current_version_id 조회 후 lineage payload 구성 |
| `backend/src/services/testcase_svc.py` `generate_testcases` | input SRS sections → SRS artifact의 current_version_id + section_ids 기록 |
| `backend/src/agents/design_generator.py` (Phase D 신규) | SRS sections 입력 → 동일 패턴 |

### E.4 Frontend 노출

| 파일 | 변경 |
|---|---|
| `frontend/src/components/artifacts/SrsArtifact.tsx` (version selector) | 각 version에 "based on REC-003 v2, REC-005 v1, ..." 표시 |
| 동일 패턴: DesignArtifact, TestCaseArtifact | 각 version 선택 시 source 명시 |
| `frontend/src/services/artifact-service.ts` | `listVersions` 응답에 `source_artifact_versions` 포함 |

### DB 마이그레이션
컬럼 추가 1건 + 백필 데이터 마이그레이션 1건 (분리 권장).

### 위험 / 완화
- 백필 정확도 한계 → null 허용, 향후 인스턴스부터 정확
- 컬럼 nullable → 기존 코드 영향 최소

### 롤백
컬럼 drop 가능 (기능 단순 추가).

### 테스트
- SRS 생성 시 source_artifact_versions가 올바른 record version으로 채워지는지
- TC 생성 시 SRS section_id까지 기록되는지

### 추정 LOC: ~300

---

## Phase F — Impact API + Stale UI (G3, G4 해결)

### 목적
영향도 그래프 트래버스 + Frontend stale 마킹.

### F.1 Backend Impact API

**신규 엔드포인트**: `GET /api/v1/projects/{pid}/impact?changed_artifact_ids=uuid1,uuid2`

응답:
```json
{
  "downstream": [
    {
      "artifact_id": "srs-uuid",
      "artifact_type": "srs",
      "display_id": "SRS-001",
      "stale_reason": [
        {"source_artifact_id": "rec-uuid1", "current_version": 4, "referenced_version": 3}
      ],
      "stale_sections": ["section-3-2-uuid"]
    },
    {"artifact_id": "tc-uuid", "artifact_type": "testcase", ...}
  ]
}
```

**알고리즘**:
1. changed_artifact_ids 각각의 current_version_id 조회
2. ArtifactVersion 전체에서 `source_artifact_versions` JSONB 안에 `artifact_id` 매칭 + `version_number < current_version`인 row 검색
3. 그 row가 속한 Artifact가 영향받는 downstream
4. 재귀로 2차 downstream까지 (record→SRS→TC)

| 파일 | 변경 |
|---|---|
| `backend/src/services/impact_svc.py` | 신규 |
| `backend/src/routers/artifact.py` | `GET .../impact` 추가 |
| `backend/src/schemas/impact.py` | 신규 (response 모델) |

### F.2 Frontend Stale 마킹

| 파일 | 변경 |
|---|---|
| `frontend/src/services/impact-service.ts` | 신규 — getImpact 호출 |
| `frontend/src/hooks/useImpact.ts` | 신규 — 프로젝트 단위 polling 또는 SSE 트리거 |
| `frontend/src/components/artifacts/SrsArtifact.tsx` | stale section 헤더에 노란 배지 + 툴팁 ("REC-003 v3 → v4 변경됨") |
| `frontend/src/components/artifacts/TestCaseArtifact.tsx` | TC row에 stale 배지 |
| `frontend/src/components/artifacts/DesignArtifact.tsx` | 동일 |

### F.3 SSE 통합 (선택)

`backend/src/services/artifact_svc.py:merge_pr` 후 ChangeEvent 발행 + `impact_summary` 미리 계산해 JSONB 저장 → 프론트에 SSE event `artifact_impact_updated` 발행.

| 파일 | 변경 |
|---|---|
| `backend/src/schemas/events.py` | `ArtifactImpactUpdated` event 추가 |
| `frontend/src/types/agent-events.ts` | 1:1 동기화 |

### DB 마이그레이션
ChangeEvent에 `impact_summary`는 이미 컬럼 있음 — 활용만 하면 됨.

### 위험 / 완화
- 그래프 트래버스 비용 (대형 프로젝트) → ChangeEvent에 미리 계산해 캐싱
- stale 배지 spam → 사용자 dismissable

### 롤백
신규 API/UI라 단순 disable 가능.

### 테스트
- impact_svc unit test (그래프 시나리오)
- E2E: REC 편집/머지 → SRS/TC 화면 stale 표시

### 추정 LOC: ~400

---

## Phase G — Auto-regenerate + Critic 도구 (Phase 4 완성)

### 목적
영향받는 산출물을 일괄 재생성하는 사용자 흐름. Critic agent 도입.

### 변경 파일

| 파일 | 변경 |
|---|---|
| `backend/src/agents/critic.py` | 신규 또는 보강 — `calculate_impact` 도구, `regenerate_stale` 도구 |
| `backend/src/routers/artifact.py` | `POST /projects/{pid}/impact/apply` (선택된 stale artifact 일괄 재생성) |
| `frontend/src/components/artifacts/ImpactPanel.tsx` | 신규 — 영향받는 항목 리스트 + 일괄 선택 UI |
| `frontend/src/components/layout/RightPanel.tsx` (또는 적절한 위치) | ImpactPanel 토글 |

### DB 마이그레이션
없음 (앞 단계 인프라 활용).

### 위험 / 완화
- 자동 재생성 → 사용자 의도와 어긋날 위험 → 항상 PR 생성 후 사용자 승인 (auto-merge 금지)
- LLM 비용 폭증 → 일괄 처리 시 명시적 cost 표시

### 롤백
ImpactPanel만 hide. backend 단순 disable.

### 테스트
- E2E: REC 머지 → ImpactPanel 표시 → 일괄 재생성 → 각 산출물 PR 생성

### 추정 LOC: ~500

---

## 4. 누적 추정

| Phase | LOC | DB 마이그레이션 |
|---|---|---|
| A. Frontend 제네릭화 | 150 | - |
| B. TC staging | 120 | - |
| C. SRS 마이그레이션 | 500 | 1건 (백필) |
| D. DESIGN agent + UI | 400 | - |
| E. Lineage 컬럼 | 300 | 2건 (컬럼 + 백필) |
| F. Impact API + Stale UI | 400 | - |
| G. Auto-regenerate | 500 | - |
| **합계** | **~2,370 LOC** | **3건** |

> **메모리 추정 (~800 LOC)은 A~C 범위만 본 수치**. Lineage/Impact 작업이 추가되어 약 3배 증가.

---

## 5. 의존성/순서 매트릭스

```
Phase A (인프라)
  ├─► Phase B (TC staging) ──┐
  ├─► Phase C (SRS 마이그레이션) ──┤
  └─► Phase D (DESIGN agent) ──┘
                              ↓
                        Phase E (Lineage 컬럼)
                              ↓
                        Phase F (Impact API + Stale UI)
                              ↓
                        Phase G (Auto-regenerate)
```

- B, C, D는 A 완료 후 **병렬 진행 가능**
- E는 B/C/D 완료 후 시작 (모든 artifact 타입의 agent가 lineage 기록 가능해야 함)
- F는 E 완료 후 (lineage 데이터 없이 impact 계산 부정확)
- G는 F 완료 후 (impact 데이터를 기반으로 재생성)

---

## 6. 단계별 PR 전략

각 Phase = 별도 PR 권장. C와 E는 마이그레이션 포함 → 더 작게 분리:

- **PR-A**: Frontend 인프라 제네릭화
- **PR-B**: TC staging 합류
- **PR-C1**: SRS 마이그레이션 (backend, alembic + dry-run script)
- **PR-C2**: SRS staging 통합 (frontend)
- **PR-D**: DESIGN agent + UI
- **PR-E1**: Lineage 컬럼 추가 (alembic, nullable)
- **PR-E2**: Agent/Service에 lineage 저장 로직
- **PR-E3**: Frontend version selector에 lineage 표시
- **PR-F1**: Backend Impact API
- **PR-F2**: Frontend Stale UI
- **PR-G**: Auto-regenerate + Critic

총 **11개 PR**. 평균 200~400 LOC.

---

## 7. 핵심 위험 종합

| 위험 | Phase | 완화 |
|---|---|---|
| sessionStorage stale draft schema mismatch | A | persist key v2 bump |
| SRS 마이그레이션 데이터 손실 | C | dry-run + pg_dump + legacy 테이블 보존 |
| testcase_svc가 SrsDocument 의존 | C | 동일 PR에서 함께 변경 + integration test |
| Lineage 백필 정확도 한계 | E | nullable, 향후 인스턴스부터 정확 |
| Impact 그래프 트래버스 비용 | F | ChangeEvent.impact_summary 캐싱 |
| Auto-regenerate 의도 어긋남 | G | 항상 PR 생성, auto-merge 금지 |
| LLM 비용 폭증 | G | 일괄 처리 cost 명시 |
| SSE 이벤트 계약 변경 | F | backend/frontend 동시 배포 |

---

## 8. 테스트 우선순위

| 시나리오 | Phase | 우선순위 |
|---|---|---|
| record E2E 회귀 (편집/PR/merge) | A | 최우선 |
| staging-store JsonObject schema unit | A | 최우선 |
| SRS 마이그레이션 dry-run + parity | C | 최우선 |
| TC 생성이 SRS clean version만 입력으로 사용 | C | 높음 |
| Lineage 저장: SRS v 생성 시 input record version 기록 | E | 높음 |
| Impact API: REC 변경 → 영향받는 SRS/TC 정확 식별 | F | 최우선 |
| Stale UI 표시 회귀 | F | 높음 |
| 일괄 재생성 → PR 11개 동시 생성 케이스 | G | 중간 |

---

## 9. 후속 (이 plan 범위 외)

- legacy `srs_documents/srs_sections` drop (Phase C 완료 + 안정화 2 release 후)
- 다중 SRS/DESIGN 지원 (현재는 프로젝트당 1개 가정)
- branch/fork 모델 (현재는 main 단일 trunk)
- conflict resolution UI (동시 편집 케이스)
- **Stale 알림 / 영향도 모달 UI 재검토** — Phase G 1차 구현은 탭바 우측 amber
  버튼 + ImpactPanel 모달(체크박스 리스트). 사용자 피드백: 위치/모양 재설계 필요.
  검토 방향:
  1. 위치 — 탭바 우측 외 후보: 우측 사이드바 상단 알림 영역, 화면 하단 sticky banner,
     또는 각 artifact 화면의 헤더 안 inline alert
  2. 모달 본문 — 체크박스 리스트 대신 카드/타임라인/그래프 시각화 검토
  3. 진입점 빈도 — 항상 보이게 vs stale > 0 일 때만 vs 사용자가 명시적으로 토글
- **record version 히스토리 UI** — 백엔드는 `Artifact(record)` + 다수 `ArtifactVersion`
  로 모든 머지 버전을 보존 중이고 `GET .../artifacts/{id}/versions` API 도 존재
  하나, ArtifactRecordsPanel 에 version selector / history 모달이 미구현.
  SRS/Design 화면과 동일한 패턴(version selector + diff)으로 추가 필요.
- **프로젝트 soft delete + 삭제 영향 미리보기 + MinIO 파일 정리** — 현재
  `DELETE /api/v1/projects/{id}` 는 hard delete 이며 모든 FK 가 CASCADE 로 묶여
  있어 16+ 테이블의 데이터(지식 문서, 세션 대화 기록, 모든 산출물 버전 히스토리,
  lineage, 감사 로그 등)가 즉시 영구 삭제됨. 개발 단계에서는 의도된 동작이나
  운영 전 다음을 도입 필요:
  1. **Project soft delete** — `Project.lifecycle_status` 컬럼 추가 (Artifact 와 동일
     패턴: `active`/`archived`/`deleted`), 삭제 시 status 만 `deleted` 로 변경.
     30 일 후 별도 cron 으로 hard delete (휴지통 패턴).
  2. **삭제 확인 모달에 영향 미리보기** — `GET /projects/{id}/delete-preview` 신규
     API 가 `{records: N, knowledge_docs: M, sessions: K, srs_versions: L, files_mb: F}`
     반환. ProjectOverviewTab 의 삭제 버튼이 모달로 카운트 표시 후 type-to-confirm.
  3. **휴지통 UI** — 좌측 사이드바 또는 설정에 "삭제된 프로젝트" 섹션, 복원 버튼.
  4. **MinIO 파일 cleanup (CRITICAL)** — 현재 `project_svc.delete_project` 가 DB
     CASCADE 만 의존하고 MinIO 객체는 정리하지 않아 **orphan 파일이 영구 잔존** 한다
     (`storage_key = {project_id}/{document_id}/{filename}` prefix 의 모든 객체).
     Hard delete 단계에서:
     - 프로젝트 단위 prefix 일괄 삭제: `storage_svc.delete_prefix("{project_id}/")`
       헬퍼 신규 (boto3 `list_objects_v2 + delete_objects` 페이지네이션)
     - 또는 트랜잭션 시작 전 `knowledge_documents` 의 모든 `storage_key` 수집 →
       삭제 후 best-effort 정리 (실패 시 nightly cron 으로 orphan 스캔/회수)
     - `knowledge_svc.delete_document` (개별 삭제) 는 이미 MinIO cleanup 정상 동작 — 같은 헬퍼 재사용.
  5. 추정 규모: backend ~350 LOC (마이그레이션 + service 분기 + cron + MinIO 정리),
     frontend ~200 LOC (preview 모달 + 휴지통 화면).

---

## 10. 승인 후 진행 방식

1. 사용자 승인 → 본 PLAN을 PROGRESS.md에 정식 등록 (Phase 4 세분화)
2. **Phase A부터 PR 단위로 순차 진행**. 각 PR 완료 시 사용자 확인
3. C/D 시점에 운영 DB 백업 절차 사전 합의
4. F/G 진입 전 Phase 3 (HITL)와의 통합 영향 재검토

---

## 부록: 핵심 참조 파일

- `backend/src/models/artifact.py` (L34, L97, L137-183, L240-278, L281-326)
- `backend/src/services/artifact_svc.py` (L57-62, L293, L328-364, L370-445, L517-558)
- `backend/src/services/srs_svc.py` (전체)
- `backend/src/services/testcase_svc.py` (L96-216)
- `backend/src/agents/srs_generator.py` (L62-89)
- `backend/alembic/versions/c6e3d4f50607_backfill_records_to_artifacts.py` (마이그레이션 템플릿)
- `frontend/src/stores/staging-store.ts` (전체)
- `frontend/src/components/artifacts/workspace/ChangesWorkspaceModal.tsx` (L36-134)
- `frontend/src/components/artifacts/{SrsArtifact,TestCaseArtifact,DesignArtifact}.tsx`
- `frontend/src/types/agent-events.ts` (L83-202)
