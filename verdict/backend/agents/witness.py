"""Witness Agent factory — spawns specialist witnesses to verify contested claims.

Constitutional role: Neutral verification. Witnesses evaluate claims objectively
without knowledge of which agent (Prosecutor or Defense) made the claim.

Three specialist types:
- FactWitness: Verifies factual accuracy of assertions
- DataWitness: Evaluates statistical claims and data quality
- PrecedentWitness: Validates historical precedent citations

Uses low temperature (0.3) for deterministic, grounded verification.
"""

import json
import logging
from typing import Callable, Literal, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from agents.prompts import WITNESS_SYSTEM
from models.schemas import WitnessReport, StreamEvent
from utils.resilience import retry_with_backoff
from utils.llm_helpers import parse_llm_json, create_llm

logger = logging.getLogger(__name__)

class WitnessAgent:
    """Factory that spawns specialist witnesses to verify claims."""

    def __init__(self) -> None:
        self.llm = create_llm(temperature=0.3, max_tokens=1024)

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

        system_prompt = WITNESS_SYSTEM.format(witness_type=witness_type)

        type_instruction = {
            "fact": "Focus on factual accuracy — check for verifiable assertions, logical consistency, and source reliability.",
            "data": "Focus on data quality — check statistical validity, sample sizes, methodology, and potential biases.",
            "precedent": "Focus on precedent relevance — check if cited precedents are applicable, recent, and correctly interpreted.",
        }.get(witness_type, "Verify this claim thoroughly.")

        prompt = (
            f"CLAIM TO VERIFY:\n"
            f"Statement: {claim_statement}\n"
            f"Evidence provided: {claim_evidence}\n\n"
            f"{type_instruction}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]

        try:
            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=0.5, operation_name=f"Witness ({witness_type})",
            )
            full_response = response.content

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
        """Parse JSON from LLM response — delegates to shared utility."""
        return parse_llm_json(
            response,
            fallback={"resolution": response.strip()[:500], "confidence": 0.5, "verdict_on_claim": "inconclusive"},
            operation_name="Witness",
        )
