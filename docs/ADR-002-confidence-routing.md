# ADR-002: Confidence-Based Verdict Routing

## Status
Accepted

## Context
LLM agents can hallucinate or produce overconfident results. We need a mechanism to detect and handle low-confidence or suspicious verdict conditions before presenting results to users.

## Decision
Implement a three-path confidence gate (`_confidence_gate()`) as a LangGraph conditional edge:

1. **Normal path** → `verdict` node: Average witness confidence >= 0.6 and no hallucination indicators
2. **Low-confidence path** → `verdict_with_review` node: Average witness confidence < 0.6, triggers `interrupt_before` for human-in-the-loop review
3. **Hallucination guard path** → `verdict_low_temp` node: Average confidence > 0.9 AND majority overruled (suspicious pattern), re-runs verdict at `temperature=0.3` for deterministic output

## Consequences
- **Pro**: Catches hallucinated high-confidence claims that contradict witness evidence
- **Pro**: Human-in-the-loop checkpoint prevents low-quality verdicts from reaching users
- **Pro**: Temperature reduction produces more conservative, grounded output
- **Con**: Additional latency for edge cases (re-run at low temp)
- **Con**: Human review requirement pauses async pipeline

## Thresholds
- `LOW_CONFIDENCE_THRESHOLD = 0.6`
- `HIGH_CONFIDENCE_OVERRULE_THRESHOLD = 0.9`
