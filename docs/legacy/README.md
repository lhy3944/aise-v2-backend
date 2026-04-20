# docs/legacy/

프로토타입 저장소 [lhy3944/aise-v2](https://github.com/lhy3944/aise-v2)의 **읽기 전용** 참고 문서.

본 저장소(`aise-v2-backend`)의 활성 문서는 루트의 `DESIGN.md` / `FRONTEND_DESIGN.md` / `ANALYSIS.md` / `MIGRATION_PLAN.md` / `PROGRESS.md` / `CLAUDE.md` 이며, 이 디렉토리는 **이관 기준 시점의 프로토타입 상태를 보존**한다.

## 파일

| 파일 | 원본 | 용도 |
|---|---|---|
| `CLAUDE.md` | `aise-v2/CLAUDE.md` | 프로토타입용 Claude 가이드 (aise 2.0 팀 규칙) |
| `AGENTS.md` | `aise-v2/AGENTS.md` | CLAUDE.md와 거의 동일(중복) |
| `PLAN.md` | `aise-v2/PLAN.md` | 프로토타입 Phase 1~7 작업 계획 |
| `PROGRESS.md` | `aise-v2/PROGRESS.md` | 프로토타입 진행 로그 (~2026-04-18) |
| `REFECTORING.md` | `aise-v2/REFECTORING.md` | ⭐ 본 프로젝트의 직접 선행 리팩토링 로드맵 (Harness Engineering). `MIGRATION_PLAN.md §0.2`에서 DESIGN.md 용어로 매핑 |
| `prototype-docs/` | `aise-v2/docs/` | 요구사항 정의서 (FR-PF/FR-RQ/FR-TC), 인터페이스 명세, 아키텍처, 리뷰 |

## 규칙

- **수정 금지**. 변경이 필요한 내용은 루트의 활성 문서에 반영.
- 새 세션이 기존 맥락을 참조할 때 읽기 전용 소스로 활용.
- 이관 당시 프로토타입은 Phase 1~4 대부분 구현 완료, 93 passed / 3 skipped 상태.
