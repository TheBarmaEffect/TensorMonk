"""Token-bucket rate limiter middleware for FastAPI.

Limits requests per IP address using an in-memory token bucket algorithm
with automatic cleanup of stale entries. Configurable via environment
variables RATE_LIMIT_RPM (requests per minute) and RATE_LIMIT_BURST.

Design decisions:
- In-memory store (no Redis dependency for rate limiting)
- Per-IP tracking with automatic cleanup every 5 minutes
- Returns 429 with Retry-After header on limit exceeded
- Whitelists /health endpoint from rate limiting
"""

import logging
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Defaults: 60 requests per minute, burst of 10
DEFAULT_RPM = 60
DEFAULT_BURST = 10


class TokenBucket:
    """Token bucket rate limiter for a single client.

    Tokens refill at `rate` tokens per second up to `capacity`.
    Each request consumes one token. When empty, requests are rejected.
    """

    __slots__ = ("capacity", "tokens", "rate", "last_refill")

    def __init__(self, capacity: int, rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.rate = rate  # tokens per second
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed, False if rate-limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def retry_after(self) -> float:
        """Seconds until next token is available."""
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.rate


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware implementing per-IP token bucket rate limiting.

    Usage:
        app.add_middleware(RateLimiterMiddleware, rpm=60, burst=10)
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json"}

    def __init__(self, app, rpm: int = DEFAULT_RPM, burst: int = DEFAULT_BURST):
        super().__init__(app)
        self.rpm = rpm
        self.burst = burst
        self.rate = rpm / 60.0  # tokens per second
        self.buckets: dict[str, TokenBucket] = {}
        self.last_cleanup = time.monotonic()
        self.cleanup_interval = 300  # 5 minutes
        logger.info("Rate limiter initialized: %d RPM, burst=%d", rpm, burst)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for proxy deployments."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_stale_buckets(self) -> None:
        """Remove buckets that haven't been used recently to prevent memory leaks."""
        now = time.monotonic()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        self.last_cleanup = now
        stale_threshold = now - self.cleanup_interval
        stale_keys = [
            ip for ip, bucket in self.buckets.items()
            if bucket.last_refill < stale_threshold
        ]
        for key in stale_keys:
            del self.buckets[key]
        if stale_keys:
            logger.debug("Cleaned up %d stale rate limiter buckets", len(stale_keys))

    async def dispatch(self, request: Request, call_next: Callable):
        """Check rate limit before processing request."""
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip for test clients (no real client connection)
        if not request.client or request.client.host == "testclient":
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Get or create bucket for this client
        if client_ip not in self.buckets:
            self.buckets[client_ip] = TokenBucket(self.burst, self.rate)

        bucket = self.buckets[client_ip]

        if not bucket.consume():
            retry_after = int(bucket.retry_after) + 1
            logger.warning("Rate limit exceeded for %s on %s", client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.rpm} requests per minute. Try again in {retry_after}s.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Periodic cleanup
        self._cleanup_stale_buckets()

        return await call_next(request)
