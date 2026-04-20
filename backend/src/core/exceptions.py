from fastapi import Request
from fastapi.responses import JSONResponse

from loguru import logger


async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리 핸들러"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


class AppException(Exception):
    """애플리케이션 커스텀 예외 베이스 클래스"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


async def app_exception_handler(request: Request, exc: AppException):
    """커스텀 예외 처리 핸들러"""
    logger.warning(f"AppException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
