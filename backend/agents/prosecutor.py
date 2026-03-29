"""Prosecutor Agent — argues FOR the decision with maximum rigor.

Constitutional role: Argue FOR the decision regardless of personal assessment.
Adversarial isolation: Receives only the anonymous research package, never the defense's output.
"""

import asyncio
import json
import logging
from typing import Callable, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from agents.prompts import get_format_instruction, PROSECUTOR_SYSTEM
from config.domain_config import get_constitutional_overlay, get_evidence_hierarchy
from models.schemas import Argument, Claim, StreamEvent
from utils.resilience import retry_with_backoff
from utils.llm_helpers import parse_llm_json, emit_thinking_phases, create_llm, retry_with_low_temperature

logger = logging.getLogger(__name__)

class ProsecutorAgent:
    """Argues FOR the decision using the anonymous research package.

    Adversarial isolation is enforced at the graph level — this agent
    never receives the defense agent's output.
    """

    def __init__(self) -> None:
        self.llm = create_llm(temperature=0.7, max_tokens=2048)

    async def run(
        self,
        decision_question: str,
        research_package: dict,
        output_format: str = "executive",
        domain: str = "business",
        stream_callback: Optional[Callable] = None,
    ) -> Argument:
        """Build the prosecution's case.

        Args:
            decision_question: The decision being evaluated.
            research_package: Anonymous neutral research (author unknown to this agent).
            output_format: Style of argument (executive/technical/legal/investor).
            domain: Decision domain for constitutional overlay (business, legal, medical, etc.).
            stream_callback: Async callback to emit StreamEvents.

        Returns:
            A structured Argument from the prosecution.
        """
        format_guidance = get_format_instruction(output_format)

        # Domain-aware constitutional overlay — loaded from YAML config at runtime.
        # Each domain defines argumentation constraints, evidence hierarchy, and
        # synthesis anchors in backend/config/domains.yaml.
        domain_overlay = get_constitutional_overlay(domain)
        evidence_types = get_evidence_hierarchy(domain)
        if evidence_types:
            domain_overlay += f"\nPrioritize evidence in this order: {', '.join(evidence_types)}."

        system_prompt = PROSECUTOR_SYSTEM.format(domain_overlay=domain_overlay)

        prompt = (
            f"Decision: {decision_question}\n"
            f"Domain: {domain}\n\n"
            f"Research Briefing (anonymous source):\n{json.dumps(research_package, indent=2)}\n\n"
            f"{format_guidance}\n\n"
            "Build your case FOR this decision. Be aggressive, specific, and compelling."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]

        try:
            await emit_thinking_phases(
                phases=[
                    "Reviewing research briefing for supporting evidence...",
                    "Constructing opening argument in favor of this decision...",
                    "Building claim 1 with supporting evidence...",
                    "Building claim 2 with market validation...",
                    "Building claim 3 with precedent support...",
                    "Building claim 4 with risk mitigation analysis...",
                    "Finalizing prosecution case with confidence assessment...",
                ],
                agent_name="prosecutor",
                event_type="prosecutor_thinking",
                stream_callback=stream_callback,
                delay=0.4,
            )

            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=1.0, operation_name="Prosecutor LLM",
            )
            argument = self._parse_response(response.content)

            # Hallucination guard: if parse produced fallback, retry with low temperature
            if len(argument.claims) == 1 and argument.claims[0].statement == "Argument parsing failed":
                argument = await retry_with_low_temperature(
                    messages=messages,
                    parse_fn=self._parse_response,
                    quality_check_fn=lambda a: len(a.claims) > 1,
                    max_tokens=2048,
                    operation_name="Prosecutor",
                )

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="prosecutor_complete",
                        agent="prosecutor",
                        content="Prosecution rests.",
                        data=argument.model_dump(mode="json"),
                    )
                )

            logger.info("Prosecutor agent completed, confidence=%.2f", argument.confidence)
            return argument

        except Exception as e:
            logger.error("Prosecutor agent failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="error",
                        agent="prosecutor",
                        content=f"Prosecutor error: {str(e)}",
                    )
                )
            raise

    def _parse_response(self, response: str) -> Argument:
        """Parse LLM output into a structured Argument — delegates to shared utility."""
        data = parse_llm_json(
            response,
            fallback={
                "opening": response.strip()[:300],
                "claims": [
                    {"statement": "Argument parsing failed", "evidence": response.strip()[:200], "confidence": 0.5}
                ],
                "confidence": 0.5,
            },
            operation_name="Prosecutor",
        )

        claims = [
            Claim(
                statement=c.get("statement", ""),
                evidence=c.get("evidence", ""),
                confidence=c.get("confidence", 0.5),
            )
            for c in data.get("claims", [])
        ]

        return Argument(
            agent="prosecutor",
            opening=data.get("opening", ""),
            claims=claims,
            confidence=data.get("confidence", 0.5),
        )
