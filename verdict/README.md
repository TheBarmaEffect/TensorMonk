# Verdict

```
 __     __            _ _      _
 \ \   / /__ _ __ ___| (_) ___| |_
  \ \ / / _ \ '__/ _ \ | |/ __| __|
   \ V /  __/ | |  __/ | | (__| |_
    \_/ \___|_|  \___|_|_|\___|\__|
```

**Multi-agent adversarial AI courtroom for decision evaluation.**

Verdict transforms any startup or product decision into a live AI courtroom proceeding. Specialized agents debate, challenge each other, verify claims, and produce a final verdict — then synthesize a stronger, battle-tested version of the original idea.

Every decision deserves a challenger.

---

## Architecture

```
User Input
    |
    v
[Research Agent] ── neutral research package
    |
    +──────────+──────────+
    |                     |
    v                     v
[Prosecutor]        [Defense]
  argues FOR         argues AGAINST
    |                     |
    +──────────+──────────+
               |
               v
         [Judge Agent]
         cross-examines
               |
    +----------+----------+
    |          |          |
    v          v          v
[Witness]  [Witness]  [Witness]
  fact       data     precedent
    |          |          |
    +----------+----------+
               |
               v
         [Judge Agent]
         delivers verdict
               |
               v
       [Synthesis Agent]
       battle-tested output
               |
               v
        WebSocket Stream → Frontend
```

## Agent Roles

| Agent | Role | Directive |
|-------|------|-----------|
| Research | Neutral analyst | Produces factual research package shared by both sides |
| Prosecutor | Argues FOR | Constitutional directive to build strongest case for the decision |
| Defense | Argues AGAINST | Constitutional directive to build strongest case against the decision |
| Judge | Arbitrator | Cross-examines, spawns witnesses, delivers final ruling |
| Witness (x3) | Verifiers | Fact, Data, and Precedent specialists verify contested claims |
| Synthesis | Architect | Reads full proceeding, produces improved battle-tested version |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API key (free at console.groq.com)

### Run with Docker

```bash
# Clone the repository
git clone https://github.com/your-team/verdict.git
cd verdict

# Set your Groq API key
echo "GROQ_API_KEY=your-key-here" > .env

# Start everything
docker-compose up --build
```

Frontend: http://localhost:5173
Backend: http://localhost:8000
Health check: http://localhost:8000/health

### Run in Demo Mode (no API key needed)

```bash
echo "DEMO_MODE=true" >> .env
docker-compose up --build
```

### Development (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your GROQ_API_KEY
uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes* | — | Groq API key for LLM inference |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL |
| `DEMO_MODE` | No | `false` | Use pre-cached demo data |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

*Not required when `DEMO_MODE=true`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/verdict/start` | Submit a decision, returns `session_id` |
| `GET` | `/api/verdict/{id}/status` | Get session status |
| `GET` | `/api/verdict/{id}/result` | Get complete result JSON |
| `WS` | `/api/verdict/{id}/stream` | Real-time agent event stream |
| `GET` | `/health` | Health check |

### POST /api/verdict/start

```json
{
  "question": "Should I pivot my SaaS from B2C to B2B?",
  "context": "Optional additional context..."
}
```

Response:
```json
{
  "session_id": "uuid",
  "decision": { "id": "uuid", "question": "..." },
  "status": "created"
}
```

### WebSocket Events

Connect to `ws://localhost:8000/api/verdict/{session_id}/stream` to receive real-time events:

```json
{
  "event_type": "prosecutor_thinking",
  "agent": "prosecutor",
  "content": "Building the case FOR...",
  "data": null,
  "timestamp": "2026-03-28T12:00:00Z"
}
```

Event types: `research_start`, `research_complete`, `prosecutor_thinking`, `prosecutor_complete`, `defense_thinking`, `defense_complete`, `judge_start`, `witness_spawned`, `witness_complete`, `cross_examination_complete`, `verdict_start`, `verdict_complete`, `synthesis_start`, `synthesis_complete`, `error`

## Tech Stack

- **Backend**: FastAPI, LangGraph, Groq (Llama 3.3 70B), Pydantic v2, Redis
- **Frontend**: React 18, Vite, Tailwind CSS, Framer Motion, Zustand, WebSocket
- **Deployment**: Docker, Railway
- **LLM**: Groq inference (llama-3.3-70b-versatile)

## Team

**Tensor Monk** — New England Inter-Collegiate AI Hackathon 2026

---

*Verdict. Every decision deserves a challenger.*
