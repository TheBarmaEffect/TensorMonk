"""Tests for argument quality scoring — multi-dimensional assessment."""

import pytest
from utils.argument_quality import (
    score_evidence_specificity,
    score_claim_diversity,
    score_logical_structure,
    score_confidence_calibration,
    score_opening_coherence,
    score_actionability,
    score_argument_quality,
)


class TestEvidenceSpecificity:
    """Test evidence specificity scoring."""

    def test_specific_evidence_scores_high(self):
        claims = [{"evidence": "Revenue grew 25% in 2024, reaching $50M according to the annual report"}]
        score = score_evidence_specificity(claims)
        assert score > 0.3

    def test_vague_evidence_scores_low(self):
        claims = [{"evidence": "Many significant improvements were possibly achieved"}]
        score = score_evidence_specificity(claims)
        assert score < 0.3

    def test_empty_claims(self):
        assert score_evidence_specificity([]) == 0.0

    def test_no_evidence_field(self):
        claims = [{"statement": "test"}]
        score = score_evidence_specificity(claims)
        assert score == 0.0


class TestClaimDiversity:
    """Test claim diversity scoring."""

    def test_diverse_claims(self):
        claims = [
            {"statement": "Revenue growth exceeds industry benchmarks"},
            {"statement": "Technical architecture scales horizontally"},
            {"statement": "Customer retention rates above average"},
        ]
        score = score_claim_diversity(claims)
        assert score > 0.5

    def test_repetitive_claims(self):
        claims = [
            {"statement": "Market growth strong demand increasing rapidly"},
            {"statement": "Market demand growing strongly with increase"},
        ]
        score = score_claim_diversity(claims)
        assert score < 0.7

    def test_single_claim(self):
        assert score_claim_diversity([{"statement": "test"}]) == 1.0

    def test_empty(self):
        assert score_claim_diversity([]) == 1.0


class TestConfidenceCalibration:
    """Test confidence calibration scoring."""

    def test_well_calibrated(self):
        claims = [
            {"confidence": 0.8}, {"confidence": 0.7},
            {"confidence": 0.85}, {"confidence": 0.75},
        ]
        score = score_confidence_calibration(claims, overall_confidence=0.78)
        assert score > 0.5

    def test_overconfident_overall(self):
        claims = [{"confidence": 0.5}, {"confidence": 0.4}]
        score = score_confidence_calibration(claims, overall_confidence=0.95)
        assert score < 0.5

    def test_extreme_claim_confidence(self):
        claims = [{"confidence": 0.99}, {"confidence": 0.98}]
        score = score_confidence_calibration(claims, overall_confidence=0.98)
        assert score < 0.8

    def test_empty_claims(self):
        assert score_confidence_calibration([], 0.5) == 0.5


class TestOpeningCoherence:
    """Test opening-to-claims alignment."""

    def test_coherent_opening(self):
        opening = "This market opportunity represents significant growth potential"
        claims = [
            {"statement": "The market is growing rapidly"},
            {"statement": "Growth potential exceeds projections"},
        ]
        score = score_opening_coherence(opening, claims)
        assert score > 0.0

    def test_incoherent_opening(self):
        opening = "The weather is nice today"
        claims = [
            {"statement": "Revenue metrics exceed benchmarks"},
            {"statement": "Technical infrastructure is robust"},
        ]
        score = score_opening_coherence(opening, claims)
        assert score == 0.0

    def test_empty_opening(self):
        assert score_opening_coherence("", [{"statement": "test"}]) == 0.0

    def test_empty_claims(self):
        assert score_opening_coherence("test", []) == 0.0


class TestActionability:
    """Test claim actionability scoring."""

    def test_actionable_claims(self):
        claims = [
            {"statement": "Revenue will increase because the market data shows demand"},
            {"statement": "If we invest in infrastructure, then scalability improves"},
        ]
        score = score_actionability(claims)
        assert score > 0.3

    def test_passive_claims(self):
        claims = [
            {"statement": "Things are happening in the industry"},
            {"statement": "Stuff is going on with technology"},
        ]
        score = score_actionability(claims)
        assert score < 0.3

    def test_empty(self):
        assert score_actionability([]) == 0.0


class TestOverallQuality:
    """Test comprehensive quality scoring."""

    def test_high_quality_argument(self):
        data = {
            "agent": "prosecutor",
            "opening": "This market opportunity for cloud computing presents compelling growth evidence",
            "claims": [
                {"statement": "Revenue will grow because market demand shows 25% increase", "evidence": "According to Gartner 2024 report, market grew 25%", "confidence": 0.85},
                {"statement": "Technical infrastructure can scale to handle enterprise workloads", "evidence": "Load tests showed 10x throughput vs baseline in 2023", "confidence": 0.8},
                {"statement": "Customer retention exceeds industry benchmarks specifically", "evidence": "NPS of 72 compared to industry average of 45", "confidence": 0.75},
                {"statement": "If partnerships are secured then distribution reach multiplies", "evidence": "Channel partners increased revenue 3x according to case study", "confidence": 0.7},
            ],
            "confidence": 0.8,
        }
        result = score_argument_quality(data)
        assert result["grade"] in ("A", "B", "C")
        assert result["overall"] > 0.3
        assert result["claim_count"] == 4

    def test_low_quality_argument(self):
        data = {
            "agent": "defense",
            "opening": "Bad idea",
            "claims": [
                {"statement": "Things might go wrong", "evidence": "Various concerns exist", "confidence": 0.99},
            ],
            "confidence": 0.3,
        }
        result = score_argument_quality(data)
        assert result["grade"] in ("C", "D")

    def test_empty_argument(self):
        result = score_argument_quality({})
        assert result["grade"] == "D"
        assert result["overall"] == 0.0

    def test_none_argument(self):
        result = score_argument_quality(None)
        assert result["grade"] == "D"

    def test_contains_all_dimensions(self):
        data = {
            "opening": "test opening",
            "claims": [{"statement": "test", "evidence": "test", "confidence": 0.7}],
            "confidence": 0.7,
        }
        result = score_argument_quality(data)
        dims = result["dimensions"]
        assert "evidence_specificity" in dims
        assert "claim_diversity" in dims
        assert "logical_structure" in dims
        assert "confidence_calibration" in dims
        assert "opening_coherence" in dims
        assert "actionability" in dims


class TestLogicalStructure:
    """Test logical structure scoring."""

    def test_chained_claims(self):
        """Claims that reference each other should score high."""
        claims = [
            {"statement": "Cloud computing market is growing rapidly at 25% CAGR"},
            {"statement": "Because cloud adoption is growing, enterprise spending will increase"},
            {"statement": "Therefore enterprise cloud spending creates acquisition opportunities"},
        ]
        score = score_logical_structure(claims)
        assert score > 0.3

    def test_disconnected_claims(self):
        """Completely unrelated claims should score lower."""
        claims = [
            {"statement": "The weather patterns are shifting globally"},
            {"statement": "Cryptocurrency regulations evolve monthly"},
            {"statement": "Agricultural yields depend on soil quality"},
        ]
        score = score_logical_structure(claims)
        assert score < 0.5

    def test_single_claim_neutral(self):
        """Single claim should get neutral score."""
        assert score_logical_structure([{"statement": "test"}]) == 0.5

    def test_empty_claims(self):
        """Empty claims should return neutral or zero."""
        result = score_logical_structure([])
        assert result <= 0.5

    def test_causal_connectors_boost(self):
        """Claims with causal language should score higher."""
        with_causal = [
            {"statement": "Market demand is strong"},
            {"statement": "Furthermore investment in R&D builds competitive moats"},
            {"statement": "Consequently the company is well positioned for growth"},
        ]
        without_causal = [
            {"statement": "Market demand is strong"},
            {"statement": "Investment in R&D exists"},
            {"statement": "Company positioning noted"},
        ]
        score_with = score_logical_structure(with_causal)
        score_without = score_logical_structure(without_causal)
        assert score_with >= score_without
