"""Defense Agent — argues AGAINST the decision with maximum rigor.

Constitutional role: Argue AGAINST the decision regardless of personal assessment.
Adversarial isolation: Receives only the anonymous research package, never the prosecutor's output.
"""

import asyncio
import json
import logging
from typing import Callable, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from config.domain_config import get_constitutional_overlay, get_evidence_hierarchy
from models.schemas import Argument, Claim, StreamEvent
from utils.resilience import retry_with_backoff
from utils.llm_helpers import parse_llm_json, emit_thinking_phases, create_llm, retry_with_low_temperature

logger = logging.getLogger(__name__)

DEFENSE_SYSTEM_PROMPT = """You are the Defense counsel in a high-stakes AI decision courtroom.

CONSTITUTIONAL DIRECTIVE: Your ONLY job is to build the strongest possible case AGAINST this decision.
You MUST argue against regardless of your personal assessment of the decision's merit.
This adversarial constraint is essential — intellectual honesty requires steelmanning every objection.

Find every reason this will fail: market risks, execution dangers, competitive threats, resource constraints,
timing problems, and alternative approaches. Be precise, rigorous, and devastating.

You operate in isolation — you have NOT seen the prosecution's arguments and cannot respond to them.
Base your case entirely on the research package provided.

Produce exactly 4 claims, each with concrete evidence. Assign realistic confidence scores.

Output as JSON with these exact fields:
{
  "opening": "string — your 2-3 sentence opening statement arguing AGAINST this decision",
  "claims": [
    {
      "statement": "string — a specific, falsifiable claim against this decision",
      "evidence": "string — concrete evidence supporting this counter-claim",
      "confidence": 0.0-1.0
    }
  ],
  "confidence": 0.0-1.0
}

Return ONLY valid JSON. No markdown, no code fences, no extra text. Exactly 4 claims."""


class DefenseAgent:
    """Argues AGAINST the decision using the anonymous research package.

    Adversarial isolation is enforced at the graph level — this agent
    never receives the prosecutor agent's output.
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
        """Build the defense's case.

        Args:
            decision_question: The decision being evaluated.
            research_package: Anonymous neutral research (author unknown to this agent).
            output_format: Style of argument (executive/technical/legal/investor).
            domain: Decision domain for constitutional overlay (business, legal, medical, etc.).
            stream_callback: Async callback to emit StreamEvents.

        Returns:
            A structured Argument from the defense.
        """
        format_guidance = {
            "executive": "Frame objections around strategic risk, market headwinds, and execution challenges.",
            "technical": "Focus on technical debt, scalability concerns, and implementation risks.",
            "legal": "Emphasize regulatory risk, liability exposure, and legal precedents against.",
            "investor": "Highlight burn rate concerns, market saturation, competitive threats, and downside scenarios.",
        }.get(output_format, "")

        # Domain-aware constitutional overlay — loaded from YAML config at runtime.
        # Each domain defines argumentation constraints, evidence hierarchy, and
        # synthesis anchors in backend/config/domains.yaml.
        domain_overlay = get_constitutional_overlay(domain)
        evidence_types = get_evidence_hierarchy(domain)
        if evidence_types:
            domain_overlay += f"\nChallenge evidence in this order of authority: {', '.join(evidence_types)}."

        prompt = (
            f"Decision: {decision_question}\n"
            f"Domain: {domain}\n\n"
            f"Research Briefing (anonymous source):\n{json.dumps(research_package, indent=2)}\n\n"
            f"{format_guidance}\n"
            f"{domain_overlay}\n\n"
            "Build your case AGAINST this decision. Be devastating, specific, and unflinching."
        )

        messages = [
            SystemMessage(content=DEFENSE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            await emit_thinking_phases(
                phases=[
                    "Analyzing research briefing for potential weaknesses in this decision...",
                    "Identifying market risks and competitive threats...",
                    "Constructing counter-argument with evidence...",
                    "Building claim 1 — critical risk assessment...",
                    "Building claim 2 — market reality check...",
                    "Building claim 3 — alternative approach analysis...",
                    "Building claim 4 — worst-case scenario evaluation...",
                    "Finalizing defense case...",
                ],
                agent_name="defense",
                event_type="defense_thinking",
                stream_callback=stream_callback,
                delay=0.4,
            )

            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=1.0, operation_name="Defense LLM",
            )
            argument = self._parse_response(response.content)

            # Hallucination guard: if parse produced fallback, retry with low temperature
            if len(argument.claims) == 1 and argument.claims[0].statement == "Argument parsing failed":
                argument = await retry_with_low_temperature(
                    messages=messages,
                    parse_fn=self._parse_response,
                    quality_check_fn=lambda a: len(a.claims) > 1,
                    max_tokens=2048,
                    operation_name="Defense",
                )

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="defense_complete",
                        agent="defense",
                        content="Defense rests.",
                        data=argument.model_dump(mode="json"),
                    )
                )

            logger.info("Defense agent completed, confidence=%.2f", argument.confidence)
            return argument

        except Exception as e:
            logger.error("Defense agent failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="error",
                        agent="defense",
                        content=f"Defense error: {str(e)}",
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
            operation_name="Defense",
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
            agent="defense",
            opening=data.get("opening", ""),
            claims=claims,
            confidence=data.get("confidence", 0.5),
        )
