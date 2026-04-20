import time
import uuid

from loguru import logger


class LoggingASGIMiddleware:
    """
    Pure ASGI 방식의 로깅 미들웨어
    - BaseHTTPMiddleware보다 빠름
    - 코드가 복잡하지만 저수준 제어 가능
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # HTTP 요청만 처리 (websocket, lifespan 등은 패스)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 요청 정보 추출
        request_id = str(uuid.uuid4())[:8]
        method = scope["method"]
        path = scope["path"]

        start_time = time.time()
        status_code = None

        # 응답 status_code 캡처를 위한 래퍼
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        # 로깅 컨텍스트 설정
        with logger.contextualize(request_id=request_id):
            logger.info(f"Request: {method} {path}")

            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as e:
                process_time = (time.time() - start_time) * 1000
                logger.error(f"Error: {e} (took: {process_time:.2f}ms)")
                raise e

            process_time = (time.time() - start_time) * 1000
            logger.info(f"Response: Status={status_code} (took: {process_time:.2f}ms)")
