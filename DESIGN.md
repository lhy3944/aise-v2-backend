# DESIGN.md — FastAPI 멀티 에이전트 시스템 설계 문서

> **목적**: 프로젝트별 지식 데이터, 요구사항, SRS, TC 등 산출물을 관리하는 확장 가능한 멀티 에이전트 백엔드 시스템 구축
>
> **상태**: 설계 확정 · Claude Code에서 구현 착수 예정
>
> **원칙**: 에이전트는 플러그인 방식으로 확장 가능 · 자연어 지시문 라우팅 · Human-in-the-Loop 내장

---

## 1. 프로젝트 개요

### 1.1 배경
FastAPI 기반 프로토타입 백엔드가 존재하며, 여기에 다음과 같은 멀티 에이전트 기능을 추가하고자 한다.

### 1.2 핵심 요구사항
1. **지식 데이터 관리**: 프로젝트별 문서를 임베딩하여 벡터 스토어에 저장, RAG 기반 답변 생성
2. **요구사항 정제**: 사용자의 모호한 요구사항을 정리된 형태로 변환
3. **산출물 자동 생성**: 요구사항 기반 SRS(Software Requirements Specification), TC(Test Case) 생성
4. **확장성**: 새로운 에이전트를 플러그인처럼 추가 가능
5. **자연어 라우팅**: 사용자 지시문(자연어)을 분석해 적절한 에이전트(들) 호출
6. **Human-in-the-Loop**: 모호한 요청은 사용자에게 되묻고 컨센서스 확보 후 진행

### 1.3 비기능 요구사항
- 프로젝트별 데이터 격리 (멀티 테넌시)
- 세션 중단/재개 가능 (장시간 대화, HITL 대기 지원)
- 스트리밍 응답 지원
- 관측성 (비용, 지연시간, 품질 모니터링)

---

## 2. 전체 아키텍처

### 2.1 3계층 구조

```
┌─────────────────────────────────────────────────┐
│  API Layer (FastAPI)                            │
│  - REST: /chat /projects /artifacts             │
│  - SSE: 토큰 스트리밍                             │
│  - /chat/{session_id}/resume: HITL 응답 재개     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Orchestration Layer (LangGraph)                │
│  - Supervisor: 자연어 → 에이전트 라우팅           │
│  - State 관리 · Checkpoint · interrupt()         │
│  - Plan 기반 다단계 실행                          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Agent Layer (플러그인 레지스트리)                 │
│  ├─ KnowledgeQA Agent    (RAG 기반 질의응답)     │
│  ├─ Requirement Agent    (요구사항 정제)         │
│  ├─ SRS Generator        (SRS 문서 생성)         │
│  ├─ TestCase Generator   (TC 생성)               │
│  ├─ Critic Agent         (산출물 자가 검토)      │
│  └─ [신규 에이전트 플러그인...]                    │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Infrastructure                                 │
│  PostgreSQL(+pgvector) · Redis · S3/MinIO       │
└─────────────────────────────────────────────────┘
```

### 2.2 주요 데이터 흐름

1. **단일 질의 (RAG)**:
   `사용자 요청 → Supervisor → KnowledgeQA → 벡터 검색 → LLM → 응답`

2. **산출물 생성 (다단계)**:
   `요청 → Supervisor(plan) → Requirement Agent → SRS Generator → TC Generator → Critic → 응답`

3. **HITL 개입**:
   `요청 → Supervisor → 모호함 감지 → interrupt() → [체크포인트 저장] → 사용자 응답 → resume → 재개`

---

## 3. 기술 스택

| 레이어 | 선택 | 선택 이유 |
|---|---|---|
| **API 프레임워크** | FastAPI | 기존 프로토타입 활용, async 네이티브, 자동 OpenAPI |
| **오케스트레이션** | **LangGraph** | HITL `interrupt()` 내장, 체크포인트로 요청 간 상태 영속화 |
| **에이전트 구현** | LangGraph 노드 + Pydantic | 프레임워크 락인 최소화, 테스트 용이 |
| **LLM 추상화** | **LiteLLM** | 100+ 모델 통합, 비용 트래킹, 모델 교체 자유 |
| **벡터 스토어** | **pgvector** (1차) / Qdrant (확장 시) | pgvector는 PostgreSQL 하나로 운영 단순화 |
| **임베딩 모델** | OpenAI `text-embedding-3-large` 또는 BGE-M3 | 한국어 혼용 시 BGE-M3 우선 검토 |
| **체크포인터** | LangGraph PostgresSaver | HITL 중단 상태를 DB에 영속 저장 |
| **관계형 DB** | PostgreSQL 15+ | pgvector 지원, 트랜잭션 강함 |
| **캐시/큐** | Redis | 세션 캐시, Celery 브로커 |
| **비동기 작업** | Celery 또는 FastAPI BackgroundTasks | 장시간 산출물 생성은 백그라운드 처리 |
| **실시간 스트리밍** | **SSE (Server-Sent Events)** | WebSocket보다 단순, LLM 토큰 스트리밍에 충분 |
| **스키마/검증** | Pydantic v2 | 구조화된 LLM 출력, API 스키마 통합 |
| **스토리지** | S3 호환 (MinIO/AWS S3) | 원본 문서, 생성된 산출물 파일 저장 |
| **관측성** | Langfuse 또는 LangSmith | 트레이싱, 비용, 프롬프트 버저닝 |

**핵심 선택 근거**:
LangGraph는 "상태 기반 그래프 + 중단/재개" 모델이 HITL 시나리오에 최적. AutoGen·CrewAI는 에이전트 간 대화에 강하지만, 사용자가 중간에 개입하고 세션이 끊겼다 이어지는 시나리오엔 LangGraph가 훨씬 자연스러움.

---

## 4. 에이전트 레지스트리 패턴

### 4.1 공통 인터페이스

```python
# agents/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Literal

class AgentCapability(BaseModel):
    name: str                        # "knowledge_qa"
    description: str                 # Supervisor가 라우팅 판단에 사용
    input_schema: dict               # 기대 입력 형식
    output_schema: dict              # 산출 형식
    triggers: list[str]              # 예시 자연어 패턴
    requires_hitl: bool = False
    estimated_tokens: int = 2000     # 비용 예측용
    tags: list[str] = []             # 예: ["rag", "generation"]

class BaseAgent(ABC):
    capability: AgentCapability

    @abstractmethod
    async def run(self, state: "AgentState") -> "AgentState":
        """에이전트 실행. state를 받아 갱신된 state 반환."""
        ...
```

### 4.2 자동 등록

```python
# agents/registry.py
AGENT_REGISTRY: dict[str, BaseAgent] = {}

def register_agent(cls):
    instance = cls()
    AGENT_REGISTRY[cls.capability.name] = instance
    return cls

# 새 에이전트 추가 예시
@register_agent
class KnowledgeQAAgent(BaseAgent):
    capability = AgentCapability(
        name="knowledge_qa",
        description="프로젝트 지식베이스에서 정보를 검색하여 질문에 답변",
        triggers=["~이 뭐야", "~에 대해 알려줘", "~문서 찾아줘"],
        input_schema={"query": "str", "project_id": "str"},
        output_schema={"answer": "str", "sources": "list"},
        tags=["rag", "qa"],
    )
    async def run(self, state): ...
```

**장점**: 새 에이전트는 파일 하나 추가하면 Supervisor가 자동 인식 (`capability.description`이 라우팅 프롬프트에 동적 주입).

---

## 5. Supervisor 라우팅

### 5.1 라우팅 결정 구조

```python
class RoutingDecision(BaseModel):
    action: Literal["single", "plan", "clarify"]
    agent: str | None = None           # single일 때
    plan: list[str] | None = None      # plan일 때 순차 실행할 에이전트
    clarification: str | None = None   # clarify일 때 사용자에게 할 질문
    reasoning: str                     # 판단 근거 (로깅/디버깅)
```

### 5.2 3가지 라우팅 결과

| 액션 | 의미 | 예시 |
|---|---|---|
| `single` | 단일 에이전트 직행 | "로그인 API 설명해줘" → `knowledge_qa` |
| `plan` | 다단계 순차 실행 | "SRS 만들어줘" → `[requirement, srs_gen, critic]` |
| `clarify` | 사용자에게 되묻기 (HITL) | "그거 좀 해줘" → "'그거'가 구체적으로 무엇인가요?" |

### 5.3 하이브리드 라우팅 (권장)

순수 LLM 판정은 불안정. 2단계 접근:
1. **1차 필터**: `capability.triggers` 임베딩으로 후보 에이전트 top-5 추출
2. **2차 판정**: 후보 목록만 LLM에게 주고 최종 선택 + plan 수립

---

## 6. Human-in-the-Loop 설계

### 6.1 LangGraph `interrupt` 활용

```python
from langgraph.types import interrupt, Command

async def clarification_node(state: AgentState):
    question = await generate_clarifying_question(state)

    # 실행 중단 → 체크포인트 저장 → FastAPI 응답 반환
    user_response = interrupt({
        "type": "clarification",
        "question": question,
        "options": ["선택지 A", "선택지 B", "자유 입력"],
        "context": state.current_context,
    })

    # 사용자 응답이 오면 이 지점부터 재개
    return {"clarified_input": user_response}
```

### 6.2 FastAPI 엔드포인트

```python
@app.post("/chat")
async def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.session_id}}
    result = await graph.ainvoke(
        {"user_input": req.message, "project_id": req.project_id},
        config
    )

    if "__interrupt__" in result:
        return {
            "status": "needs_input",
            "session_id": req.session_id,
            "question": result["__interrupt__"]
        }
    return {"status": "done", "result": result}

@app.post("/chat/{session_id}/resume")
async def resume(session_id: str, user_answer: UserAnswer):
    config = {"configurable": {"thread_id": session_id}}
    # 체크포인트에서 정확히 중단 지점부터 재개
    result = await graph.ainvoke(Command(resume=user_answer.dict()), config)
    return result
```

### 6.3 HITL 트리거 시점

- Supervisor가 요청 해석 불가 시 (액션=`clarify`)
- 생성된 산출물이 중대한 결정 포함 시 (예: 아키텍처 변경)
- Critic이 품질 미달 판정 시 사용자 확인 요청
- 외부 API 호출 등 비가역 작업 직전

---

## 7. RAG 파이프라인 (지식 에이전트)

### 7.1 프로젝트 격리

모든 벡터 데이터는 `project_id` 메타데이터 필수.

```python
# 인덱싱
await vectorstore.add_documents(
    docs,
    metadata={
        "project_id": project_id,
        "doc_type": "srs",        # srs | tc | manual | code
        "version": "1.2",
        "source_file": filename,
    }
)

# 검색 (필터 필수)
results = await vectorstore.similarity_search(
    query,
    filter={"project_id": project_id},
    k=5
)
```

⚠️ **중요**: `project_id` 필터 누락은 보안 사고. 테스트로 반드시 검증.

### 7.2 단계적 개선 로드맵

| 단계 | 기법 | 효과 |
|---|---|---|
| 1 | 기본 코사인 유사도 | 기준선 |
| 2 | **하이브리드 검색** (BM25 + 벡터) | 고유명사·코드명 강함 |
| 3 | **리랭킹** (Cohere Rerank, BGE-reranker) | 정확도 크게 향상 |
| 4 | **Query rewriting** | 검색 친화적 쿼리 변환 |
| 5 | **Self-RAG / CRAG** | 검색 결과 자가 평가 후 재검색 |

### 7.3 청킹 전략

SRS·TC 같은 정형 문서는 **구조 보존 청킹** (섹션·요구사항 ID 단위)이 균등 길이 청킹보다 훨씬 효과적.

```python
# 정형 문서 예시
{
    "chunk_id": "SRS-LOGIN-REQ-001",
    "doc_type": "srs",
    "section": "3.2.1 로그인 기능",
    "requirement_id": "REQ-001",
    "content": "...",
    "parent_chunk_id": "SRS-LOGIN"   # 상위 섹션 참조
}
```

---

## 8. 산출물 생성 에이전트

### 8.1 구조화된 출력 강제 (Pydantic)

```python
class Requirement(BaseModel):
    id: str                                          # REQ-001
    type: Literal["functional", "non_functional"]
    priority: Literal["high", "medium", "low"]
    description: str
    acceptance_criteria: list[str]
    ears_format: str                                 # EARS 문법
    rationale: str | None = None
    source: str | None = None                        # 원 요구사항 ID

class SRSDocument(BaseModel):
    project_id: str
    version: str
    title: str
    requirements: list[Requirement]
    overview: str
    scope: str
    glossary: dict[str, str] = {}

class TestCase(BaseModel):
    id: str                                          # TC-001
    requirement_ids: list[str]                       # 연결된 요구사항
    title: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    priority: Literal["high", "medium", "low"]
    type: Literal["functional", "integration", "e2e"]

# LLM 호출
srs = await llm.with_structured_output(SRSDocument).ainvoke(prompt)
```

### 8.2 체이닝 전략

```
[Requirement Agent]
    ↓ (정제된 요구사항 목록)
[SRS Generator]
    ↓ (SRS 문서)
[TC Generator]
    ↓ (TC 목록)
[Critic Agent]
    ↓ (품질 평가 + 개선점)
[필요시 HITL]
```

각 단계 산출물은 state에 누적 저장하여 다음 단계에서 참조 가능.

### 8.3 Critic 에이전트

생성 직후 자가 검토:
- SRS: 완전성, 일관성, EARS 문법 준수, 중복 요구사항 감지
- TC: 요구사항 커버리지, 테스트 독립성, 재현 가능성

품질 미달 시: 자동 재생성 또는 HITL 트리거.

---

## 9. 데이터 모델 (PostgreSQL 스키마)

```sql
-- 프로젝트 (멀티 테넌시 기본 단위)
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_id UUID NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 지식 문서 메타
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    source_type VARCHAR(50),                 -- upload | url | generated
    doc_type VARCHAR(50),                    -- manual | srs | tc | code
    version VARCHAR(50),
    file_path TEXT,                          -- S3 경로
    metadata JSONB,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- 벡터 청크 (pgvector)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL,                -- 필터링용 denormalize
    chunk_index INT,
    content TEXT,
    embedding vector(1536),                  -- 모델에 맞춰 조정
    metadata JSONB
);

CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON document_chunks (project_id);

-- 대화 세션 = LangGraph thread_id
CREATE TABLE conversations (
    id UUID PRIMARY KEY,                     -- LangGraph thread_id로 사용
    project_id UUID REFERENCES projects(id),
    user_id UUID NOT NULL,
    title VARCHAR(500),
    status VARCHAR(50),                      -- active | waiting_hitl | completed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW()
);

-- 산출물 (SRS, TC 등)
CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    conversation_id UUID REFERENCES conversations(id),
    type VARCHAR(50),                        -- srs | tc | requirement_list
    version VARCHAR(50),
    title VARCHAR(500),
    content JSONB,                           -- Pydantic 직렬화
    status VARCHAR(50),                      -- draft | approved | archived
    created_by_agent VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HITL 기록 (감사/분석용)
CREATE TABLE hitl_requests (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    question TEXT,
    context JSONB,
    response TEXT,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 에이전트 실행 이력 (비용/성능 분석)
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    agent_name VARCHAR(100),
    input JSONB,
    output JSONB,
    tokens_used INT,
    cost_usd NUMERIC(10, 6),
    latency_ms INT,
    status VARCHAR(50),                      -- success | failed | interrupted
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LangGraph 체크포인트 테이블은 라이브러리가 자동 생성
```

---

## 10. API 명세 (주요 엔드포인트)

### 10.1 대화
```
POST   /chat                                 # 새 메시지 전송 (SSE 스트리밍)
POST   /chat/{session_id}/resume             # HITL 응답으로 재개
GET    /chat/{session_id}                    # 대화 이력 조회
DELETE /chat/{session_id}                    # 세션 종료
```

### 10.2 프로젝트 / 지식
```
POST   /projects                             # 프로젝트 생성
GET    /projects                             # 목록
GET    /projects/{project_id}                # 상세
POST   /projects/{project_id}/documents      # 문서 업로드 (자동 임베딩)
GET    /projects/{project_id}/documents      # 문서 목록
DELETE /projects/{project_id}/documents/{id} # 삭제
```

### 10.3 산출물
```
GET    /projects/{project_id}/artifacts      # 산출물 목록
GET    /artifacts/{artifact_id}              # 상세
POST   /artifacts/{artifact_id}/export       # 다운로드 (md/docx/pdf)
PATCH  /artifacts/{artifact_id}              # 수동 수정
```

### 10.4 에이전트 메타
```
GET    /agents                               # 등록된 에이전트 목록 (capability 노출)
GET    /agents/{agent_name}                  # 특정 에이전트 상세
```

---

## 11. 프로젝트 구조 (권장)

```
app/
├── main.py                          # FastAPI 진입점
├── config.py                        # Pydantic Settings
├── dependencies.py                  # DI
├── api/
│   ├── __init__.py
│   ├── chat.py
│   ├── projects.py
│   ├── documents.py
│   ├── artifacts.py
│   └── agents.py
├── agents/
│   ├── __init__.py
│   ├── base.py                      # BaseAgent, AgentCapability
│   ├── registry.py                  # AGENT_REGISTRY + register_agent
│   ├── knowledge_qa.py
│   ├── requirement.py
│   ├── srs_generator.py
│   ├── testcase_generator.py
│   └── critic.py
├── orchestration/
│   ├── __init__.py
│   ├── graph.py                     # LangGraph 그래프 구성
│   ├── supervisor.py                # 라우팅 노드
│   ├── state.py                     # AgentState (Pydantic)
│   └── hitl.py                      # interrupt 핸들러
├── rag/
│   ├── __init__.py
│   ├── embedder.py                  # 임베딩 래퍼
│   ├── vectorstore.py               # pgvector 인터페이스
│   ├── chunker.py                   # 문서 청킹 (구조 보존)
│   └── retriever.py                 # 하이브리드 검색 + 리랭킹
├── models/                          # SQLAlchemy ORM
│   ├── __init__.py
│   ├── project.py
│   ├── document.py
│   ├── conversation.py
│   └── artifact.py
├── schemas/                         # Pydantic 스키마
│   ├── __init__.py
│   ├── chat.py
│   ├── artifact.py
│   ├── srs.py                       # SRSDocument, Requirement
│   └── testcase.py                  # TestCase
├── services/                        # 비즈니스 로직
│   ├── __init__.py
│   ├── project_service.py
│   ├── document_service.py
│   └── llm_service.py               # LiteLLM 래퍼
├── db/
│   ├── __init__.py
│   ├── session.py                   # async SQLAlchemy 세션
│   └── migrations/                  # Alembic
└── utils/
    ├── __init__.py
    ├── logger.py
    └── cost_tracker.py

tests/
├── unit/
├── integration/
└── e2e/

prompts/                             # 프롬프트 버저닝 (코드 분리)
├── supervisor.md
├── requirement.md
└── ...

docker-compose.yml                   # PostgreSQL + Redis + MinIO
pyproject.toml                       # 의존성
alembic.ini
.env.example
```

---

## 12. 단계별 로드맵

### Phase 1 — 기반 (1~2주)
**목표**: 단일 에이전트로 RAG 왕복 검증

- [ ] 프로젝트 구조 스캐폴딩
- [ ] FastAPI + PostgreSQL(pgvector) + Redis docker-compose
- [ ] Alembic 마이그레이션 (projects, documents, chunks 테이블)
- [ ] 기본 API: `/projects`, `/documents` 업로드/임베딩
- [ ] `BaseAgent` + 레지스트리 구현
- [ ] `KnowledgeQAAgent` 단일 에이전트 구현
- [ ] LangGraph 최소 그래프 (Supervisor → KnowledgeQA)
- [ ] `/chat` 엔드포인트 (non-streaming)
- [ ] thread_id 기반 세션 관리

**완료 기준**: 문서 업로드 → 질문 → RAG 답변이 정상 동작

### Phase 2 — 멀티 에이전트 (2~3주)
**목표**: 다단계 산출물 생성

- [ ] Supervisor 라우팅 (single/plan/clarify 3가지 액션)
- [ ] `RequirementAgent` 구현
- [ ] `SRSGeneratorAgent` 구현 (Pydantic structured output)
- [ ] `TestCaseGeneratorAgent` 구현
- [ ] `CriticAgent` 구현
- [ ] Plan 기반 순차 실행 로직
- [ ] Artifacts 저장/조회 API
- [ ] 산출물 export (Markdown 먼저)

**완료 기준**: "요구사항 → SRS → TC" 플로우가 자동 생성

### Phase 3 — HITL (1~2주)
**목표**: 사용자 개입 및 세션 재개

- [ ] LangGraph PostgresSaver 연동
- [ ] `interrupt()` 기반 clarification 노드
- [ ] `/chat/{session_id}/resume` API
- [ ] SSE 스트리밍 응답
- [ ] 프론트 대응용 응답 스키마 (`needs_input` 상태)
- [ ] HITL 이력 기록

**완료 기준**: 모호한 질문 → 사용자 되묻기 → 응답 후 재개가 세션 끊겨도 동작

### Phase 4 — 품질 강화 (지속)
- [ ] 하이브리드 검색 (BM25 + 벡터)
- [ ] 리랭킹 도입
- [ ] Query rewriting
- [ ] 관측성 (Langfuse 연동)
- [ ] 비용 트래킹 대시보드
- [ ] RAGAS 평가 파이프라인
- [ ] 프롬프트 버저닝

### Phase 5 — 운영화
- [ ] A/B 테스트 인프라
- [ ] 에이전트별 성능 대시보드
- [ ] 권한 시스템 (RBAC)
- [ ] 감사 로그
- [ ] DOCX/PDF export
- [ ] Celery 기반 대규모 배치 처리

---

## 13. 주요 함정 및 대응

| 함정 | 대응 |
|---|---|
| **컨텍스트 폭발** (다단계 에이전트의 토큰 증가) | 단계 간 요약 압축 노드 삽입 |
| **LLM 라우팅 불안정** | 하이브리드 라우팅 (임베딩 필터 + LLM 판정) |
| **HITL 무한 대기** | 세션 TTL 설정, 정리 워커 |
| **프로젝트 격리 누락** | 모든 RAG 쿼리에 project_id 필터 테스트 강제 |
| **프롬프트 하드코딩** | `prompts/` 디렉토리 분리, Langfuse 버저닝 |
| **LLM 비용 폭증** | 에이전트별 token budget, 모델 티어 분리 (Haiku/Sonnet/Opus) |
| **동시 실행 경합** | LangGraph thread_id 기반 직렬화, Redis lock |

---

## 14. 기존 프로토타입에서 가져올 것 (Claude Code에서 분석할 항목)

새 프로젝트로 이관 시 다음을 재사용 가능한지 점검:
- [ ] 기존 의존성 목록 (requirements.txt / pyproject.toml)
- [ ] DB 연결 설정, 환경 변수 처리
- [ ] 인증/인가 미들웨어 (JWT 등)
- [ ] 기존 Pydantic 스키마
- [ ] 기존 API 엔드포인트 (유지할 것과 재설계할 것 구분)
- [ ] 로깅/에러 핸들링
- [ ] 테스트 설정 (pytest 픽스처 등)
- [ ] CI/CD 설정

---

## 15. 참고 링크

- LangGraph HITL: https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/
- LangGraph PostgresSaver: https://langchain-ai.github.io/langgraph/reference/checkpoints/
- pgvector: https://github.com/pgvector/pgvector
- LiteLLM: https://docs.litellm.ai/
- Langfuse: https://langfuse.com/
- EARS 요구사항 표기법: https://alistairmavin.com/ears/

---

**문서 버전**: v1.0
**다음 액션**: Claude Code에서 본 문서 + 프로토타입 저장소 분석 후 `MIGRATION_PLAN.md` 작성
