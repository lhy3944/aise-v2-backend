# FastAPI Boilerplate

프로덕션 레벨의 FastAPI 보일러플레이트입니다.

## 주요 기능

- ✅ **로깅** - Loguru 기반, 환경별 설정, JSON 로그 지원
- ✅ **미들웨어** - 요청/응답 로깅, request_id 추적
- ✅ **CORS** - 설정 분리
- ✅ **예외 처리** - 전역 예외 핸들러, 커스텀 예외 클래스
- ✅ **라우터 구조** - 표준적인 폴더 구조

## 프로젝트 구조

```
src/
├── main.py                 # 앱 진입점
├── core/
│   ├── cors.py             # CORS 설정
│   ├── logging.py          # Loguru 설정
│   └── exceptions.py       # 예외 핸들러
├── middleware/
│   ├── __init__.py
│   └── logging_middleware.py
└── routers/
    ├── __init__.py
    └── sample.py
```

## 시작하기

### 1. 프로젝트 초기화

```bash
uv init --python=3.11
```

### 2. 의존성 설치

```bash
uv add "fastapi[standard]" "loguru"
```

### 3. 서버 실행

```bash
uv run uvicorn src.main:app --port=8081 --reload --host 0.0.0.0
```

### 4. API 확인

- Swagger UI: http://localhost:8081/docs
- Sample API: http://localhost:8081/api/v1/sample/

## 환경 변수

`.env.example`을 참고하여 `.env` 파일을 생성하세요.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ENVIRONMENT` | `local` | 환경 (local, dev, staging, prod) |
| `LOG_LEVEL` | `DEBUG` | 로그 레벨 (DEBUG, INFO, WARNING, ERROR) |

## 커스텀 예외 사용법

```python
from src.core.exceptions import AppException

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = find_user(user_id)
    if not user:
        raise AppException(status_code=404, detail="User not found")
    return user
```

## 라이선스

MIT
