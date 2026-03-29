# Changelog

All notable changes to the Verdict project.

## [1.0.0] — 2026-03-29

### Added
- **Core Pipeline**: 6 AI agents (Research, Prosecutor, Defense, Judge, Witness, Synthesis) orchestrated via LangGraph StateGraph
- **Adversarial Isolation**: Prosecutor and Defense run in parallel with zero shared memory
- **Authorship Blindness**: `strip_authorship()` removes 11 metadata fields from research output
- **Dynamic Witness Spawning**: Judge determines contested claims; conditional edges route to FactWitness, DataWitness, PrecedentWitness
- **Confidence-Based Routing**: 3 verdict paths (normal, low-confidence review, hallucination guard at temperature=0.3)
- **Domain Detection**: Auto-classifies business, financial, legal, medical, technology, hiring domains
- **Domain-Aware Overlays**: Constitutional directives, evidence hierarchies, and synthesis anchors loaded from `domains.yaml`
- **Web Search Grounding**: Research Agent queries Tavily (DuckDuckGo fallback) for current facts
- **Real-Time Streaming**: WebSocket with typed StreamEvent objects for live agent updates
- **Export Pipeline**: Markdown, PDF (domain-themed), DOCX (styled), JSON export endpoints
- **Domain PDF Themes**: 9 unique color themes with accent-colored titles, headers, and dividers
- **Comparison Mode**: Side-by-side prosecution vs defense view with strength bars and claim alignment
- **Analytics Panel**: Recharts BarChart, RadarChart, StatCards wired to live agent data
- **Voice Input**: Web Speech API with animated waveform indicator (Chrome/Edge)
- **Session Persistence**: JSON file store with in-memory cache for crash recovery
- **Verdict Sharing**: SHA256-based token generation for shareable verdict URLs
- **Follow-Up Q&A**: Context-aware follow-up questions against session results
- **Session History**: Persistent session listing with metadata display

### Infrastructure
- **Rate Limiting**: Token bucket middleware (per-IP, configurable RPM/burst)
- **Request Timing**: X-Request-ID and X-Response-Time headers on all responses
- **Circuit Breaker**: Fail-fast pattern with CLOSED/OPEN/HALF_OPEN states for LLM calls
- **Retry with Backoff**: Exponential backoff with jitter for transient failures
- **TTL Cache**: Domain detection caching to reduce redundant LLM calls
- **Deep Health Check**: Dependency readiness (Groq API, Redis, session store, uptime)
- **Input Validation**: Pydantic field validators on all API request models
- **Graceful Lifecycle**: Startup/shutdown handlers with structured logging

### Testing
- 89 unit tests across 8 test files (schemas, graph topology, API contracts, exports, resilience, cache, middleware, domain config)
- Shared test fixtures in conftest.py

### Deployment
- Frontend on Vercel with API rewrites to backend
- Backend on Hugging Face Spaces (Docker, Python 3.12)
- Docker Compose with Redis for local development
- Vercel WebSocket direct connection via VITE_WS_URL

### Frontend
- Sequential ACT-based courtroom UI (5 Acts with Framer Motion transitions)
- Speech-bubble debate layout (Prosecutor LEFT, Defense RIGHT)
- Warm judicial design system (Cormorant Garamond, liquid glass cards)
- Output format selector (Executive, Technical, Legal, Investor)
- Robust export download helper with error handling
