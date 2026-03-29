"""Tests for the LangGraph verdict pipeline — verifying graph topology and routing."""

import pytest
from graph.verdict_graph import (
    build_verdict_graph,
    strip_authorship,
    _should_spawn_witnesses,
    _confidence_gate,
    _adaptive_temperature,
    _calibrate_from_witnesses,
    _validate_constitutional_compliance,
    LOW_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_OVERRULE_THRESHOLD,
)
from models.schemas import Argument, Claim, WitnessReport
from utils.confidence_calibration import CalibrationTracker


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
        ], "domain": "business"}
        assert _confidence_gate(state) == "verdict"

    def test_confidence_gate_low_confidence(self):
        state = {"witness_reports": [
            {"confidence": 0.3, "verdict_on_claim": "inconclusive"},
            {"confidence": 0.4, "verdict_on_claim": "sustained"},
        ], "domain": "business"}
        assert _confidence_gate(state) == "verdict_with_review"

    def test_confidence_gate_hallucination_guard(self):
        state = {"witness_reports": [
            {"confidence": 0.95, "verdict_on_claim": "overruled"},
            {"confidence": 0.92, "verdict_on_claim": "sustained"},
        ], "domain": "business"}
        assert _confidence_gate(state) == "verdict_low_temp"

    def test_confidence_gate_empty_reports(self):
        state = {"witness_reports": []}
        assert _confidence_gate(state) == "verdict"

    def test_confidence_gate_domain_medical_higher_threshold(self):
        """Medical domain requires higher confidence (0.7 vs 0.6)."""
        state = {"witness_reports": [
            {"confidence": 0.62, "verdict_on_claim": "sustained"},
            {"confidence": 0.65, "verdict_on_claim": "sustained"},
        ], "domain": "medical"}
        # avg=0.635 which is below medical threshold (0.7) but above business (0.6)
        assert _confidence_gate(state) == "verdict_with_review"

    def test_confidence_gate_domain_technology_lower_threshold(self):
        """Technology domain has a lower threshold (0.55)."""
        state = {"witness_reports": [
            {"confidence": 0.56, "verdict_on_claim": "sustained"},
            {"confidence": 0.58, "verdict_on_claim": "sustained"},
        ], "domain": "technology"}
        # avg=0.57 which is above tech threshold (0.55)
        assert _confidence_gate(state) == "verdict"

    def test_confidence_gate_low_agreement_routes_to_review(self):
        """When witnesses disagree (mixed verdicts), route to review."""
        state = {"witness_reports": [
            {"confidence": 0.8, "verdict_on_claim": "sustained"},
            {"confidence": 0.8, "verdict_on_claim": "overruled"},
            {"confidence": 0.8, "verdict_on_claim": "inconclusive"},
        ], "domain": "business"}
        # No majority (each verdict appears once) → agreement < 0.5
        assert _confidence_gate(state) == "verdict_with_review"

    def test_confidence_gate_high_variance_routes_to_review(self):
        """When witness confidence levels diverge widely, route to review."""
        state = {"witness_reports": [
            {"confidence": 0.95, "verdict_on_claim": "sustained"},
            {"confidence": 0.3, "verdict_on_claim": "sustained"},
        ], "domain": "business"}
        # avg=0.625 (above threshold), but variance is high (~0.106)
        assert _confidence_gate(state) == "verdict_with_review"


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


class TestAdaptiveTemperature:
    """Verify adaptive temperature adjusts based on research quality."""

    def test_default_when_no_quality_scores(self):
        """Returns base_temp when research has no quality data."""
        assert _adaptive_temperature({}) == 0.7
        assert _adaptive_temperature({"summary": "test"}) == 0.7

    def test_lower_temp_for_high_quality_research(self):
        """High quality research should produce lower temperature."""
        pkg = {"_quality_scores": {"overall": 0.9, "grounding": 0.8}}
        temp = _adaptive_temperature(pkg)
        assert temp < 0.7  # Lower than default
        assert temp >= 0.4  # Within bounds

    def test_higher_temp_for_low_quality_research(self):
        """Low quality research should produce higher temperature."""
        pkg = {"_quality_scores": {"overall": 0.2, "grounding": 0.0}}
        temp = _adaptive_temperature(pkg)
        assert temp > 0.7  # Higher than default

    def test_clamped_to_bounds(self):
        """Temperature should always be between 0.4 and 0.85."""
        # Extreme high quality
        pkg_high = {"_quality_scores": {"overall": 1.0, "grounding": 1.0}}
        assert _adaptive_temperature(pkg_high) >= 0.4

        # Extreme low quality
        pkg_low = {"_quality_scores": {"overall": 0.0, "grounding": 0.0}}
        assert _adaptive_temperature(pkg_low) <= 0.85

    def test_grounding_reduces_temperature(self):
        """Fully grounded research should reduce temperature."""
        pkg_no_ground = {"_quality_scores": {"overall": 0.5, "grounding": 0.0}}
        pkg_grounded = {"_quality_scores": {"overall": 0.5, "grounding": 1.0}}
        assert _adaptive_temperature(pkg_grounded) < _adaptive_temperature(pkg_no_ground)

    def test_custom_base_temp(self):
        """Should respect custom base temperature."""
        temp = _adaptive_temperature({}, base_temp=0.5)
        assert temp == 0.5


class TestCalibrateFromWitnesses:
    """Verify calibration wiring from witness verdicts."""

    def _make_arg(self, claims_data, confidence=0.8, agent="prosecutor"):
        claims = [
            Claim(id=c["id"], statement=c["stmt"], evidence="ev", confidence=c["conf"])
            for c in claims_data
        ]
        return Argument(
            agent=agent,
            opening="test opening",
            claims=claims,
            confidence=confidence,
        )

    def _make_witness(self, claim_id, verdict, confidence=0.8):
        return WitnessReport(
            claim_id=claim_id,
            witness_type="fact",
            resolution="Test resolution",
            verdict_on_claim=verdict,
            confidence=confidence,
        )

    def test_sustained_records_correct(self):
        """Sustained claim should record as correct prediction."""
        from utils.confidence_calibration import calibration_tracker as ct
        # Reset tracker state
        ct._agents.clear()
        ct._domain_agents.clear()

        pro = self._make_arg([{"id": "p1", "stmt": "claim", "conf": 0.85}], agent="prosecutor")
        defense = self._make_arg([{"id": "d1", "stmt": "counter", "conf": 0.7}], agent="defense")
        witnesses = [self._make_witness("p1", "sustained")]

        _calibrate_from_witnesses(pro, defense, witnesses, "business")

        cal = ct.get_agent_calibration("prosecutor")
        assert cal is not None
        assert cal._total_predictions == 1

    def test_overruled_records_incorrect(self):
        """Overruled claim should record as incorrect prediction."""
        from utils.confidence_calibration import calibration_tracker as ct
        ct._agents.clear()
        ct._domain_agents.clear()

        pro = self._make_arg([{"id": "p1", "stmt": "claim", "conf": 0.9}], agent="prosecutor")
        defense = self._make_arg([{"id": "d1", "stmt": "counter", "conf": 0.7}], agent="defense")
        witnesses = [self._make_witness("p1", "overruled")]

        _calibrate_from_witnesses(pro, defense, witnesses, "business")

        cal = ct.get_agent_calibration("prosecutor")
        assert cal is not None

    def test_inconclusive_skipped(self):
        """Inconclusive verdicts should not be recorded."""
        from utils.confidence_calibration import calibration_tracker as ct
        ct._agents.clear()
        ct._domain_agents.clear()

        pro = self._make_arg([{"id": "p1", "stmt": "claim", "conf": 0.8}], agent="prosecutor")
        defense = self._make_arg([], agent="defense")
        witnesses = [self._make_witness("p1", "inconclusive")]

        _calibrate_from_witnesses(pro, defense, witnesses, "business")

        # No agent should have any recorded predictions
        cal = ct.get_agent_calibration("prosecutor")
        assert cal is None

    def test_defense_claims_tracked(self):
        """Defense claims should be tracked under defense agent."""
        from utils.confidence_calibration import calibration_tracker as ct
        ct._agents.clear()
        ct._domain_agents.clear()

        pro = self._make_arg([], agent="prosecutor")
        defense = self._make_arg([{"id": "d1", "stmt": "counter", "conf": 0.75}], agent="defense")
        witnesses = [self._make_witness("d1", "sustained")]

        _calibrate_from_witnesses(pro, defense, witnesses, "legal")

        cal = ct.get_agent_calibration("defense")
        assert cal is not None
        assert cal._total_predictions == 1


class TestConstitutionalCompliance:
    """Verify constitutional directive compliance checking."""

    def test_compliant_prosecutor(self):
        """Prosecutor with positive opening should pass."""
        data = {
            "opening": "This decision should proceed — the opportunity for growth is significant.",
            "claims": [
                {"statement": "c1"}, {"statement": "c2"},
                {"statement": "c3"}, {"statement": "c4"},
            ],
            "confidence": 0.8,
        }
        result = _validate_constitutional_compliance(data, "prosecutor")
        assert result["compliant"] is True
        assert result["violations"] == []

    def test_noncompliant_prosecutor(self):
        """Prosecutor arguing against should be flagged."""
        data = {
            "opening": "This should not proceed. It will fail and is risky and dangerous.",
            "claims": [{"statement": "c1"}, {"statement": "c2"}, {"statement": "c3"}, {"statement": "c4"}],
            "confidence": 0.8,
        }
        result = _validate_constitutional_compliance(data, "prosecutor")
        assert result["compliant"] is False
        assert len(result["violations"]) > 0

    def test_wrong_claim_count(self):
        """Non-4 claim count should be flagged."""
        data = {
            "opening": "We should proceed with this opportunity.",
            "claims": [{"statement": "c1"}, {"statement": "c2"}],
            "confidence": 0.7,
        }
        result = _validate_constitutional_compliance(data, "prosecutor")
        assert result["compliant"] is False
        assert any("Expected 4 claims" in v for v in result["violations"])

    def test_suspicious_confidence(self):
        """Extreme confidence should be flagged."""
        data = {
            "opening": "Good opportunity here.",
            "claims": [{"statement": f"c{i}"} for i in range(4)],
            "confidence": 0.01,
        }
        result = _validate_constitutional_compliance(data, "prosecutor")
        assert any("Suspicious confidence" in v for v in result["violations"])

    def test_none_argument(self):
        """None argument should return non-compliant."""
        result = _validate_constitutional_compliance(None, "prosecutor")
        assert result["compliant"] is False

    def test_compliant_defense(self):
        """Defense with critical language should pass."""
        data = {
            "opening": "This proposal carries significant risk and concern — the weakness is clear.",
            "claims": [{"statement": f"c{i}"} for i in range(4)],
            "confidence": 0.75,
        }
        result = _validate_constitutional_compliance(data, "defense")
        assert result["compliant"] is True
