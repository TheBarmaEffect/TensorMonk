"""Judge Agent — cross-examines arguments and delivers final verdict."""

import asyncio
import json
import logging
from typing import Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import Argument, WitnessReport, VerdictResult, StreamEvent

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
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=2048,
            api_key=settings.groq_api_key,
        )

    async def cross_examine(
        self,
        decision_question: str,
        prosecutor_argument: Argument,
        defense_argument: Argument,
        stream_callback: Optional[Callable] = None,
    ) -> list[dict]:
        """Identify the 3 most contested claims for witness verification.

        Args:
            decision_question: The decision being evaluated.
            prosecutor_argument: The prosecution's structured argument.
            defense_argument: The defense's structured argument.
            stream_callback: Async callback for stream events.

        Returns:
            List of contested claim dicts with witness_type.
        """
        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type="judge_start",
                    agent="judge",
                    content="Cross-examination initiated. Reviewing both arguments...",
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
            thinking_phases = [
                "Reviewing prosecution's opening statement and claims...",
                "Reviewing defense's opening statement and claims...",
                "Comparing conflicting evidence from both sides...",
                "Identifying the most contested factual claims...",
                "Selecting claims for witness verification...",
            ]

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(
                        StreamEvent(
                            event_type="judge_start",
                            agent="judge",
                            content=phase + "\n",
                        )
                    )
                    await asyncio.sleep(0.3)

            response = await self.llm.ainvoke(messages)
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

        prompt = (
            f"Decision: {decision_question}\n\n"
            f"PROSECUTION (confidence {prosecutor_argument.confidence}):\n{prosecutor_argument.opening}\n\n"
            f"DEFENSE (confidence {defense_argument.confidence}):\n{defense_argument.opening}\n\n"
            f"WITNESS VERIFICATION REPORTS:\n{json.dumps(witness_data, indent=2)}\n\n"
            "Deliver your final verdict."
        )

        messages = [
            SystemMessage(content=VERDICT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            thinking_phases = [
                "Weighing prosecution arguments against evidence...",
                "Weighing defense arguments against evidence...",
                "Reviewing witness verification reports...",
                "Assessing overall weight of evidence...",
                "Formulating final ruling...",
            ]

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(
                        StreamEvent(
                            event_type="verdict_start",
                            agent="judge",
                            content=phase + "\n",
                        )
                    )
                    await asyncio.sleep(0.4)

            response = await self.llm.ainvoke(messages)
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

    def _parse_json(self, response: str) -> dict:
        """Parse JSON from LLM response, handling markdown fences."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse judge JSON response")
            return {}
