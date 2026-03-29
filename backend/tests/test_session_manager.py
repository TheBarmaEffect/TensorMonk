"""Tests for session state machine — validates FSM transitions and lifecycle."""

import asyncio
import pytest
from services.session_manager import (
    SessionLifecycle,
    SessionState,
    InvalidTransitionError,
    _VALID_TRANSITIONS,
)


@pytest.fixture
def session():
    return SessionLifecycle("test-session-001")


class TestSessionCreation:
    """Test initial session state."""

    def test_initial_state_is_created(self, session):
        assert session.state == SessionState.CREATED

    def test_has_creation_timestamp(self, session):
        assert session.created_at is not None

    def test_initial_history_has_one_entry(self, session):
        assert len(session.history) == 1
        assert session.history[0]["to_state"] == "created"

    def test_is_not_terminal(self, session):
        assert session.is_terminal is False

    def test_is_not_active(self, session):
        assert session.is_active is False


class TestValidTransitions:
    """Test valid state transitions."""

    @pytest.mark.asyncio
    async def test_created_to_running(self, session):
        await session.transition(SessionState.RUNNING)
        assert session.state == SessionState.RUNNING
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_running_to_complete(self, session):
        await session.transition(SessionState.RUNNING)
        await session.transition(SessionState.COMPLETE)
        assert session.state == SessionState.COMPLETE
        assert session.is_terminal is True

    @pytest.mark.asyncio
    async def test_running_to_error(self, session):
        await session.transition(SessionState.RUNNING)
        await session.transition(SessionState.ERROR)
        assert session.state == SessionState.ERROR

    @pytest.mark.asyncio
    async def test_created_to_expired(self, session):
        await session.transition(SessionState.EXPIRED)
        assert session.state == SessionState.EXPIRED
        assert session.is_terminal is True

    @pytest.mark.asyncio
    async def test_error_to_running_retry(self, session):
        await session.transition(SessionState.RUNNING)
        await session.transition(SessionState.ERROR)
        await session.transition(SessionState.RUNNING)
        assert session.state == SessionState.RUNNING


class TestInvalidTransitions:
    """Test that invalid transitions are rejected."""

    @pytest.mark.asyncio
    async def test_cannot_skip_running(self, session):
        with pytest.raises(InvalidTransitionError):
            await session.transition(SessionState.COMPLETE)

    @pytest.mark.asyncio
    async def test_cannot_go_back_from_complete(self, session):
        await session.transition(SessionState.RUNNING)
        await session.transition(SessionState.COMPLETE)
        with pytest.raises(InvalidTransitionError):
            await session.transition(SessionState.RUNNING)

    @pytest.mark.asyncio
    async def test_cannot_go_back_from_expired(self, session):
        await session.transition(SessionState.EXPIRED)
        with pytest.raises(InvalidTransitionError):
            await session.transition(SessionState.CREATED)

    @pytest.mark.asyncio
    async def test_error_has_session_id(self, session):
        try:
            await session.transition(SessionState.COMPLETE)
        except InvalidTransitionError as e:
            assert e.session_id == "test-session-001"
            assert e.current_state == SessionState.CREATED
            assert e.target_state == SessionState.COMPLETE


class TestTransitionHistory:
    """Test that transition history is recorded correctly."""

    @pytest.mark.asyncio
    async def test_history_grows_with_transitions(self, session):
        await session.transition(SessionState.RUNNING)
        await session.transition(SessionState.COMPLETE)
        assert len(session.history) == 3  # created + running + complete

    @pytest.mark.asyncio
    async def test_history_records_from_and_to(self, session):
        await session.transition(SessionState.RUNNING)
        last = session.history[-1]
        assert last["from_state"] == "created"
        assert last["to_state"] == "running"

    @pytest.mark.asyncio
    async def test_history_has_timestamps(self, session):
        await session.transition(SessionState.RUNNING)
        for entry in session.history:
            assert "timestamp" in entry


class TestSerialization:
    """Test to_dict serialization."""

    @pytest.mark.asyncio
    async def test_to_dict_has_required_fields(self, session):
        d = session.to_dict()
        assert "session_id" in d
        assert "state" in d
        assert "created_at" in d
        assert "duration_seconds" in d
        assert "is_terminal" in d
        assert "history" in d

    @pytest.mark.asyncio
    async def test_to_dict_reflects_state(self, session):
        await session.transition(SessionState.RUNNING)
        d = session.to_dict()
        assert d["state"] == "running"
        assert d["is_terminal"] is False

    def test_duration_is_non_negative(self, session):
        assert session.duration_seconds >= 0


class TestFSMCompleteness:
    """Verify the FSM transition table is well-defined."""

    def test_all_states_have_transition_entries(self):
        for state in SessionState:
            assert state in _VALID_TRANSITIONS

    def test_terminal_states_have_empty_transitions(self):
        assert _VALID_TRANSITIONS[SessionState.COMPLETE] == set()
        assert _VALID_TRANSITIONS[SessionState.EXPIRED] == set()

    def test_created_can_reach_running(self):
        assert SessionState.RUNNING in _VALID_TRANSITIONS[SessionState.CREATED]

    def test_elapsed_in_current_state(self, session):
        import time
        time.sleep(0.01)
        elapsed = session.elapsed_in_current_state
        assert elapsed >= 0.01
