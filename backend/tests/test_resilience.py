"""Tests for resilience patterns — retry with backoff and circuit breaker."""

import asyncio
import pytest
from utils.resilience import retry_with_backoff, CircuitBreaker, CircuitState, CircuitOpenError


class TestRetryWithBackoff:
    """Verify exponential backoff retry logic."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(succeed, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "recovered"

        result = await retry_with_backoff(
            fail_then_succeed, max_retries=3, base_delay=0.01, max_delay=0.05
        )
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        async def always_fail():
            raise RuntimeError("permanent error")

        with pytest.raises(RuntimeError, match="permanent error"):
            await retry_with_backoff(
                always_fail, max_retries=2, base_delay=0.01, max_delay=0.02
            )

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        call_count = 0

        async def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            await retry_with_backoff(
                raise_type_error,
                max_retries=3,
                base_delay=0.01,
                retryable_exceptions=(ValueError,),
            )
        # Should not retry because TypeError is not in retryable_exceptions
        assert call_count == 1


class TestCircuitBreaker:
    """Verify circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0, name="test")

        async def fail():
            raise RuntimeError("error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_rejects_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0, name="test")

        async def fail():
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError):
            await cb.call(fail)

    @pytest.mark.asyncio
    async def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3, name="test")

        async def succeed():
            return "ok"

        result = await cb.call(succeed)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0, name="test")

        async def fail():
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01, name="test")

        async def fail():
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert cb.state == CircuitState.OPEN
        await asyncio.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
