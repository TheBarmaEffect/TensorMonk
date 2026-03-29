"""Tests for the LangGraph verdict pipeline — verifying graph topology and routing."""

import pytest
from graph.verdict_graph import (
    build_verdict_graph,
    strip_authorship,
    _should_spawn_witnesses,
    _confidence_gate,
    LOW_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_OVERRULE_THRESHOLD,
)


class TestStripAuthorship:
    """Verify authorship blindness strips all identifying metadata."""

    def test_strips_agent_fields(self):
        pkg = {"summary": "test", "agent_id": "res-1", "model": "llama", "source": "groq"}
        result = strip_authorship(pkg)
        assert "summary" in result
        assert "agent_id" not in result
        assert "model" not in result
        assert "source" not in result

    def test_preserves_data_fields(self):
        pkg = {"summary": "market data", "key_data_points": [1, 2, 3], "risk_landscape": ["risk"]}
        result = strip_authorship(pkg)
        assert result["summary"] == "market data"
        assert result["key_data_points"] == [1, 2, 3]

    def test_handles_empty_input(self):
        assert strip_authorship({}) == {}
        assert strip_authorship(None) == {}

    def test_strips_all_known_fields(self):
        pkg = {
            "data": "keep",
            "agent_id": "x", "agent": "x", "source": "x", "model": "x",
            "timestamp": "x", "metadata": "x", "author": "x",
            "provider": "x", "version": "x", "run_id": "x", "trace_id": "x",
        }
        result = strip_authorship(pkg)
        assert list(result.keys()) == ["data"]


class TestConditionalEdges:
    """Verify dynamic witness spawning and confidence-based routing."""

    def test_spawn_witnesses_when_contested(self):
        state = {"contested_claims": [{"claim_id": "c1"}, {"claim_id": "c2"}]}
        assert _should_spawn_witnesses(state) == "witnesses"

    def test_skip_witnesses_when_none_contested(self):
        state = {"contested_claims": []}
        assert _should_spawn_witnesses(state) == "verdict"

    def test_skip_witnesses_when_missing(self):
        state = {}
        assert _should_spawn_witnesses(state) == "verdict"

    def test_confidence_gate_normal(self):
        state = {"witness_reports": [
            {"confidence": 0.8, "verdict_on_claim": "sustained"},
            {"confidence": 0.7, "verdict_on_claim": "sustained"},
        ]}
        assert _confidence_gate(state) == "verdict"

    def test_confidence_gate_low_confidence(self):
        state = {"witness_reports": [
            {"confidence": 0.3, "verdict_on_claim": "inconclusive"},
            {"confidence": 0.4, "verdict_on_claim": "sustained"},
        ]}
        assert _confidence_gate(state) == "verdict_with_review"

    def test_confidence_gate_hallucination_guard(self):
        state = {"witness_reports": [
            {"confidence": 0.95, "verdict_on_claim": "overruled"},
            {"confidence": 0.92, "verdict_on_claim": "sustained"},
        ]}
        assert _confidence_gate(state) == "verdict_low_temp"

    def test_confidence_gate_empty_reports(self):
        state = {"witness_reports": []}
        assert _confidence_gate(state) == "verdict"


class TestGraphTopology:
    """Verify the compiled graph has correct node structure."""

    def test_graph_compiles(self):
        g = build_verdict_graph()
        assert g is not None

    def test_graph_has_all_nodes(self):
        g = build_verdict_graph()
        node_names = list(g.get_graph().nodes.keys())
        expected = [
            "research", "arguments", "cross_examination", "witnesses",
            "verdict", "verdict_with_review", "verdict_low_temp", "synthesis",
        ]
        for name in expected:
            assert name in node_names, f"Missing node: {name}"

    def test_graph_with_interrupt_before(self):
        g = build_verdict_graph(interrupt_before_verdict=True)
        assert g is not None

    def test_thresholds_are_correct(self):
        assert LOW_CONFIDENCE_THRESHOLD == 0.6
        assert HIGH_CONFIDENCE_OVERRULE_THRESHOLD == 0.9
