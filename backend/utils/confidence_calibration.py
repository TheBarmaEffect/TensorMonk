"""Confidence calibration — tracks agent confidence accuracy over time.

Implements Bayesian-inspired calibration tracking for agent confidence scores.
A well-calibrated agent should have its stated confidence match its actual
accuracy: when it says "0.8 confidence", it should be correct ~80% of the time.

This module tracks calibration curves per agent per domain, enabling:
- Detection of overconfident agents (confidence > accuracy)
- Detection of underconfident agents (confidence < accuracy)
- Domain-specific calibration adjustments
- Historical accuracy trend analysis

Calibration bins: Confidence scores are bucketed into 10 bins (0.0-0.1, 0.1-0.2, etc.)
For each bin, we track: number of predictions and number of correct outcomes.

Reference: Guo et al., "On Calibration of Modern Neural Networks" (ICML 2017)
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Number of calibration bins (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
NUM_BINS = 10


@dataclass
class CalibrationBin:
    """A single bin in the calibration curve.

    Attributes:
        confidence_sum: Sum of confidence scores in this bin
        correct_count: Number of predictions that were correct
        total_count: Total predictions in this bin
    """
    confidence_sum: float = 0.0
    correct_count: int = 0
    total_count: int = 0

    @property
    def avg_confidence(self) -> float:
        """Average stated confidence in this bin."""
        return self.confidence_sum / self.total_count if self.total_count > 0 else 0.0

    @property
    def accuracy(self) -> float:
        """Actual accuracy (fraction of correct predictions) in this bin."""
        return self.correct_count / self.total_count if self.total_count > 0 else 0.0

    @property
    def gap(self) -> float:
        """Calibration gap: |confidence - accuracy|. Lower is better."""
        return abs(self.avg_confidence - self.accuracy)


def _bin_index(confidence: float) -> int:
    """Map a confidence score [0.0, 1.0] to a bin index [0, NUM_BINS-1]."""
    idx = int(confidence * NUM_BINS)
    return min(idx, NUM_BINS - 1)


class AgentCalibration:
    """Tracks calibration metrics for a single agent.

    Maintains per-bin statistics to construct a calibration curve
    and compute Expected Calibration Error (ECE).

    Usage:
        cal = AgentCalibration("prosecutor")
        cal.record(confidence=0.85, was_correct=True)
        cal.record(confidence=0.92, was_correct=False)
        print(cal.expected_calibration_error)
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.bins = [CalibrationBin() for _ in range(NUM_BINS)]
        self._total_predictions = 0

    def record(self, confidence: float, was_correct: bool) -> None:
        """Record a prediction outcome for calibration tracking.

        Args:
            confidence: The agent's stated confidence [0.0, 1.0]
            was_correct: Whether the prediction was actually correct
        """
        confidence = max(0.0, min(1.0, confidence))
        idx = _bin_index(confidence)
        self.bins[idx].confidence_sum += confidence
        self.bins[idx].total_count += 1
        if was_correct:
            self.bins[idx].correct_count += 1
        self._total_predictions += 1

    @property
    def expected_calibration_error(self) -> float:
        """Expected Calibration Error (ECE) — weighted average of per-bin gaps.

        ECE = sum(n_bin / N * |accuracy_bin - confidence_bin|)

        Lower is better. A perfectly calibrated agent has ECE = 0.
        """
        if self._total_predictions == 0:
            return 0.0

        ece = 0.0
        for b in self.bins:
            if b.total_count > 0:
                weight = b.total_count / self._total_predictions
                ece += weight * b.gap
        return ece

    @property
    def is_overconfident(self) -> bool:
        """Whether the agent's confidence systematically exceeds its accuracy."""
        if self._total_predictions < 5:
            return False  # Not enough data
        weighted_diff = 0.0
        for b in self.bins:
            if b.total_count > 0:
                weight = b.total_count / self._total_predictions
                weighted_diff += weight * (b.avg_confidence - b.accuracy)
        return weighted_diff > 0.1  # 10% threshold

    @property
    def is_underconfident(self) -> bool:
        """Whether the agent's accuracy systematically exceeds its confidence."""
        if self._total_predictions < 5:
            return False
        weighted_diff = 0.0
        for b in self.bins:
            if b.total_count > 0:
                weight = b.total_count / self._total_predictions
                weighted_diff += weight * (b.accuracy - b.avg_confidence)
        return weighted_diff > 0.1

    def calibration_curve(self) -> list[dict[str, Any]]:
        """Generate the calibration curve data points.

        Returns:
            List of dicts with bin midpoint, avg_confidence, accuracy, and count.
        """
        curve = []
        for i, b in enumerate(self.bins):
            if b.total_count > 0:
                curve.append({
                    "bin_midpoint": (i + 0.5) / NUM_BINS,
                    "avg_confidence": round(b.avg_confidence, 3),
                    "accuracy": round(b.accuracy, 3),
                    "count": b.total_count,
                    "gap": round(b.gap, 3),
                })
        return curve

    def summary(self) -> dict[str, Any]:
        """Summary statistics for this agent's calibration."""
        return {
            "agent": self.agent_name,
            "total_predictions": self._total_predictions,
            "ece": round(self.expected_calibration_error, 4),
            "is_overconfident": self.is_overconfident,
            "is_underconfident": self.is_underconfident,
            "calibration_curve": self.calibration_curve(),
        }


class CalibrationTracker:
    """Global tracker for all agent calibration data.

    Maintains per-agent, per-domain calibration records.

    Usage:
        tracker = CalibrationTracker()
        tracker.record("prosecutor", "business", confidence=0.85, was_correct=True)
        summary = tracker.summary()
    """

    def __init__(self):
        self._agents: dict[str, AgentCalibration] = {}
        self._domain_agents: dict[str, dict[str, AgentCalibration]] = defaultdict(dict)

    def record(
        self,
        agent_name: str,
        domain: str,
        confidence: float,
        was_correct: bool,
    ) -> None:
        """Record a prediction outcome.

        Args:
            agent_name: Which agent made the prediction
            domain: Decision domain for domain-specific tracking
            confidence: Stated confidence [0.0, 1.0]
            was_correct: Whether the prediction was correct
        """
        # Global per-agent tracking
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentCalibration(agent_name)
        self._agents[agent_name].record(confidence, was_correct)

        # Domain-specific tracking
        if agent_name not in self._domain_agents[domain]:
            self._domain_agents[domain][agent_name] = AgentCalibration(
                f"{agent_name}@{domain}"
            )
        self._domain_agents[domain][agent_name].record(confidence, was_correct)

    def get_agent_calibration(self, agent_name: str) -> Optional[AgentCalibration]:
        """Get calibration data for a specific agent."""
        return self._agents.get(agent_name)

    def summary(self) -> dict[str, Any]:
        """Full calibration summary across all agents and domains."""
        return {
            "agents": {
                name: cal.summary() for name, cal in self._agents.items()
            },
            "domains": {
                domain: {
                    name: cal.summary() for name, cal in agents.items()
                }
                for domain, agents in self._domain_agents.items()
            },
        }


# Global singleton
calibration_tracker = CalibrationTracker()
