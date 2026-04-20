---
title: AUTOSAD.ai 플랫폼 분석
date: 2026-03-25
source: https://app.autosad.ai/documentation#getting-started
tags: [autosad, srs, architecture, reference-platform]
---

# AUTOSAD.ai 분석 결과

## 개요

AUTOSAD (Automated Software Architecture & Design)는 자연어 요구사항을 시스템 아키텍처 문서, UML 다이어그램, 코드까지 변환하는 AI 플랫폼. "Plan It Before You Build It" 철학.

## 4단계 워크플로우

1. **Requirements Engineering** — 자연어/BRD 업로드/회의록으로 FR/NFR 입력. NFR 자동 생성 지원.
2. **System Models** — 6가지 다이어그램 자동 생성 (Use Case, C4, Sequence, Data Model, Component, Deployment)
3. **AI-Augmented Software Engineering** — 아키텍처 기반 코드 생성
4. **Live Application** — CI/CD 파이프라인 포함 배포

## One-shot이 아닌 이유 (핵심 차별점)

### A. 연동된 산출물 (Living Documents)
- 요구사항 변경 시 하위 다이어그램/문서 자동 연쇄 업데이트
- 정적 문서가 아닌 지속적으로 진화하는 산출물

### B. Architecture Review Board (ARB) 라우팅
- 생성 → ARB 리뷰 → 피드백 → 수정 → 재승인 사이클
- Corporate/Enterprise 티어에서 제공

### C. 협업 편집 및 리뷰
- 역할 기반 접근 제어 (RBAC)
- 다이어그램/문서 인라인 댓글
- 변경 추적 포함 버전 관리

### D. DiagramsGPT (맥락 인식 대화형 프롬프팅)
- 같은 자연어 프롬프트가 현재 뷰에 따라 다르게 동작
  - 요구사항 뷰에서 "로그인" → 요구사항 생성
  - 유스케이스 뷰에서 "로그인" → 유스케이스 생성
  - 배포 뷰에서 "로그인" → 인프라 생성

### E. 산출물별 생성→검토→편집→저장 루프
- 각 다이어그램: AI 생성 → 사용자 리뷰 → 편집(PlantUML/DrawIO/Excalidraw) → 저장

### F. 거버넌스 및 표준 가이드
- 조직 표준을 설정하면 생성물이 표준에 맞는지 자동 검증

## 기술 특징

| 기능 | 상세 |
|------|------|
| 입력 방식 | 자연어, BRD 업로드, 회의록 전사 |
| 다이어그램 에디터 | PlantUML, DrawIO, Excalidraw 내장 |
| 출력 형식 | PDF, Word, HTML, PNG, SVG |
| 아키텍처 스타일 | 마이크로서비스/모놀리식/Pub-Sub 원클릭 전환 |
| 멀티 클라우드 | AWS, Azure, GCP, 온프레미스 |
| Private LLM | 온프레미스/고객 클라우드 배포 (데이터 주권) |

## 가격 티어

- **Diagrams As Code** ($5-7/mo): 수동 다이어그램만
- **Individual** ($14-20/mo): 전체 자동 생성 + PDF/Word 내보내기
- **Corporate** ($34-49/mo): + 비즈니스 룰 엔진, 거버넌스, 감사
- **Enterprise** (커스텀): API 연동, 온프레미스, Private LLM

## AISE 2.0 MVP 적용 포인트

| AUTOSAD 기능 | MVP 적용 | 우선순위 |
|-------------|---------|---------|
| FR/NFR 입력 + 자동 생성 | AI 어시스트 (보완/제안) | Must |
| 표준 템플릿 기반 문서 생성 | IEEE 830 SRS 생성 | Must |
| 생성→검토→편집 루프 | 생성 전 품질 체크 | Should |
| Living Documents | 요구사항 수정 시 SRS 재생성 | Won't (v2.1) |
| ARB 라우팅/협업 | 미적용 | Won't (v2.1) |
| DiagramsGPT | 미적용 | Won't (v2.1) |
