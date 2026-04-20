---
title: AISE 1.0 코드베이스 분석
date: 2026-03-25
source: ref_aise1.0/doc_gen/
tags: [aise1, codebase, architecture, langgraph]
---

# AISE 1.0 코드베이스 분석

## 기술 스택

| 항목 | 기술 |
|------|------|
| Framework | FastAPI 0.111 |
| Server | Gunicorn + Uvicorn workers |
| LLM Orchestration | LangGraph 1.0.4, LangChain 1.1.0 |
| LLM Provider | Azure OpenAI (GPT-4, GPT-4o) |
| 문서 처리 | pdfplumber, MinIO |
| 연동 | JIRA, Polarion |
| 모니터링 | Langfuse 3.3.5 |
| Python | 3.11 |
| Package Manager | UV |

## 아키텍처 패턴

### LangGraph 워크플로우
- `graph/base.py` — BaseGraphManager 추상 클래스
- `graph/workflows/` — SRS, TestCase, ATL 워크플로우
- `graph/nodes/` — 그래프 노드 (처리 단위)
- `graph/states/` — Pydantic 상태 스키마

### 서비스 레이어
- `services/graph_svc.py` — 그래프 실행 오케스트레이션
- `services/llm_svc.py` — Azure OpenAI 설정 + 프롬프트 관리
- `services/jira_svc.py` — JIRA REST API 연동 (3,380+ lines)
- `services/document_processor_svc.py` — PDF 처리 + MinIO

### API 엔드포인트
- `POST /api/v1/srs` — SRS 생성
- `POST /api/v1/testcase` — 테스트 케이스 생성
- `POST /api/v1/atl/initiative|epic|story` — ATL 생성
- JIRA/Polarion 연동 엔드포인트

### 에러 처리
- 커스텀 예외 계층 (AiseGraphBaseException)
- 에러 코드 정의 (error_codes.py)

### 모니터링
- Langfuse 2단계 폴백: 서비스 불가 시 자동 폴백 → 수동 비활성화

## One-shot 방식의 한계 (AISE 2.0에서 개선할 점)
- 요구사항 입력 → SRS 즉시 생성 (검토 과정 없음)
- 요구사항 품질 검증 없이 생성 시작
- 사용자 피드백 루프 부재
- 프로젝트 단위 관리 없음 (단건 생성)

## AISE 2.0에서 재활용 가능한 부분
- FastAPI 보일러플레이트 패턴 (이미 적용됨)
- Loguru 로깅 설정 (이미 적용됨)
- 프롬프트 관리 구조 (`prompts/` 디렉토리)
- 예외 처리 패턴
