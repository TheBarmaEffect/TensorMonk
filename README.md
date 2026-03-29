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
- **Human-in-the-Loop**: `interrupt_before=['verdict_with_review']` activates via `INTERRUPT_BEFORE_VERDICT=true` env var — the confidence gate routes low-confidence verdicts to a review node where human reviewers can intervene before the final ruling.
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
| DOCX generation | python-docx |
| Security | XSS detection, sanitization, security headers |
| Rate limiting | Token bucket middleware (in-memory) |
| Resilience | Circuit breaker + exponential backoff |
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
- Multi-factor confidence gate: 4-factor routing (domain-adjusted threshold, witness agreement ratio, confidence variance, overrule detection) with 3 verdict paths (normal, low-confidence review, hallucination guard at `temperature=0.3`)
- Hallucination guard — agent outputs validated against Pydantic v2 schemas, malformed JSON triggers `temperature=0.3` retry
- Real-time WebSocket streaming with typed `StreamEvent` objects
- Export: Markdown, PDF (via fpdf2), DOCX (via python-docx), and structured JSON — all endpoints functional
- Follow-up questions: context-aware Q&A against session results via `POST /api/verdict/{id}/followup`
- Session history: persistent JSON-backed session store via `GET /api/verdict/sessions/history`, displayed in frontend `SessionHistory` component
- Verdict sharing: `GET /api/verdict/{id}/share` generates short URL token, `GET /shared/{token}` retrieves results
- Web search grounding: Research Agent queries Tavily (or DuckDuckGo fallback) for current facts before LLM analysis
- Inline analysis in session results: argument quality, stability, and dependency graph computed and embedded in every completed session result — no separate endpoint required
- 409 tests across 22 test files: schemas, graph, API, exports, resilience, cache, middleware, domain config, errors, metrics, security, prompts, integration, graph viz, session FSM, validators, event bus, calibration, LLM helpers (pytest)
- Input validation on all API request models (question length, context length, format enum)
- Rate limiting middleware: token bucket per IP with configurable RPM/burst
- Request timing middleware: X-Request-ID + X-Response-Time headers on all responses
- Retry with exponential backoff + jitter for transient LLM failures
- Circuit breaker (CLOSED/OPEN/HALF_OPEN) wired into LLM retry path via `call_llm_with_resilience()` for external service fault tolerance
- TTL cache for domain detection to reduce redundant LLM calls
- Deep health check: Groq API, Redis, session store, uptime reporting
- Graceful startup/shutdown lifecycle handlers with structured logging
- Session-aware structured logging via contextvars for async correlation IDs
- Structured error hierarchy: VerdictError → AgentError/SessionError/ExportError with JSON serialization
- Pipeline performance metrics: per-agent durations with p50/p95/p99 percentiles, error rates, and pipeline-wide aggregates exposed via `/metrics` endpoint
- Pipeline progress tracking: `/status` endpoint returns completion percentage, current stage, stages remaining, and estimated time to completion
- Security middleware: XSS pattern detection, HTML entity sanitization, body size limits, security headers
- Shared LLM utilities: `utils/llm_helpers.py` — all 6 agents use `parse_llm_json()`, `create_llm()`, `emit_thinking_phases()`, and `retry_with_low_temperature()` (eliminated ~160 lines of duplicated boilerplate)
- Centralized prompt templates: ALL 6 agent system prompts defined in `agents/prompts.py` — zero inline prompt definitions, single source of truth for constitutional directives
- Session analytics: aggregate ruling distribution, domain breakdown, format usage via `/sessions/analytics`
- Pipeline graph visualization: structured topology generation with dynamic witness nodes and routing paths
- Async event bus: topic-based pub/sub with fire-and-forget delivery for pipeline observability
- Confidence calibration: Bayesian ECE tracking per agent per domain with overconfidence detection
- Witness-calibrated confidence: `_calibrate_from_witnesses()` uses witness verdicts as ground truth for per-agent ECE tracking in the pipeline
- Adaptive temperature: `_adaptive_temperature()` adjusts prosecutor/defense LLM temperature based on research quality scores
- Pipeline-wide observability: all 7 graph nodes emit start/complete/error events via event bus with rich payloads (confidence, claim counts, ruling outcomes)
- Research quality scoring: 5-dimension assessment (breadth, depth, grounding, balance, completeness) with weighted overall score
- Witness-weighted evidence scoring: Judge computes quantitative pro/defense scores adjusted by witness verdicts (sustained/overruled)
- Synthesis coverage assessment: measures objection coverage %, action time-boundedness, and strength delta
- Argument dependency graph: DAG of claim dependencies with BFS cascading impact, coherence scoring, critical path detection
- Verdict stability analysis: Monte Carlo perturbation testing (50 runs, ±10% witness confidence) with evidence margin and flip rate
- Argument quality scoring: 5-dimension heuristic assessment (specificity, diversity, calibration, coherence, actionability) with A-D grading
- Session lifecycle FSM: 5-state machine (created→running→complete/error/expired) with validated transitions wired into API routes
- Domain-aware input validators: question quality scoring, research package completeness, format-domain compatibility — wired into API and pipeline
- Quality-aware synthesis: argument quality scores feed into the synthesis prompt, weighting the stronger side's arguments
- py.typed PEP 561 marker for static type checking support

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
- Analytics panel: Recharts BarChart (claim confidence), RadarChart (argument comparison), StatCards, witness verdicts — wired to live agent data
- Comparison mode: side-by-side prosecution vs defense view with strength bars, aligned claims, confidence indicators, and witness verdict summary
- Pipeline visualization: interactive agent pipeline flow diagram with real-time status indicators, parallel branch display, and dynamic witness node rendering
- Domain-specific PDF reports: 9 domain color themes (business gold, legal indigo, medical red, financial emerald, etc.) with accent-colored titles, section headers, and dividers
- WebSocket reconnection with exponential backoff (5 attempts, jitter, clean disconnect)
- Robust export download helper with error handling, response validation, and user feedback

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
| Recharts analytics panel | ✅ Functional — `AnalyticsPanel.jsx` wired to live `agentStates`, `verdict`, `synthesis` | Moved to Tier 1 |
| Verdict history persistence | ✅ Functional — JSON file persistence in `data/sessions/` | Moved to Tier 1 |
| Voice input | ✅ Functional — `MicButton.jsx` + `useVoiceInput.js` | Moved to Tier 1; works in Chrome/Edge |
| Verdict sharing URL | ✅ Functional — `GET /{id}/share` + `GET /shared/{token}` | Moved to Tier 1 |
| DOCX export | ✅ Functional — `GET /api/verdict/{id}/export/docx` | Moved to Tier 1 |

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
| `GET` | `/api/verdict/{id}/export/docx` | Export as formatted DOCX |
| `POST` | `/api/verdict/{id}/followup` | Context-aware follow-up Q&A |
| `GET` | `/api/verdict/{id}/share` | Generate shareable verdict URL token |
| `GET` | `/api/verdict/shared/{token}` | Retrieve verdict by share token |
| `GET` | `/api/verdict/{id}/analysis` | Argument quality, stability, and dependency graph analysis |
| `GET` | `/api/verdict/{id}/graph` | Pipeline graph visualization for session |
| `GET` | `/api/verdict/graph/topology` | Static pipeline topology diagram |
| `GET` | `/api/verdict/sessions/analytics` | Aggregate session analytics |
| `GET` | `/health` | Deep health check with dependency readiness |
| `GET` | `/metrics` | Pipeline performance metrics |

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
| `INTERRUPT_BEFORE_VERDICT` | No | — | Set to `true` to enable human-in-the-loop review before verdict |
| `TAVILY_API_KEY` | No | — | Tavily API key for high-quality web search grounding (falls back to DuckDuckGo) |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

---

*Verdict — every decision deserves a challenger.*
