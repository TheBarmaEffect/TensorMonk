"""Tests for structured error types — verifying serialization and hierarchy."""

import pytest
from utils.errors import (
    VerdictError,
    AgentError,
    AgentTimeoutError,
    AgentParseError,
    SessionNotFoundError,
    SessionExpiredError,
    ExportError,
    ERROR_CODES,
)


class TestVerdictError:
    def test_base_error(self):
        err = VerdictError("something went wrong", session_id="s1")
        assert str(err) == "something went wrong"
        assert err.session_id == "s1"

    def test_to_dict(self):
        err = VerdictError("test", session_id="s1", details={"key": "value"})
        d = err.to_dict()
        assert d["error"] == "VerdictError"
        assert d["message"] == "test"
        assert d["session_id"] == "s1"
        assert d["details"]["key"] == "value"


class TestAgentError:
    def test_includes_agent_name(self):
        err = AgentError("LLM failed", agent_name="prosecutor", session_id="s2")
        d = err.to_dict()
        assert d["agent"] == "prosecutor"
        assert d["session_id"] == "s2"

    def test_timeout_inherits(self):
        err = AgentTimeoutError("timeout", agent_name="research")
        assert isinstance(err, AgentError)
        assert isinstance(err, VerdictError)

    def test_parse_error_includes_raw_output(self):
        err = AgentParseError(
            "bad JSON",
            agent_name="defense",
            raw_output="not valid json at all" * 20,
            session_id="s3",
        )
        d = err.to_dict()
        assert "raw_output_preview" in d["details"]
        assert len(d["details"]["raw_output_preview"]) <= 200


class TestSessionError:
    def test_not_found(self):
        err = SessionNotFoundError("abc-123")
        assert "abc-123" in str(err)
        assert err.session_id == "abc-123"

    def test_expired(self):
        err = SessionExpiredError("def-456", ttl_seconds=3600)
        assert "expired" in str(err).lower()
        assert err.details["ttl_seconds"] == 3600


class TestExportError:
    def test_includes_format(self):
        err = ExportError("PDF generation failed", export_format="pdf", session_id="s4")
        d = err.to_dict()
        assert d["details"]["export_format"] == "pdf"
        assert d["session_id"] == "s4"


class TestInheritanceHierarchy:
    def test_all_inherit_from_verdict_error(self):
        errors = [
            AgentError("x", agent_name="y"),
            AgentTimeoutError("x", agent_name="y"),
            AgentParseError("x", agent_name="y"),
            SessionNotFoundError("s"),
            SessionExpiredError("s", 100),
            ExportError("x", export_format="pdf"),
        ]
        for err in errors:
            assert isinstance(err, VerdictError)

    def test_all_have_to_dict(self):
        errors = [
            VerdictError("base"),
            AgentError("agent", agent_name="test"),
            SessionNotFoundError("s"),
            ExportError("export", export_format="json"),
        ]
        for err in errors:
            d = err.to_dict()
            assert "error" in d
            assert "message" in d


class TestErrorCodes:
    def test_error_codes_dict_exists(self):
        assert isinstance(ERROR_CODES, dict)
        assert len(ERROR_CODES) >= 10

    def test_all_codes_unique(self):
        codes = list(ERROR_CODES.values())
        assert len(codes) == len(set(codes))

    def test_code_format(self):
        for name, code in ERROR_CODES.items():
            assert code.startswith("E"), f"{name} code should start with E"
            assert len(code) == 5, f"{name} code should be 5 chars"

    def test_to_dict_includes_code_when_set(self):
        err = VerdictError("test", code="E1001")
        d = err.to_dict()
        assert d["code"] == "E1001"

    def test_to_dict_omits_code_when_none(self):
        err = VerdictError("test")
        d = err.to_dict()
        assert "code" not in d

    def test_agent_error_codes_start_with_e1(self):
        agent_codes = {k: v for k, v in ERROR_CODES.items() if "agent" in k.lower() or "llm" in k.lower() or "parse" in k.lower()}
        for name, code in agent_codes.items():
            assert code.startswith("E1"), f"{name} should be E1xxx (agent errors)"

    def test_session_error_codes_start_with_e2(self):
        session_codes = {k: v for k, v in ERROR_CODES.items() if "session" in k.lower()}
        for name, code in session_codes.items():
            assert code.startswith("E2"), f"{name} should be E2xxx (session errors)"
