"""Research Agent — produces a neutral research package on the decision topic."""

import json
import logging
from typing import Callable, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import StreamEvent

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are a neutral research analyst. Produce a comprehensive, factual research package on the following decision. Include: market context, relevant data points, known precedents, key stakeholders, and risk landscape. Be thorough and neutral.

Output as structured JSON with these exact fields:
{
  "market_context": "string — overview of the market landscape relevant to this decision",
  "key_data_points": ["string — specific facts, statistics, or data relevant to the decision"],
  "precedents": ["string — historical examples of similar decisions and their outcomes"],
  "stakeholders": ["string — key parties affected by or involved in this decision"],
  "risk_landscape": ["string — major risks and uncertainties"],
  "summary": "string — neutral 2-3 sentence summary of the research findings"
}

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


class ResearchAgent:
    """Produces a neutral research package shared by both Prosecutor and Defense."""

    def __init__(self) -> None:
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=2048,
            api_key=settings.groq_api_key,
        )

    async def run(
        self,
        decision_question: str,
        context: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
    ) -> dict:
        """Execute research and return a structured research package.

        Args:
            decision_question: The decision to research.
            context: Optional additional context.
            stream_callback: Async callback to emit StreamEvents.

        Returns:
            Parsed research package dict.
        """
        if stream_callback:
            await stream_callback(
                StreamEvent(
                    event_type="research_start",
                    agent="research",
                    content="Initiating neutral research analysis...",
                )
            )

        prompt = f"Decision under analysis: {decision_question}"
        if context:
            prompt += f"\n\nAdditional context: {context}"

        messages = [
            SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            # Send thinking messages (not raw tokens)
            thinking_phases = [
                "Scanning market landscape and competitive environment...",
                "Gathering relevant data points and statistics...",
                "Analyzing historical precedents and case studies...",
                "Identifying key stakeholders and risk factors...",
                "Compiling research synthesis...",
            ]

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(
                        StreamEvent(
                            event_type="research_start",
                            agent="research",
                            content=phase + "\n",
                        )
                    )
                    import asyncio
                    await asyncio.sleep(0.3)

            # Run LLM (don't stream raw tokens to UI)
            response = await self.llm.ainvoke(messages)
            full_response = response.content

            research_package = self._parse_response(full_response)

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="research_complete",
                        agent="research",
                        content="Research analysis complete.",
                        data=research_package,
                    )
                )

            logger.info("Research agent completed successfully")
            return research_package

        except Exception as e:
            logger.error("Research agent failed: %s", str(e))
            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="error",
                        agent="research",
                        content=f"Research agent error: {str(e)}",
                    )
                )
            raise

    def _parse_response(self, response: str) -> dict:
        """Parse the LLM JSON response into a research package dict."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse research JSON, wrapping raw text")
            return {
                "market_context": cleaned,
                "key_data_points": [],
                "precedents": [],
                "stakeholders": [],
                "risk_landscape": [],
                "summary": cleaned[:500],
            }
