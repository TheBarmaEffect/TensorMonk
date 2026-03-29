"""Synthesis Agent — produces an improved, battle-tested version of the original idea."""

import asyncio
import json
import logging
from typing import Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from config.domain_config import get_synthesis_anchors, get_suggested_format
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
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=3000,
            api_key=settings.groq_api_key,
        )

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
            f"KEY FACTORS: {', '.join(verdict.key_factors)}\n\n"
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

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(
                        StreamEvent(
                            event_type="synthesis_start",
                            agent="synthesis",
                            content=phase + "\n",
                        )
                    )
                    await asyncio.sleep(0.3)

            response = await self.llm.ainvoke(messages)
            full_response = response.content

            data = self._parse_json(full_response)

            # Hallucination guard: if parse failed, retry with low temperature
            if not data.get("improved_idea") or len(data.get("improved_idea", "")) < 50:
                logger.warning("Synthesis output malformed, retrying with temperature=0.3")
                retry_llm = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    max_tokens=3000,
                    api_key=settings.groq_api_key,
                )
                retry_response = await retry_llm.ainvoke(messages)
                data = self._parse_json(retry_response.content)

            synthesis = Synthesis(
                decision_id=verdict.decision_id,
                improved_idea=data.get("improved_idea", ""),
                addressed_objections=data.get("addressed_objections", []),
                recommended_actions=data.get("recommended_actions", []),
                strength_score=data.get("strength_score", 0.7),
            )

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="synthesis_complete",
                        agent="synthesis",
                        content="Synthesis complete. Battle-tested version ready.",
                        data=synthesis.model_dump(mode="json"),
                    )
                )

            logger.info("Synthesis complete, strength_score=%.2f", synthesis.strength_score)
            return synthesis

        except Exception as e:
            logger.error("Synthesis agent failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(event_type="error", agent="synthesis", content=f"Synthesis error: {str(e)}")
                )
            raise

    def _parse_json(self, response: str) -> dict:
        """Parse JSON from LLM response."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse synthesis JSON")
            return {
                "improved_idea": cleaned[:1000],
                "addressed_objections": [],
                "recommended_actions": [],
                "strength_score": 0.6,
            }
