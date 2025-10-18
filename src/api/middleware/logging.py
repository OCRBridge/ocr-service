"""Request logging middleware with structured logging."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with structured data."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Bind request context to logger
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Start timing
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000

            # Log successful request
            logger.info(
                "request_completed",
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            # Log failed request
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                latency_ms=round(latency_ms, 2),
            )
            raise
