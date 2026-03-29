"""FastAPI routes for the Verdict API — REST + WebSocket endpoints."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings
from models.schemas import Decision, StreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verdict")

# In-memory session store (Redis upgrade path exists but not required for hackathon)
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
        """Execute the verdict graph or demo data."""
        try:
            if settings.demo_mode:
                await _run_demo_pipeline(stream_callback, session)
            else:
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


async def _run_demo_pipeline(stream_callback, session: dict):
    """Replay pre-cached demo data with realistic streaming delays."""
    from demo_data import (
        DEMO_STREAM_EVENTS,
        DEMO_RESEARCH_PACKAGE,
        DEMO_PROSECUTOR_ARGUMENT,
        DEMO_DEFENSE_ARGUMENT,
        DEMO_WITNESS_REPORTS,
        DEMO_VERDICT,
        DEMO_SYNTHESIS,
    )

    for event_data in DEMO_STREAM_EVENTS:
        event = StreamEvent(**event_data)
        await stream_callback(event)

        # Simulate realistic streaming delays
        content = event_data.get("content", "")
        if "thinking" in event_data["event_type"] or "start" in event_data["event_type"]:
            # Stream thinking tokens at ~30ms per token
            delay = min(len(content) * 0.03, 3.0)
        elif "complete" in event_data["event_type"]:
            delay = 0.5
        elif "spawned" in event_data["event_type"]:
            delay = 0.3
        else:
            delay = 0.2

        await asyncio.sleep(delay)

    session["result"] = {
        "decision": session["decision"],
        "research_package": DEMO_RESEARCH_PACKAGE,
        "prosecutor_argument": DEMO_PROSECUTOR_ARGUMENT,
        "defense_argument": DEMO_DEFENSE_ARGUMENT,
        "witness_reports": DEMO_WITNESS_REPORTS,
        "verdict": DEMO_VERDICT,
        "synthesis": DEMO_SYNTHESIS,
        "errors": [],
    }
