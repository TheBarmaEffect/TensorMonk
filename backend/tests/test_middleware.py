"""Tests for rate limiter middleware — token bucket algorithm and edge cases."""

import pytest
from middleware.rate_limiter import TokenBucket, RateLimiterMiddleware


class TestTokenBucket:
    """Verify token bucket rate limiting logic."""

    def test_allows_requests_within_limit(self):
        bucket = TokenBucket(capacity=5, rate=1.0)
        for _ in range(5):
            assert bucket.consume() is True

    def test_rejects_when_empty(self):
        bucket = TokenBucket(capacity=2, rate=0.01)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_retry_after_positive_when_empty(self):
        bucket = TokenBucket(capacity=1, rate=1.0)
        bucket.consume()  # use the token
        bucket.consume()  # try again
        assert bucket.retry_after > 0

    def test_retry_after_zero_when_tokens_available(self):
        bucket = TokenBucket(capacity=5, rate=1.0)
        assert bucket.retry_after == 0.0

    def test_capacity_does_not_exceed_max(self):
        bucket = TokenBucket(capacity=3, rate=100.0)
        import time
        time.sleep(0.05)  # Would add 5 tokens at rate=100
        bucket.consume()
        # Should still have at most capacity (3) tokens
        assert bucket.tokens <= 3.0


class TestRateLimiterMiddleware:
    """Verify middleware configuration and exempt paths."""

    def test_exempt_paths_include_health(self):
        assert "/health" in RateLimiterMiddleware.EXEMPT_PATHS

    def test_exempt_paths_include_docs(self):
        assert "/docs" in RateLimiterMiddleware.EXEMPT_PATHS
