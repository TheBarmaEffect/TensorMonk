"""Defense Agent — argues AGAINST the decision with maximum rigor."""

import json
import logging
from typing import Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import Argument, Claim, StreamEvent

logger = logging.getLogger(__name__)

DEFENSE_SYSTEM_PROMPT = """You are the Defense counsel in a high-stakes decision courtroom. Your ONLY job is to build the strongest possible case AGAINST this decision proceeding. Find every reason this will fail, every market risk, every execution danger, every competitive threat.

Produce exactly 4 claims each with evidence. Be precise, rigorous, and devastating.

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
    """Argues AGAINST the decision using the research package."""

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
        """Build the defense's case.

        Args:
            decision_question: The decision being evaluated.
            research_package: Neutral research from the Research agent.
            stream_callback: Async callback to emit StreamEvents.

        Returns:
            A structured Argument from the defense.
        """
        prompt = (
            f"Decision: {decision_question}\n\n"
            f"Research Package:\n{json.dumps(research_package, indent=2)}\n\n"
            "Build your case AGAINST this decision. Be devastating, specific, and unflinching."
        )

        messages = [
            SystemMessage(content=DEFENSE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            thinking_phases = [
                "Analyzing research for potential weaknesses in this decision...",
                "Identifying market risks and competitive threats...",
                "Constructing counter-argument with evidence...",
                "Building claim 1 — critical risk assessment...",
                "Building claim 2 — market reality check...",
                "Building claim 3 — alternative approach analysis...",
                "Building claim 4 — worst-case scenario evaluation...",
                "Finalizing defense case...",
            ]

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(
                        StreamEvent(
                            event_type="defense_thinking",
                            agent="defense",
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
            logger.warning("Failed to parse defense JSON, creating fallback")
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
            agent="defense",
            opening=data.get("opening", ""),
            claims=claims,
            confidence=data.get("confidence", 0.5),
        )
