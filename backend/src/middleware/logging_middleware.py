import time
import uuid

from loguru import logger
from starlette.types import ASGIApp, Receive, Scope, Send

from src.core.exceptions import AppException


class LoggingMiddleware:
    """순수 ASGI 로깅 미들웨어.

    BaseHTTPMiddleware는 SSE 스트리밍과 충돌하여 CancelledError를 유발한다.
    (Starlette의 cancel scope가 SSE 응답 완료 후 DB 연결 종료를 취소시킴)
    따라서 BaseHTTPMiddleware 대신 순수 ASGI 미들웨어로 구현한다.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())[:8]
        path = scope.get("path", "")
        method = scope.get("method", "")

        with logger.contextualize(request_id=request_id):
            logger.info(f"Request: {method} {path}")
            start_time = time.time()
            status_code: int | None = None

            async def send_wrapper(message: dict) -> None:
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message.get("status")
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            except AppException as e:
                process_time = (time.time() - start_time) * 1000
                logger.warning(f"AppException: {e.detail}")
                logger.info(f"Response: Status={e.status_code} (took: {process_time:.2f}ms)")
                raise
            except Exception as e:
                process_time = (time.time() - start_time) * 1000
                logger.exception(f"Unhandled exception: {e}")
                logger.info(f"Response: Status=500 (took: {process_time:.2f}ms)")
                raise

            if status_code is not None:
                process_time = (time.time() - start_time) * 1000
                logger.info(f"Response: Status={status_code} (took: {process_time:.2f}ms)")
