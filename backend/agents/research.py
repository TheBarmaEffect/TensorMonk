"""Research Agent — produces a neutral, anonymous research package on the decision topic.

Constitutional role: Strictly neutral. Authorship is hidden from adversarial agents.
The research package is the ONLY shared context between Prosecutor and Defense.

Grounding: When available, the agent performs lightweight web retrieval via
DuckDuckGo Instant Answers and (optionally) Tavily Search API to ground
claims in current factual data rather than relying solely on LLM training data.
"""

import asyncio
import json
import logging
import os
from typing import Callable, Optional

import httpx
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from models.schemas import StreamEvent
from utils.resilience import retry_with_backoff

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight web retrieval for factual grounding
# ---------------------------------------------------------------------------

async def _web_search_grounding(query: str, max_results: int = 3) -> list[str]:
    """Retrieve web search snippets to ground LLM research in current facts.

    Strategy:
    1. Try Tavily Search API if TAVILY_API_KEY is set (best quality).
    2. Fall back to DuckDuckGo Instant Answers API (no key required).
    3. Return empty list on failure — research proceeds with LLM-only.
    """
    snippets = []

    # Try Tavily first (higher quality, structured results)
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", [])[:max_results]:
                        snippet = r.get("content", "")[:300]
                        source = r.get("url", "")
                        if snippet:
                            snippets.append(f"{snippet} (source: {source})")
                    if snippets:
                        logger.info("Tavily grounding: %d snippets for '%s'", len(snippets), query[:50])
                        return snippets
        except Exception as e:
            logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)

    # Fallback: DuckDuckGo Instant Answers (no API key needed)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
            if resp.status_code == 200:
                data = resp.json()
                # Abstract text (Wikipedia-sourced summary)
                if data.get("AbstractText"):
                    snippets.append(data["AbstractText"][:400])
                # Related topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        snippets.append(topic["Text"][:200])
                if snippets:
                    logger.info("DuckDuckGo grounding: %d snippets for '%s'", len(snippets), query[:50])
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)

    return snippets

RESEARCH_SYSTEM_PROMPT = """You are a neutral research analyst producing anonymous briefing material for an adversarial review process.

CONSTITUTIONAL DIRECTIVE: Remain strictly neutral. Do not advocate for or against any outcome.
Your authorship is intentionally withheld from the agents who will argue this decision.
Present only verified facts, relevant data, and documented precedents.

Produce a comprehensive factual research package. Include: market context, relevant data points,
known precedents, key stakeholders, and risk landscape. Be thorough and impartial.

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
    """Produces a neutral, anonymous research package shared by both Prosecutor and Defense."""

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
        output_format: str = "executive",
        domain: str = "business",
        stream_callback: Optional[Callable] = None,
    ) -> dict:
        """Execute research and return a structured research package.

        Args:
            decision_question: The decision to research.
            context: Optional additional context.
            output_format: Output style (executive/technical/legal/investor).
            domain: Decision domain for context-aware research depth.
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

        format_instruction = {
            "executive": "Focus on strategic implications and high-level business impact.",
            "technical": "Include technical depth, implementation complexity, and architecture considerations.",
            "legal": "Emphasize regulatory context, legal precedents, and compliance requirements.",
            "investor": "Highlight market size, growth metrics, competitive landscape, and financial projections.",
        }.get(output_format, "")

        prompt = f"Decision under analysis: {decision_question}"
        if context:
            prompt += f"\n\nAdditional context: {context}"
        if format_instruction:
            prompt += f"\n\nFormat guidance: {format_instruction}"
        prompt += f"\nDomain: {domain}"

        messages = [
            SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            # Phase 1: Web retrieval for factual grounding
            if stream_callback:
                await stream_callback(StreamEvent(
                    event_type="research_start", agent="research",
                    content="Retrieving current web data for factual grounding...\n",
                ))

            web_snippets = await _web_search_grounding(decision_question)

            if web_snippets and stream_callback:
                await stream_callback(StreamEvent(
                    event_type="research_start", agent="research",
                    content=f"Found {len(web_snippets)} grounding sources. Analyzing...\n",
                ))

            # Inject web grounding into the prompt so LLM has current facts
            if web_snippets:
                grounding_text = "\n".join(f"- {s}" for s in web_snippets)
                messages.append(HumanMessage(
                    content=f"Web-retrieved grounding data (use these current facts to supplement your analysis):\n{grounding_text}"
                ))

            # Phase 2: LLM analysis with grounding context
            thinking_phases = [
                "Scanning market landscape and competitive environment...",
                "Analyzing data points and historical precedents...",
                "Identifying stakeholders and risk factors...",
                "Compiling grounded research synthesis...",
            ]

            for phase in thinking_phases:
                if stream_callback:
                    await stream_callback(StreamEvent(
                        event_type="research_start", agent="research",
                        content=phase + "\n",
                    ))
                    await asyncio.sleep(0.3)

            response = await retry_with_backoff(
                self.llm.ainvoke, messages,
                max_retries=2, base_delay=1.0, operation_name="Research LLM",
            )
            research_package = self._parse_response(response.content)

            # Score research quality before emitting completion
            quality_scores = self.score_research_quality(research_package)
            research_package["_quality_scores"] = quality_scores

            if stream_callback:
                await stream_callback(
                    StreamEvent(
                        event_type="research_complete",
                        agent="research",
                        content=f"Research analysis complete. Quality: {quality_scores['overall']:.0%}",
                        data={**research_package, "quality": quality_scores},
                    )
                )

            logger.info("Research agent completed (quality=%.3f)", quality_scores["overall"])
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

    def score_research_quality(self, package: dict) -> dict:
        """Score the quality and completeness of the research package.

        Evaluates the research across 5 dimensions:
        - Breadth: How many distinct areas were covered
        - Depth: Average length/detail of data points
        - Grounding: Whether web-sourced evidence is present
        - Balance: Presence of both opportunities and risks
        - Completeness: All 6 required fields populated

        This score is included in the research_complete StreamEvent
        so the frontend can display research quality indicators.

        Args:
            package: The parsed research package dict.

        Returns:
            Dict with dimension scores and overall quality score.
        """
        scores = {}

        # Breadth: How many of the 6 fields have content?
        required_fields = ["market_context", "key_data_points", "precedents",
                          "stakeholders", "risk_landscape", "summary"]
        populated = sum(1 for f in required_fields if package.get(f))
        scores["breadth"] = round(populated / len(required_fields), 2)

        # Depth: Average richness of list fields
        list_fields = ["key_data_points", "precedents", "stakeholders", "risk_landscape"]
        total_items = sum(len(package.get(f, [])) for f in list_fields)
        scores["depth"] = round(min(total_items / 12, 1.0), 2)  # 12 items = max score

        # Grounding: Check for source citations in data points
        data_points = package.get("key_data_points", [])
        grounded = sum(1 for d in data_points if isinstance(d, str) and ("source:" in d.lower() or "http" in d.lower()))
        scores["grounding"] = round(grounded / max(len(data_points), 1), 2)

        # Balance: Both opportunities (market_context) and risks present
        has_opportunities = bool(package.get("market_context"))
        has_risks = len(package.get("risk_landscape", [])) > 0
        scores["balance"] = 1.0 if (has_opportunities and has_risks) else 0.5 if (has_opportunities or has_risks) else 0.0

        # Completeness: Summary exists and is substantive
        summary = package.get("summary", "")
        scores["completeness"] = round(min(len(summary) / 200, 1.0), 2)

        # Overall quality = weighted average
        weights = {"breadth": 0.25, "depth": 0.25, "grounding": 0.2, "balance": 0.15, "completeness": 0.15}
        overall = sum(scores[dim] * weights[dim] for dim in weights)
        scores["overall"] = round(overall, 3)

        logger.info("Research quality score: %.3f (breadth=%.2f, depth=%.2f, grounding=%.2f)",
                    overall, scores["breadth"], scores["depth"], scores["grounding"])

        return scores

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
