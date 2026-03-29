"""Tests for confidence calibration — ECE, overconfidence, and calibration curves."""

import pytest
from utils.confidence_calibration import (
    AgentCalibration,
    CalibrationTracker,
    CalibrationBin,
    _bin_index,
    NUM_BINS,
)


class TestBinIndex:
    """Test confidence-to-bin mapping."""

    def test_zero_maps_to_first_bin(self):
        assert _bin_index(0.0) == 0

    def test_one_maps_to_last_bin(self):
        assert _bin_index(1.0) == NUM_BINS - 1

    def test_midpoint_maps_correctly(self):
        assert _bin_index(0.55) == 5

    def test_boundary_maps_to_higher_bin(self):
        assert _bin_index(0.3) == 3


class TestCalibrationBin:
    """Test individual calibration bin calculations."""

    def test_empty_bin_has_zero_accuracy(self):
        b = CalibrationBin()
        assert b.accuracy == 0.0
        assert b.avg_confidence == 0.0

    def test_perfect_bin(self):
        b = CalibrationBin(confidence_sum=1.6, correct_count=2, total_count=2)
        assert b.accuracy == 1.0
        assert b.avg_confidence == 0.8

    def test_gap_calculation(self):
        b = CalibrationBin(confidence_sum=1.8, correct_count=1, total_count=2)
        # avg_confidence = 0.9, accuracy = 0.5, gap = 0.4
        assert abs(b.gap - 0.4) < 0.001


class TestAgentCalibration:
    """Test per-agent calibration tracking."""

    def test_empty_agent_has_zero_ece(self):
        cal = AgentCalibration("test")
        assert cal.expected_calibration_error == 0.0

    def test_perfect_calibration_has_low_ece(self):
        cal = AgentCalibration("test")
        # Record predictions where confidence matches accuracy
        for _ in range(10):
            cal.record(confidence=0.8, was_correct=True)
        for _ in range(2):
            cal.record(confidence=0.8, was_correct=False)
        # 10/12 = 0.83 accuracy at 0.8 confidence — close to calibrated
        assert cal.expected_calibration_error < 0.1

    def test_overconfident_detection(self):
        cal = AgentCalibration("test")
        # Says 0.9 confident but always wrong
        for _ in range(10):
            cal.record(confidence=0.9, was_correct=False)
        assert cal.is_overconfident is True

    def test_underconfident_detection(self):
        cal = AgentCalibration("test")
        # Says 0.2 confident but always correct
        for _ in range(10):
            cal.record(confidence=0.2, was_correct=True)
        assert cal.is_underconfident is True

    def test_not_enough_data(self):
        cal = AgentCalibration("test")
        cal.record(confidence=0.9, was_correct=False)
        # Not enough data (< 5) to determine overconfidence
        assert cal.is_overconfident is False
        assert cal.is_underconfident is False

    def test_calibration_curve_format(self):
        cal = AgentCalibration("test")
        cal.record(confidence=0.8, was_correct=True)
        cal.record(confidence=0.3, was_correct=False)
        curve = cal.calibration_curve()
        assert len(curve) == 2
        for point in curve:
            assert "bin_midpoint" in point
            assert "avg_confidence" in point
            assert "accuracy" in point
            assert "count" in point

    def test_summary_has_expected_fields(self):
        cal = AgentCalibration("prosecutor")
        cal.record(0.7, True)
        s = cal.summary()
        assert s["agent"] == "prosecutor"
        assert "ece" in s
        assert "is_overconfident" in s
        assert "calibration_curve" in s

    def test_confidence_clamped(self):
        cal = AgentCalibration("test")
        cal.record(confidence=1.5, was_correct=True)  # Should clamp to 1.0
        cal.record(confidence=-0.5, was_correct=False)  # Should clamp to 0.0
        assert cal._total_predictions == 2


class TestCalibrationTracker:
    """Test global calibration tracker."""

    def test_records_per_agent(self):
        tracker = CalibrationTracker()
        tracker.record("prosecutor", "business", 0.8, True)
        tracker.record("defense", "business", 0.7, False)
        assert tracker.get_agent_calibration("prosecutor") is not None
        assert tracker.get_agent_calibration("defense") is not None

    def test_records_per_domain(self):
        tracker = CalibrationTracker()
        tracker.record("prosecutor", "business", 0.8, True)
        tracker.record("prosecutor", "legal", 0.9, False)
        summary = tracker.summary()
        assert "business" in summary["domains"]
        assert "legal" in summary["domains"]

    def test_nonexistent_agent_returns_none(self):
        tracker = CalibrationTracker()
        assert tracker.get_agent_calibration("nonexistent") is None

    def test_summary_structure(self):
        tracker = CalibrationTracker()
        tracker.record("prosecutor", "business", 0.8, True)
        summary = tracker.summary()
        assert "agents" in summary
        assert "domains" in summary
        assert "prosecutor" in summary["agents"]


class TestPlattScaling:
    """Test Platt scaling logistic calibration."""

    def test_insufficient_data_returns_not_fitted(self):
        cal = AgentCalibration("test_agent")
        cal.record(0.9, True)
        result = cal.fit_platt_scaling()
        assert result["fitted"] is False

    def test_platt_fitting_with_sufficient_data(self):
        cal = AgentCalibration("test_agent")
        # Overconfident agent: says 0.9 but correct ~60% of time
        for _ in range(6):
            cal.record(0.9, True)
        for _ in range(4):
            cal.record(0.9, False)
        # Low confidence, usually correct
        for _ in range(8):
            cal.record(0.3, True)
        for _ in range(2):
            cal.record(0.3, False)

        result = cal.fit_platt_scaling()
        assert result["fitted"] is True
        assert "a" in result
        assert "b" in result
        assert "loss" in result
        assert result["samples"] == 20

    def test_platt_calibrate_returns_bounded(self):
        cal = AgentCalibration("test_agent")
        for _ in range(10):
            cal.record(0.8, True)
        for _ in range(5):
            cal.record(0.8, False)
        cal.fit_platt_scaling()

        calibrated = cal.calibrate_confidence(0.8)
        assert 0.0 <= calibrated <= 1.0

    def test_calibrate_without_fit_returns_raw(self):
        cal = AgentCalibration("test_agent")
        assert cal.calibrate_confidence(0.75) == 0.75

    def test_platt_in_summary(self):
        cal = AgentCalibration("test_agent")
        for _ in range(10):
            cal.record(0.7, True)
        for _ in range(5):
            cal.record(0.7, False)
        cal.fit_platt_scaling()
        summary = cal.summary()
        assert "platt_scaling" in summary
        assert "a" in summary["platt_scaling"]


class TestIsotonicRegression:
    """Test PAVA isotonic calibration."""

    def test_insufficient_bins_returns_not_fitted(self):
        cal = AgentCalibration("test_agent")
        cal.record(0.5, True)
        result = cal.fit_isotonic_regression()
        assert result["fitted"] is False

    def test_isotonic_fitting_with_monotonic_data(self):
        cal = AgentCalibration("test_agent")
        # Already monotonic: low conf → low accuracy, high → high
        for _ in range(5):
            cal.record(0.15, False)
        for _ in range(3):
            cal.record(0.15, True)
        for _ in range(7):
            cal.record(0.55, True)
        for _ in range(3):
            cal.record(0.55, False)
        for _ in range(9):
            cal.record(0.85, True)
        for _ in range(1):
            cal.record(0.85, False)

        result = cal.fit_isotonic_regression()
        assert result["fitted"] is True
        assert result["violations_fixed"] == 0  # Already monotonic

    def test_isotonic_fixes_violations(self):
        cal = AgentCalibration("test_agent")
        # Non-monotonic: mid-confidence has HIGHER accuracy than high
        for _ in range(3):
            cal.record(0.25, True)
        for _ in range(7):
            cal.record(0.25, False)
        # Mid-conf: 90% accuracy (violation)
        for _ in range(9):
            cal.record(0.55, True)
        for _ in range(1):
            cal.record(0.55, False)
        # High-conf: 50% accuracy (should be higher than mid!)
        for _ in range(5):
            cal.record(0.85, True)
        for _ in range(5):
            cal.record(0.85, False)

        result = cal.fit_isotonic_regression()
        assert result["fitted"] is True
        assert result["violations_fixed"] >= 1
        # Calibrated values should be non-decreasing
        probs = result["calibrated_probabilities"]
        for i in range(len(probs) - 1):
            assert probs[i] <= probs[i + 1] + 0.001  # Monotone
