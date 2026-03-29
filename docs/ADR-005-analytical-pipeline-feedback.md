# ADR-005: Analytical Pipeline Feedback Loops

## Status
Accepted

## Context
The initial pipeline (v1.0) relied on single-pass LLM output with basic validation. While the constitutional isolation and adversarial design ensured argument diversity, there was no mechanism to quantitatively assess argument quality, verdict robustness, or claim dependencies. This meant the pipeline could not self-assess its output quality.

## Decision
We introduce three analytical feedback systems that run alongside the main pipeline:

### 1. Argument Dependency Graph (`utils/argument_graph.py`)
- Builds a directed acyclic graph (DAG) of logical dependencies between claims
- Uses keyword co-occurrence to detect shared concepts between claims
- Computes graph-theoretic metrics: foundation claims (zero in-degree), critical claims (max out-degree), cascading impact (BFS transitive count), coherence (connected component ratio)
- Wired into Judge cross-examination to help prioritize contested claims by cascading impact

### 2. Verdict Stability Analysis (`utils/verdict_stability.py`)
- Monte Carlo-inspired perturbation testing: 50 simulations with ±10% witness confidence perturbation
- Computes evidence margin (how close the verdict is to flipping) and stability score (1 - flip_rate)
- Combined robustness score averages margin-based and perturbation-based stability
- No additional LLM calls — pure numerical analysis of existing evidence scores

### 3. Argument Quality Scoring (`utils/argument_quality.py`)
- 5-dimension heuristic assessment: evidence specificity (regex patterns), claim diversity (pairwise overlap), confidence calibration (internal consistency), opening coherence (keyword alignment), actionability (testable assertions)
- Produces letter grade (A/B/C/D) for quality gate enforcement
- Wired into parallel_arguments_node immediately after prosecution/defense complete

## Consequences
### Positive
- Pipeline output now includes quantitative quality metadata at every stage
- Judge has structural insight into argument quality before cross-examination
- Verdict robustness is measurable without additional LLM cost
- Calibration tracking accumulates accuracy data across sessions

### Negative
- Keyword-based heuristics are approximate (no semantic similarity model)
- Perturbation analysis assumes linear evidence score response
- Additional computational overhead per pipeline run (~5ms, negligible vs LLM latency)

## Metrics
- Argument graph: O(n²) claim pairs, bounded by 4 claims per side = 16 pairs max
- Perturbation: 50 simulations × 3 witnesses = 150 score adjustments per run
- Quality scoring: 5 regex passes per claim = ~20 regex evaluations per argument
