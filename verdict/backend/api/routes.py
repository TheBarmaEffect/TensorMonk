"""FastAPI routes for the Verdict API — REST + WebSocket endpoints."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from services.export_service import generate_markdown_report, generate_json_report

from config import settings
from models.schemas import Decision, StreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verdict")

# In-memory session store
sessions: dict[str, dict] = {}


class StartRequest(BaseModel):
    """Request body for starting a new verdict session."""

    question: str
    context: Optional[str] = None


class StartResponse(BaseModel):
    """Response for a new session."""

    session_id: str
    decision: dict
    status: str


@router.post("/start", response_model=StartResponse)
async def start_verdict(request: StartRequest):
    """Submit a decision for adversarial evaluation.

    Returns a session_id to connect via WebSocket for real-time streaming.
    """
    decision = Decision(question=request.question, context=request.context)

    session = {
        "id": decision.id,
        "decision": decision.model_dump(mode="json"),
        "status": "created",
        "events": [],
        "result": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    sessions[decision.id] = session

    logger.info("Session created: %s — %s", decision.id, request.question[:80])

    return StartResponse(
        session_id=decision.id,
        decision=decision.model_dump(mode="json"),
        status="created",
    )


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
            "ruling": session.get("result", {}).get("verdict", {}).get("ruling") if session.get("result") else None,
        })
    return {"sessions": sorted(history, key=lambda x: x.get("created_at", ""), reverse=True)}


@router.get("/{session_id}/status")
async def get_status(session_id: str):
    """Get the current status of a verdict session."""
    session = sessions.get(session_id)
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
    session = sessions.get(session_id)
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

    session = sessions.get(session_id)
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
            )
            session["result"] = {
                "decision": session["decision"],
                "research_package": result.get("research_package"),
                "prosecutor_argument": result.get("prosecutor_argument"),
                "defense_argument": result.get("defense_argument"),
                "witness_reports": result.get("witness_reports"),
                "verdict": result.get("verdict"),
                "synthesis": result.get("synthesis"),
                "errors": result.get("errors", []),
            }

            session["status"] = "complete"
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
                # Pipeline complete — send final message
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
# Export & follow-up endpoints
# ---------------------------------------------------------------------------


@router.get("/{session_id}/export/markdown")
async def export_markdown(session_id: str):
    """Export the verdict session as a markdown report."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    report = generate_markdown_report(session["result"])
    return PlainTextResponse(content=report, media_type="text/markdown")


@router.get("/{session_id}/export/json")
async def export_json(session_id: str):
    """Export the verdict session as JSON."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    report = generate_json_report(session["result"])
    return PlainTextResponse(content=report, media_type="application/json")


class FollowUpRequest(BaseModel):
    question: str


@router.post("/{session_id}/followup")
async def followup_question(session_id: str, request: FollowUpRequest):
    """Ask a follow-up question about the verdict session."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.get("result"):
        raise HTTPException(status_code=202, detail="Session not complete")

    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage

    result = session["result"]

    # Build context from session
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
        SystemMessage(content=f"""You are a legal analyst following up on a courtroom AI analysis. Here's the context of the session:

{context}

Answer the user's follow-up question based on this context. Be concise and insightful. Reference specific findings from the analysis when relevant."""),
        HumanMessage(content=request.question),
    ]

    try:
        response = await llm.ainvoke(messages)
        return {"answer": response.content, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up: {str(e)}")
