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
