# assist-reference (DEPRECATED snapshot)

프로토타입 Phase 1의 "요구사항 정제/보완/대화형 추출" 자산을 본 저장소에서
제거하기 전, 참고용으로 보존하는 디렉토리.

## 결정 배경

- MIGRATION_PLAN §5 **D3 = 제거**. 사유: 장기 유지보수 시 레거시 경로와
  신규 Agent Chat 경로가 공존하면 어떤 코드가 "정답"인지 혼선.
- 단, 프롬프트·구조화 JSON 파싱·사용자 대화 흐름은 **Phase 2 Requirement
  Agent 설계에 참고 가치**가 있으므로 스냅샷으로 유지.

## 포함 파일

| 경로 | 원본 위치 | 용도 |
|---|---|---|
| `backend/routers/assist.py` | `backend/src/routers/assist.py` | `POST /api/v1/projects/{id}/assist/{refine|suggest|chat}` |
| `backend/services/assist_svc.py` | `backend/src/services/assist_svc.py` | refine/suggest/chat 오케스트레이션 |
| `backend/schemas/assist.py` | `backend/src/schemas/api/assist.py` | AssistRequest/Response/ExtractedRequirement |
| `backend/prompts/assist/*` | `backend/src/prompts/assist/*` | refine.py / suggest.py / chat.py 시스템 프롬프트 |
| `backend/tests/test_assist.py` | `backend/tests/test_assist.py` | pytest 케이스 (monkeypatched LLM) |
| `frontend/services/assist-service.ts` | `frontend/src/services/assist-service.ts` | 프론트 assist API 래퍼 |

## 제거 일정

**Phase 2 말** — Requirement Agent(신규)가 다음을 완전히 대체한 뒤 제거:
- `assist.refine` → `RequirementAgent.refine()` 스킬
- `assist.suggest` → `RequirementAgent.suggest_extensions()` 스킬
- `assist.chat` → Supervisor routing → `RequirementAgent`

제거 대상 파일 (MIGRATION_PLAN §1.1-D · §2.3 완료 기준):
- `backend/src/routers/assist.py`
- `backend/src/services/assist_svc.py`
- `backend/src/schemas/api/assist.py`
- `backend/src/prompts/assist/` 전체
- `backend/tests/test_assist.py`
- `frontend/src/services/assist-service.ts`
- 프론트 호출부 3곳도 교체:
  - `frontend/src/components/artifacts/RequirementsArtifact.tsx`
  - `frontend/src/components/requirements/ChatPanel.tsx`
  - `frontend/src/app/(main)/projects/[id]/requirements/page.tsx`
- `backend/src/main.py` / `routers/__init__.py`의 `assist_router` 등록 해제

## 규칙

- **수정 금지**. 이 디렉토리는 스냅샷이다.
- 현재 활성 assist_* 코드를 고치다가 혼란스러우면 이 스냅샷과 비교.
- Phase 2 말 제거 PR에서 "재현 가치가 있는 프롬프트/파서"는 Requirement
  Agent 모듈 주석으로 인용하고, 이 디렉토리는 그대로 둔다.
