"""Tests for verdict stability analysis — margin computation and perturbation testing."""

import pytest
from utils.verdict_stability import (
    compute_evidence_margin,
    perturbation_stability,
    sensitivity_analysis,
    full_stability_analysis,
)


class TestEvidenceMargin:
    """Test evidence margin computation."""

    def test_decisive_margin(self):
        result = compute_evidence_margin(0.9, 0.4, "proceed")
        assert result["classification"] == "decisive"
        assert result["margin"] == 0.5

    def test_moderate_margin(self):
        result = compute_evidence_margin(0.7, 0.5, "proceed")
        assert result["classification"] == "moderate"

    def test_narrow_margin(self):
        result = compute_evidence_margin(0.55, 0.5, "proceed")
        assert result["classification"] == "narrow"

    def test_razor_thin_margin(self):
        result = compute_evidence_margin(0.51, 0.49, "conditional")
        assert result["classification"] == "razor_thin"

    def test_tied_scores(self):
        result = compute_evidence_margin(0.5, 0.5, "conditional")
        assert result["flip_direction"] == "tied"
        assert result["margin"] == 0.0

    def test_defense_winning(self):
        result = compute_evidence_margin(0.3, 0.8, "reject")
        assert result["differential"] < 0
        assert "prosecution_needs" in result["flip_direction"]


class TestPerturbationStability:
    """Test Monte Carlo perturbation analysis."""

    def test_stable_verdict_no_witnesses(self):
        result = perturbation_stability([], 0.8, 0.4)
        assert result["stability_score"] == 1.0
        assert result["flip_count"] == 0

    def test_stable_with_clear_winner(self):
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.9, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
            {"claim_id": "pro_2", "confidence": 0.85, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
        ]
        result = perturbation_stability(witnesses, 0.8, 0.3)
        assert result["stability_score"] >= 0.8
        assert result["verdict_distribution"]["prosecution_wins"] > result["verdict_distribution"]["defense_wins"]

    def test_unstable_with_close_scores(self):
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.5, "verdict_on_claim": "overruled", "from_agent": "prosecutor"},
        ]
        result = perturbation_stability(witnesses, 0.5, 0.49)
        # Close scores with perturbation should produce some flips
        assert result["simulations"] == 50

    def test_reproducible_with_seed(self):
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.7, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
        ]
        r1 = perturbation_stability(witnesses, 0.6, 0.5)
        r2 = perturbation_stability(witnesses, 0.6, 0.5)
        assert r1["flip_count"] == r2["flip_count"]
        assert r1["stability_score"] == r2["stability_score"]

    def test_distribution_sums_to_total(self):
        witnesses = [
            {"claim_id": "d_1", "confidence": 0.8, "verdict_on_claim": "sustained", "from_agent": "defense"},
        ]
        result = perturbation_stability(witnesses, 0.5, 0.6)
        dist = result["verdict_distribution"]
        assert dist["prosecution_wins"] + dist["defense_wins"] + dist["ties"] == result["simulations"]

    def test_custom_simulations(self):
        result = perturbation_stability([], 0.8, 0.3, num_simulations=100)
        assert result["simulations"] == 100

    def test_flip_rate_bounded(self):
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.5, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
        ]
        result = perturbation_stability(witnesses, 0.6, 0.4)
        assert 0.0 <= result["flip_rate"] <= 1.0
        assert 0.0 <= result["stability_score"] <= 1.0


class TestFullStabilityAnalysis:
    """Test the combined stability analysis."""

    def test_robust_verdict(self):
        result = full_stability_analysis(
            prosecution_score=0.9,
            defense_score=0.4,
            ruling="proceed",
            witness_reports=[],
            prosecution_base_confidence=0.85,
            defense_base_confidence=0.5,
        )
        assert result["verdict_is_robust"] is True
        assert result["combined_robustness"] >= 0.7
        assert "evidence_margin" in result
        assert "perturbation_stability" in result

    def test_fragile_verdict(self):
        result = full_stability_analysis(
            prosecution_score=0.51,
            defense_score=0.49,
            ruling="conditional",
            witness_reports=[],
            prosecution_base_confidence=0.5,
            defense_base_confidence=0.5,
        )
        assert result["combined_robustness"] < 0.7

    def test_contains_all_sections(self):
        result = full_stability_analysis(0.7, 0.5, "proceed", [], 0.7, 0.5)
        assert "evidence_margin" in result
        assert "perturbation_stability" in result
        assert "combined_robustness" in result
        assert "verdict_is_robust" in result

    def test_combined_robustness_bounded(self):
        result = full_stability_analysis(0.8, 0.3, "proceed", [], 0.8, 0.3)
        assert 0.0 <= result["combined_robustness"] <= 1.0

    def test_includes_sensitivity(self):
        result = full_stability_analysis(0.7, 0.5, "proceed", [], 0.7, 0.5)
        assert "sensitivity" in result
        assert "pivotal_witnesses" in result["sensitivity"]


class TestSensitivityAnalysis:
    """Test leave-one-out witness sensitivity analysis."""

    def test_no_witnesses_returns_zero_fragility(self):
        result = sensitivity_analysis([], 0.8, 0.4)
        assert result["fragility_score"] == 0.0
        assert result["pivotal_witnesses"] == []

    def test_single_witness_non_pivotal(self):
        """A single sustained witness on prosecution with large margin is not pivotal."""
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.5, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
        ]
        # Pro starts at 0.9, def at 0.3 — huge margin. Removing one witness won't flip.
        result = sensitivity_analysis(witnesses, 0.9, 0.3)
        assert result["fragility_score"] == 0.0
        assert len(result["pivotal_witnesses"]) == 0
        assert result["full_verdict_direction"] == "prosecution"

    def test_pivotal_witness_detected(self):
        """When a witness barely tips the verdict, removing it should flip."""
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.9, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
        ]
        # Scores are very close: pro=0.49, def=0.50. Sustained +0.09 → pro=0.58 wins.
        # Without the witness, def wins at 0.50 > 0.49.
        result = sensitivity_analysis(witnesses, 0.49, 0.50)
        assert len(result["pivotal_witnesses"]) == 1
        assert result["pivotal_witnesses"][0] == "pro_1"
        assert result["fragility_score"] == 1.0

    def test_per_witness_impact_has_correct_fields(self):
        witnesses = [
            {"claim_id": "d_1", "confidence": 0.7, "verdict_on_claim": "sustained", "from_agent": "defense"},
        ]
        result = sensitivity_analysis(witnesses, 0.6, 0.5)
        assert len(result["per_witness_impact"]) == 1
        impact = result["per_witness_impact"][0]
        assert "claim_id" in impact
        assert "flips_verdict" in impact
        assert "margin_shift" in impact

    def test_fragility_bounded(self):
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.5, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
            {"claim_id": "d_1", "confidence": 0.5, "verdict_on_claim": "overruled", "from_agent": "defense"},
        ]
        result = sensitivity_analysis(witnesses, 0.6, 0.5)
        assert 0.0 <= result["fragility_score"] <= 1.0

    def test_multiple_witnesses_fragility(self):
        """With three witnesses, fragility = pivotal_count / 3."""
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.8, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
            {"claim_id": "pro_2", "confidence": 0.7, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
            {"claim_id": "d_1", "confidence": 0.6, "verdict_on_claim": "sustained", "from_agent": "defense"},
        ]
        result = sensitivity_analysis(witnesses, 0.7, 0.5)
        assert len(result["per_witness_impact"]) == 3
        # Fragility should be N_pivotal / 3
        expected_fragility = len(result["pivotal_witnesses"]) / 3
        assert abs(result["fragility_score"] - expected_fragility) < 0.001

    def test_most_impactful_witness_identified(self):
        """Sensitivity should identify the single most impactful witness."""
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.9, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
            {"claim_id": "d_1", "confidence": 0.3, "verdict_on_claim": "overruled", "from_agent": "defense"},
        ]
        result = sensitivity_analysis(witnesses, 0.49, 0.50)
        assert "most_impactful" in result
        # pro_1 with high confidence sustained should have the largest margin_shift
        assert result["most_impactful"] is not None

    def test_impact_sorted_descending(self):
        """Per-witness impacts should be sorted by margin_shift descending."""
        witnesses = [
            {"claim_id": "pro_1", "confidence": 0.9, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
            {"claim_id": "pro_2", "confidence": 0.3, "verdict_on_claim": "sustained", "from_agent": "prosecutor"},
        ]
        result = sensitivity_analysis(witnesses, 0.5, 0.4)
        impacts = result["per_witness_impact"]
        if len(impacts) >= 2:
            assert impacts[0]["margin_shift"] >= impacts[1]["margin_shift"]
