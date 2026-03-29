"""Confidence calibration — tracks and corrects agent confidence accuracy.

Implements post-hoc calibration tracking and correction for agent confidence
scores. A well-calibrated agent should have its stated confidence match its
actual accuracy: when it says "0.8 confidence", it should be correct ~80%.

Three calibration techniques:
1. **ECE measurement**: Binned Expected Calibration Error (Guo et al. ICML 2017)
2. **Platt scaling**: Logistic regression fit (sigmoid) to map raw → calibrated
   confidence via gradient descent on cross-entropy loss
3. **Isotonic regression**: Pool-Adjacent-Violators Algorithm (PAVA) for
   non-parametric monotone calibration — more flexible than Platt but needs
   more data

This module tracks calibration curves per agent per domain, enabling:
- Detection of overconfident agents (confidence > accuracy)
- Detection of underconfident agents (confidence < accuracy)
- Post-hoc correction via Platt scaling or isotonic regression
- Domain-specific calibration adjustments

Calibration bins: Confidence scores are bucketed into 10 bins (0.0-0.1, etc.)
For each bin, we track: number of predictions and number of correct outcomes.

References:
- Guo et al., "On Calibration of Modern Neural Networks" (ICML 2017)
- Platt, "Probabilistic Outputs for SVMs" (1999)
- Zadrozny & Elkan, "Transforming Classifier Scores into Calibration" (KDD 2002)
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

    def fit_platt_scaling(self) -> dict[str, Any]:
        """Fit Platt scaling to transform raw confidence → calibrated probability.

        Platt scaling fits a logistic regression (sigmoid) to the calibration data:
            P_calibrated = 1 / (1 + exp(-(a * P_raw + b)))

        Parameters a, b are learned via gradient descent on cross-entropy loss
        over the (confidence, correctness) pairs stored in calibration bins.

        Reference: Platt, "Probabilistic Outputs for SVMs" (1999)

        Returns:
            Dict with coefficients a, b, final loss, and fitted flag.
        """
        # Collect (confidence, was_correct) pairs from all bins
        pairs: list[tuple[float, int]] = []
        for b in self.bins:
            if b.total_count > 0:
                avg_conf = b.avg_confidence
                pairs.extend([(avg_conf, 1)] * b.correct_count)
                pairs.extend([(avg_conf, 0)] * (b.total_count - b.correct_count))

        if len(pairs) < 5:
            return {"fitted": False, "reason": "insufficient data (need >= 5 samples)"}

        # Gradient descent on cross-entropy loss
        a, b_coeff = 1.0, 0.0
        lr = 0.01
        n = len(pairs)

        for _ in range(200):
            grad_a, grad_b = 0.0, 0.0
            loss = 0.0

            for conf, y in pairs:
                z = a * conf + b_coeff
                # Numerically stable sigmoid
                p = 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))
                error = p - y
                grad_a += error * conf
                grad_b += error
                loss -= y * math.log(p + 1e-12) + (1 - y) * math.log(1 - p + 1e-12)

            a -= lr * grad_a / n
            b_coeff -= lr * grad_b / n

        self._platt_a = a
        self._platt_b = b_coeff

        logger.info(
            "Platt scaling fit for %s: a=%.4f, b=%.4f, loss=%.4f",
            self.agent_name, a, b_coeff, loss / n,
        )

        return {
            "fitted": True,
            "method": "platt",
            "a": round(a, 4),
            "b": round(b_coeff, 4),
            "loss": round(loss / n, 4),
            "samples": n,
        }

    def fit_isotonic_regression(self) -> dict[str, Any]:
        """Fit isotonic (monotone non-decreasing) calibration via PAVA.

        The Pool-Adjacent-Violators Algorithm (PAVA) iteratively merges
        adjacent bins where accuracy violates monotonicity, producing a
        non-decreasing calibration curve. More flexible than Platt scaling
        (non-parametric) but requires more data.

        Reference: Zadrozny & Elkan, "Transforming Classifier Scores" (KDD 2002)

        Returns:
            Dict with calibrated values, violations fixed, and fitted flag.
        """
        # Extract non-empty bins sorted by confidence
        bins_data = [
            (b.avg_confidence, b.accuracy, b.total_count)
            for b in self.bins
            if b.total_count > 0
        ]

        if len(bins_data) < 3:
            return {"fitted": False, "reason": "insufficient bins (need >= 3 non-empty)"}

        # PAVA: merge adjacent blocks that violate monotonicity
        # Each block: (weighted_sum, total_weight)
        blocks: list[tuple[float, int]] = [
            (acc * cnt, cnt) for _, acc, cnt in bins_data
        ]

        violations_fixed = 0
        i = 0
        while i < len(blocks) - 1:
            avg_i = blocks[i][0] / blocks[i][1]
            avg_next = blocks[i + 1][0] / blocks[i + 1][1]

            if avg_i > avg_next:
                # Merge: pool adjacent violators
                merged_sum = blocks[i][0] + blocks[i + 1][0]
                merged_weight = blocks[i][1] + blocks[i + 1][1]
                blocks[i] = (merged_sum, merged_weight)
                blocks.pop(i + 1)
                violations_fixed += 1
                i = max(0, i - 1)  # Backtrack to check earlier blocks
            else:
                i += 1

        # Extract calibrated probabilities
        calibrated = [round(s / w, 4) for s, w in blocks]

        self._isotonic_values = calibrated
        self._isotonic_bins = len(blocks)

        logger.info(
            "Isotonic regression fit for %s: %d blocks, %d violations fixed",
            self.agent_name, len(blocks), violations_fixed,
        )

        return {
            "fitted": True,
            "method": "isotonic",
            "calibrated_probabilities": calibrated,
            "blocks": len(blocks),
            "violations_fixed": violations_fixed,
        }

    def calibrate_confidence(self, raw_confidence: float) -> float:
        """Apply learned Platt scaling correction to a raw confidence score.

        If Platt coefficients have been fit, applies the sigmoid transform:
            P_calibrated = 1 / (1 + exp(-(a * P_raw + b)))

        Falls back to raw confidence if no correction is available.

        Args:
            raw_confidence: The agent's uncalibrated confidence [0.0, 1.0].

        Returns:
            Calibrated confidence score.
        """
        a = getattr(self, "_platt_a", None)
        b = getattr(self, "_platt_b", None)
        if a is not None and b is not None:
            z = a * raw_confidence + b
            return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))
        return raw_confidence

    def summary(self) -> dict[str, Any]:
        """Summary statistics for this agent's calibration."""
        result = {
            "agent": self.agent_name,
            "total_predictions": self._total_predictions,
            "ece": round(self.expected_calibration_error, 4),
            "is_overconfident": self.is_overconfident,
            "is_underconfident": self.is_underconfident,
            "calibration_curve": self.calibration_curve(),
        }
        # Include Platt coefficients if fitted
        if hasattr(self, "_platt_a"):
            result["platt_scaling"] = {
                "a": round(self._platt_a, 4),
                "b": round(self._platt_b, 4),
            }
        return result


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
