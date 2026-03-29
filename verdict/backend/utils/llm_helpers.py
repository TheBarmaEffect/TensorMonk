"""Shared LLM utilities — DRY helpers used across all agent implementations.

Consolidates repeated patterns found in every agent:
1. JSON response parsing (markdown fence stripping + fallback)
2. Thinking phase streaming (emit sequential phase events with delay)
3. LLM factory (consistent ChatGroq initialization)
4. Low-temperature retry (hallucination guard fallback)
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage

from config import settings
from models.schemas import StreamEvent
from utils.resilience import retry_with_backoff, CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

# Module-level circuit breaker for LLM calls — opens after 5 consecutive
# failures and rejects calls for 30 seconds to avoid cascading failures.
_llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5, recovery_timeout=30.0, name="llm"
)


def parse_llm_json(
    response: str,
    fallback: Optional[dict] = None,
    operation_name: str = "LLM",
) -> dict:
    """Parse JSON from an LLM response, stripping markdown code fences.

    Handles the common case where LLMs wrap JSON in ```json ... ``` blocks
    despite being told not to. Falls back to the provided dict on parse failure.

    This consolidates the _parse_json / _parse_response methods that were
    duplicated across all 6 agents (prosecutor, defense, judge, witness,
    research, synthesis).

    Args:
        response: Raw LLM response text.
        fallback: Dict to return if JSON parsing fails. Defaults to empty dict.
        operation_name: Name for log messages on parse failure.

    Returns:
        Parsed dict or fallback.
    """
    cleaned = response.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse %s JSON response", operation_name)
        return fallback if fallback is not None else {}


async def emit_thinking_phases(
    phases: list[str],
    agent_name: str,
    event_type: str,
    stream_callback: Optional[Callable] = None,
    delay: float = 0.3,
) -> None:
    """Emit a sequence of thinking phases via the stream callback.

    Every agent emits a series of "thinking" phases to give the frontend
    a sense of progress. This consolidates the repeated for-loop pattern
    found in all 6 agents.

    Args:
        phases: List of phase description strings.
        agent_name: Agent identifier for the StreamEvent.
        event_type: Event type string (e.g., "prosecutor_thinking").
        stream_callback: Async callback to emit StreamEvents.
        delay: Seconds to pause between phases (simulates thinking).
    """
    for phase in phases:
        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type=event_type,
                    agent=agent_name,
                    content=phase + "\n",
                )
            )
            await asyncio.sleep(delay)


def create_llm(
    temperature: float = 0.7,
    max_tokens: int = 2048,
    model: str = "llama-3.3-70b-versatile",
) -> ChatGroq:
    """Factory for consistently configured Groq LLM instances.

    Centralizes LLM initialization that was duplicated across all agents.
    Each agent can customize temperature and max_tokens while sharing
    the same model and API key configuration.

    Args:
        temperature: Sampling temperature [0.0-1.0].
        max_tokens: Maximum output tokens.
        model: Groq model identifier.

    Returns:
        Configured ChatGroq instance.
    """
    return ChatGroq(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.groq_api_key,
    )


async def retry_with_low_temperature(
    messages: list[BaseMessage],
    parse_fn: Callable[[str], Any],
    quality_check_fn: Callable[[Any], bool],
    max_tokens: int = 2048,
    operation_name: str = "LLM",
) -> Any:
    """Retry an LLM call with temperature=0.3 if initial output fails quality check.

    Implements the hallucination guard pattern used by prosecutor, defense,
    and synthesis agents: if the initial parse produces low-quality output,
    retry with a lower temperature for more deterministic results.

    Args:
        messages: The LLM message list to resend.
        parse_fn: Function that parses response.content into the target type.
        quality_check_fn: Returns True if the parsed output is acceptable.
        max_tokens: Token limit for the retry LLM.
        operation_name: Human-readable name for logging.

    Returns:
        Parsed output from the successful attempt.
    """
    logger.warning("%s output failed quality check, retrying with temperature=0.3", operation_name)
    retry_llm = create_llm(temperature=0.3, max_tokens=max_tokens)
    retry_response = await call_llm_with_resilience(
        retry_llm.ainvoke, messages,
        max_retries=1, base_delay=0.5,
        operation_name=f"{operation_name} (low-temp retry)",
    )
    return parse_fn(retry_response.content)


async def call_llm_with_resilience(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    operation_name: str = "LLM",
    **kwargs: Any,
) -> Any:
    """Execute an LLM call with circuit breaker + retry-with-backoff.

    Combines two resilience layers:
    1. Circuit breaker — fails fast when the LLM provider is unhealthy.
    2. Retry with exponential backoff — handles transient failures.

    Args:
        fn: Async callable (e.g. ``llm.ainvoke``).
        *args: Positional args forwarded to *fn*.
        max_retries: Max retry attempts for backoff.
        base_delay: Initial backoff delay in seconds.
        operation_name: Human-readable label for logging.
        **kwargs: Keyword args forwarded to *fn*.

    Returns:
        The result of the successful function call.

    Raises:
        CircuitOpenError: If the circuit breaker is open.
    """
    async def _guarded(*a: Any, **kw: Any) -> Any:
        return await _llm_circuit_breaker.call(fn, *a, **kw)

    return await retry_with_backoff(
        _guarded, *args,
        max_retries=max_retries,
        base_delay=base_delay,
        operation_name=operation_name,
        retryable_exceptions=(Exception,),
        **kwargs,
    )
