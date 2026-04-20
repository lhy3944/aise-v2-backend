import os
import sys
from pathlib import Path

from loguru import logger


# 환경변수 가져오기 : 환경변수에 따라 diagnose enable 결정
env = os.getenv("ENVIRONMENT", "local").lower()
is_dev = env not in ("prod", "production", "staging")

# 로그 레벨 설정 (환경변수로 오버라이드 가능)
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if is_dev else "INFO").upper()

def setup_logging():
    logger.remove()  # 기존 핸들러 제거 (중복 로깅 방지)
    logger.configure(extra={"request_id": "-"})  # 기본 extra 필드 설정


    # 공통 설정
    common_config = {
        "enqueue": True,  # 비동기 로깅 활성화 (여러 사용자 동기 로깅 대비)
        "backtrace": True,  # ✅ 항상 True (스택 트레이스는 필수)
        "diagnose": is_dev,  # ⚠️ 개발 환경에서만 True
    }

    # 로그 디렉토리 생성
    log_dir = Path("var/logs")
    log_dir.mkdir(parents=True, exist_ok=True)


    log_file = "var/logs/app.log"
    serialize_log_file = "var/logs/app.json"

    # log format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<yellow>[{extra[request_id]: <8}]</yellow> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        log_file,
        rotation="00:00",  # 매일 새로운 파일 생성
        retention="7 days",  # 7일 이상 지난 파일 삭제
        format=log_format,
        level=LOG_LEVEL,
        **common_config,
    )
    # serialize로 로그 파일 생성
    # format 설정이 의미 없으므로 설정하지 않습니다.
    logger.add(
        serialize_log_file,
        serialize=True,
        rotation="00:00",  # 매일 새로운 파일 생성
        retention="7 days",  # 7일 이상 지난 파일 삭제
        level=LOG_LEVEL,
        **common_config,
    )

    logger.add(sys.stderr, format=log_format, level=LOG_LEVEL, colorize=True, **common_config)

    return logger
