"""Prosecutor Agent — argues FOR the decision with maximum rigor."""

import json
import logging
from typing import Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import Argument, Claim, StreamEvent

logger = logging.getLogger(__name__)

PROSECUTOR_SYSTEM_PROMPT = """You are the Prosecutor in a high-stakes decision courtroom. Your ONLY job is to build the strongest possible case FOR this decision proceeding. Argue with maximum rigor. Find every reason this idea will work, every market condition that supports it, every precedent for success.

Produce exactly 4 claims, each with evidence. Be forceful, specific, and persuasive.

Output as JSON with these exact fields:
{
  "opening": "string — your 2-3 sentence opening statement arguing FOR this decision",
  "claims": [
    {
      "statement": "string — a specific, falsifiable claim supporting this decision",
      "evidence": "string — concrete evidence supporting this claim",
      "confidence": 0.0-1.0
    }
  ],
  "confidence": 0.0-1.0
}

Return ONLY valid JSON. No markdown, no code fences, no extra text. Exactly 4 claims."""


class ProsecutorAgent:
    """Argues FOR the decision using the research package."""

    def __init__(self) -> None:
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
            api_key=settings.groq_api_key,
        )

    async def run(
        self,
        decision_question: str,
        research_package: dict,
        stream_callback: Optional[Callable] = None,
    ) -> Argument:
        """Build the prosecution's case.

        Args:
            decision_question: The decision being evaluated.
            research_package: Neutral research from the Research agent.
            stream_callback: Async callback to emit StreamEvents.

        Returns:
            A structured Argument from the prosecution.
        """
        prompt = (
            f"Decision: {decision_question}\n\n"
            f"Research Package:\n{json.dumps(research_package, indent=2)}\n\n"
            "Build your case FOR this decision. Be aggressive, specific, and compelling."
        )

        messages = [
            SystemMessage(content=PROSECUTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            thinking_phases = [
                "Reviewing research package for supporting evidence...",
                "Constructing opening argument in favor of this decision...",
                "Building claim 1 with supporting evidence...",
                "Building claim 2 with market validation...",
                "Building claim 3 with precedent support...",
                "Building claim 4 with risk mitigation analysis...",
                "Finalizing prosecution case with confidence assessment...",
            ]

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(
                        StreamEvent(
                            event_type="prosecutor_thinking",
                            agent="prosecutor",
                            content=phase + "\n",
                        )
                    )
                    import asyncio
                    await asyncio.sleep(0.4)

            response = await self.llm.ainvoke(messages)
            full_response = response.content
            argument = self._parse_response(full_response)

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
        """Parse LLM output into a structured Argument."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse prosecutor JSON, creating fallback")
            data = {
                "opening": cleaned[:300],
                "claims": [
                    {"statement": "Argument parsing failed", "evidence": cleaned[:200], "confidence": 0.5}
                ],
                "confidence": 0.5,
            }

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
