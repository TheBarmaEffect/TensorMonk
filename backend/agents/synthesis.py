"""Synthesis Agent — produces an improved, battle-tested version of the original idea.

Constitutional role: Neutral synthesizer. Takes the best from both sides.
The Synthesis Agent is the ONLY agent that sees the complete proceeding:
research, prosecution, defense, witness reports, and verdict.

Produces a battle-tested version that:
1. Preserves prosecution's strongest sustained claims
2. Directly addresses every defense objection
3. Incorporates witness findings into action items
4. Uses domain-specific few-shot anchors for concrete recommendations

Output quality is measured by:
- Objection coverage: % of defense claims explicitly addressed
- Action specificity: Whether recommended_actions include time bounds
- Strength delta: improvement of strength_score over original confidence
"""

import asyncio
import json
import logging
from typing import Callable, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from config.domain_config import get_synthesis_anchors, get_suggested_format
from utils.resilience import retry_with_backoff
from utils.llm_helpers import parse_llm_json, emit_thinking_phases, create_llm, retry_with_low_temperature
from utils.argument_quality import score_argument_quality
from models.schemas import (
    Argument,
    WitnessReport,
    VerdictResult,
    Synthesis,
    StreamEvent,
)

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are the Synthesis architect. You have witnessed a full adversarial proceeding about a decision. Your job is not to pick a side — it is to produce a BETTER version of the original idea that incorporates the strongest points from both sides and directly addresses every weakness the Defense exposed.

Output as JSON:
{
  "improved_idea": "string — full description of the enhanced, battle-tested version of the original idea (3-5 paragraphs)",
  "addressed_objections": ["string — each Defense objection and specifically how the improved idea addresses it"],
  "recommended_actions": ["string — concrete, actionable next steps to implement the improved idea"],
  "strength_score": 0.0-1.0
}

The strength_score rates the improved idea vs the original: 0.5 means equal, >0.5 means the improved version is stronger, 1.0 means vastly superior.

Return ONLY valid JSON. No markdown, no code fences."""


class SynthesisAgent:
    """Reads the entire proceeding and produces an evolved version of the idea."""

    def __init__(self) -> None:
        self.llm = create_llm(temperature=0.7, max_tokens=3000)

    async def run(
        self,
        decision_question: str,
        research_package: dict,
        prosecutor_argument: Argument,
        defense_argument: Argument,
        witness_reports: list[WitnessReport],
        verdict: VerdictResult,
        output_format: str = "executive",
        domain: str = "business",
        stream_callback: Optional[Callable] = None,
    ) -> Synthesis:
        """Synthesize an improved idea from the full proceeding.

        Args:
            decision_question: The original decision.
            research_package: Neutral research.
            prosecutor_argument: The prosecution's argument.
            defense_argument: The defense's argument.
            witness_reports: All witness verification reports.
            verdict: The judge's final ruling.
            output_format: Style of synthesis output (executive/technical/legal/investor).
            stream_callback: Async callback for stream events.

        Returns:
            A Synthesis with the improved idea.
        """
        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type="synthesis_start",
                    agent="synthesis",
                    content="Synthesizing battle-tested version from full proceeding...",
                )
            )

        witness_data = [
            {
                "claim_id": w.claim_id,
                "type": w.witness_type,
                "resolution": w.resolution,
                "verdict": w.verdict_on_claim,
            }
            for w in witness_reports
        ]

        pro_claims = [{"statement": c.statement, "evidence": c.evidence} for c in prosecutor_argument.claims]
        def_claims = [{"statement": c.statement, "evidence": c.evidence} for c in defense_argument.claims]

        # Score argument quality to inform synthesis priorities
        pro_quality = score_argument_quality(prosecutor_argument.model_dump(mode="json"))
        def_quality = score_argument_quality(defense_argument.model_dump(mode="json"))

        # Few-shot synthesis anchors — domain-specific action examples loaded
        # from YAML config at runtime to ground recommended_actions in reality
        anchors = get_synthesis_anchors(domain)
        anchor_block = ""
        if anchors:
            anchor_block = (
                "\n\nFEW-SHOT ACTION EXAMPLES (for this domain):\n"
                + "\n".join(f"  - {a}" for a in anchors)
                + "\n\nUse these as stylistic anchors for your recommended_actions. "
                "Produce similarly concrete, time-bound steps."
            )

        # Build quality-aware priority guidance
        quality_guidance = ""
        if pro_quality["grade"] != def_quality["grade"]:
            stronger = "prosecution" if pro_quality["overall"] > def_quality["overall"] else "defense"
            quality_guidance = (
                f"\n\nARGUMENT QUALITY ASSESSMENT:\n"
                f"  Prosecution: Grade {pro_quality['grade']} (score {pro_quality['overall']:.2f})\n"
                f"  Defense: Grade {def_quality['grade']} (score {def_quality['overall']:.2f})\n"
                f"  The {stronger}'s arguments were stronger — weight your synthesis accordingly.\n"
            )

        prompt = (
            f"ORIGINAL DECISION: {decision_question}\n\n"
            f"RESEARCH SUMMARY: {research_package.get('summary', '')}\n\n"
            f"PROSECUTION OPENING: {prosecutor_argument.opening}\n"
            f"PROSECUTION CLAIMS:\n{json.dumps(pro_claims, indent=2)}\n\n"
            f"DEFENSE OPENING: {defense_argument.opening}\n"
            f"DEFENSE CLAIMS:\n{json.dumps(def_claims, indent=2)}\n\n"
            f"WITNESS FINDINGS:\n{json.dumps(witness_data, indent=2)}\n\n"
            f"JUDGE VERDICT: {verdict.ruling.upper()}\n"
            f"REASONING: {verdict.reasoning}\n"
            f"KEY FACTORS: {', '.join(verdict.key_factors)}\n"
            f"{quality_guidance}\n"
            f"Output format: {output_format} — tailor your synthesis to this audience.\n"
            f"{anchor_block}\n\n"
            "Now produce a STRONGER, battle-tested version of the original idea "
            "that addresses every weakness exposed during this proceeding."
        )

        messages = [
            SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            thinking_phases = [
                "Reviewing prosecution's strongest points...",
                "Reviewing defense's key objections...",
                "Analyzing witness verification outcomes...",
                "Incorporating judge's ruling and reasoning...",
                "Constructing improved, battle-tested version...",
                "Identifying concrete next steps and actions...",
            ]

            await emit_thinking_phases(
                phases=thinking_phases,
                agent_name="synthesis",
                event_type="synthesis_start",
                stream_callback=stream_callback,
            )

            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=1.0, operation_name="Synthesis LLM",
            )
            full_response = response.content

            data = self._parse_json(full_response)

            # Hallucination guard: if parse failed, retry with low temperature
            if not data.get("improved_idea") or len(data.get("improved_idea", "")) < 50:
                data = await retry_with_low_temperature(
                    messages=messages,
                    parse_fn=self._parse_json,
                    quality_check_fn=lambda d: bool(d.get("improved_idea")) and len(d.get("improved_idea", "")) >= 50,
                    max_tokens=3000,
                    operation_name="Synthesis",
                )

            synthesis = Synthesis(
                decision_id=verdict.decision_id,
                improved_idea=data.get("improved_idea", ""),
                addressed_objections=data.get("addressed_objections", []),
                recommended_actions=data.get("recommended_actions", []),
                strength_score=data.get("strength_score", 0.7),
            )

            # Assess synthesis quality before emitting completion
            coverage = self.assess_synthesis_coverage(
                synthesis, defense_argument, prosecutor_argument,
            )

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="synthesis_complete",
                        agent="synthesis",
                        content=f"Synthesis complete. {coverage['objection_coverage']:.0%} objections addressed.",
                        data={**synthesis.model_dump(mode="json"), "coverage": coverage},
                    )
                )

            logger.info(
                "Synthesis complete — strength=%.2f, coverage=%.0f%%, delta=%+.3f",
                synthesis.strength_score, coverage["objection_coverage"] * 100,
                coverage["strength_delta"],
            )
            return synthesis

        except Exception as e:
            logger.error("Synthesis agent failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(event_type="error", agent="synthesis", content=f"Synthesis error: {str(e)}")
                )
            raise

    def assess_synthesis_coverage(
        self,
        synthesis: Synthesis,
        defense_argument: Argument,
        prosecutor_argument: Argument,
    ) -> dict:
        """Assess how thoroughly the synthesis addresses the proceeding.

        Measures objection coverage (how many defense claims are addressed),
        action specificity (whether recommendations include time bounds),
        and strength delta (improvement over original confidence).

        Args:
            synthesis: The produced synthesis output.
            defense_argument: The defense's case (objections to address).
            prosecutor_argument: The prosecution's case (points to preserve).

        Returns:
            Dict with coverage metrics for quality monitoring.
        """
        # Objection coverage: what fraction of defense claims appear addressed?
        addressed_text = " ".join(synthesis.addressed_objections).lower()
        def_claims_addressed = 0
        for claim in defense_argument.claims:
            # Check if any meaningful words from the claim appear in addressed text
            claim_words = set(claim.statement.lower().split())
            significant_words = {w for w in claim_words if len(w) > 4}
            if significant_words:
                overlap = sum(1 for w in significant_words if w in addressed_text)
                if overlap >= len(significant_words) * 0.3:
                    def_claims_addressed += 1

        total_def_claims = max(len(defense_argument.claims), 1)
        objection_coverage = round(def_claims_addressed / total_def_claims, 3)

        # Action specificity: do recommended_actions include time indicators?
        time_indicators = ("week", "month", "day", "quarter", "q1", "q2", "q3", "q4",
                          "sprint", "phase", "stage", "step 1", "immediately", "within")
        actions_text = " ".join(synthesis.recommended_actions).lower()
        has_time_bounds = any(t in actions_text for t in time_indicators)
        action_count = len(synthesis.recommended_actions)

        # Strength delta: how much stronger is the synthesis vs prosecution's original
        strength_delta = synthesis.strength_score - prosecutor_argument.confidence

        metrics = {
            "objection_coverage": objection_coverage,
            "objections_addressed": def_claims_addressed,
            "total_objections": total_def_claims,
            "action_count": action_count,
            "has_time_bounds": has_time_bounds,
            "strength_delta": round(strength_delta, 3),
            "strength_score": synthesis.strength_score,
        }

        logger.info(
            "Synthesis coverage: %.0f%% objections addressed, %d actions%s, delta=%+.3f",
            objection_coverage * 100, action_count,
            " (time-bound)" if has_time_bounds else "",
            strength_delta,
        )

        return metrics

    def _parse_json(self, response: str) -> dict:
        """Parse JSON from LLM response — delegates to shared utility."""
        return parse_llm_json(
            response,
            fallback={
                "improved_idea": response.strip()[:1000],
                "addressed_objections": [],
                "recommended_actions": [],
                "strength_score": 0.6,
            },
            operation_name="Synthesis",
        )
