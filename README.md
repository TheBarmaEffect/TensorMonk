# Verdict

```
 __     __            _ _      _
 \ \   / /__ _ __ ___| (_) ___| |_
  \ \ / / _ \ '__/ _ \ | |/ __| __|
   \ V /  __/ | |  __/ | | (__| |_
    \_/ \___|_|  \___|_|_|\___|\__|
```

**Multi-agent adversarial AI courtroom for decision evaluation.**

**Live Demo:** [https://frontend-phi-ten-83.vercel.app](https://frontend-phi-ten-83.vercel.app)

Submit any decision or idea and Verdict runs it through a full AI courtroom proceeding: specialized agents research, argue for and against, cross-examine witnesses, deliver a ruling, and synthesize a battle-tested version of the original idea — all streamed to the browser in real time over WebSocket.

---

## Architecture

```
User Input (question + context + output_format)
    |
    v
[Domain Detection] ── classifies decision domain (business, legal, etc.)
    |
    v
[Research Agent] ── produces anonymous research package
    |                (authorship hidden from downstream agents)
    +──────────────+──────────────+
    |              |              |
    v              |              v
[Prosecutor]    ISOLATED    [Defense]
 argues FOR   (cannot see   argues AGAINST
               each other)
    |              |              |
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
            [interrupt_before]  ← human-in-the-loop checkpoint
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

### Adversarial Design Constraints

- **Authorship Blindness**: The research package is stripped of source metadata before reaching prosecutor/defense. Neither agent knows who authored the research.
- **Constitutional Directives**: Prosecutor MUST argue FOR, Defense MUST argue AGAINST, regardless of personal assessment. Enforced via system prompts.
- **Adversarial Isolation**: Prosecutor and defense run in parallel and never see each other's output. The judge is the first node to receive both.
- **Hallucination Guard**: Agent outputs are validated against Pydantic schemas. Malformed JSON triggers a retry with `temperature=0.3` for deterministic recovery.
- **Checkpointing**: LangGraph `AsyncRedisSaver` for production fault tolerance (falls back to `MemorySaver` when `REDIS_URL` is unset). State persisted at every node for resume/replay.
- **Human-in-the-Loop**: `interrupt_before=['verdict']` pauses the graph when average witness confidence < 0.6, allowing human review before the final ruling.
- **Dynamic Witness Spawning**: Conditional edges route through `_should_spawn_witnesses` — the Judge's cross-examination determines which claims are contested and what witness type to spawn for each. If no claims are contested, witnesses are skipped entirely.
- **Domain-Aware Constitutional Overlays**: Loaded from `backend/config/domains.yaml` at runtime — each domain defines argumentation constraints, evidence hierarchy, and few-shot synthesis anchors.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend framework | FastAPI |
| Agent orchestration | LangGraph (StateGraph + AsyncRedisSaver / MemorySaver) |
| LLM inference | Groq (Llama 3.3 70B Versatile) |
| Data models | Pydantic v2 with field validators |
| Real-time streaming | WebSocket (native FastAPI) |
| Frontend framework | React 18 |
| Build tool | Vite |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| State management | Zustand |
| Charts | Recharts (scope-trimmed, see below) |
| PDF generation | fpdf2 |
| Containerization | Docker + docker-compose |

## What's Built and Working

**Core Pipeline (fully functional)**
- 6 AI agents: Research, Prosecutor, Defense, Judge, up to 3 Witnesses, Synthesis
- Constitutional isolation — Prosecutor and Defense share zero memory
- Authorship blindness — Judge receives arguments with agent identity stripped via `strip_authorship()`
- Dynamic Witness spawning — Judge spawns FactWitness, DataWitness, PrecedentWitness based on contested claims via LangGraph conditional edges
- Domain detection — auto-classifies startup / legal / medical / financial / technical / hiring
- Domain-aware constitutional overlays loaded from `backend/config/domains.yaml` at runtime
- Few-shot synthesis anchors per domain (e.g., "Week 1-2: Implement WorkOS for enterprise SSO")
- Parallel Prosecutor + Defense execution via `asyncio.gather`
- LangGraph StateGraph with `MemorySaver` checkpointing (`AsyncRedisSaver` when `REDIS_URL` set)
- Confidence-based routing: 3 verdict paths (normal, low-confidence review, hallucination guard at `temperature=0.3`)
- Hallucination guard — agent outputs validated against Pydantic v2 schemas, malformed JSON triggers `temperature=0.3` retry
- Real-time WebSocket streaming with typed `StreamEvent` objects
- Export: Markdown, PDF (via fpdf2), and structured JSON — all endpoints functional
- Follow-up questions: context-aware Q&A against session results via `POST /api/verdict/{id}/followup`
- Session history: in-memory session list via `GET /api/verdict/sessions/history`, displayed in frontend `SessionHistory` component

**Frontend (fully functional)**
- Sequential ACT-based courtroom UI (5 Acts: Investigation, Debate, Cross-Examination, Ruling, Synthesis)
- Speech-bubble debate layout (Prosecutor LEFT, Defense RIGHT)
- Live agent status indicators with active/complete states
- Verdict card with typewriter-animated ruling
- Synthesis card with battle-tested improved version
- Warm judicial design system (Cormorant Garamond headings, liquid glass cards)
- Framer Motion ACT transitions and staggered reveal animations
- Output format selector (Executive, Technical, Legal, Investor)
- Domain badge auto-detected as user types
- Voice input via Web Speech API — mic button with animated waveform indicator, transcript streams into text input

**Deployment**
- Frontend live on Vercel: [https://frontend-phi-ten-83.vercel.app](https://frontend-phi-ten-83.vercel.app)
- Backend API live on Hugging Face Spaces: [https://shani987-verdict-api.hf.space](https://shani987-verdict-api.hf.space)
- Docker + docker-compose with Redis service for local development
- Vercel rewrites proxy `/api/*` to HF Space backend; WebSocket connects directly via `VITE_WS_URL`

## Scope-Trimmed (time constraints — pre-committed Tier 2 cut rule)

The following were planned but explicitly cut per the master plan's pre-committed
Tier 2 cut rule: *"analytics charts are cut before the courtroom UI is degraded."*

| Feature | Status | Reason for cut |
|---------|--------|----------------|
| Recharts analytics panel | Component scaffolded, not wired to live data | Courtroom UI polish prioritized over charts |
| Verdict history persistence | In-memory only, resets on restart | Redis persistence deferred to post-hackathon |
| Voice input | ✅ Functional — `MicButton.jsx` + `useVoiceInput.js` | Moved to Tier 1; works in Chrome/Edge |
| Verdict sharing URL | Not implemented | Time constraint |
| DOCX export | Not implemented | PDF + Markdown + JSON sufficient for demo |

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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/verdict/start` | Submit a decision with output_format, returns session_id + detected domain |
| `POST` | `/api/verdict/detect-domain` | LLM-powered domain detection with format suggestion |
| `GET` | `/api/verdict/formats` | List available output formats with descriptions |
| `GET` | `/api/verdict/sessions/history` | List all sessions with metadata |
| `GET` | `/api/verdict/{id}/status` | Get session status |
| `GET` | `/api/verdict/{id}/result` | Get complete result JSON |
| `WS` | `/api/verdict/{id}/stream` | Real-time agent event stream |
| `GET` | `/api/verdict/{id}/export/markdown` | Export as Markdown report |
| `GET` | `/api/verdict/{id}/export/pdf` | Export as formatted PDF |
| `GET` | `/api/verdict/{id}/export/json` | Export as structured JSON |
| `POST` | `/api/verdict/{id}/followup` | Context-aware follow-up Q&A |
| `GET` | `/health` | Health check |

### POST /api/verdict/start

```json
{
  "question": "Should I pivot my SaaS from B2C to B2B?",
  "context": "Optional additional context...",
  "output_format": "executive"
}
```

Response includes auto-detected `domain` and chosen `output_format`.

### POST /api/verdict/detect-domain

```json
{
  "question": "Should we raise a Series A at $15M valuation?"
}
```

Returns: `{ "domain": "financial", "confidence": 0.9, "suggested_format": "investor", "reasoning": "..." }`

### WebSocket Events

Connect to `ws://localhost:8000/api/verdict/{session_id}/stream` to receive real-time events:

| Event Type | Agent | Description |
|-----------|-------|-------------|
| `research_start` | research | Research agent begins analysis |
| `research_complete` | research | Research package ready |
| `prosecutor_thinking` | prosecutor | Prosecution building case |
| `prosecutor_complete` | prosecutor | Prosecution rests |
| `defense_thinking` | defense | Defense building counter-case |
| `defense_complete` | defense | Defense rests |
| `judge_start` | judge | Cross-examination begins |
| `witness_spawned` | witness_* | Specialist witness activated |
| `witness_complete` | witness_* | Witness report filed |
| `verdict_complete` | judge | Final ruling delivered |
| `synthesis_start` | synthesis | Battle-tested synthesis begins |
| `synthesis_complete` | synthesis | Improved idea ready |
| `pipeline_complete` | — | All agents finished |
| `error` | varies | Error during processing |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM inference |
| `REDIS_URL` | No | — | Redis connection string for production checkpointing (`redis://host:6379/0`) |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

---

*Verdict — every decision deserves a challenger.*
