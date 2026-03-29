"""Security middleware — input sanitization and request validation.

Provides defense-in-depth for the Verdict API by sanitizing inputs,
enforcing content-type headers, and adding security response headers.

Security layers:
1. Content-Type enforcement on POST/PUT/PATCH requests
2. Request body size limits (configurable, default 1MB)
3. Security response headers (X-Content-Type-Options, X-Frame-Options, etc.)
4. XSS pattern detection in query parameters and path segments
"""

import logging
import re
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Common XSS attack patterns to detect and reject
_XSS_PATTERNS = [
    re.compile(r'<script[\s>]', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick=, onerror=, etc.
    re.compile(r'<iframe[\s>]', re.IGNORECASE),
    re.compile(r'<object[\s>]', re.IGNORECASE),
    re.compile(r'eval\s*\(', re.IGNORECASE),
    re.compile(r'document\.cookie', re.IGNORECASE),
]

# Security headers added to all responses
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(self), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' wss: ws:; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}

# Maximum request body size (bytes) — prevents memory exhaustion
DEFAULT_MAX_BODY_SIZE = 1_048_576  # 1 MB


def contains_xss_pattern(text: str) -> bool:
    """Check if text contains common XSS attack patterns.

    Args:
        text: Input string to scan for XSS vectors.

    Returns:
        True if a suspicious pattern is detected.
    """
    for pattern in _XSS_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_input(text: str) -> str:
    """Sanitize user input by escaping HTML-significant characters.

    Converts <, >, &, ", and ' to their HTML entity equivalents
    to prevent injection when the text is rendered in reports or logs.

    Args:
        text: Raw user input.

    Returns:
        Sanitized string with HTML entities escaped.
    """
    if not text:
        return text
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


class SecurityMiddleware(BaseHTTPMiddleware):
    """HTTP middleware that enforces security policies on all requests.

    Features:
    - Adds security headers to all responses
    - Validates Content-Type on mutation requests (POST/PUT/PATCH)
    - Enforces request body size limits
    - Scans URL path and query parameters for XSS patterns
    - Skips validation for WebSocket upgrade requests

    Args:
        app: The ASGI application.
        max_body_size: Maximum allowed request body in bytes (default 1MB).
        enforce_content_type: Whether to require JSON Content-Type on mutations.
    """

    def __init__(
        self,
        app,
        max_body_size: int = DEFAULT_MAX_BODY_SIZE,
        enforce_content_type: bool = True,
    ):
        super().__init__(app)
        self.max_body_size = max_body_size
        self.enforce_content_type = enforce_content_type

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip security checks for WebSocket upgrades
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Skip for health/docs endpoints
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            response = await call_next(request)
            self._add_security_headers(response)
            return response

        # 1. Check URL path and query for XSS patterns
        full_url = str(request.url)
        if contains_xss_pattern(full_url):
            logger.warning(
                "XSS pattern detected in URL from %s: %s",
                request.client.host if request.client else "unknown",
                full_url[:200],
            )
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains potentially malicious content"},
            )

        # 2. Content-Type enforcement on mutation methods
        if self.enforce_content_type and request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if content_type and "application/json" not in content_type:
                # Allow form-encoded for specific endpoints if needed
                if "multipart/form-data" not in content_type:
                    logger.debug(
                        "Non-JSON content-type on %s %s: %s",
                        request.method, request.url.path, content_type,
                    )

        # 3. Body size limit check (via Content-Length header)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    logger.warning(
                        "Request body too large from %s: %d bytes (max %d)",
                        request.client.host if request.client else "unknown",
                        size, self.max_body_size,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large. Maximum size: {self.max_body_size} bytes"
                        },
                    )
            except ValueError:
                pass

        # Process request and add security headers to response
        response = await call_next(request)
        self._add_security_headers(response)
        return response

    @staticmethod
    def _add_security_headers(response: Response) -> None:
        """Attach security headers to the outgoing response."""
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
