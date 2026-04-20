import os

from fastapi.middleware.cors import CORSMiddleware


# =============================================================================
# CORS (Cross-Origin Resource Sharing) 미들웨어 설정
# =============================================================================
# CORS란?
#   - 브라우저가 다른 도메인(Origin)의 리소스에 접근할 때 적용되는 보안 정책
#   - 예: http://localhost:3000 (프론트엔드) → http://localhost:8081 (백엔드) 요청 시 필요
#
# 동작 방식:
#   1. 브라우저가 OPTIONS 요청(Preflight)을 먼저 보내 서버가 허용하는지 확인
#   2. 서버가 허용하면 실제 요청(GET, POST 등)을 보냄
#
# 주의: allow_credentials=True와 allow_origins=["*"]는 함께 사용할 수 없음
#   - 브라우저가 credentials 요청 시 와일드카드 origin을 거부함
#   - 반드시 구체적인 origin을 명시해야 함
# =============================================================================

_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

_origins_env = os.getenv("CORS_ORIGINS", _DEFAULT_ORIGINS)
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

# 개발 환경: 모든 localhost/내부IP의 3000 포트를 허용
_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.\d+\.\d+\.\d+|[\w-]+\.devbanjang\.cloud)(:\d+)?$",
)

CORS_CONFIG = {
    "allow_origins": ALLOWED_ORIGINS,
    "allow_origin_regex": _ORIGIN_REGEX,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "max_age": 600,
}


def setup_cors(app):
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)
