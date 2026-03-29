"""Witness Agent factory — spawns specialist witnesses to verify contested claims."""

import json
import logging
from typing import Callable, Literal, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import WitnessReport, StreamEvent

logger = logging.getLogger(__name__)

WITNESS_PROMPTS: dict[str, str] = {
    "fact": (
        "You are a Fact Witness in an AI courtroom. You verify factual claims. "
        "Research this claim and determine if it is accurate, partially accurate, or false. "
        "Cite your reasoning with specific facts."
    ),
    "data": (
        "You are a Data Witness in an AI courtroom. You verify data and statistical claims. "
        "Evaluate the quality, recency, and relevance of data cited in this claim. "
        "Identify any cherry-picked statistics, outdated figures, or misrepresentations."
    ),
    "precedent": (
        "You are a Precedent Witness in an AI courtroom. You verify precedent-based claims. "
        "Evaluate whether the historical precedents cited actually support this claim in this context. "
        "Identify false analogies or missing context."
    ),
}

WITNESS_OUTPUT_FORMAT = """
Output as JSON:
{
  "resolution": "string — your detailed finding on this claim (3-5 sentences)",
  "confidence": 0.0-1.0,
  "verdict_on_claim": "sustained | overruled | inconclusive"
}

Return ONLY valid JSON. No markdown, no code fences."""


class WitnessAgent:
    """Factory that spawns specialist witnesses to verify claims."""

    def __init__(self) -> None:
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=1024,
            api_key=settings.groq_api_key,
        )

    async def verify_claim(
        self,
        claim_id: str,
        claim_statement: str,
        claim_evidence: str,
        witness_type: Literal["fact", "data", "precedent"],
        stream_callback: Optional[Callable] = None,
    ) -> WitnessReport:
        """Spawn a specialist witness to verify a single contested claim.

        Args:
            claim_id: ID of the claim being verified.
            claim_statement: The claim text.
            claim_evidence: The evidence provided for the claim.
            witness_type: Type of specialist witness to spawn.
            stream_callback: Async callback for stream events.

        Returns:
            A WitnessReport with the verification result.
        """
        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type="witness_spawned",
                    agent=f"witness_{witness_type}",
                    content=f"Spawning {witness_type} witness to verify claim...",
                    data={"witness_type": witness_type, "claim": claim_statement},
                )
            )

        system_prompt = WITNESS_PROMPTS.get(witness_type, WITNESS_PROMPTS["fact"])
        system_prompt += WITNESS_OUTPUT_FORMAT

        prompt = (
            f"CLAIM TO VERIFY:\n"
            f"Statement: {claim_statement}\n"
            f"Evidence provided: {claim_evidence}\n\n"
            f"Verify this claim thoroughly."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]

        try:
            full_response = ""
            async for chunk in self.llm.astream(messages):
                token = chunk.content
                if token:
                    full_response += token

            data = self._parse_json(full_response)

            # Normalize verdict_on_claim to valid enum values
            raw_verdict = str(data.get("verdict_on_claim", "inconclusive")).lower().strip()
            if "sustain" in raw_verdict or "accurate" in raw_verdict or "true" in raw_verdict or "confirm" in raw_verdict or "support" in raw_verdict:
                normalized_verdict = "sustained"
            elif "overrule" in raw_verdict or "false" in raw_verdict or "reject" in raw_verdict or "invalid" in raw_verdict or "refute" in raw_verdict:
                normalized_verdict = "overruled"
            else:
                normalized_verdict = "inconclusive"

            report = WitnessReport(
                claim_id=claim_id,
                witness_type=witness_type,
                resolution=data.get("resolution", full_response[:500]),
                confidence=min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
                verdict_on_claim=normalized_verdict,
            )

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="witness_complete",
                        agent=f"witness_{witness_type}",
                        content=f"Witness ({witness_type}): {report.verdict_on_claim.upper()}",
                        data=report.model_dump(mode="json"),
                    )
                )

            logger.info(
                "Witness (%s) completed: %s (confidence=%.2f)",
                witness_type,
                report.verdict_on_claim,
                report.confidence,
            )
            return report

        except Exception as e:
            logger.error("Witness agent (%s) failed: %s", witness_type, str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="error",
                        agent=f"witness_{witness_type}",
                        content=f"Witness error: {str(e)}",
                    )
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
            logger.warning("Failed to parse witness JSON")
            return {"resolution": cleaned[:500], "confidence": 0.5, "verdict_on_claim": "inconclusive"}
