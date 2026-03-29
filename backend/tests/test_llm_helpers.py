"""Tests for shared LLM utilities — JSON parsing, thinking phases, LLM factory, retry."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.schemas import StreamEvent
from utils.llm_helpers import (
    parse_llm_json,
    emit_thinking_phases,
    create_llm,
    retry_with_low_temperature,
)


class TestParseLlmJson:
    """Verify markdown-fence stripping and JSON fallback behaviour."""

    def test_valid_json_parses_correctly(self):
        raw = '{"verdict": "guilty", "confidence": 0.9}'
        result = parse_llm_json(raw)
        assert result == {"verdict": "guilty", "confidence": 0.9}

    def test_json_wrapped_in_json_code_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_json_wrapped_in_plain_code_fence(self):
        raw = '```\n{"key": "value"}\n```'
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_invalid_json_returns_fallback(self):
        fallback = {"default": True}
        result = parse_llm_json("not json at all", fallback=fallback)
        assert result == fallback

    def test_invalid_json_no_fallback_returns_empty_dict(self):
        result = parse_llm_json("not json at all")
        assert result == {}

    def test_whitespace_around_json(self):
        raw = '   \n  {"score": 42}  \n  '
        result = parse_llm_json(raw)
        assert result == {"score": 42}

    def test_nested_json_objects(self):
        raw = '{"outer": {"inner": [1, 2, 3]}, "flag": true}'
        result = parse_llm_json(raw)
        assert result == {"outer": {"inner": [1, 2, 3]}, "flag": True}

    def test_empty_string_returns_fallback(self):
        fallback = {"empty": True}
        result = parse_llm_json("", fallback=fallback)
        assert result == fallback

    def test_empty_string_no_fallback_returns_empty_dict(self):
        result = parse_llm_json("")
        assert result == {}

    def test_code_fence_with_whitespace_inside(self):
        raw = '```json\n  \n{"a": 1}\n  \n```'
        result = parse_llm_json(raw)
        assert result == {"a": 1}

    def test_operation_name_used_in_logging(self):
        """Ensure custom operation_name does not break fallback path."""
        result = parse_llm_json("{bad", operation_name="TestOp")
        assert result == {}


class TestEmitThinkingPhases:
    """Verify thinking phase streaming logic."""

    @pytest.mark.asyncio
    async def test_emits_correct_number_of_events(self):
        callback = AsyncMock()
        phases = ["Analyzing...", "Reasoning...", "Concluding..."]
        await emit_thinking_phases(
            phases, "prosecutor", "prosecutor_thinking", callback, delay=0.0
        )
        assert callback.call_count == 3

    @pytest.mark.asyncio
    async def test_events_have_correct_agent_and_type(self):
        callback = AsyncMock()
        await emit_thinking_phases(
            ["Phase 1"], "judge", "prosecutor_thinking", callback, delay=0.0
        )
        event = callback.call_args[0][0]
        assert isinstance(event, StreamEvent)
        assert event.agent == "judge"
        assert event.event_type == "prosecutor_thinking"

    @pytest.mark.asyncio
    async def test_content_has_trailing_newline(self):
        callback = AsyncMock()
        await emit_thinking_phases(
            ["Thinking"], "defense", "defense_thinking", callback, delay=0.0
        )
        event = callback.call_args[0][0]
        assert event.content == "Thinking\n"

    @pytest.mark.asyncio
    async def test_no_callback_does_not_raise(self):
        # Should complete without error when callback is None
        await emit_thinking_phases(
            ["Phase 1", "Phase 2"], "agent", "thinking", stream_callback=None, delay=0.0
        )

    @pytest.mark.asyncio
    async def test_empty_phases_emits_nothing(self):
        callback = AsyncMock()
        await emit_thinking_phases([], "agent", "thinking", callback, delay=0.0)
        callback.assert_not_called()


class TestCreateLlm:
    """Verify ChatGroq factory behaviour."""

    @patch("utils.llm_helpers.settings")
    @patch("utils.llm_helpers.ChatGroq")
    def test_returns_instance_with_correct_temperature(self, mock_groq, mock_settings):
        mock_settings.groq_api_key = "test-key"
        create_llm(temperature=0.5)
        _, kwargs = mock_groq.call_args
        assert kwargs["temperature"] == 0.5

    @patch("utils.llm_helpers.settings")
    @patch("utils.llm_helpers.ChatGroq")
    def test_returns_instance_with_correct_max_tokens(self, mock_groq, mock_settings):
        mock_settings.groq_api_key = "test-key"
        create_llm(max_tokens=4096)
        _, kwargs = mock_groq.call_args
        assert kwargs["max_tokens"] == 4096

    @patch("utils.llm_helpers.settings")
    @patch("utils.llm_helpers.ChatGroq")
    def test_default_parameters(self, mock_groq, mock_settings):
        mock_settings.groq_api_key = "test-key"
        create_llm()
        _, kwargs = mock_groq.call_args
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 2048
        assert kwargs["model"] == "llama-3.3-70b-versatile"

    @patch("utils.llm_helpers.settings")
    @patch("utils.llm_helpers.ChatGroq")
    def test_custom_model(self, mock_groq, mock_settings):
        mock_settings.groq_api_key = "test-key"
        create_llm(model="custom-model")
        _, kwargs = mock_groq.call_args
        assert kwargs["model"] == "custom-model"


class TestRetryWithLowTemperature:
    """Verify low-temperature retry fallback."""

    @pytest.mark.asyncio
    @patch("utils.llm_helpers.retry_with_backoff")
    @patch("utils.llm_helpers.create_llm")
    async def test_calls_retry_with_temperature_0_3(self, mock_create, mock_retry):
        mock_response = MagicMock()
        mock_response.content = '{"result": "ok"}'
        mock_retry.return_value = mock_response

        parse_fn = MagicMock(return_value={"result": "ok"})
        quality_fn = MagicMock(return_value=True)

        await retry_with_low_temperature(
            messages=[], parse_fn=parse_fn, quality_check_fn=quality_fn,
            max_tokens=1024, operation_name="test",
        )

        mock_create.assert_called_once_with(temperature=0.3, max_tokens=1024)

    @pytest.mark.asyncio
    @patch("utils.llm_helpers.retry_with_backoff")
    @patch("utils.llm_helpers.create_llm")
    async def test_returns_parsed_result(self, mock_create, mock_retry):
        mock_response = MagicMock()
        mock_response.content = '{"score": 5}'
        mock_retry.return_value = mock_response

        expected = {"score": 5}
        parse_fn = MagicMock(return_value=expected)
        quality_fn = MagicMock(return_value=True)

        result = await retry_with_low_temperature(
            messages=[], parse_fn=parse_fn, quality_check_fn=quality_fn,
        )

        assert result == expected
        parse_fn.assert_called_once_with('{"score": 5}')

    @pytest.mark.asyncio
    @patch("utils.llm_helpers.call_llm_with_resilience")
    @patch("utils.llm_helpers.create_llm")
    async def test_passes_messages_to_ainvoke(self, mock_create, mock_resilience):
        mock_llm = MagicMock()
        mock_create.return_value = mock_llm

        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_resilience.return_value = mock_response

        messages = [MagicMock(), MagicMock()]
        parse_fn = MagicMock(return_value={})

        await retry_with_low_temperature(
            messages=messages, parse_fn=parse_fn,
            quality_check_fn=MagicMock(return_value=True),
        )

        # call_llm_with_resilience called with llm.ainvoke and the messages list
        args, kwargs = mock_resilience.call_args
        assert args[0] == mock_llm.ainvoke
        assert args[1] is messages
