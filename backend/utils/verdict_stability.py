"""Verdict Stability Analysis — validates ruling robustness via perturbation testing.

Implements a lightweight Monte Carlo-inspired approach to verdict confidence:
instead of trusting a single LLM ruling, we analyze how sensitive the verdict
is to small changes in the evidence weighting.

The stability analysis:
1. Computes the "evidence margin" — how much the prosecution/defense scores
   would need to change to flip the verdict.
2. Simulates evidence perturbations by varying witness confidence ±10%.
3. Tracks how often the ruling would change under perturbation.
4. Produces a stability score: high stability = robust verdict, low = fragile.

This does NOT make additional LLM calls — it's a pure numerical analysis of
the existing evidence scores, making it fast and free.

Reference: Sensitivity analysis in decision theory (French, 1986)
"""

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

# Seed for reproducibility in perturbation analysis
_PERTURBATION_SEED = 42
_NUM_PERTURBATIONS = 50
_PERTURBATION_RANGE = 0.10  # ±10% witness confidence perturbation


def compute_evidence_margin(
    prosecution_score: float,
    defense_score: float,
    ruling: str,
) -> dict[str, Any]:
    """Compute the evidence margin — how close the verdict is to flipping.

    The margin is the absolute score differential. A larger margin means
    the verdict is more robust; a small margin means it could easily flip
    with slightly different evidence.

    Args:
        prosecution_score: Weighted prosecution evidence score [0.0-1.0].
        defense_score: Weighted defense evidence score [0.0-1.0].
        ruling: The actual ruling (proceed/reject/conditional).

    Returns:
        Dict with margin, closest_flip_direction, and margin classification.
    """
    differential = prosecution_score - defense_score
    margin = abs(differential)

    # Classify margin robustness
    if margin >= 0.3:
        classification = "decisive"
    elif margin >= 0.15:
        classification = "moderate"
    elif margin >= 0.05:
        classification = "narrow"
    else:
        classification = "razor_thin"

    # Direction of closest flip
    if differential > 0:
        flip_direction = "defense_needs_+{:.3f}".format(margin)
    elif differential < 0:
        flip_direction = "prosecution_needs_+{:.3f}".format(margin)
    else:
        flip_direction = "tied"

    return {
        "margin": round(margin, 4),
        "differential": round(differential, 4),
        "classification": classification,
        "flip_direction": flip_direction,
        "ruling": ruling,
    }


def perturbation_stability(
    witness_reports: list[dict],
    prosecution_base_confidence: float,
    defense_base_confidence: float,
    num_simulations: int = _NUM_PERTURBATIONS,
    perturbation_range: float = _PERTURBATION_RANGE,
) -> dict[str, Any]:
    """Simulate witness confidence perturbations to test verdict stability.

    For each simulation, randomly perturbs each witness's confidence by
    ±perturbation_range, recomputes the evidence scores, and checks if
    the ruling direction would change.

    Args:
        witness_reports: List of witness report dicts with confidence, verdict_on_claim, claim_id.
        prosecution_base_confidence: Base prosecution confidence before witness adjustment.
        defense_base_confidence: Base defense confidence before witness adjustment.
        num_simulations: Number of perturbation runs (default 50).
        perturbation_range: Maximum perturbation magnitude (default 0.10).

    Returns:
        Dict with stability_score, flip_count, flip_rate, and confidence interval.
    """
    if not witness_reports:
        return {
            "stability_score": 1.0,
            "flip_count": 0,
            "flip_rate": 0.0,
            "simulations": num_simulations,
            "verdict_distribution": {"prosecution_wins": num_simulations, "defense_wins": 0, "ties": 0},
        }

    rng = random.Random(_PERTURBATION_SEED)
    base_winner = "prosecution" if prosecution_base_confidence >= defense_base_confidence else "defense"

    pro_wins = 0
    def_wins = 0
    ties = 0
    flip_count = 0

    for _ in range(num_simulations):
        pro_score = prosecution_base_confidence
        def_score = defense_base_confidence

        for w in witness_reports:
            # Perturb witness confidence
            original_conf = w.get("confidence", 0.5)
            perturbation = rng.uniform(-perturbation_range, perturbation_range)
            perturbed_conf = max(0.0, min(1.0, original_conf + perturbation))

            verdict = w.get("verdict_on_claim", "inconclusive")

            if verdict == "sustained":
                boost = 0.1 * perturbed_conf
                # Determine which side this claim belongs to based on claim_id prefix
                # (prosecution claims typically start with "pro_" or similar)
                from_agent = w.get("from_agent", "")
                if from_agent == "prosecutor" or (w.get("claim_id", "").startswith("pro")):
                    pro_score = min(1.0, pro_score + boost)
                else:
                    def_score = min(1.0, def_score + boost)
            elif verdict == "overruled":
                penalty = 0.15 * perturbed_conf
                from_agent = w.get("from_agent", "")
                if from_agent == "prosecutor" or (w.get("claim_id", "").startswith("pro")):
                    pro_score = max(0.0, pro_score - penalty)
                else:
                    def_score = max(0.0, def_score - penalty)

        # Determine winner of this simulation
        if pro_score > def_score:
            pro_wins += 1
            if base_winner != "prosecution":
                flip_count += 1
        elif def_score > pro_score:
            def_wins += 1
            if base_winner != "defense":
                flip_count += 1
        else:
            ties += 1
            flip_count += 1  # Tie is effectively a flip if there was a clear winner

    flip_rate = flip_count / num_simulations
    stability_score = round(1.0 - flip_rate, 4)

    result = {
        "stability_score": stability_score,
        "flip_count": flip_count,
        "flip_rate": round(flip_rate, 4),
        "simulations": num_simulations,
        "perturbation_range": perturbation_range,
        "verdict_distribution": {
            "prosecution_wins": pro_wins,
            "defense_wins": def_wins,
            "ties": ties,
        },
        "base_winner": base_winner,
    }

    logger.info(
        "Verdict stability: %.2f (flips=%d/%d, pro_wins=%d, def_wins=%d)",
        stability_score, flip_count, num_simulations, pro_wins, def_wins,
    )

    return result


def full_stability_analysis(
    prosecution_score: float,
    defense_score: float,
    ruling: str,
    witness_reports: list[dict],
    prosecution_base_confidence: float,
    defense_base_confidence: float,
) -> dict[str, Any]:
    """Run complete verdict stability analysis.

    Combines evidence margin analysis with perturbation testing to produce
    a comprehensive stability assessment of the verdict.

    Args:
        prosecution_score: Final weighted prosecution score.
        defense_score: Final weighted defense score.
        ruling: The verdict ruling (proceed/reject/conditional).
        witness_reports: All witness reports.
        prosecution_base_confidence: Pre-witness prosecution confidence.
        defense_base_confidence: Pre-witness defense confidence.

    Returns:
        Complete stability analysis dict.
    """
    margin = compute_evidence_margin(prosecution_score, defense_score, ruling)
    stability = perturbation_stability(
        witness_reports, prosecution_base_confidence, defense_base_confidence,
    )

    # Combined robustness: average of margin-based and perturbation-based scores
    margin_robustness = min(margin["margin"] / 0.3, 1.0)  # Normalize: 0.3 margin = max
    combined = round((margin_robustness + stability["stability_score"]) / 2, 4)

    return {
        "evidence_margin": margin,
        "perturbation_stability": stability,
        "combined_robustness": combined,
        "verdict_is_robust": combined >= 0.7,
    }
