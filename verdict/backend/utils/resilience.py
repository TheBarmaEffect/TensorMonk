"""Resilience patterns for LLM calls — retry with backoff and circuit breaker.

Provides production-grade fault tolerance for external API calls:
- Exponential backoff with jitter to prevent thundering herd
- Circuit breaker to fail fast when a dependency is unhealthy
- Configurable retry counts, delays, and failure thresholds

Design decisions:
- Async-native (all patterns are async-first)
- Jitter uses random offset (0-50% of delay) to distribute retries
- Circuit breaker has 3 states: CLOSED (healthy), OPEN (failing), HALF_OPEN (testing)
- Half-open state allows one probe request through to test recovery
"""

import asyncio
import logging
import random
import time
from enum import Enum
from typing import TypeVar, Callable, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 15.0,
    retryable_exceptions: tuple = (Exception,),
    operation_name: str = "LLM call",
    **kwargs: Any,
) -> Any:
    """Execute an async function with exponential backoff retry.

    Args:
        fn: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles each retry)
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Tuple of exception types that trigger a retry
        operation_name: Human-readable name for logging

    Returns:
        The result of the successful function call

    Raises:
        The last exception if all retries are exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(
                    "[%s] Failed after %d attempts: %s",
                    operation_name, max_retries + 1, str(e),
                )
                raise

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.5)
            total_delay = delay + jitter

            logger.warning(
                "[%s] Attempt %d/%d failed (%s), retrying in %.1fs",
                operation_name, attempt + 1, max_retries + 1, type(e).__name__, total_delay,
            )
            await asyncio.sleep(total_delay)

    raise last_exception  # type: ignore[misc]


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation — requests flow through
    OPEN = "open"           # Failing — requests rejected immediately
    HALF_OPEN = "half_open" # Testing — one probe request allowed


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Tracks consecutive failures and opens the circuit when a threshold
    is exceeded, preventing cascading failures. Automatically tests
    recovery after a cooldown period.

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        result = await breaker.call(some_async_function, arg1, arg2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, accounting for recovery timeout."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("[CircuitBreaker:%s] Transitioning to HALF_OPEN", self.name)
        return self._state

    async def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function through the circuit breaker.

        Raises:
            CircuitOpenError: If the circuit is open (dependency unhealthy)
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit breaker '{self.name}' is OPEN — "
                f"{self._failure_count} consecutive failures. "
                f"Recovery in {self.recovery_timeout - (time.monotonic() - self._last_failure_time):.0f}s"
            )

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Record a successful call — reset failure count, close circuit."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("[CircuitBreaker:%s] Recovery confirmed, closing circuit", self.name)
        self._failure_count = 0
        self._success_count += 1
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """Record a failed call — increment counter, potentially open circuit."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                "[CircuitBreaker:%s] Circuit OPENED after %d failures",
                self.name, self._failure_count,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        logger.info("[CircuitBreaker:%s] Manually reset", self.name)

    def summary(self) -> dict[str, Any]:
        """Return circuit breaker status for health checks and metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_s": self.recovery_timeout,
        }


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open and rejecting requests."""
    pass
