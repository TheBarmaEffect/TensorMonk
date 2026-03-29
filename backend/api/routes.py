"""FastAPI routes for the Verdict API — REST + WebSocket endpoints."""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, field_validator

from services.export_service import generate_markdown_report, generate_json_report, generate_pdf_report, generate_docx_report
from utils.cache import TTLCache

from config import settings
from models.schemas import Decision, StreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verdict")

# ---------------------------------------------------------------------------
# Session persistence — JSON file store with in-memory cache
# ---------------------------------------------------------------------------

SESSION_DIR = Path(os.getenv("SESSION_DIR", "data/sessions"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# In-memory session cache backed by JSON file persistence
sessions: dict[str, dict] = {}

# TTL cache for domain detection — avoids redundant LLM calls for similar questions
_domain_cache = TTLCache(ttl_seconds=300, max_entries=200)


def _persist_session(session_id: str, session: dict) -> None:
    """Write session to disk as JSON for persistence across restarts."""
    try:
        path = SESSION_DIR / f"{session_id}.json"
        with open(path, "w") as f:
            json.dump(session, f, default=str)
    except Exception as e:
        logger.warning("Failed to persist session %s: %s", session_id, e)


def _load_session(session_id: str) -> Optional[dict]:
    """Load a session from disk if not in memory cache."""
    path = SESSION_DIR / f"{session_id}.json"
    if path.exists():
        try:
            with open(path) as f:
                session = json.load(f)
            sessions[session_id] = session  # Warm the cache
            return session
        except Exception as e:
            logger.warning("Failed to load session %s: %s", session_id, e)
    return None


def _get_session(session_id: str) -> Optional[dict]:
    """Get session from cache or disk."""
    if session_id in sessions:
        return sessions[session_id]
    return _load_session(session_id)


def _load_all_sessions() -> None:
    """Load all persisted sessions into memory on startup."""
    for path in SESSION_DIR.glob("*.json"):
        sid = path.stem
        if sid not in sessions:
            _load_session(sid)


# Load persisted sessions on module import
_load_all_sessions()

# Valid output formats and their descriptions
OUTPUT_FORMATS = {
    "executive": "High-level summary for executives and decision-makers",
    "technical": "In-depth technical analysis with implementation details",
    "legal": "Formal legal-style analysis with precedents and risk assessment",
    "investor": "Financial and market-focused analysis for investors",
}


class StartRequest(BaseModel):
    """Request body for starting a new verdict session.

    Validates question length (10-2000 chars) and optional context (max 5000 chars)
    to prevent abuse and ensure meaningful LLM analysis.
    """

    question: str
    context: Optional[str] = None
    output_format: Literal["executive", "technical", "legal", "investor"] = "executive"

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Question must be at least 10 characters for meaningful analysis")
        if len(v) > 2000:
            raise ValueError("Question must not exceed 2000 characters")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 5000:
            raise ValueError("Context must not exceed 5000 characters")
        return v


class StartResponse(BaseModel):
    """Response for a new session."""

    session_id: str
    decision: dict
    status: str
    output_format: str
    domain: str


class DetectDomainRequest(BaseModel):
    """Request body for domain detection.

    Validates question length for consistent domain classification.
    """

    question: str
    context: Optional[str] = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Question must be at least 5 characters for domain detection")
        if len(v) > 2000:
            raise ValueError("Question must not exceed 2000 characters")
        return v


class DetectDomainResponse(BaseModel):
    """Response for domain detection."""

    domain: str
    confidence: float
    suggested_format: str
    reasoning: str


@router.post("/detect-domain", response_model=DetectDomainResponse)
async def detect_domain(request: DetectDomainRequest):
    """Detect the decision domain and suggest the optimal output format.

    Uses the LLM to classify the decision into a domain category and
    recommends the most appropriate output format for that domain.
    """
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=512,
        api_key=settings.groq_api_key,
    )

    system_prompt = """You are a domain classifier for business decisions.
Classify the given decision question into one of these domains:
business, technology, legal, medical, financial, product, hiring, operations, marketing, strategic

Also suggest the best output format: executive, technical, legal, or investor

Respond with ONLY valid JSON:
{
  "domain": "string",
  "confidence": 0.0-1.0,
  "suggested_format": "executive|technical|legal|investor",
  "reasoning": "string — one sentence explaining the classification"
}"""

    cache_key = request.question + (request.context or "")

    # Check cache first to avoid redundant LLM calls
    cached = _domain_cache.get(cache_key)
    if cached:
        logger.debug("Domain detection cache hit for: %s", request.question[:50])
        return DetectDomainResponse(**cached)

    prompt = f"Decision: {request.question}"
    if request.context:
        prompt += f"\nContext: {request.context}"

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])

        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        result = {
            "domain": data.get("domain", "business"),
            "confidence": data.get("confidence", 0.8),
            "suggested_format": data.get("suggested_format", "executive"),
            "reasoning": data.get("reasoning", "General business decision"),
        }

        # Cache successful detection
        _domain_cache.set(cache_key, result)
        logger.debug("Domain detection cached: %s -> %s", request.question[:50], result["domain"])

        return DetectDomainResponse(**result)
    except Exception as e:
        logger.error("Domain detection failed: %s", e)
        return DetectDomainResponse(
            domain="business",
            confidence=0.5,
            suggested_format="executive",
            reasoning="Could not classify — defaulting to business/executive",
        )


@router.get("/formats")
async def get_output_formats():
    """Return available output formats and their descriptions."""
    return {"formats": [
        {"id": k, "description": v}
        for k, v in OUTPUT_FORMATS.items()
    ]}


@router.post("/start", response_model=StartResponse)
async def start_verdict(request: StartRequest):
    """Submit a decision for adversarial evaluation.

    Returns a session_id to connect via WebSocket for real-time streaming.
    Auto-detects domain from the question for context-aware analysis.
    """
    decision = Decision(question=request.question, context=request.context)

    # Quick domain classification (keyword heuristics, no LLM call)
    domain = _classify_domain_heuristic(request.question)

    session = {
        "id": decision.id,
        "decision": decision.model_dump(mode="json"),
        "output_format": request.output_format,
        "domain": domain,
        "status": "created",
        "events": [],
        "result": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    sessions[decision.id] = session
    _persist_session(decision.id, session)

    logger.info(
        "Session created: %s — %s [format=%s, domain=%s]",
        decision.id, request.question[:80], request.output_format, domain,
    )

    return StartResponse(
        session_id=decision.id,
        decision=decision.model_dump(mode="json"),
        status="created",
        output_format=request.output_format,
        domain=domain,
    )


def _classify_domain_heuristic(question: str) -> str:
    """Fast keyword-based domain classification (no LLM call needed at start)."""
    q = question.lower()
    if any(w in q for w in ("hire", "cto", "team", "employee", "recruit")):
        return "hiring"
    if any(w in q for w in ("raise", "series", "valuation", "invest", "vc", "fund")):
        return "financial"
    if any(w in q for w in ("acquire", "acquisition", "merge", "merger")):
        return "strategic"
    if any(w in q for w in ("legal", "lawsuit", "compliance", "regulation", "contract")):
        return "legal"
    if any(w in q for w in ("product", "feature", "launch", "mvp", "build")):
        return "product"
    if any(w in q for w in ("tech", "stack", "platform", "api", "cloud", "migrate")):
        return "technology"
    if any(w in q for w in ("market", "campaign", "brand", "customer", "growth")):
        return "marketing"
    return "business"


@router.get("/sessions/history")
async def get_history():
    """Get all verdict sessions for the history panel."""
    history = []
    for sid, session in sessions.items():
        history.append({
            "session_id": sid,
            "question": session["decision"].get("question", ""),
            "status": session["status"],
            "created_at": session.get("created_at"),
            "output_format": session.get("output_format", "executive"),
            "domain": session.get("domain", "business"),
            "ruling": session.get("result", {}).get("verdict", {}).get("ruling") if session.get("result") else None,
        })
    return {"sessions": sorted(history, key=lambda x: x.get("created_at", ""), reverse=True)}


@router.get("/{session_id}/status")
async def get_status(session_id: str):
    """Get the current status of a verdict session."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "status": session["status"],
        "event_count": len(session["events"]),
        "has_result": session["result"] is not None,
    }


@router.get("/{session_id}/result")
async def get_result(session_id: str):
    """Get the complete result of a verdict session."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "complete":
        raise HTTPException(status_code=202, detail="Session still in progress")

    return session["result"]


@router.websocket("/{session_id}/stream")
async def stream_verdict(websocket: WebSocket, session_id: str):
    """WebSocket endpoint that streams all agent events in real time.

    Flow:
    1. Accept connection
    2. Start the LangGraph execution in a background task
    3. Stream every StreamEvent as it fires
    4. Send final result
    5. Close connection
    """
    await websocket.accept()
    logger.info("WebSocket connected: %s", session_id)

    session = _get_session(session_id)
    if not session:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    session["status"] = "running"
    event_queue: asyncio.Queue = asyncio.Queue()

    async def stream_callback(event: StreamEvent):
        """Push events to the queue for WebSocket delivery."""
        event_dict = event.model_dump(mode="json")
        session["events"].append(event_dict)
        await event_queue.put(event_dict)

    async def run_pipeline():
        """Execute the multi-agent verdict pipeline."""
        try:
            from graph.verdict_graph import run_verdict_graph

            result = await run_verdict_graph(
                decision=session["decision"],
                stream_callback=stream_callback,
                output_format=session.get("output_format", "executive"),
                domain=session.get("domain", "business"),
                thread_id=session_id,
            )
            session["result"] = {
                "decision": session["decision"],
                "output_format": session.get("output_format", "executive"),
                "domain": session.get("domain", "business"),
                "research_package": result.get("research_package"),
                "prosecutor_argument": result.get("prosecutor_argument"),
                "defense_argument": result.get("defense_argument"),
                "witness_reports": result.get("witness_reports"),
                "verdict": result.get("verdict"),
                "synthesis": result.get("synthesis"),
                "errors": result.get("errors", []),
            }

            session["status"] = "complete"
            _persist_session(session_id, session)
        except Exception as e:
            logger.error("Pipeline failed: %s", str(e))
            session["status"] = "error"
            await event_queue.put(
                StreamEvent(
                    event_type="error",
                    content=f"Pipeline error: {str(e)}",
                ).model_dump(mode="json")
            )
        finally:
            await event_queue.put(None)  # Sentinel to signal completion

    # Start pipeline in background
    pipeline_task = asyncio.create_task(run_pipeline())

    try:
        while True:
            event = await event_queue.get()
            if event is None:
                await websocket.send_json({
                    "event_type": "pipeline_complete",
                    "content": "All agents have completed.",
                    "data": {"status": session["status"]},
                })
                break

            await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
        pipeline_task.cancel()
    except Exception as e:
        logger.error("WebSocket error: %s", str(e))
    finally:
        if not pipeline_task.done():
            pipeline_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------


@router.get("/{session_id}/export/markdown")
async def export_markdown(session_id: str):
    """Export the verdict session as a markdown report."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    report = generate_markdown_report(session["result"])
    return PlainTextResponse(content=report, media_type="text/markdown")


@router.get("/{session_id}/export/json")
async def export_json(session_id: str):
    """Export the verdict session as structured JSON."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    report = generate_json_report(session["result"])
    return PlainTextResponse(content=report, media_type="application/json")


@router.get("/{session_id}/export/pdf")
async def export_pdf(session_id: str):
    """Export the verdict session as a formatted PDF report."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    pdf_bytes = generate_pdf_report(session["result"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=verdict-{session_id[:8]}.pdf"},
    )


@router.get("/{session_id}/export/docx")
async def export_docx(session_id: str):
    """Export the verdict session as a formatted DOCX report."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    docx_bytes = generate_docx_report(session["result"])
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=verdict-{session_id[:8]}.docx"},
    )


# ---------------------------------------------------------------------------
# Follow-up Q&A endpoint
# ---------------------------------------------------------------------------


class FollowUpRequest(BaseModel):
    """Request body for follow-up questions against session results."""

    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Follow-up question must be at least 5 characters")
        if len(v) > 1000:
            raise ValueError("Follow-up question must not exceed 1000 characters")
        return v


@router.post("/{session_id}/followup")
async def followup_question(session_id: str, request: FollowUpRequest):
    """Ask a follow-up question about the verdict session."""
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage

    result = session["result"]
    output_format = session.get("output_format", "executive")
    domain = session.get("domain", "business")

    context_parts = []
    if result.get("decision"):
        context_parts.append(f"Decision: {result['decision'].get('question', '')}")
    if result.get("verdict"):
        v = result["verdict"]
        context_parts.append(f"Verdict: {v.get('ruling', 'N/A')} (confidence: {v.get('confidence', 0)})")
        context_parts.append(f"Reasoning: {v.get('reasoning', '')}")
    if result.get("synthesis"):
        s = result["synthesis"]
        context_parts.append(f"Synthesis: {s.get('improved_idea', '')}")

    context = "\n".join(context_parts)

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.6,
        max_tokens=1024,
        api_key=settings.groq_api_key,
    )

    messages = [
        SystemMessage(content=f"""You are a legal analyst following up on a courtroom AI analysis.
Domain: {domain} | Output format: {output_format}

Session context:
{context}

Answer the user's follow-up question based on this context. Be concise and insightful.
Tailor your response to the {output_format} format and {domain} domain."""),
        HumanMessage(content=request.question),
    ]

    try:
        response = await llm.ainvoke(messages)
        return {"answer": response.content, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up: {str(e)}")


# ---------------------------------------------------------------------------
# Verdict sharing endpoint
# ---------------------------------------------------------------------------


def _generate_share_token(session_id: str) -> str:
    """Generate a short, URL-safe share token from a session ID."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:12]


@router.get("/{session_id}/share")
async def create_share_link(session_id: str):
    """Generate a shareable link for a completed verdict session.

    Returns a short share token that can be used to retrieve the session
    results without needing the full session ID.
    """
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    token = _generate_share_token(session_id)

    # Store mapping from share token to session ID
    session["share_token"] = token
    _persist_session(session_id, session)

    return {
        "share_token": token,
        "share_url": f"/shared/{token}",
        "session_id": session_id,
    }


@router.get("/shared/{share_token}")
async def get_shared_verdict(share_token: str):
    """Retrieve a verdict session via its share token.

    This allows anyone with the share link to view the verdict results
    without needing the original session ID.
    """
    # Search for session with matching share token
    for sid, session in sessions.items():
        if session.get("share_token") == share_token:
            if not session.get("result"):
                raise HTTPException(status_code=202, detail="Session not complete")
            return {
                "session_id": sid,
                "question": session["decision"].get("question", ""),
                "domain": session.get("domain", "business"),
                "output_format": session.get("output_format", "executive"),
                "result": session["result"],
            }

    # Also check persisted sessions on disk
    for path in SESSION_DIR.glob("*.json"):
        try:
            with open(path) as f:
                session = json.load(f)
            if session.get("share_token") == share_token:
                return {
                    "session_id": path.stem,
                    "question": session.get("decision", {}).get("question", ""),
                    "domain": session.get("domain", "business"),
                    "output_format": session.get("output_format", "executive"),
                    "result": session.get("result"),
                }
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Shared verdict not found")
