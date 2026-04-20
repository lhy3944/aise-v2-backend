---
title: "LangChain Deep Agents 조사"
date: 2026-03-27
source:
  - https://blog.langchain.com/deep-agents/
  - https://docs.langchain.com/oss/python/deepagents/overview
  - https://github.com/langchain-ai/deepagents
  - https://changelog.langchain.com/announcements/deep-agents-v0-4
  - https://blog.langchain.com/doubling-down-on-deepagents/
  - https://blog.langchain.com/improving-deep-agents-with-harness-engineering/
  - https://deepwiki.com/langchain-ai/deepagents
  - https://pypi.org/project/deepagents/
  - https://www.datacamp.com/tutorial/deep-agents
tags: [langchain, deep-agents, langgraph, agent-framework, ai-agent]
---

# LangChain Deep Agents 조사

## 1. Deep Agents란 무엇인가? (개요, 목적)

### 정의

Deep Agents는 LangChain이 2025년 7월에 공개한 오픈소스 "에이전트 하네스(agent harness)"이다. LangChain과 LangGraph 위에 구축되었으며, 복잡하고 장시간 실행되는 멀티스텝 작업을 수행할 수 있는 자율적 AI 에이전트를 쉽게 만들 수 있도록 설계되었다.

### 탄생 배경

기존 LLM 에이전트는 단순한 도구 호출 루프(tool-calling loop)로 동작하여, 짧은 작업에는 잘 동작하지만 멀티스텝, 상태 유지, 산출물 기반 작업에서는 한계를 보였다. LangChain CEO Harrison Chase가 Claude Code, OpenAI Deep Research, Manus 같은 성공적인 에이전트 시스템들의 공통 패턴을 분석하여, 이를 누구나 사용할 수 있는 오픈소스 프레임워크로 만든 것이 Deep Agents이다.

### 핵심 목적

- **"Shallow Agent"의 한계 극복**: 단순 루프 에이전트가 실패하는 복잡한 계획, 장기 실행, 컨텍스트 관리 문제를 해결
- **배터리 포함(Batteries-included)**: 프롬프트, 도구, 컨텍스트 관리를 직접 배선할 필요 없이 즉시 동작하는 에이전트 제공
- **수직 도메인 커스터마이징**: 각 도메인(리서치, 코딩, 분석 등)에 맞는 Deep Agent를 쉽게 구축

### 현재 상태

- **최신 안정 버전**: 0.4.12 (2026년 3월 20일)
- **프리릴리스**: 0.5.0a2 (2026년 3월 23일)
- **GitHub 스타**: 9,900+ (2026년 3월 업데이트 후 5시간 만에 달성)
- **라이선스**: MIT
- **Python 지원**: 3.11 ~ 3.14
- **개발 상태**: Beta

---

## 2. LangChain/LangGraph와의 관계

### 3계층 구조

Deep Agents는 LangChain 생태계 내에서 다음과 같은 3계층 구조로 위치한다:

```
┌──────────────────────────┐
│     Deep Agents          │  ← 에이전트 하네스 (계획, 파일시스템, 서브에이전트)
├──────────────────────────┤
│     LangChain            │  ← 에이전트 프레임워크 (모델, 도구, 체인)
├──────────────────────────┤
│     LangGraph            │  ← 런타임 엔진 (상태 관리, 스트리밍, 체크포인트)
└──────────────────────────┘
```

### 관계 정리

| 구분 | LangChain | LangGraph | Deep Agents |
|------|-----------|-----------|-------------|
| 역할 | 에이전트 프레임워크 | 런타임/오케스트레이션 | 에이전트 하네스 |
| 추상화 수준 | 낮음 (기본 빌딩 블록) | 중간 (상태 그래프) | 높음 (완성형 에이전트) |
| 사용 시점 | 기본 도구 호출 에이전트 | 커스텀 워크플로우 | 복잡한 자율 에이전트 |
| 비유 | 부품 | 엔진 | 완성차 |

- **LangChain**: 모델 통합, 도구 정의, 프롬프트 관리 등 기본 빌딩 블록 제공
- **LangGraph**: 상태 그래프 기반 런타임. 스트리밍, 영속성, 체크포인팅 지원. `CompiledStateGraph`가 Deep Agents의 런타임 엔진
- **Deep Agents**: LangGraph 위에 구축된 opinionated 하네스. `create_deep_agent()`가 LangGraph의 compiled graph를 반환하므로, LangGraph의 모든 기능(스트리밍, Studio, 체크포인터 등) 활용 가능

---

## 3. 아키텍처 및 동작 방식

### 핵심 알고리즘

기본적으로 "LLM이 루프 안에서 도구를 호출하는" 패턴은 동일하다. 하지만 Deep Agents는 4가지 핵심 컴포넌트를 통해 이 루프를 강화한다:

1. **상세한 시스템 프롬프트** (Detailed System Prompt)
2. **계획 도구** (Planning Tool)
3. **서브 에이전트** (Sub-agents)
4. **파일 시스템** (File System)

### 미들웨어 스택

Deep Agents는 미들웨어 패턴으로 기능을 주입한다. 기본 미들웨어 스택 (실행 순서):

```
1.  TodoListMiddleware        - 작업 계획/추적
2.  MemoryMiddleware          - AGENTS.md 파일 로드 (장기 기억)
3.  SkillsMiddleware          - 커스텀 Python 도구 로드
4.  FilesystemMiddleware      - 파일 읽기/쓰기/편집
5.  SubAgentMiddleware        - 서브에이전트 생성/위임
6.  SummarizationMiddleware   - 대화 이력 자동 압축
7.  AnthropicPromptCachingMiddleware
8.  PatchToolCallsMiddleware
9.  (사용자 커스텀 미들웨어)
10. HumanInTheLoopMiddleware  - 사람 승인 (옵션)
```

### 내장 도구

| 도구 | 용도 |
|------|------|
| `write_todos` | 작업을 하위 단계로 분해, 진행 추적 |
| `ls` | 디렉토리 목록 |
| `read_file` | 파일 읽기 |
| `write_file` | 파일 쓰기 |
| `edit_file` | 파일 편집 |
| `glob` | 패턴 기반 파일 검색 |
| `grep` | 파일 내용 검색 |
| `execute` | 셸 명령 실행 (샌드박스 지원) |
| `task` | 서브에이전트 생성/위임 |

### 백엔드 추상화 (Pluggable Backends)

`BackendProtocol` 추상화를 통해 파일 저장소를 교체할 수 있다:

| 백엔드 | 설명 |
|--------|------|
| `StateBackend` | 에이전트 상태에 파일 저장 (기본값, 임시) |
| `FilesystemBackend` | 로컬 파일시스템 직접 접근 |
| `StoreBackend` | LangGraph의 영속 스토어 사용 |
| `CompositeBackend` | 경로 접두사별 라우팅 (예: `/memories/` → S3) |
| `SandboxBackendProtocol` | 셸 실행을 포함한 원격 샌드박스 |

지원 샌드박스: Modal, Daytona, Runloop, Deno, QuickJS

### 컨텍스트 관리

- **SummarizationMiddleware**: 토큰 사용량이 컨텍스트 윈도우의 85%에 도달하면 자동으로 이전 메시지를 LLM으로 요약
- 전체 이력은 `/conversation_history/{thread_id}.md`로 오프로드
- 큰 도구 출력은 자동으로 파일시스템으로 덤프
- 서브에이전트를 통한 컨텍스트 격리

### 모노레포 구조

```
deepagents/
├── deepagents           # 코어 SDK (v0.5.0a2)
├── deepagents-cli       # 터미널 UI, 스레드 관리
├── deepagents-acp       # Agent Client Protocol 구현
├── deepagents-harbor    # 평가 프레임워크
└── partner packages     # Modal, Daytona, Runloop, QuickJS 샌드박스
```

---

## 4. 주요 기능 및 특징

### 4.1 계획 도구 (Planning Tool)

- `write_todos` 도구로 복잡한 작업을 하위 작업으로 분해
- 일종의 "컨텍스트 엔지니어링 전략"으로, 에이전트가 트랙을 유지하도록 도움
- 진행 상황 추적 및 새 정보에 따라 계획 적응

### 4.2 파일 시스템 (File System)

- 가상 파일시스템을 통한 대규모 컨텍스트 관리
- 컨텍스트 윈도우 오버플로 방지
- 작업 산출물(리포트, 코드 등) 저장
- 플러그 가능한 백엔드로 스토리지 교체

### 4.3 서브 에이전트 (Sub-agents)

- `task` 도구로 전문 서브에이전트 생성
- 컨텍스트 격리: 메인 에이전트의 컨텍스트를 깨끗하게 유지
- 병렬 작업 가능

### 4.4 장기 기억 (Long-term Memory)

- LangGraph의 Memory Store를 통한 크로스 스레드 기억 유지
- AGENTS.md 파일을 통한 에이전트 설정/기억 로드

### 4.5 자동 요약 (Conversation Summarization)

- 대화가 길어지면 자동으로 이전 내용 요약
- v0.4에서 "더 스마트한" 요약 메커니즘 도입

### 4.6 샌드박스 실행 (v0.4+)

- Modal, Daytona, Runloop과 네이티브 통합
- 두 가지 패턴: (1) 에이전트를 샌드박스 내에서 실행, (2) 에이전트는 서버에서 실행하고 샌드박스를 원격 도구로 호출
- API 키를 외부에 유지하면서 격리된 실행 가능

### 4.7 하네스 엔지니어링 (Harness Engineering)

- Terminal Bench 2.0에서 52.8% → 66.5%로 13.7점 향상 (Top 30 → Top 5)
- 모델 변경 없이 하네스만 개선
- 핵심 기법:
  - **PreCompletionChecklistMiddleware**: 완료 전 검증 강제
  - **LocalContextMiddleware**: 환경 정보 주입
  - **LoopDetectionMiddleware**: 반복 패턴 감지 및 복구
  - **Reasoning Sandwich**: 계획/검증에 추론 예산 집중

### 4.8 CLI (Deep Agents CLI)

- 터미널에서 직접 Deep Agent 실행
- 인터랙티브 TUI, 웹 검색, 헤드리스 모드
- 스레드 관리, 영속 기억
- 비인터랙티브 모드로 cron/파이프라인에 통합 가능

---

## 5. 기존 LangChain Agent와의 차이점

| 항목 | 기존 LangChain Agent | Deep Agents |
|------|---------------------|-------------|
| **분류** | 에이전트 프레임워크 | 에이전트 하네스 |
| **철학** | 직접 프롬프트/도구 구성 | 배터리 포함 (즉시 실행 가능) |
| **계획** | 없음 (직접 구현 필요) | `write_todos` 내장 |
| **파일시스템** | 없음 | 가상 파일시스템 + 플러그 가능 백엔드 |
| **서브에이전트** | 없음 (직접 구현) | `task` 도구 내장 |
| **컨텍스트 관리** | 수동 | 자동 요약, 대용량 출력 파일 오프로드 |
| **시스템 프롬프트** | 사용자 작성 | 도구 사용법/행동 규칙이 포함된 긴 프롬프트 내장 |
| **적합 작업** | 단순, 단일 스텝 | 복잡, 멀티스텝, 장기 실행 |
| **미들웨어** | 없음 | 10개 미들웨어 스택 |
| **장기 기억** | 없음 | Memory Store 통합 |

### 핵심 차이

기존 LangChain Agent는 **빌딩 블록**을 제공하여 개발자가 처음부터 조립하는 방식이고, Deep Agents는 **완성된 하네스**를 제공하여 커스터마이징하는 방식이다. 비유하면 LangChain은 "부품 키트", Deep Agents는 "완성차에 튜닝"이다.

---

## 6. 사용 방법

### 설치

```bash
pip install deepagents
# 또는
uv add deepagents
```

### 기본 사용

```python
from deepagents import create_deep_agent

# 기본 에이전트 생성 (기본 모델: Claude Sonnet 4.6)
agent = create_deep_agent()

# 실행
result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Research LangGraph and write a summary"
    }]
})
```

### 모델 커스터마이징

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=init_chat_model("openai:gpt-4o"),
    tools=[my_custom_tool],
    system_prompt="You are a research assistant."
)
```

### create_deep_agent() 주요 파라미터

| 파라미터 | 설명 |
|----------|------|
| `model` | LLM 모델 (기본값: Claude Sonnet 4.6) |
| `tools` | 추가 커스텀 도구 리스트 |
| `system_prompt` | 시스템 프롬프트 오버라이드 |

`create_deep_agent()`는 LangGraph의 `CompiledStateGraph`를 반환하므로, 스트리밍, Studio, 체크포인터 등 LangGraph의 모든 기능을 사용할 수 있다.

### CLI 사용

```bash
pip install deepagents-cli
deepagents  # 인터랙티브 모드
deepagents --headless "Research topic X"  # 헤드리스 모드
```

---

## 7. Azure OpenAI와 함께 사용 가능한지

### 결론: 사용 가능

Deep Agents는 LangChain의 `init_chat_model`을 통해 모델을 주입받으므로, LangChain이 지원하는 모든 LLM 프로바이더를 사용할 수 있다. Azure OpenAI도 포함된다.

### Azure OpenAI 설정 방법

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# 방법 1: azure_openai 프로바이더 사용
model = init_chat_model("azure_openai:gpt-4o")

# 방법 2: AzureChatOpenAI 직접 사용
from langchain_openai import AzureChatOpenAI
model = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2025-04-01-preview",
    api_key="your-key"
)

agent = create_deep_agent(model=model)
```

### 필요 환경변수

```
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### 주의사항

- Deep Agents의 기본 모델은 Claude Sonnet 4.6이므로, Azure OpenAI를 사용하려면 반드시 `model` 파라미터를 명시해야 한다
- tool_calling을 지원하는 모델이어야 한다 (GPT-4o, GPT-4 Turbo 등)
- 프로바이더 불가지론적(provider-agnostic) 아키텍처이므로, 프론티어 모델과 오픈소스 모델 모두 지원

---

## 8. Responses API와 함께 사용 가능한지

### 결론: 사용 가능 (v0.4부터 기본값)

Deep Agents v0.4 (2026년 2월 10일)부터 **OpenAI Responses API가 OpenAI 모델의 기본값**으로 설정되었다.

### 세부 사항

- OpenAI의 Responses API는 Assistants API를 대체하는 새로운 상태 기반 에이전트 API
- Deep Agents v0.4에서 OpenAI 모델 사용 시 자동으로 Responses API가 적용됨
- 이전 Chat Completions API도 여전히 지원

### Azure OpenAI + Responses API 조합

- Azure OpenAI도 Responses API를 지원 (2025년 8월부터 GA)
- 따라서 Deep Agents + Azure OpenAI + Responses API 조합이 가능
- 단, Azure OpenAI의 Responses API 지원 모델/리전 제한 확인 필요 (별도 조사 문서 참조: `references/2026-03-27_azure-openai-responses-api.md`)

---

## 9. 실제 사용 사례 및 예시

### 9.1 리서치 및 분석

- 웹에서 데이터 수집 → 교차 참조 → 구조화된 리포트 작성
- Deep Research 패턴: 멀티스텝 리서치 자동화

### 9.2 코딩

- Terminal Bench 2.0 Top 5 달성
- 코드 작성, 테스트, 디버깅, 릴리스 노트 생성
- Deep Agents CLI를 통한 터미널 기반 코딩 에이전트

### 9.3 금융 서비스

- 규제 컴플라이언스 분석
- 비즈니스 케이스 + 재무 전망 작성
- 리스크 레지스터 + 완화 전략 생성

### 9.4 고객 지원

- 멀티티어 지원 시스템: 메인 에이전트가 요청을 분류하고 전문 서브에이전트(FAQ, 에스컬레이션, 기술)에 위임

### 9.5 엔터프라이즈 검색

- NVIDIA AI-Q Blueprint: Deep Agents + NVIDIA의 병렬/투기적 실행 도구 결합
- 프로덕션 엔터프라이즈 리서치 시스템

### 9.6 잡 지원 어시스턴트

- DataCamp 튜토리얼: 직책 검색 + 맞춤형 커버레터 생성

---

## 10. AISE 2.0 프로젝트에 적용 가능성

### 10.1 적용 가능한 영역

#### AI 어시스트 (요구사항 보완/제안)

- **적합도: 높음**
- Deep Agents의 계획 도구와 서브에이전트를 활용하여:
  - FR/NFR/BR 입력 시 누락 항목 분석 (보완)
  - 관련 요구사항 추가 제안
  - 서브에이전트로 각 요구사항 유형별 전문 분석 위임
- 파일시스템에 요구사항 스냅샷을 저장하고 교차 분석 가능

#### SRS 생성

- **적합도: 높음**
- Deep Agents의 강점이 가장 잘 발휘되는 영역:
  - 계획 도구로 SRS 섹션별 생성 계획 수립
  - 서브에이전트로 각 섹션(기능 명세, 비기능 요구사항, 시스템 아키텍처 등) 전문 생성
  - 파일시스템에 중간 산출물 저장 → 최종 통합
  - IEEE 830 템플릿을 시스템 프롬프트에 포함
  - 생성 전 품질 체크를 PreCompletionChecklistMiddleware 패턴으로 구현 가능

#### 품질 체크 (생성 전 검증)

- **적합도: 중간~높음**
- Deep Agents의 자기 검증 루프(self-verification loop) 패턴 활용:
  - 요구사항 충분성 검증
  - 일관성 검토
  - 누락 항목 식별

### 10.2 적용 시 고려사항

#### 장점

1. **즉시 사용 가능**: 프롬프트, 도구, 컨텍스트 관리가 내장되어 개발 시간 단축
2. **구조화된 출력**: 계획 → 실행 → 검증 패턴이 SRS 생성에 적합
3. **컨텍스트 관리**: 많은 요구사항을 다룰 때 자동 요약/파일 오프로드로 컨텍스트 윈도우 한계 극복
4. **서브에이전트**: 각 SRS 섹션을 병렬로 생성 가능
5. **Azure OpenAI 호환**: 기존 Azure 인프라 활용 가능
6. **MIT 라이선스**: 상업적 사용 가능
7. **LangGraph 통합**: 스트리밍, 체크포인팅 등 프로덕션 기능

#### 단점/우려

1. **의존성 추가**: LangChain + LangGraph + Deep Agents 3개 패키지 의존
2. **Beta 상태**: 아직 v0.x이며 API 변경 가능성
3. **오버엔지니어링 가능성**: AISE 2.0 MVP에 Deep Agents의 모든 기능이 필요하지 않을 수 있음
4. **추상화 비용**: 문제 발생 시 3계층(LangChain → LangGraph → Deep Agents) 디버깅 필요
5. **기본 모델이 Claude**: Azure OpenAI 사용 시 명시적 설정 필요

### 10.3 AISE 2.0 적용 전략 제안

#### 옵션 A: Deep Agents 전면 채택

- AI 어시스트 + SRS 생성 모두 Deep Agents로 구현
- 장점: 일관된 아키텍처, 서브에이전트/계획 도구 활용
- 단점: 학습 곡선, Beta 리스크

#### 옵션 B: 선택적 채택

- SRS 생성(복잡한 멀티스텝 작업)에만 Deep Agents 사용
- AI 어시스트(단순 보완/제안)는 직접 LLM API 호출
- 장점: 복잡도 적정, 각 영역에 맞는 도구
- 단점: 두 가지 패턴 관리

#### 옵션 C: Deep Agents 불채택, 패턴만 참조

- Deep Agents의 아키텍처 패턴(계획 → 실행 → 검증, 서브에이전트 위임 등)을 참고하되
- LangChain + LangGraph를 직접 사용하여 구현
- 장점: 의존성 최소화, 완전한 제어
- 단점: 구현 공수 증가

#### 권장: 옵션 B (선택적 채택)

MVP 단계에서는 AI 어시스트는 단순 API 호출로 빠르게 구현하고, SRS 생성처럼 복잡한 멀티스텝 작업에 Deep Agents를 활용하는 것이 균형적이다. 이후 Deep Agents가 안정화되면 전면 확대할 수 있다.

---

## 버전 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| 0.0.1 | 2025-07-29 | 최초 릴리스 |
| 0.2.0 | 2025-10 (추정) | 플러그 가능 백엔드, 대용량 출력 파일 덤프, 대화 이력 압축 |
| 0.4.0 | 2026-02-10 | 샌드박스 지원 (Modal/Daytona/Runloop), Responses API 기본값, 스마트 요약 |
| 0.4.12 | 2026-03-20 | 최신 안정 버전 |
| 0.5.0a2 | 2026-03-23 | 프리릴리스 |

## NVIDIA 파트너십 (2026년 3월)

- LangChain과 NVIDIA의 전략적 파트너십 발표
- **AI-Q Blueprint**: Deep Agents 기반 프로덕션 엔터프라이즈 리서치 시스템
- NVIDIA의 병렬/투기적 실행 도구 + LangGraph 런타임 결합
- Deep Agents의 엔터프라이즈 레디 포지셔닝 강화

---

## 참고 자료

- [LangChain Blog - Deep Agents](https://blog.langchain.com/deep-agents/)
- [Deep Agents 공식 문서](https://docs.langchain.com/oss/python/deepagents/overview)
- [GitHub 저장소](https://github.com/langchain-ai/deepagents)
- [Deep Agents v0.4 Changelog](https://changelog.langchain.com/announcements/deep-agents-v0-4)
- [Doubling Down on Deep Agents (v0.2 블로그)](https://blog.langchain.com/doubling-down-on-deepagents/)
- [Harness Engineering 개선 블로그](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/)
- [Deep Agents CLI 소개](https://blog.langchain.com/introducing-deepagents-cli/)
- [NVIDIA Enterprise 파트너십](https://blog.langchain.com/nvidia-enterprise/)
- [PyPI - deepagents](https://pypi.org/project/deepagents/)
- [DeepWiki - deepagents](https://deepwiki.com/langchain-ai/deepagents)
- [DataCamp 튜토리얼](https://www.datacamp.com/tutorial/deep-agents)
- [LangChain Academy - Deep Agents 코스](https://academy.langchain.com/courses/deep-agents-with-langgraph)
- [LangChain Deep Agents 제품 페이지](https://www.langchain.com/deep-agents)
