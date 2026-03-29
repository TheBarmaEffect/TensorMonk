"""Structured logging with session correlation IDs.

Provides async-safe context propagation for session_id across all log messages
within a request/WebSocket lifecycle. Uses Python contextvars for thread-safe
async context management.

Usage:
    from utils.logging import set_session_context, get_session_logger

    set_session_context("session-123")
    logger = get_session_logger(__name__)
    logger.info("Processing verdict")
    # Output: 2026-03-29 [INFO] module: [session-123] Processing verdict
"""

import contextvars
import logging
from typing import Optional

# Async-safe context variable for session tracking
_session_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "session_id", default=None
)


def set_session_context(session_id: str) -> contextvars.Token:
    """Set the session ID for the current async context.

    Args:
        session_id: The verdict session ID to attach to all log messages

    Returns:
        A token that can be used to reset the context
    """
    return _session_id_var.set(session_id)


def clear_session_context(token: contextvars.Token) -> None:
    """Reset the session context to its previous value."""
    _session_id_var.reset(token)


def get_session_id() -> Optional[str]:
    """Get the current session ID from async context."""
    return _session_id_var.get()


class SessionContextFilter(logging.Filter):
    """Logging filter that injects session_id into log records.

    Adds the current session_id (from contextvars) to every log record,
    enabling structured log correlation across async agent calls.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        session_id = _session_id_var.get()
        record.session_id = session_id or "no-session"  # type: ignore[attr-defined]
        if session_id:
            record.msg = f"[{session_id[:12]}] {record.msg}"
        return True


def get_session_logger(name: str) -> logging.Logger:
    """Get a logger with the session context filter attached.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger with SessionContextFilter applied
    """
    logger = logging.getLogger(name)
    # Avoid duplicate filters
    if not any(isinstance(f, SessionContextFilter) for f in logger.filters):
        logger.addFilter(SessionContextFilter())
    return logger
