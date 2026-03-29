"""Argument Quality Scoring — multi-dimensional heuristic assessment of argument strength.

Evaluates argument quality across 6 dimensions before the argument enters
the adversarial process. This enables early detection of weak arguments
and provides quality metadata for the Judge's cross-examination.

Dimensions:
1. Evidence specificity: Do claims cite specific data vs vague assertions?
2. Claim diversity: Are claims addressing different aspects or repetitive?
3. Logical structure: Do claims build on each other logically?
4. Confidence calibration: Is the stated confidence realistic given the evidence?
5. Opening coherence: Does the opening statement align with the claims?
6. Actionability: Do claims lead to testable, verifiable conclusions?

Quality grades:
- A (≥0.8): Strong, well-structured argument with specific evidence
- B (≥0.6): Adequate argument with some areas for improvement
- C (≥0.4): Weak argument with significant gaps in evidence or structure
- D (<0.4): Poor argument that may need hallucination guard intervention
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Specificity indicators — words/patterns that suggest concrete evidence
_SPECIFICITY_PATTERNS = [
    r"\d+%",           # Percentages
    r"\$[\d,.]+",      # Dollar amounts
    r"\d{4}",          # Years
    r"\d+[xX]",        # Multipliers (3x, 10X)
    r"according to",   # Attribution
    r"study|research|survey|report",  # Source types
    r"compared to|versus|vs\.",  # Comparisons
    r"increased|decreased|grew|declined",  # Directional data
]

# Vague language patterns — reduce specificity score
_VAGUE_PATTERNS = [
    r"many|some|several|various",
    r"might|could|possibly|perhaps",
    r"significant|considerable|substantial",  # Weasel words without numbers
    r"it is well known|everyone knows",       # Unsubstantiated universals
]


def score_evidence_specificity(claims: list[dict]) -> float:
    """Score how specific and data-grounded the evidence is.

    Looks for concrete indicators (numbers, percentages, citations)
    and penalizes vague, unsubstantiated language.

    Args:
        claims: List of claim dicts with 'evidence' field.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not claims:
        return 0.0

    total_score = 0.0
    for claim in claims:
        evidence = claim.get("evidence", "")
        if not evidence:
            continue

        # Count specificity indicators
        specific_count = sum(
            1 for pattern in _SPECIFICITY_PATTERNS
            if re.search(pattern, evidence, re.IGNORECASE)
        )
        # Count vague indicators
        vague_count = sum(
            1 for pattern in _VAGUE_PATTERNS
            if re.search(pattern, evidence, re.IGNORECASE)
        )

        # Net specificity: specific indicators minus vague penalties
        claim_score = min(1.0, max(0.0, (specific_count * 0.2) - (vague_count * 0.1)))
        total_score += claim_score

    return round(total_score / len(claims), 3) if claims else 0.0


def score_claim_diversity(claims: list[dict]) -> float:
    """Score how diverse the claims are — penalize repetitive arguments.

    Uses keyword overlap between claims to detect redundancy.
    High-quality arguments address different facets of the decision.

    Args:
        claims: List of claim dicts with 'statement' field.

    Returns:
        Score between 0.0 (all identical) and 1.0 (fully diverse).
    """
    if len(claims) <= 1:
        return 1.0

    keyword_sets = []
    for claim in claims:
        words = {w.lower() for w in claim.get("statement", "").split() if len(w) > 3}
        keyword_sets.append(words)

    # Compute average pairwise Jaccard distance for diversity
    total_overlap = 0.0
    pair_count = 0
    for i in range(len(keyword_sets)):
        for j in range(i + 1, len(keyword_sets)):
            if keyword_sets[i] and keyword_sets[j]:
                intersection = len(keyword_sets[i] & keyword_sets[j])
                union = len(keyword_sets[i] | keyword_sets[j])
                jaccard_sim = intersection / union if union > 0 else 0.0
                total_overlap += jaccard_sim
                pair_count += 1

    avg_overlap = total_overlap / pair_count if pair_count > 0 else 0.0
    diversity = 1.0 - avg_overlap

    return round(max(0.0, diversity), 3)


def score_confidence_calibration(claims: list[dict], overall_confidence: float) -> float:
    """Score whether confidence levels are internally consistent.

    Flags if overall confidence is much higher than individual claim
    confidences (overconfident) or if all claims are high confidence
    (unrealistically optimistic).

    Args:
        claims: List of claim dicts with 'confidence' field.
        overall_confidence: The argument's stated overall confidence.

    Returns:
        Score between 0.0 and 1.0. Higher = better calibrated.
    """
    if not claims:
        return 0.5

    claim_confs = [c.get("confidence", 0.5) for c in claims]
    avg_claim_conf = sum(claim_confs) / len(claim_confs)

    # Penalty for overall confidence deviating too far from claim average
    conf_gap = abs(overall_confidence - avg_claim_conf)
    gap_penalty = min(1.0, conf_gap * 3)  # >0.33 gap = max penalty

    # Penalty for all claims being identically confident (unrealistic)
    if len(set(round(c, 1) for c in claim_confs)) == 1 and len(claims) > 2:
        gap_penalty += 0.2

    # Penalty for extreme confidence (>0.95 or <0.1) without strong evidence
    extreme_count = sum(1 for c in claim_confs if c > 0.95 or c < 0.1)
    if extreme_count > 0:
        gap_penalty += extreme_count * 0.1

    return round(max(0.0, 1.0 - gap_penalty), 3)


def score_opening_coherence(opening: str, claims: list[dict]) -> float:
    """Score alignment between opening statement and claims.

    A coherent argument has an opening that previews the main claims.
    Incoherent arguments have openings that don't connect to the evidence.

    Args:
        opening: The argument's opening statement.
        claims: List of claim dicts with 'statement' field.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not opening or not claims:
        return 0.0

    opening_words = {w.lower() for w in opening.split() if len(w) > 3}
    if not opening_words:
        return 0.0

    # Check how many claims share keywords with the opening
    claims_connected = 0
    for claim in claims:
        claim_words = {w.lower() for w in claim.get("statement", "").split() if len(w) > 3}
        if claim_words and opening_words:
            overlap = len(opening_words & claim_words)
            if overlap >= 1:
                claims_connected += 1

    return round(claims_connected / len(claims), 3)


def score_logical_structure(claims: list[dict]) -> float:
    """Score whether claims build on each other in a logical chain.

    A well-structured argument has claims that reference or build upon
    earlier claims, creating a logical progression. We detect this by
    looking for forward references (keywords from earlier claims appearing
    in later claims) and causal connectors.

    Args:
        claims: List of claim dicts with 'statement' field.

    Returns:
        Score between 0.0 and 1.0. Higher = stronger logical chain.
    """
    if len(claims) <= 1:
        return 0.5  # Single claim has neutral structure

    # Extract keyword sets per claim
    claim_words = []
    for claim in claims:
        words = {w.lower() for w in claim.get("statement", "").split() if len(w) > 3}
        claim_words.append(words)

    # Check for forward references: later claims referencing earlier claim keywords
    forward_refs = 0
    total_pairs = 0
    for i in range(1, len(claim_words)):
        for j in range(i):
            if claim_words[i] and claim_words[j]:
                overlap = len(claim_words[i] & claim_words[j])
                if overlap >= 1:
                    forward_refs += 1
                total_pairs += 1

    reference_score = forward_refs / total_pairs if total_pairs > 0 else 0.0

    # Check for causal connectors within claims
    causal_patterns = [
        r"therefore|consequently|thus|hence",
        r"because|since|given that|as a result",
        r"building on|furthermore|additionally|moreover",
        r"this means|this implies|this suggests",
    ]
    causal_count = 0
    for claim in claims:
        stmt = claim.get("statement", "")
        if any(re.search(p, stmt, re.IGNORECASE) for p in causal_patterns):
            causal_count += 1

    causal_score = min(1.0, causal_count / max(1, len(claims) - 1))

    return round(0.6 * reference_score + 0.4 * causal_score, 3)


def score_actionability(claims: list[dict]) -> float:
    """Score whether claims are testable and lead to verifiable conclusions.

    Actionable claims contain specific, falsifiable assertions rather than
    vague opinions. Looks for indicators of testability.

    Args:
        claims: List of claim dicts with 'statement' field.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not claims:
        return 0.0

    actionable_indicators = [
        r"will|can|should|must",     # Directional assertions
        r"because|therefore|since",  # Causal reasoning
        r"if.*then",                 # Conditional logic
        r"evidence|data|shows",      # Evidence-backed
        r"specifically|exactly",     # Precision
    ]

    total = 0.0
    for claim in claims:
        statement = claim.get("statement", "")
        matches = sum(1 for p in actionable_indicators if re.search(p, statement, re.IGNORECASE))
        total += min(1.0, matches * 0.3)

    return round(total / len(claims), 3)


def score_argument_quality(argument_data: dict) -> dict[str, Any]:
    """Compute comprehensive argument quality assessment.

    Evaluates the argument across 6 dimensions and produces an overall
    quality grade (A/B/C/D) with per-dimension scores.

    Args:
        argument_data: Serialized Argument dict with opening, claims, confidence.

    Returns:
        Quality assessment dict with per-dimension scores and overall grade.
    """
    if not argument_data:
        return {"overall": 0.0, "grade": "D", "dimensions": {}}

    claims = argument_data.get("claims", [])
    opening = argument_data.get("opening", "")
    confidence = argument_data.get("confidence", 0.5)

    dimensions = {
        "evidence_specificity": score_evidence_specificity(claims),
        "claim_diversity": score_claim_diversity(claims),
        "logical_structure": score_logical_structure(claims),
        "confidence_calibration": score_confidence_calibration(claims, confidence),
        "opening_coherence": score_opening_coherence(opening, claims),
        "actionability": score_actionability(claims),
    }

    # Weighted overall score (6 dimensions)
    weights = {
        "evidence_specificity": 0.22,
        "claim_diversity": 0.17,
        "logical_structure": 0.15,
        "confidence_calibration": 0.17,
        "opening_coherence": 0.12,
        "actionability": 0.17,
    }

    overall = sum(dimensions[dim] * weights[dim] for dim in weights)
    overall = round(overall, 3)

    # Grade assignment
    if overall >= 0.8:
        grade = "A"
    elif overall >= 0.6:
        grade = "B"
    elif overall >= 0.4:
        grade = "C"
    else:
        grade = "D"

    result = {
        "overall": overall,
        "grade": grade,
        "dimensions": dimensions,
        "claim_count": len(claims),
        "agent": argument_data.get("agent", "unknown"),
    }

    logger.info(
        "Argument quality [%s]: grade=%s, overall=%.3f (specificity=%.2f, diversity=%.2f)",
        result["agent"], grade, overall,
        dimensions["evidence_specificity"], dimensions["claim_diversity"],
    )

    return result


def compare_argument_strength(pro_quality: dict, def_quality: dict) -> dict:
    """Compare prosecution vs defense argument strength across all dimensions.

    Produces a per-dimension comparison showing which side is stronger
    in each area, plus an overall winner determination.

    Args:
        pro_quality: Prosecution quality scores from score_argument_quality().
        def_quality: Defense quality scores from score_argument_quality().

    Returns:
        Dict with per-dimension winners, overall winner, and margin.
    """
    pro_dims = pro_quality.get("dimensions", {})
    def_dims = def_quality.get("dimensions", {})

    all_dims = set(list(pro_dims.keys()) + list(def_dims.keys()))
    dimension_comparison = {}
    pro_wins = 0
    def_wins = 0

    for dim in sorted(all_dims):
        pro_score = pro_dims.get(dim, 0.0)
        def_score = def_dims.get(dim, 0.0)
        if pro_score > def_score:
            winner = "prosecution"
            pro_wins += 1
        elif def_score > pro_score:
            winner = "defense"
            def_wins += 1
        else:
            winner = "tie"
        dimension_comparison[dim] = {
            "prosecution": round(pro_score, 3),
            "defense": round(def_score, 3),
            "winner": winner,
            "margin": round(abs(pro_score - def_score), 3),
        }

    overall_winner = "prosecution" if pro_wins > def_wins else "defense" if def_wins > pro_wins else "tie"

    return {
        "dimensions": dimension_comparison,
        "prosecution_dimension_wins": pro_wins,
        "defense_dimension_wins": def_wins,
        "overall_winner": overall_winner,
        "overall_margin": round(abs(pro_quality.get("overall", 0) - def_quality.get("overall", 0)), 3),
    }
