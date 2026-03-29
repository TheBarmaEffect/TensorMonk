"""Structured error types for the Verdict API.

Provides a hierarchy of domain-specific exceptions that carry structured
context (session_id, agent, retry info) for better error reporting and
debugging. All exceptions serialize to JSON for API error responses.

Exception hierarchy:
    VerdictError (base)
    ├── AgentError (LLM agent failures)
    │   ├── AgentTimeoutError (LLM response timeout)
    │   └── AgentParseError (malformed LLM output)
    ├── SessionError (session management)
    │   ├── SessionNotFoundError (unknown session ID)
    │   └── SessionExpiredError (session past TTL)
    └── ExportError (report generation failures)
"""

from typing import Optional


# Machine-readable error codes for API consumers and monitoring
ERROR_CODES = {
    "AGENT_TIMEOUT": "E1001",
    "AGENT_PARSE_FAILURE": "E1002",
    "AGENT_LLM_UNAVAILABLE": "E1003",
    "SESSION_NOT_FOUND": "E2001",
    "SESSION_EXPIRED": "E2002",
    "SESSION_INVALID_STATE": "E2003",
    "EXPORT_GENERATION_FAILED": "E3001",
    "EXPORT_FORMAT_UNSUPPORTED": "E3002",
    "VALIDATION_FAILED": "E4001",
    "RATE_LIMITED": "E4002",
    "XSS_DETECTED": "E4003",
}


class VerdictError(Exception):
    """Base exception for all Verdict application errors.

    Carries structured context for logging and API error responses.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.code = code
        self.session_id = session_id
        self.details = details or {}

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict for API responses."""
        result = {
            "error": type(self).__name__,
            "message": str(self),
            "session_id": self.session_id,
            "details": self.details,
        }
        if self.code:
            result["code"] = self.code
        return result


class AgentError(VerdictError):
    """Error during LLM agent execution."""

    def __init__(
        self,
        message: str,
        *,
        agent_name: str,
        session_id: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, session_id=session_id, details=details)
        self.agent_name = agent_name

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["agent"] = self.agent_name
        return d


class AgentTimeoutError(AgentError):
    """LLM agent response exceeded timeout threshold."""
    pass


class AgentParseError(AgentError):
    """LLM agent returned malformed/unparseable output.

    This triggers the hallucination guard retry at temperature=0.3.
    """

    def __init__(
        self,
        message: str,
        *,
        agent_name: str,
        raw_output: str = "",
        session_id: Optional[str] = None,
    ):
        super().__init__(
            message,
            agent_name=agent_name,
            session_id=session_id,
            details={"raw_output_preview": raw_output[:200]},
        )


class SessionError(VerdictError):
    """Error related to session management."""
    pass


class SessionNotFoundError(SessionError):
    """Requested session ID does not exist in memory or on disk."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' not found",
            session_id=session_id,
        )


class SessionExpiredError(SessionError):
    """Session exists but has exceeded its TTL."""

    def __init__(self, session_id: str, ttl_seconds: int):
        super().__init__(
            f"Session '{session_id}' expired (TTL: {ttl_seconds}s)",
            session_id=session_id,
            details={"ttl_seconds": ttl_seconds},
        )


class ExportError(VerdictError):
    """Error during report export generation."""

    def __init__(
        self,
        message: str,
        *,
        export_format: str,
        session_id: Optional[str] = None,
    ):
        super().__init__(
            message,
            session_id=session_id,
            details={"export_format": export_format},
        )
