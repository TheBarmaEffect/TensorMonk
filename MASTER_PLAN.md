# Verdict — Master Plan

## Vision

Build a **multi-agent adversarial AI courtroom** that takes any decision or idea and stress-tests it through a full legal proceeding — research, prosecution, defense, cross-examination, witness testimony, verdict, and synthesis — producing a battle-tested version of the original idea.

## Architecture Principles

### 1. Adversarial Isolation (ADR-001)
- Prosecutor and Defense run in **parallel** and **never see each other's output**
- Research authorship is **stripped** before reaching adversarial agents (authorship blindness)
- Constitutional directives force Prosecutor to argue FOR and Defense to argue AGAINST

### 2. Confidence-Based Routing (ADR-002)
- Three verdict paths: normal, low-confidence review, hallucination guard (temperature=0.3)
- Multi-factor confidence gate: domain-adjusted thresholds, witness agreement ratio, confidence variance, overrule detection
- `interrupt_before` activated via `INTERRUPT_BEFORE_VERDICT` env var
- Confidence > 0.9 with majority overruled triggers low-temperature retry

### 3. Domain-Aware Overlays (ADR-003)
- Domain classification via LLM with TTL caching
- Per-domain constitutional overlays, evidence hierarchies, synthesis anchors
- 6+ domains: business, financial, legal, medical, technology, hiring

### 4. Event-Driven Observability (ADR-004)
- Async event bus with topic-based pub/sub and priority ordering
- All graph nodes emit start/complete/error events with rich payloads
- Fire-and-forget delivery for zero-overhead pipeline instrumentation

### 5. Analytical Pipeline Feedback (ADR-005)
- Argument dependency graph: DAG construction with cascading impact analysis
- Verdict stability: Monte Carlo perturbation testing (50 runs, ±10%)
- Argument quality scoring: 5-dimension heuristic assessment with A-D grading
- Confidence calibration: binned ECE + Platt scaling + isotonic regression (PAVA) per agent per domain

### 6. Intelligence-Driven Routing (ADR-006)
- Computed intelligence (quality scores, graph analysis, stability) flows through VerdictState — not just emitted as telemetry
- Cross-examination receives structural analysis: critical paths, foundation claims, coherence differentials inform claim selection
- Witness prioritization: contested claims reordered by cascading impact from dependency graph — high-impact claims verified first
- Stability-aware synthesis: fragile verdicts trigger cautious recommendations with contingency plans; narrow margins generate monitoring triggers
- Domain-aware confidence thresholds: medical (0.7), legal (0.65), technology (0.55) — high-stakes domains require higher witness agreement

## Delivery Tiers

### Tier 1 — Core Courtroom (COMPLETE)
| Feature | Status | Evidence |
|---------|--------|----------|
| 6 AI agents (Research, Prosecutor, Defense, Judge, Witness, Synthesis) | ✅ | `backend/agents/*.py` |
| LangGraph StateGraph with conditional edges | ✅ | `backend/graph/verdict_graph.py` |
| Constitutional isolation + authorship blindness | ✅ | `strip_authorship()` removes 11 fields |
| Dynamic witness spawning | ✅ | `_should_spawn_witnesses()` conditional edge |
| Confidence-based 3-path verdict routing | ✅ | `_confidence_gate()` in verdict_graph.py |
| Pydantic v2 schema validation + hallucination guard | ✅ | `backend/models/schemas.py` |
| Real-time WebSocket streaming | ✅ | `StreamEvent` objects via FastAPI WS |
| 5-Act courtroom UI | ✅ | `frontend/src/components/CourtRoom.jsx` |
| Speech-bubble debate layout | ✅ | Prosecutor LEFT, Defense RIGHT |
| Framer Motion ACT transitions | ✅ | `ActDivider` with scaleX entrance |
| Domain detection + format selector | ✅ | LLM-powered with 4 output formats |
| Export pipeline (MD, PDF, DOCX, JSON) | ✅ | `backend/services/export_service.py` |
| Follow-up Q&A | ✅ | `POST /api/verdict/{id}/followup` |

### Tier 2 — Production Polish (COMPLETE)
| Feature | Status | Evidence |
|---------|--------|----------|
| Recharts analytics panel | ✅ | `AnalyticsPanel.jsx` wired to live data |
| Session persistence (JSON file store) | ✅ | `data/sessions/` with in-memory cache |
| Voice input (Web Speech API) | ✅ | `MicButton.jsx` + `useVoiceInput.js` |
| Verdict sharing URL | ✅ | SHA256 token via `GET /{id}/share` |
| DOCX export | ✅ | `python-docx` with styled headings |
| Comparison mode (side-by-side) | ✅ | `ComparisonMode.jsx` |
| Domain-specific PDF themes (9 domains) | ✅ | `DOMAIN_PDF_THEMES` with accent colors |
| WebSocket reconnection with backoff | ✅ | 5 attempts, exponential + jitter |
| Web search grounding (Tavily/DDG) | ✅ | `_web_search_grounding()` in research.py |

### Tier 3 — Infrastructure & Resilience (COMPLETE)
| Feature | Status | Evidence |
|---------|--------|----------|
| Rate limiting middleware | ✅ | Token bucket per-IP in `middleware/rate_limiter.py` |
| Request timing + correlation IDs | ✅ | X-Request-ID, X-Response-Time headers |
| Retry with exponential backoff | ✅ | Wired into all 6 agent LLM calls |
| Circuit breaker | ✅ | 3-state (CLOSED/OPEN/HALF_OPEN) — wired into LLM calls via `call_llm_with_resilience()` |
| TTL cache for domain detection | ✅ | Wired into detect-domain endpoint |
| Pipeline performance metrics | ✅ | `/metrics` endpoint with per-agent stats, p50/p95/p99 percentiles, error rates |
| Structured error hierarchy | ✅ | VerdictError → AgentError/SessionError/ExportError |
| Input validation | ✅ | Pydantic field_validator on all API models |
| Deep health checks | ✅ | Groq, Redis, session store, uptime |
| Structured logging | ✅ | contextvars session correlation IDs |
| Security middleware (XSS, headers) | ✅ | `middleware/security.py` with 7 XSS patterns |
| Session state machine (FSM) | ✅ | `services/session_manager.py` — wired into routes for created→running→complete/error transitions |
| Pipeline graph visualization | ✅ | `services/graph_visualizer.py` + `PipelineGraph.jsx` |
| Centralized prompt templates | ✅ | `agents/prompts.py` — ALL 6 agent system prompts imported from single source, zero inline prompt definitions |
| Session analytics aggregation | ✅ | `GET /sessions/analytics` endpoint |
| Keyboard shortcuts | ✅ | `useKeyboardShortcuts.js` with 6 shortcuts |
| ARIA accessibility | ✅ | roles, labels, described-by on LandingInput, MicButton, PipelineGraph |
| Async event bus (Observer pattern) | ✅ | `utils/event_bus.py` with topic pub/sub |
| Confidence calibration (ECE + Platt + PAVA) | ✅ | `utils/confidence_calibration.py` — binned ECE, Platt scaling, isotonic regression |
| Domain-aware input validators | ✅ | `utils/validators.py` — wired into API routes + research node |
| Pipeline metrics + event bus wired into all graph nodes | ✅ | Every node emits start/complete/error events with rich payloads |
| Adaptive temperature from research quality | ✅ | `_adaptive_temperature()` adjusts prosecutor/defense LLM temp |
| Witness-calibrated confidence tracking | ✅ | `_calibrate_from_witnesses()` uses verdicts as ground truth |
| Witness-weighted evidence scoring | ✅ | `judge.compute_evidence_score()` adjusts verdict confidence |
| Research quality scoring (5 dimensions) | ✅ | `research.score_research_quality()` — breadth/depth/grounding/balance |
| Synthesis coverage assessment | ✅ | `synthesis.assess_synthesis_coverage()` — objection/action/strength |
| Argument strength analysis | ✅ | `judge.analyze_argument_strength()` pre-cross-examination |
| Claim overlap detection | ✅ | `judge.detect_claim_overlaps()` keyword overlap + conflict scoring |
| Constitutional compliance validation | ✅ | `_validate_constitutional_compliance()` directive enforcement |
| Argument dependency graph (DAG) | ✅ | `utils/argument_graph.py` — BFS cascading impact, coherence scoring |
| Verdict stability perturbation analysis | ✅ | `utils/verdict_stability.py` — 50-run Monte Carlo, evidence margin |
| Argument quality scoring (A-D grades) | ✅ | `utils/argument_quality.py` — 5-dimension heuristic assessment |
| Inline analysis in session results | ✅ | `run_pipeline()` computes quality/stability/graph and embeds in result |
| Intelligence-driven routing | ✅ | Computed analysis flows through VerdictState to influence cross-exam, witness priority, and synthesis |
| Structural cross-examination | ✅ | Judge receives argument graph critical paths + foundation claims for smarter claim selection |
| Impact-weighted witness prioritization | ✅ | Contested claims reordered by DAG cascading impact before witness spawning |
| Stability-aware synthesis | ✅ | Fragile verdicts trigger cautious recommendations with contingency plans |
| 426 tests (unit + integration) | ✅ | 22 test files (pytest) |

### Pre-Committed Cut Rule
> "Analytics charts are cut before the courtroom UI is degraded."

All Tier 2 features were moved to functional status. The courtroom UI was never degraded.

## Deployment Architecture

```
[User Browser]
    |
    v
[Vercel CDN] ── serves React SPA
    |
    ├── /api/* ── rewrites to ──> [HF Spaces Backend]
    |                              (FastAPI + Docker)
    |
    └── wss:// ── direct ──> [HF Spaces Backend]
                              (WebSocket streaming)
```

- **Frontend**: Vercel (https://frontend-phi-ten-83.vercel.app)
- **Backend**: Hugging Face Spaces (https://shani987-verdict-api.hf.space)
- **Local**: Docker Compose with Redis service

## Test Strategy

| Test File | Count | Scope |
|-----------|-------|-------|
| test_schemas.py | 13 | Pydantic model validation, confidence bounds |
| test_graph.py | 37 | Graph topology, strip_authorship, conditional edges, multi-factor confidence gate, domain thresholds, quality-gap spawning, adaptive temp, calibration, constitutional compliance |
| test_api.py | 24 | API contracts, input validation, domain detection, quality gate, progress tracking |
| test_exports.py | 11 | PDF/DOCX/MD/JSON generation, domain themes |
| test_resilience.py | 10 | Retry backoff, circuit breaker states |
| test_cache.py | 9 | TTL expiration, key normalization, eviction |
| test_middleware.py | 7 | Token bucket algorithm, exempt paths |
| test_domain_config.py | 5 | YAML loading, constitutional overlays |
| test_errors.py | 10 | Error hierarchy, JSON serialization |
| test_metrics.py | 17 | Agent tracking, pipeline metrics, percentile computation, error rates |
| test_security.py | 22 | XSS detection, input sanitization, security headers |
| test_prompts.py | 22 | Constitutional directive auditing, prompt structure |
| test_integration.py | 44 | Session lifecycle, domain detection, analytics, claim overlap, research quality, synthesis coverage, analysis pipeline, intelligence pipeline wiring |
| test_graph_viz.py | 17 | Pipeline topology, witness nodes, routing paths |
| test_session_manager.py | 23 | FSM state transitions, lifecycle tracking, serialization |
| test_validators.py | 22 | Question quality, research completeness, format-domain fit |
| test_event_bus.py | 20 | Pub/sub delivery, topic matching, priority ordering |
| test_calibration.py | 27 | ECE computation, overconfidence detection, domain tracking, Platt scaling, isotonic regression (PAVA) |
| test_argument_graph.py | 23 | DAG construction, degree metrics, coherence, cascading impact |
| test_verdict_stability.py | 17 | Evidence margin, perturbation Monte Carlo, flip rate bounds |
| test_argument_quality.py | 24 | Specificity, diversity, calibration, coherence, grading |
| test_llm_helpers.py | 23 | JSON parsing, code fence stripping, thinking phases, LLM factory, low-temp retry |
| **Total** | **426** | |

## Technical Decisions

1. **Groq over OpenAI**: Llama 3.3 70B via Groq for speed (sub-second inference) and free tier
2. **LangGraph over raw chains**: StateGraph provides checkpointing, conditional edges, parallel execution
3. **Zustand over Redux**: Lightweight state management matches React 18 patterns
4. **fpdf2 over WeasyPrint**: No system dependency on wkhtmltopdf; pure Python PDF generation
5. **In-memory rate limiter over Redis**: No additional infrastructure dependency
6. **JSON file persistence over SQLite**: Simpler deployment, human-readable session data
7. **Shared LLM helpers over per-agent duplication**: `utils/llm_helpers.py` consolidates JSON parsing, LLM factory, thinking phases, and retry logic used by all 6 agents — single place to change LLM behavior
8. **Heuristic quality scoring over LLM self-evaluation**: Argument quality, research quality, and synthesis coverage use fast deterministic heuristics instead of additional LLM calls — no latency overhead, predictable results

---

*Verdict — every decision deserves a challenger.*
