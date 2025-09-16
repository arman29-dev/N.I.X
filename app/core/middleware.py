from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from logging import getLogger
from time import time


logger = getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time()

        logger.info(f"Incoming request: {request.method} {request.url} from {request.client.host if request.client else 'unknown'}")

        response = await call_next(request)
        process_time = time() - start_time

        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url}"
            f" processed in {process_time:.4f}s"
        )

        return response
