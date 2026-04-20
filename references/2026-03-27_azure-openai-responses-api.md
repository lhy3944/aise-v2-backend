---
title: "Azure OpenAI Responses API 조사"
date: 2026-03-27
source:
  - https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses
  - https://developers.openai.com/api/docs/guides/conversation-state
  - https://developers.openai.com/api/docs/guides/migrate-to-responses
  - https://developers.openai.com/api/docs/guides/pdf-files
  - https://developers.openai.com/api/docs/models/gpt-5.2
  - https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure
  - https://openai.com/index/new-tools-and-features-in-the-responses-api/
  - https://simonwillison.net/2025/Mar/11/responses-vs-chat-completions/
tags: [azure-openai, responses-api, llm, api-design, gpt-5]
---

# Azure OpenAI Responses API 조사

## 1. Responses API란 무엇인가?

### 개요

Responses API는 OpenAI가 2025년 3월 11일에 공식 발표한 새로운 API 프리미티브다. 기존 Chat Completions API와 Assistants API의 장점을 하나의 통합된 인터페이스로 결합한 것이 핵심이다.

- **Chat Completions API**: 단순하고 stateless한 텍스트 생성 API
- **Assistants API**: stateful하지만 복잡한 에이전트 API (2026년 8월 26일 deprecated 예정)
- **Responses API**: 두 API의 장점을 통합 - 단순한 인터페이스 + stateful 대화 + 빌트인 도구

### Chat Completions API와의 주요 차이점

| 항목 | Chat Completions | Responses |
|------|-----------------|-----------|
| 엔드포인트 | `POST /v1/chat/completions` | `POST /v1/responses` |
| 입력 파라미터 | `messages` 배열 (role 기반) | `input` (문자열 또는 메시지 배열) |
| 시스템 프롬프트 | `messages`에 `system` role 포함 | `instructions` 파라미터로 분리 가능 |
| 응답 구조 | `choices[0].message.content` | `output_text` 헬퍼 + `output` 배열 (typed Items) |
| 상태 관리 | Stateless (매번 전체 이력 전송) | Stateful (`previous_response_id` 지원) |
| 빌트인 도구 | 없음 (function calling만 지원) | Web Search, File Search, Code Interpreter, Computer Use, MCP |
| 함수 정의 | Externally-tagged, non-strict 기본값 | Internally-tagged, strict 기본값 |
| 구조화 출력 | `response_format` 파라미터 | `text.format` 파라미터 |
| 병렬 생성 | `n` 파라미터로 복수 생성 가능 | 제거됨 (단일 생성만) |
| 데이터 저장 | 저장 안함 | 기본 30일 저장 (`store: false`로 비활성화 가능) |

### 응답 형식 비교

**Chat Completions 응답:**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "응답 텍스트"
    }
  }]
}
```

**Responses API 응답:**
```json
{
  "id": "resp_xxx",
  "object": "response",
  "output": [{
    "id": "msg_xxx",
    "type": "message",
    "role": "assistant",
    "content": [{
      "type": "output_text",
      "text": "응답 텍스트"
    }]
  }],
  "output_text": "응답 텍스트",
  "status": "completed",
  "usage": { "input_tokens": 20, "output_tokens": 11, "total_tokens": 31 }
}
```

---

## 2. 멀티턴 대화 처리 방식

### 기존 Chat Completions 방식의 문제

Chat Completions API에서는 매번 전체 대화 이력을 클라이언트에서 관리하고 전송해야 했다:

```python
# Chat Completions: 매번 전체 이력을 보내야 함
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "안녕하세요"},
    {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"},
    {"role": "user", "content": "날씨 알려줘"},  # 새 메시지
]
response = client.chat.completions.create(model="gpt-4o", messages=messages)
```

### Responses API의 3가지 대화 관리 방식

#### 방식 1: `previous_response_id` 체이닝 (가장 간편)

서버가 이전 대화 상태를 보관하므로, 새 메시지만 보내면 된다:

```python
# 첫 번째 요청
response = client.responses.create(
    model="gpt-4o",
    input="카타스트로픽 포겟팅이란 무엇인가?"
)

# 두 번째 요청 - 이전 응답 ID만 전달하면 전체 컨텍스트 자동 포함
second_response = client.responses.create(
    model="gpt-4o",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "대학 신입생 수준으로 설명해줘"}]
)
```

#### 방식 2: Conversations API (장기 대화용)

별도의 Conversation 객체를 생성하여 세션 간에도 대화를 유지:

```python
conversation = openai.conversations.create()

response = openai.responses.create(
    model="gpt-4o-mini",
    input=[{"role": "user", "content": "5D가 뭐야?"}],
    conversation="conv_689667905b048191b4740501625afd940c7533ace33a2dab"
)
```

#### 방식 3: 수동 이력 관리 (기존 방식과 유사)

Chat Completions처럼 직접 이력을 관리하되, Responses API 형식 사용:

```python
inputs = [{"type": "message", "role": "user", "content": "첫 번째 질문"}]
response = client.responses.create(model="gpt-4o", input=inputs)

# 응답을 이력에 추가
inputs += response.output
inputs.append({"role": "user", "type": "message", "content": "후속 질문"})

second_response = client.responses.create(model="gpt-4o", input=inputs)
```

### 컨텍스트 압축 (Compaction)

긴 대화에서 컨텍스트 윈도우를 관리하기 위한 압축 기능을 제공한다:

- **수동 압축**: `client.responses.compact()` 호출
- **서버측 자동 압축**: `context_management`에 `compact_threshold` 설정

```python
response = client.responses.create(
    model="gpt-5.3-codex",
    input=conversation,
    store=False,
    context_management=[{"type": "compaction", "compact_threshold": 200000}],
)
```

### 주요 주의사항

- `previous_response_id`를 사용해도 **이전 모든 입력 토큰이 입력 토큰으로 과금**된다 (토큰 절약 아님)
- Response 객체는 기본 30일간 보관 (Conversation 객체는 보관 기한 없음)
- Reasoning 모델 사용 시 `previous_response_id`로 이전 reasoning items에 자동 접근 가능 -> 최대 성능 + 최저 비용

---

## 3. 이미지, PDF 등 파일 입력 지원

### 지원 파일 형식

| 파일 유형 | 처리 방식 |
|-----------|-----------|
| PDF | 텍스트 추출 + 각 페이지 이미지 (비전 모델 필요) |
| 이미지 (PNG, JPEG, WEBP, GIF) | 비전 모델로 직접 처리 |
| 문서 (.docx, .pptx, .txt) | 텍스트만 추출 (이미지/차트 미포함) |
| 스프레드시트 (.csv, .xlsx) | 시트당 최대 1,000행 파싱 + 헤더 메타데이터 |

### 파일 입력 방법 3가지

#### 방법 1: 외부 URL

```python
response = client.responses.create(
    model="gpt-4o",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "이 문서를 요약해줘"},
            {"type": "input_file", "file_url": "https://example.com/document.pdf"}
        ]
    }]
)
```

#### 방법 2: Files API를 통한 업로드

```python
file = client.files.create(
    file=open("document.pdf", "rb"),
    purpose="user_data"
)

response = client.responses.create(
    model="gpt-4o",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "이 문서를 분석해줘"},
            {"type": "input_file", "file_id": file.id}
        ]
    }]
)
```

#### 방법 3: Base64 인코딩

```python
import base64

with open("document.pdf", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

response = client.responses.create(
    model="gpt-4o",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "이 문서를 분석해줘"},
            {
                "type": "input_file",
                "filename": "document.pdf",
                "file_data": f"data:application/pdf;base64,{b64}"
            }
        ]
    }]
)
```

### 제약 사항

- 파일당 최대 50MB
- 요청당 전체 파일 합계 최대 50MB
- PDF 텍스트+이미지 처리에는 비전 지원 모델 필요 (gpt-4o 이상)
- .docx 등 비-PDF 파일은 임베디드 이미지/차트 미보존 -> PDF 변환 후 전송 권장

---

## 4. Python SDK에서 사용하는 방법

### 설치

```bash
pip install --upgrade openai
```

### OpenAI 직접 사용

```python
from openai import OpenAI

client = OpenAI()  # OPENAI_API_KEY 환경변수 자동 사용

# 기본 텍스트 생성
response = client.responses.create(
    model="gpt-5.2",
    input="한 문장으로 유니콘 이야기를 써줘"
)
print(response.output_text)
```

### Azure OpenAI 사용 (API Key)

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url="https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/",
)

response = client.responses.create(
    model="gpt-4.1-nano",  # 배포된 모델 이름으로 교체
    input="테스트입니다.",
)
print(response.output_text)
```

### Azure OpenAI 사용 (Microsoft Entra ID - 권장)

```python
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)

client = OpenAI(
    base_url="https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/",
    api_key=token_provider,
)

response = client.responses.create(
    model="gpt-4.1-nano",
    input="테스트입니다."
)
print(response.output_text)
```

### 스트리밍

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/",
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)

response = client.responses.create(
    input="테스트입니다",
    model="o4-mini",
    stream=True
)

for event in response:
    if event.type == 'response.output_text.delta':
        print(event.delta, end='')
```

### 비동기 스트리밍

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def main():
    stream = await client.responses.create(
        model="gpt-5.2",
        input="유니콘 이야기를 써줘",
        stream=True,
    )
    async for event in stream:
        print(event)

asyncio.run(main())
```

### Function Calling

```python
response = client.responses.create(
    model="gpt-4o",
    tools=[{
        "type": "function",
        "name": "get_weather",
        "description": "Get the weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"],
        },
    }],
    input=[{"role": "user", "content": "샌프란시스코 날씨 어때?"}],
)

# 함수 호출 결과 반환
input = []
for output in response.output:
    if output.type == "function_call":
        input.append({
            "type": "function_call_output",
            "call_id": output.call_id,
            "output": '{"temperature": "21도"}',
        })

second_response = client.responses.create(
    model="gpt-4o",
    previous_response_id=response.id,
    input=input
)
```

### 주요 SDK 메서드

| 메서드 | 설명 |
|--------|------|
| `client.responses.create()` | 응답 생성 |
| `client.responses.retrieve(id)` | 이전 응답 조회 |
| `client.responses.delete(id)` | 응답 삭제 |
| `client.responses.compact()` | 컨텍스트 압축 |
| `client.responses.input_items.list(id)` | 입력 항목 목록 조회 |

---

## 5. Azure OpenAI에서 Responses API 지원 현황

### 사용 가능 여부

Azure OpenAI에서 Responses API는 **일반 공급(GA)** 상태이며, 대부분의 주요 리전에서 사용 가능하다.

### 지원 모델 목록 (2026년 3월 기준)

#### GPT-5 시리즈
| 모델 | 버전 날짜 | 비고 |
|------|-----------|------|
| gpt-5.4 | 2026-03-05 | 최신 frontier 모델 |
| gpt-5.4-pro | 2026-03-05 | Pro 버전 |
| gpt-5.4-mini | 2026-03-17 | 경량 버전 |
| gpt-5.4-nano | 2026-03-17 | 초경량 버전 |
| gpt-5.3-codex | 2026-02-24 | 코딩 특화 |
| gpt-5.2-codex | 2026-01-14 | 코딩 특화 |
| gpt-5.2 | 2025-12-11 | |
| gpt-5.1 | 2025-11-13 | |
| gpt-5 | 2025-08-07 | |
| gpt-5-mini | 2025-08-07 | |
| gpt-5-nano | 2025-08-07 | |

#### O-시리즈 (추론 모델)
| 모델 | 비고 |
|------|------|
| o3 | 추론 모델 |
| o4-mini | 경량 추론 |
| o3-mini | 경량 추론 |
| o3-pro | East US2, Sweden Central |

#### GPT-4 시리즈 (레거시)
| 모델 | 비고 |
|------|------|
| gpt-4.1 | 2026년 중 retirement 예정 |
| gpt-4.1-mini | 2026년 중 retirement 예정 |
| gpt-4.1-nano | 2026년 중 retirement 예정 |
| gpt-4o | 지원 |
| gpt-4o-mini | 지원 |

#### 특수 모델
| 모델 | 비고 |
|------|------|
| computer-use-preview | 등록 필요, Microsoft 승인 기반 |
| codex-mini | East US2, Sweden Central |

### 주요 리전

- **권장**: East US2, Sweden Central
- **추가 지원**: South Central US, Poland Central 등
- 모델별 리전 가용성이 다르므로 공식 문서 확인 필요

### 배포 타입

Global Standard, Global Provisioned Managed, Global Batch, Data Zone 배포 모두 지원

### Azure 고유 참고사항

- Azure OpenAI에서는 `base_url`을 `https://{resource-name}.openai.azure.com/openai/v1/`로 설정
- 표준 `openai` Python 패키지 사용 (AzureOpenAI 클래스가 아닌 OpenAI 클래스 사용)
- Assistants API deprecated 영향: OpenAI 플랫폼의 Assistants API는 2026년 8월 26일 deprecated되지만, Azure OpenAI 서비스는 별도 운영이므로 직접적 영향 없음

---

## 6. GPT-5.2 모델 정보

### 기본 정보

| 항목 | 값 |
|------|-----|
| 출시일 | 2025년 12월 11일 |
| 모델 ID | gpt-5.2, gpt-5.2-2025-12-11 |
| 컨텍스트 윈도우 | 400,000 토큰 |
| 최대 출력 토큰 | 128,000 토큰 |
| 지식 컷오프 | 2025년 8월 31일 |
| 위치 | "이전 frontier 모델" (현재 최신은 gpt-5.4) |

### 모델 변형

- **gpt-5.2**: 기본 모델 (instant + thinking 모드)
- **gpt-5.2 instant**: 빠른 응답, 추론 없음
- **gpt-5.2 thinking**: 추론 모델 (standard/extended thinking)
- **gpt-5.2 pro**: 프리미엄 버전
- **gpt-5.2-codex**: 코딩 특화 (2026년 1월 14일 출시)

### Reasoning Effort 설정

`none` (기본), `low`, `medium`, `high`, `xhigh` 옵션으로 추론 강도 조절 가능

### 가격 (1M 토큰당)

| 항목 | 가격 |
|------|------|
| 입력 | $1.75 |
| 캐시된 입력 | $0.175 |
| 출력 | $14.00 |

### 주요 능력

- 스프레드시트 생성, 프레젠테이션 작성
- 코드 작성 및 디버깅
- 이미지 인식 (비전)
- 장문 컨텍스트 이해 (400K 토큰)
- 도구 사용
- 복잡한 멀티스텝 프로젝트 처리

### 후속 모델

| 모델 | 출시일 |
|------|--------|
| GPT-5.3-Codex | 2026년 2월 5일 |
| GPT-5.4 | 2026년 3월 5일 |
| GPT-5.4-mini/nano | 2026년 3월 17일 |

---

## 7. 기존 Chat Completions API 대비 장단점

### 장점

1. **서버측 상태 관리**: `previous_response_id`로 대화 이력을 서버에서 관리 -> 클라이언트 코드 단순화
2. **빌트인 도구**: Web Search, File Search, Code Interpreter, Computer Use, MCP 등 별도 구현 없이 사용 가능
3. **파일 직접 입력**: PDF, 이미지 등을 전처리 없이 API에 직접 전달
4. **더 나은 추론 성능**: 추론 모델(GPT-5 등) 사용 시 Chat Completions 대비 3% 향상 (SWE-bench 기준)
5. **캐시 활용률 향상**: 내부 테스트 기준 40~80% 향상 -> 비용 절감
6. **컨텍스트 압축(Compaction)**: 긴 대화의 컨텍스트 윈도우를 효율적으로 관리
7. **통합 API**: Assistants API의 기능 (상태 관리, 도구)과 Chat Completions의 단순함을 결합
8. **응답 조회/삭제**: 이전 응답을 ID로 조회하거나 삭제 가능

### 단점

1. **토큰 비용 절감 아님**: `previous_response_id` 사용해도 이전 전체 입력 토큰이 과금됨 (서버측 편의성일 뿐)
2. **병렬 생성 불가**: Chat Completions의 `n` 파라미터 (복수 후보 생성) 미지원
3. **데이터 저장 기본값**: 기본적으로 응답이 30일간 서버에 저장됨 -> 데이터 보안 고려 필요 (`store: false` 설정 필수)
4. **마이그레이션 부담**: 기존 Chat Completions 기반 시스템의 코드 수정 필요 (파라미터명, 응답 구조 변경)
5. **서비스 안정성 이슈**: `store: true` 사용 시 간헐적 에러율 증가 보고 사례 있음
6. **모델 전환 제약**: `previous_response_id` 체이닝 시 다른 모델로 전환하면 이전 모델 응답에 접근 불가
7. **Azure 리전 제한**: 모든 Azure 리전에서 사용 가능하지 않음 (권장: East US2, Sweden Central)
8. **생태계 성숙도**: 비교적 새로운 API이므로 서드파티 라이브러리/프레임워크 지원이 Chat Completions 대비 부족할 수 있음

### 권장 사항

| 상황 | 권장 API |
|------|---------|
| 신규 프로젝트 | **Responses API** |
| 기존 Chat Completions 프로젝트 | 당분간 Chat Completions 유지 (deprecated 아님) |
| 에이전트/도구 사용 필요 | **Responses API** (빌트인 도구 활용) |
| 멀티턴 대화 중심 | **Responses API** (`previous_response_id` 활용) |
| 단순 단발성 질의 | 어느 쪽이든 무방 (Responses가 조금 더 깔끔) |

---

## 8. AISE 2.0 프로젝트에 대한 시사점

### AI 어시스트 서비스 구현 시

- Responses API를 사용하면 요구사항 보완/제안 시 멀티턴 대화를 `previous_response_id`로 간편하게 구현 가능
- Function Calling을 통해 구조화된 AI 피드백을 받을 수 있음
- `instructions` 파라미터로 시스템 프롬프트를 깔끔하게 분리 가능

### SRS 생성 시

- 긴 요구사항 목록을 파일로 직접 전달 가능 (PDF/텍스트)
- 400K 토큰 컨텍스트 윈도우 (GPT-5.2)로 대규모 요구사항도 한 번에 처리 가능
- Structured Outputs으로 SRS 섹션별 구조화된 JSON 응답 수신 가능

### 추천 모델 선택

| 용도 | 추천 모델 | 근거 |
|------|-----------|------|
| AI 어시스트 (보완/제안) | gpt-5-mini 또는 gpt-5-nano | 빠른 응답, 낮은 비용, 충분한 품질 |
| SRS 생성 | gpt-5 또는 gpt-5.2 | 고품질 장문 생성, 400K 컨텍스트 |
| 품질 체크 | gpt-5-mini | 빠른 검증, 비용 효율적 |

### API 코드 구조 제안

```python
# Azure OpenAI + Responses API 기본 설정
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=f"https://{os.getenv('AZURE_OPENAI_RESOURCE')}.openai.azure.com/openai/v1/",
)

# AI 어시스트 - 요구사항 보완 제안
response = client.responses.create(
    model="gpt-5-mini",
    instructions="당신은 소프트웨어 요구사항 분석 전문가입니다...",
    input=[{
        "role": "user",
        "content": f"다음 요구사항을 분석하고 누락된 항목을 지적해주세요:\n{requirements_text}"
    }],
    text={"format": {"type": "json_schema", "json_schema": {...}}}
)
```

---

## 참고 링크

- [Azure OpenAI Responses API 사용법](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses)
- [OpenAI Conversation State 가이드](https://developers.openai.com/api/docs/guides/conversation-state)
- [Chat Completions에서 Responses API 마이그레이션](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Responses vs Chat Completions 비교](https://platform.openai.com/docs/guides/responses-vs-chat-completions)
- [OpenAI 파일 입력 가이드](https://developers.openai.com/api/docs/guides/pdf-files)
- [GPT-5.2 모델 정보](https://developers.openai.com/api/docs/models/gpt-5.2)
- [Azure OpenAI 지원 모델 목록](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure)
- [Responses API 새 도구/기능 발표](https://openai.com/index/new-tools-and-features-in-the-responses-api/)
- [Azure OpenAI Responses API 샘플 코드 (GitHub)](https://github.com/Azure-Samples/azure-openai-responses-api-samples)
- [Simon Willison의 Responses vs Chat Completions 분석](https://simonwillison.net/2025/Mar/11/responses-vs-chat-completions/)
