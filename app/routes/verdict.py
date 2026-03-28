cat << 'EOF' > app/routes/verdict.py
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class StartVerdictRequest(BaseModel):
    question: str
    context: Optional[str] = None

@router.post("/start")
async def start_verdict(payload: StartVerdictRequest):
    return {"decision_id": "demo-id", "status": "started"}

@router.get("/{decision_id}/status")
async def status(decision_id: str):
    return {"decision_id": decision_id, "status": "running"}

@router.get("/{decision_id}/result")
async def result(decision_id: str):
    return {"decision_id": decision_id, "ruling": "conditional"}

@router.websocket("/{decision_id}/stream")
async def stream(ws: WebSocket, decision_id: str):
    await ws.accept()
    await ws.send_json({"event": "connected", "decision_id": decision_id})
    await ws.close()
EOF