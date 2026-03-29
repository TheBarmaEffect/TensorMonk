# Verdict

```
 __     __            _ _      _
 \ \   / /__ _ __ ___| (_) ___| |_
  \ \ / / _ \ '__/ _ \ | |/ __| __|
   \ V /  __/ | |  __/ | | (__| |_
    \_/ \___|_|  \___|_|_|\___|\__|
```

**Multi-agent adversarial AI courtroom for decision evaluation.**

Submit any decision or idea and Verdict runs it through a full AI courtroom proceeding: specialized agents research, argue for and against, cross-examine witnesses, deliver a ruling, and synthesize a battle-tested version of the original idea -- all streamed to the browser in real time over WebSocket.

---

## Architecture

```
User Input (question + optional context)
    |
    v
[Research Agent] ── produces neutral research package
    |
    +──────────────+──────────────+
    |                             |
    v                             v
[Prosecutor Agent]         [Defense Agent]
  argues FOR                argues AGAINST
    |                             |
    +──────────────+──────────────+
                   |
                   v
            [Judge Agent]
            cross-examines
                   |
       +-----------+-----------+
       |           |           |
       v           v           v
   [Witness]   [Witness]   [Witness]
    fact         data       precedent
       |           |           |
       +-----------+-----------+
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
           WebSocket Stream --> React Frontend
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend framework | FastAPI |
| Agent orchestration | LangGraph |
| LLM inference | Groq (Llama 3.3 70B Versatile) |
| Data models | Pydantic v2 |
| Real-time streaming | WebSocket (native FastAPI) |
| Frontend framework | React 18 |
| Build tool | Vite |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| State management | Zustand |
| Charts | Recharts |
| Icons | Lucide React |
| Containerization | Docker |

## Features

- Six specialized AI agents (Research, Prosecutor, Defense, Judge, Witnesses, Synthesis)
- Real-time WebSocket streaming of agent reasoning as it happens
- Animated courtroom UI with agent graph visualization
- Analytics panel with scoring charts (Recharts)
- Verdict card with ruling, confidence score, and reasoning
- Synthesis card with battle-tested improved version of the idea
- Follow-up questions: ask the AI about the verdict after the trial completes
- Export results as Markdown or JSON
- Session history panel
- Demo mode with pre-cached data (no API key required)
- Voice input via browser microphone

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with your API key
echo "GROQ_API_KEY=your-key-here" > .env

# Run the server
uvicorn main:app --reload
```

Backend runs at http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

### Docker

```bash
# Set your API key in backend/.env
echo "GROQ_API_KEY=your-key-here" > backend/.env

# Start both services
docker-compose up --build
```

### Demo Mode (no API key needed)

```bash
echo "DEMO_MODE=true" > backend/.env
docker-compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/verdict/start` | Submit a decision, returns `session_id` |
| `GET` | `/api/verdict/sessions/history` | List all sessions |
| `GET` | `/api/verdict/{id}/status` | Get session status |
| `GET` | `/api/verdict/{id}/result` | Get complete result JSON |
| `WS` | `/api/verdict/{id}/stream` | Real-time agent event stream |
| `GET` | `/api/verdict/{id}/export/markdown` | Export result as Markdown |
| `GET` | `/api/verdict/{id}/export/json` | Export result as JSON |
| `POST` | `/api/verdict/{id}/followup` | Ask a follow-up question |
| `GET` | `/health` | Health check |

### POST /api/verdict/start

```json
{
  "question": "Should I pivot my SaaS from B2C to B2B?",
  "context": "Optional additional context..."
}
```

### WebSocket Events

Connect to `ws://localhost:8000/api/verdict/{session_id}/stream` to receive real-time events:

Event types: `research_start`, `research_complete`, `prosecutor_thinking`, `prosecutor_complete`, `defense_thinking`, `defense_complete`, `judge_start`, `witness_spawned`, `witness_complete`, `cross_examination_complete`, `verdict_start`, `verdict_complete`, `synthesis_start`, `synthesis_complete`, `pipeline_complete`, `error`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes* | -- | Groq API key for LLM inference |
| `DEMO_MODE` | No | `false` | Use pre-cached demo data |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `CORS_ORIGINS` | No | localhost origins | Allowed CORS origins |

*Not required when `DEMO_MODE=true`

## Screenshots

![Landing page](docs/screenshots/landing.png)
![Courtroom in progress](docs/screenshots/courtroom.png)
![Verdict card](docs/screenshots/verdict.png)
![Analytics panel](docs/screenshots/analytics.png)

---

*Verdict -- every decision deserves a challenger.*
