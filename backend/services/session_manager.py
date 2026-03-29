"""Session state machine — manages verdict session lifecycle transitions.

Implements a finite state machine (FSM) for session management with
well-defined states and valid transitions. This prevents invalid state
changes (e.g., marking a session as 'complete' before it has started).

State transitions:
    created → running → complete
    created → running → error
    created → expired
    running → error

Thread safety: Uses asyncio.Lock per session for safe concurrent access.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Valid session states in the lifecycle FSM.

    Transitions:
        CREATED → RUNNING: Session starts executing the verdict pipeline.
        RUNNING → COMPLETE: All agents finished successfully.
        RUNNING → ERROR: Pipeline encountered an unrecoverable error.
        CREATED → EXPIRED: Session timed out before execution.
    """

    CREATED = "created"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    EXPIRED = "expired"

    def __repr__(self) -> str:
        return f"SessionState.{self.name}"


# Valid state transitions — key is current state, value is set of valid next states
_VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.CREATED: {SessionState.RUNNING, SessionState.EXPIRED},
    SessionState.RUNNING: {SessionState.COMPLETE, SessionState.ERROR},
    SessionState.COMPLETE: set(),  # Terminal state
    SessionState.ERROR: {SessionState.RUNNING},  # Allow retry
    SessionState.EXPIRED: set(),  # Terminal state
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted.

    Attributes:
        current_state: The session's current state.
        target_state: The requested invalid state.
        session_id: The affected session ID.
    """

    def __init__(self, session_id: str, current: SessionState, target: SessionState):
        self.session_id = session_id
        self.current_state = current
        self.target_state = target
        super().__init__(
            f"Invalid transition for session {session_id}: "
            f"{current.value} → {target.value}"
        )


class SessionLifecycle:
    """Manages session state transitions with validation and event history.

    Each session tracks its complete transition history for debugging
    and audit purposes. State changes are validated against the FSM
    transition table before being applied.

    Attributes:
        session_id: Unique session identifier.
        state: Current session state.
        history: Ordered list of (timestamp, from_state, to_state) tuples.
        metadata: Arbitrary metadata attached to the session.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = SessionState.CREATED
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.history: list[dict[str, Any]] = [
            {
                "timestamp": self.created_at.isoformat(),
                "from_state": None,
                "to_state": SessionState.CREATED.value,
            }
        ]
        self.metadata: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def transition(self, target: SessionState) -> None:
        """Transition the session to a new state.

        Args:
            target: The desired new state.

        Raises:
            InvalidTransitionError: If the transition is not valid
                according to the FSM transition table.
        """
        async with self._lock:
            valid_targets = _VALID_TRANSITIONS.get(self.state, set())
            if target not in valid_targets:
                raise InvalidTransitionError(self.session_id, self.state, target)

            prev = self.state
            self.state = target
            self.updated_at = datetime.now(timezone.utc)
            self.history.append({
                "timestamp": self.updated_at.isoformat(),
                "from_state": prev.value,
                "to_state": target.value,
            })

            logger.info(
                "Session %s: %s → %s",
                self.session_id, prev.value, target.value,
            )

    @property
    def is_terminal(self) -> bool:
        """Whether the session is in a terminal state (complete/expired)."""
        return self.state in (SessionState.COMPLETE, SessionState.EXPIRED)

    @property
    def is_active(self) -> bool:
        """Whether the session is actively executing."""
        return self.state == SessionState.RUNNING

    @property
    def duration_seconds(self) -> float:
        """Time elapsed since session creation in seconds."""
        now = datetime.now(timezone.utc)
        return (now - self.created_at).total_seconds()

    @property
    def elapsed_in_current_state(self) -> float:
        """Time spent in the current state in seconds."""
        return (datetime.now(timezone.utc) - self.updated_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Serialize session lifecycle to a dictionary.

        Returns:
            Dict with session state, timestamps, and transition history.
        """
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "is_terminal": self.is_terminal,
            "transition_count": len(self.history),
            "history": self.history,
            "metadata": self.metadata,
        }
