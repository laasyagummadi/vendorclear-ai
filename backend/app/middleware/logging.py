# ─────────────────────────────────────────────────────────────
#  app/middleware/logging.py  —  HTTP request/response logger
# ─────────────────────────────────────────────────────────────
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()

        # Log incoming request
        logger.debug(f"→ {request.method} {request.url.path}")

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(
                f"✗ {request.method} {request.url.path} "
                f"— ERROR in {elapsed:.1f}ms: {exc}"
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        status = response.status_code

        # Choose log level based on status code
        if status >= 500:
            log = logger.error
        elif status >= 400:
            log = logger.warning
        else:
            log = logger.info

        log(
            f"← {request.method} {request.url.path} "
            f"[{status}] {elapsed:.1f}ms"
        )

        # Add timing header
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
        return response
