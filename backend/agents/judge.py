"""Judge Agent — cross-examines arguments and delivers final verdict.

Constitutional role: Impartial arbiter. The Judge is the first node in
the graph to receive both Prosecutor and Defense arguments — enforcing
adversarial isolation up to this point.

The Judge performs two distinct phases:
1. Cross-examination: Identifies contested claims for witness verification.
   Uses argument strength differential analysis to prioritize claims
   where the conflict is sharpest (high confidence on both sides).
2. Verdict: Weighs all evidence including witness reports to deliver
   a final ruling (proceed/reject/conditional) with confidence scoring.

Verdict confidence is computed using witness-weighted evidence scoring:
- Sustained witness claims boost the originating side's weight
- Overruled claims reduce that side's weight
- Inconclusive claims are neutral (no weight change)
"""

import asyncio
import json
import logging
from typing import Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import Argument, WitnessReport, VerdictResult, StreamEvent
from utils.resilience import retry_with_backoff
from utils.llm_helpers import parse_llm_json, emit_thinking_phases, create_llm

logger = logging.getLogger(__name__)

CROSS_EXAM_SYSTEM_PROMPT = """You are the Judge in an adversarial AI courtroom. You have received arguments from both the Prosecution (arguing FOR) and Defense (arguing AGAINST) a decision.

Identify the 3 most contested factual claims — claims where both sides make opposing assertions with evidence. For each contested claim, specify which claim IDs are in conflict and what type of verification is needed.

Output as JSON:
{
  "contested_claims": [
    {
      "claim_id": "string — the ID of the claim to verify",
      "from_agent": "prosecutor or defense",
      "statement": "string — the claim statement",
      "conflict_reason": "string — why this claim is contested",
      "witness_type": "fact | data | precedent"
    }
  ],
  "judge_notes": "string — your preliminary observations on the quality of both arguments"
}

Return ONLY valid JSON. Exactly 3 contested claims."""

VERDICT_SYSTEM_PROMPT = """You are the Judge in an adversarial AI courtroom. You have heard both sides argue, identified contested claims, and received verification reports from specialist witnesses.

Now deliver your final verdict. Consider:
- The strength of each side's arguments
- Which claims were sustained, overruled, or inconclusive after witness verification
- The overall weight of evidence

Output as JSON:
{
  "ruling": "proceed | reject | conditional",
  "reasoning": "string — detailed reasoning for your ruling (3-5 sentences)",
  "key_factors": ["string — the 3-5 most important factors in your decision"],
  "confidence": 0.0-1.0
}

Return ONLY valid JSON. Be decisive and well-reasoned."""


class JudgeAgent:
    """Manages cross-examination and delivers the final verdict."""

    def __init__(self) -> None:
        self.llm = create_llm(temperature=0.4, max_tokens=2048)

    def analyze_argument_strength(
        self,
        prosecutor_argument: Argument,
        defense_argument: Argument,
    ) -> dict:
        """Analyze relative argument strength before cross-examination.

        Computes per-claim confidence statistics and identifies potential
        areas of conflict based on claim overlap. This pre-analysis helps
        the cross-examination LLM focus on the most impactful claims.

        Args:
            prosecutor_argument: The prosecution's case.
            defense_argument: The defense's case.

        Returns:
            Dict with strength metrics for both sides.
        """
        pro_confs = [c.confidence for c in prosecutor_argument.claims]
        def_confs = [c.confidence for c in defense_argument.claims]

        pro_avg = sum(pro_confs) / len(pro_confs) if pro_confs else 0.0
        def_avg = sum(def_confs) / len(def_confs) if def_confs else 0.0

        # Find high-confidence claims on both sides (likely contested areas)
        pro_high = [c for c in prosecutor_argument.claims if c.confidence >= 0.8]
        def_high = [c for c in defense_argument.claims if c.confidence >= 0.8]

        return {
            "prosecution": {
                "overall_confidence": prosecutor_argument.confidence,
                "avg_claim_confidence": round(pro_avg, 3),
                "claim_count": len(pro_confs),
                "high_confidence_claims": len(pro_high),
            },
            "defense": {
                "overall_confidence": defense_argument.confidence,
                "avg_claim_confidence": round(def_avg, 3),
                "claim_count": len(def_confs),
                "high_confidence_claims": len(def_high),
            },
            "strength_differential": round(pro_avg - def_avg, 3),
            "total_claims": len(pro_confs) + len(def_confs),
            "claim_overlaps": self.detect_claim_overlaps(
                prosecutor_argument, defense_argument,
            ),
        }

    def detect_claim_overlaps(
        self,
        prosecutor_argument: Argument,
        defense_argument: Argument,
        overlap_threshold: float = 0.3,
    ) -> list[dict]:
        """Detect overlapping claims between prosecution and defense.

        Uses keyword overlap analysis to find claims that address the same
        underlying topic from opposing sides. High-overlap claim pairs
        represent the strongest contested points — they should be prioritized
        for witness verification during cross-examination.

        The overlap score is computed as:
            |significant_words_A ∩ significant_words_B| / min(|A|, |B|)

        where significant words are those with length > 3 (filtering out
        stop words, articles, prepositions).

        Args:
            prosecutor_argument: The prosecution's case.
            defense_argument: The defense's case.
            overlap_threshold: Minimum overlap score to consider claims related.

        Returns:
            List of overlap dicts with claim IDs, overlap score, and shared keywords.
        """
        overlaps = []

        for pro_claim in prosecutor_argument.claims:
            pro_words = {
                w.lower() for w in pro_claim.statement.split()
                if len(w) > 3
            }
            if not pro_words:
                continue

            for def_claim in defense_argument.claims:
                def_words = {
                    w.lower() for w in def_claim.statement.split()
                    if len(w) > 3
                }
                if not def_words:
                    continue

                shared = pro_words & def_words
                min_size = min(len(pro_words), len(def_words))
                overlap_score = len(shared) / min_size if min_size > 0 else 0.0

                if overlap_score >= overlap_threshold:
                    overlaps.append({
                        "prosecutor_claim_id": pro_claim.id,
                        "defense_claim_id": def_claim.id,
                        "overlap_score": round(overlap_score, 3),
                        "shared_keywords": sorted(shared),
                        "confidence_gap": round(
                            abs(pro_claim.confidence - def_claim.confidence), 3
                        ),
                    })

        # Sort by overlap score descending — highest conflict first
        overlaps.sort(key=lambda x: x["overlap_score"], reverse=True)

        if overlaps:
            logger.info(
                "Detected %d claim overlaps (top overlap: %.2f)",
                len(overlaps), overlaps[0]["overlap_score"],
            )

        return overlaps

    async def cross_examine(
        self,
        decision_question: str,
        prosecutor_argument: Argument,
        defense_argument: Argument,
        stream_callback: Optional[Callable] = None,
    ) -> list[dict]:
        """Identify the 3 most contested claims for witness verification.

        Performs argument strength analysis before LLM cross-examination
        to help focus on the highest-impact contested claims.

        Args:
            decision_question: The decision being evaluated.
            prosecutor_argument: The prosecution's structured argument.
            defense_argument: The defense's structured argument.
            stream_callback: Async callback for stream events.

        Returns:
            List of contested claim dicts with witness_type.
        """
        # Pre-analyze argument strength for cross-examination focus
        strength = self.analyze_argument_strength(prosecutor_argument, defense_argument)
        logger.info(
            "Argument strength — Pro: %.2f avg, Def: %.2f avg, Differential: %+.3f",
            strength["prosecution"]["avg_claim_confidence"],
            strength["defense"]["avg_claim_confidence"],
            strength["strength_differential"],
        )

        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type="judge_start",
                    agent="judge",
                    content="Cross-examination initiated. Reviewing both arguments...",
                    data={"argument_strength": strength},
                )
            )

        pro_claims = [
            {"id": c.id, "agent": "prosecutor", "statement": c.statement, "evidence": c.evidence}
            for c in prosecutor_argument.claims
        ]
        def_claims = [
            {"id": c.id, "agent": "defense", "statement": c.statement, "evidence": c.evidence}
            for c in defense_argument.claims
        ]

        prompt = (
            f"Decision: {decision_question}\n\n"
            f"PROSECUTION ARGUMENT:\nOpening: {prosecutor_argument.opening}\n"
            f"Claims: {json.dumps(pro_claims, indent=2)}\n\n"
            f"DEFENSE ARGUMENT:\nOpening: {defense_argument.opening}\n"
            f"Claims: {json.dumps(def_claims, indent=2)}\n\n"
            "Identify the 3 most contested claims across both arguments."
        )

        messages = [
            SystemMessage(content=CROSS_EXAM_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            await emit_thinking_phases(
                phases=[
                    "Reviewing prosecution's opening statement and claims...",
                    "Reviewing defense's opening statement and claims...",
                    "Comparing conflicting evidence from both sides...",
                    "Identifying the most contested factual claims...",
                    "Selecting claims for witness verification...",
                ],
                agent_name="judge",
                event_type="judge_start",
                stream_callback=stream_callback,
            )

            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=1.0, operation_name="Judge cross-examination",
            )
            full_response = response.content

            result = self._parse_json(full_response)
            contested = result.get("contested_claims", [])
            logger.info("Judge identified %d contested claims", len(contested))
            return contested

        except Exception as e:
            logger.error("Judge cross-examination failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(event_type="error", agent="judge", content=f"Judge error: {str(e)}")
                )
            raise

    async def deliver_verdict(
        self,
        decision_question: str,
        prosecutor_argument: Argument,
        defense_argument: Argument,
        witness_reports: list[WitnessReport],
        decision_id: str,
        stream_callback: Optional[Callable] = None,
    ) -> VerdictResult:
        """Deliver the final ruling based on all evidence.

        Args:
            decision_question: The decision being evaluated.
            prosecutor_argument: The prosecution's argument.
            defense_argument: The defense's argument.
            witness_reports: Verification reports from witnesses.
            decision_id: The session decision ID.
            stream_callback: Async callback for stream events.

        Returns:
            The final VerdictResult.
        """
        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type="verdict_start",
                    agent="judge",
                    content="All evidence received. Deliberating...",
                )
            )

        witness_data = [
            {
                "claim_id": w.claim_id,
                "type": w.witness_type,
                "resolution": w.resolution,
                "verdict_on_claim": w.verdict_on_claim,
                "confidence": w.confidence,
            }
            for w in witness_reports
        ]

        # Compute witness-weighted evidence scores for quantitative grounding
        evidence_scores = self.compute_evidence_score(
            prosecutor_argument, defense_argument, witness_reports,
        )

        prompt = (
            f"Decision: {decision_question}\n\n"
            f"PROSECUTION (confidence {prosecutor_argument.confidence}):\n{prosecutor_argument.opening}\n\n"
            f"DEFENSE (confidence {defense_argument.confidence}):\n{defense_argument.opening}\n\n"
            f"WITNESS VERIFICATION REPORTS:\n{json.dumps(witness_data, indent=2)}\n\n"
            f"EVIDENCE SCORING (witness-weighted):\n"
            f"  Prosecution score: {evidence_scores['prosecution_score']}\n"
            f"  Defense score: {evidence_scores['defense_score']}\n"
            f"  Score differential: {evidence_scores['score_differential']}\n\n"
            "Consider these evidence scores alongside your qualitative analysis. "
            "Deliver your final verdict."
        )

        messages = [
            SystemMessage(content=VERDICT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            await emit_thinking_phases(
                phases=[
                    "Weighing prosecution arguments against evidence...",
                    "Weighing defense arguments against evidence...",
                    "Reviewing witness verification reports...",
                    "Assessing overall weight of evidence...",
                    "Formulating final ruling...",
                ],
                agent_name="judge",
                event_type="verdict_start",
                stream_callback=stream_callback,
                delay=0.4,
            )

            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=1.0, operation_name="Judge verdict",
            )
            full_response = response.content

            data = self._parse_json(full_response)

            verdict = VerdictResult(
                decision_id=decision_id,
                ruling=data.get("ruling", "conditional"),
                reasoning=data.get("reasoning", ""),
                key_factors=data.get("key_factors", []),
                confidence=data.get("confidence", 0.5),
            )

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="verdict_complete",
                        agent="judge",
                        content=f"Verdict: {verdict.ruling.upper()}",
                        data=verdict.model_dump(mode="json"),
                    )
                )

            logger.info("Judge delivered verdict: %s (%.2f)", verdict.ruling, verdict.confidence)
            return verdict

        except Exception as e:
            logger.error("Judge verdict failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(event_type="error", agent="judge", content=f"Verdict error: {str(e)}")
                )
            raise

    def compute_evidence_score(
        self,
        prosecutor_argument: Argument,
        defense_argument: Argument,
        witness_reports: list[WitnessReport],
    ) -> dict:
        """Compute witness-weighted evidence scores for both sides.

        Each side starts with their stated confidence. Witness verdicts
        then adjust the scores:
        - Sustained claims for a side: +0.1 * witness_confidence
        - Overruled claims for a side: -0.15 * witness_confidence
        - Inconclusive: no adjustment

        This provides a quantitative foundation for the Judge's LLM
        reasoning — the LLM sees these scores in the prompt.

        Args:
            prosecutor_argument: The prosecution's case.
            defense_argument: The defense's case.
            witness_reports: All witness verification reports.

        Returns:
            Dict with pro_score, def_score, and per-claim adjustments.
        """
        pro_score = prosecutor_argument.confidence
        def_score = defense_argument.confidence

        # Build claim ownership map
        pro_claim_ids = {c.id for c in prosecutor_argument.claims}
        def_claim_ids = {c.id for c in defense_argument.claims}

        adjustments = []
        for w in witness_reports:
            is_pro_claim = w.claim_id in pro_claim_ids
            is_def_claim = w.claim_id in def_claim_ids
            adj_target = "prosecutor" if is_pro_claim else "defense" if is_def_claim else "unknown"

            if w.verdict_on_claim == "sustained":
                boost = 0.1 * w.confidence
                if is_pro_claim:
                    pro_score = min(1.0, pro_score + boost)
                elif is_def_claim:
                    def_score = min(1.0, def_score + boost)
                adjustments.append({
                    "claim_id": w.claim_id, "verdict": "sustained",
                    "side": adj_target, "adjustment": f"+{boost:.3f}",
                })
            elif w.verdict_on_claim == "overruled":
                penalty = 0.15 * w.confidence
                if is_pro_claim:
                    pro_score = max(0.0, pro_score - penalty)
                elif is_def_claim:
                    def_score = max(0.0, def_score - penalty)
                adjustments.append({
                    "claim_id": w.claim_id, "verdict": "overruled",
                    "side": adj_target, "adjustment": f"-{penalty:.3f}",
                })
            else:
                adjustments.append({
                    "claim_id": w.claim_id, "verdict": "inconclusive",
                    "side": adj_target, "adjustment": "0",
                })

        logger.info(
            "Evidence scores — Prosecution: %.3f, Defense: %.3f (%d adjustments)",
            pro_score, def_score, len(adjustments),
        )

        return {
            "prosecution_score": round(pro_score, 3),
            "defense_score": round(def_score, 3),
            "score_differential": round(pro_score - def_score, 3),
            "adjustments": adjustments,
        }

    def _parse_json(self, response: str) -> dict:
        """Parse JSON from LLM response — delegates to shared utility."""
        return parse_llm_json(response, fallback={}, operation_name="Judge")
