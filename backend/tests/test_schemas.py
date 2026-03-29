"""Tests for Pydantic v2 schema validation — verifying data integrity across the pipeline."""

import pytest
from models.schemas import (
    Decision,
    Claim,
    Argument,
    WitnessReport,
    VerdictResult,
    Synthesis,
    StreamEvent,
)


class TestDecision:
    def test_auto_generates_id(self):
        d = Decision(question="Should we pivot?")
        assert d.id is not None
        assert len(d.id) > 0

    def test_stores_question_and_context(self):
        d = Decision(question="Hire a CTO?", context="Early stage startup")
        assert d.question == "Hire a CTO?"
        assert d.context == "Early stage startup"

    def test_created_at_auto_set(self):
        d = Decision(question="test")
        assert d.created_at is not None


class TestClaim:
    def test_valid_claim(self):
        c = Claim(id="c1", statement="Market is growing", evidence="TAM $50B", confidence=0.85)
        assert c.confidence == 0.85

    def test_confidence_rejects_out_of_bounds(self):
        """Pydantic v2 field constraint ge=0.0, le=1.0 rejects invalid values."""
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            Claim(id="c1", statement="test", evidence="test", confidence=1.5)


class TestArgument:
    def test_full_argument(self):
        a = Argument(
            agent="prosecutor",
            opening="The evidence clearly shows...",
            claims=[
                Claim(id="c1", statement="Revenue growing", evidence="40% QoQ", confidence=0.9),
                Claim(id="c2", statement="Market fit", evidence="NPS 72", confidence=0.8),
            ],
            closing="Therefore we should proceed.",
            confidence=0.85,
        )
        assert len(a.claims) == 2
        assert a.agent == "prosecutor"


class TestWitnessReport:
    def test_normalize_verdict_sustained(self):
        w = WitnessReport(
            claim_id="c1",
            witness_type="fact",
            verdict_on_claim="SUSTAINED",
            resolution="Claim verified",
            confidence=0.9,
        )
        assert w.verdict_on_claim == "sustained"

    def test_normalize_verdict_overruled(self):
        w = WitnessReport(
            claim_id="c1",
            witness_type="data",
            verdict_on_claim="Overruled",
            resolution="Data contradicts claim",
            confidence=0.3,
        )
        assert w.verdict_on_claim == "overruled"

    def test_normalize_verdict_unknown_maps_to_inconclusive(self):
        w = WitnessReport(
            claim_id="c1",
            witness_type="precedent",
            verdict_on_claim="maybe",
            resolution="Unclear",
            confidence=0.5,
        )
        assert w.verdict_on_claim == "inconclusive"


class TestVerdictResult:
    def test_valid_verdict(self):
        v = VerdictResult(
            decision_id="d1",
            ruling="proceed",
            confidence=0.82,
            reasoning="Strong evidence supports moving forward.",
            key_factors=["Market growth", "Team readiness"],
            dissenting_points=["Regulatory risk"],
        )
        assert v.ruling == "proceed"
        assert len(v.key_factors) == 2


class TestSynthesis:
    def test_full_synthesis(self):
        s = Synthesis(
            decision_id="d1",
            improved_idea="Pivot to B2B with phased rollout",
            strength_score=0.88,
            addressed_objections=["Regulatory compliance via WorkOS"],
            recommended_actions=["Week 1: Implement SSO", "Week 2: Beta launch"],
        )
        assert s.strength_score == 0.88
        assert len(s.recommended_actions) == 2


class TestStreamEvent:
    def test_event_creation(self):
        e = StreamEvent(
            event_type="research_start",
            agent="research",
            content="Starting analysis...",
        )
        assert e.event_type == "research_start"
        assert e.agent == "research"

    def test_event_with_data(self):
        e = StreamEvent(
            event_type="research_complete",
            agent="research",
            content="Done",
            data={"summary": "Market is favorable"},
        )
        assert e.data["summary"] == "Market is favorable"

    def test_quality_gate_event(self):
        e = StreamEvent(event_type="quality_gate", agent="judge", content="Quality check")
        assert e.event_type == "quality_gate"

    def test_stability_check_event(self):
        e = StreamEvent(event_type="stability_check", content="Checking verdict stability")
        assert e.event_type == "stability_check"

    def test_calibration_update_event(self):
        e = StreamEvent(event_type="calibration_update", data={"method": "platt"})
        assert e.event_type == "calibration_update"
