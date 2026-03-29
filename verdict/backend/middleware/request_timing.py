"""Request timing and correlation ID middleware for FastAPI.

Adds production-grade observability headers to every response:
- X-Request-ID: Unique identifier for request tracing across services
- X-Response-Time: Server-side processing duration in milliseconds

The correlation ID is either extracted from the incoming X-Request-ID header
(for distributed tracing) or generated as a new UUID.
"""

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID and X-Response-Time headers to all responses.

    Usage:
        app.add_middleware(RequestTimingMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Extract or generate correlation ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:12])
        start_time = time.monotonic()

        response = await call_next(request)

        # Calculate processing time
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        # Add observability headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Log slow requests (>5s) as warnings for monitoring
        if duration_ms > 5000:
            logger.warning(
                "Slow request: %s %s took %.0fms [%s]",
                request.method, request.url.path, duration_ms, request_id,
            )
        else:
            logger.debug(
                "%s %s completed in %.0fms [%s]",
                request.method, request.url.path, duration_ms, request_id,
            )

        return response
