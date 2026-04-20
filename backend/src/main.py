# ============================================
# FastAPI Boilerplate
# ============================================
# 1. 프로젝트 초기화
#    uv init --python=3.11
#
# 2. 의존성 설치
#    uv add "fastapi[standard]" "loguru"
#
# 3. 서버 실행
#    uv run uvicorn src.main:app --port=8081 --reload --host 0.0.0.0
# ============================================

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from src.core.cors import setup_cors
from src.core.exceptions import (
    AppException,
    app_exception_handler,
    global_exception_handler,
)
from src.core.logging import setup_logging
from src.middleware import LoggingMiddleware
from src.routers import sample_router, dev_chat_router, project_router, requirement_router, glossary_router, assist_router, review_router, section_router, knowledge_router, agent_router, record_router, srs_router, session_router

# 로깅 초기화 (앱 시작 시점에 명시적으로 실행)
setup_logging()

app = FastAPI()

# 예외 핸들러 등록
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(AppException, app_exception_handler)

# 미들웨어 등록
setup_cors(app)
app.add_middleware(LoggingMiddleware)

# 라우터 등록
app.include_router(sample_router)
app.include_router(dev_chat_router)
app.include_router(project_router)
app.include_router(requirement_router)
app.include_router(glossary_router)
app.include_router(assist_router)
app.include_router(review_router)
app.include_router(section_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(record_router)
app.include_router(srs_router)
app.include_router(session_router)
