import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from loguru import logger

from src.core.exceptions import AppException


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 각 요청에 고유 ID 할당
        request_id = str(uuid.uuid4())[:8]

        with logger.contextualize(request_id=request_id):
            logger.info(f"Request: {request.method} {request.url.path}")
            start_time = time.time()

            # 다음 미들웨어 또는 엔드포인트 실행
            try:
                response = await call_next(request)
                process_time = (time.time() - start_time) * 1000  # 밀리초 단위
                logger.info(f"Response: Status={response.status_code} (took: {process_time:.2f}ms)")

                return response
            except AppException as e:
                # 애플리케이션 예외는 적절한 상태 코드로 반환
                process_time = (time.time() - start_time) * 1000
                logger.warning(f"AppException: {e.detail}")
                logger.info(f"Response: Status={e.status_code} (took: {process_time:.2f}ms)")
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail},
                )
            except Exception as e:
                # BaseHTTPMiddleware 특성상 exception handler로 전달되지 않으므로
                # 여기서 직접 500 응답을 반환한다.
                process_time = (time.time() - start_time) * 1000
                logger.exception(f"Unhandled exception: {e}")
                logger.info(f"Response: Status=500 (took: {process_time:.2f}ms)")
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Internal Server Error"},
                )
