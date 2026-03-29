# Changelog

All notable changes to the Verdict project.

## [1.4.0] — 2026-03-29

### Added — Deep Analytical Pipeline
- **Leave-One-Out Sensitivity Analysis**: `sensitivity_analysis()` in `verdict_stability.py` — identifies pivotal witnesses whose removal would flip the verdict. Computes per-witness margin impact and fragility score (fraction of pivotal witnesses). Combined robustness now weighted across evidence margin (35%), perturbation (40%), and sensitivity (25%).
- **TF-IDF Weighted Claim Similarity**: `compute_tfidf_similarity()` in `argument_graph.py` — replaces naive keyword overlap with smoothed TF-IDF cosine similarity for more accurate dependency detection. Common terms across claims are down-weighted; distinctive terms that indicate real logical dependency are amplified.
- **Topological Sort (Kahn's Algorithm)**: `topological_sort()` in `argument_graph.py` — produces dependency-ordered claim traversal (foundations first, dependents last). Included in `metrics()` output.
- **Stop Word Filtering**: Argument graph keyword extraction now filters 50+ English stop words for cleaner similarity computation.
- **Platt Scaling Feedback Loop**: `_calibrate_from_witnesses()` now auto-fits Platt scaling coefficients after accumulating 10+ calibration records per agent. `calibrate_confidence()` then applies the learned sigmoid correction to raw agent confidence scores during verdict computation — closing the calibration loop from measurement to correction.

### Added — Graph-Theoretic Analysis
- **Cross-Graph Dependency Analysis**: `CrossGraphAnalyzer` detects claims from opposing sides that reference the same underlying facts. Classifies pairs as contested_territory, contradictory_foundations, or foundation_attack via TF-IDF cosine similarity.
- **Structural Entropy**: Shannon entropy over normalized degree distribution measures dependency evenness. Low entropy (star topology) = fragile central claims; high entropy (mesh topology) = robust distributed dependencies.
- **Pivotal Witness Synthesis Wiring**: Sensitivity analysis results (pivotal witnesses, fragility score) propagated through VerdictState to synthesis agent for targeted recommendations.

### Added — Calibration Feedback Loop
- **Auto-Fit Calibration**: `CalibrationTracker.auto_fit_all()` fits Platt scaling for all agents with 10+ samples. Recalibration detection via `needs_recalibration()` with configurable ECE threshold.
- **Pipeline Calibration Wiring**: Witness outcomes (sustained/overruled) recorded into CalibrationTracker after pipeline completion. Auto-fits Platt scaling as data accumulates — confidence gate applies learned corrections to raw witness scores.
- **Export Stability Metrics**: Markdown reports now include Section 7 (Analysis & Quality Metrics) with robustness score, flip rate, evidence margin, argument grades, and quality gap.

### Added — Argument Quality
- **Logical Structure Dimension**: `score_logical_structure()` — detects forward references between claims and causal connectors (therefore, because, building on). Completes the documented 6-dimension quality assessment. Weights rebalanced across all 6 dimensions.

### Fixed
- **Cormorant Garamond font**: Added Google Fonts import and --font-heading CSS variable; applied to Verdict title, ruling label, and synthesis header. Resolves claim/code mismatch.
- **Liquid glass cards**: Added .glass-card and .glass-card-elevated CSS with backdrop-filter: blur. Applied to verdict and synthesis cards.
- **Domain count**: Fixed README listing 6 domains when domains.yaml defines 9 (business, financial, legal, medical, hiring, technology, strategic, product, marketing).
- **Session data cleanup**: Removed 1362 session JSON files from git tracking; added .gitignore rules to prevent future bulk commits.

### Testing
- 496 total tests across 22 test files (up from 426)
- Added 7 sensitivity analysis tests (pivotal detection, fragility scoring, leave-one-out)
- Added 11 TF-IDF and topological sort tests
- Added 5 cross-graph analysis tests (shared evidence, contradictory foundations)
- Added 7 structural entropy tests (star topology, chain, bounds)
- Added 2 Platt scaling wiring tests (auto-fit threshold, confidence correction)

## [1.3.0] — 2026-03-29

### Added — Intelligence-Driven Routing (ADR-006)
- **Structural Cross-Examination**: Argument dependency graph analysis (critical paths, foundation claims, coherence differentials) passed into the judge's cross-examination prompt for smarter claim selection
- **Impact-Weighted Witness Prioritization**: Contested claims reordered by cascading impact from DAG before witness spawning — high-impact foundation claims verified first
- **Quality-Gap Witness Spawning**: When argument quality differential exceeds 0.2, witnesses are spawned even with zero contested claims to stress-test the weaker side
- **Stability-Aware Synthesis**: Fragile verdicts (low robustness, narrow evidence margins) trigger cautious recommendations with contingency plans and monitoring triggers
- **Domain-Aware Confidence Thresholds**: Medical (0.7), legal (0.65), financial (0.65), business (0.6), technology (0.55) — high-stakes domains require higher witness agreement
- **Multi-Factor Confidence Gate**: 4-factor routing using domain-adjusted threshold, witness agreement ratio, confidence variance, and overrule detection

### Added — Production-Grade Metrics
- **Percentile Tracking**: p50/p95/p99 latency percentiles for per-agent and pipeline-wide metrics
- **Error Rate Tracking**: Per-agent and pipeline-wide error rates in metrics summary
- **Pipeline Progress Tracking**: Status endpoint returns completion percentage, current stage, stages remaining, and ETA

### Refactored — Intelligence Pipeline
- **VerdictState Extended**: Added `argument_quality`, `argument_graphs`, `verdict_stability` fields — computed intelligence now flows through the pipeline instead of being emitted-and-discarded
- **Judge accepts structural_analysis**: `cross_examine()` method now receives argument graph intelligence for smarter claim selection
- **Synthesis accepts stability/quality**: `run()` method now receives verdict stability and argument quality for calibrated recommendations

### Testing
- 418 total tests across 22 test files (up from 395)
- Added 7 intelligence pipeline integration tests (VerdictState fields, graph flow, parameter wiring)
- Added 10 percentile/error-rate metrics tests
- Added 6 multi-factor confidence gate tests (domain thresholds, agreement, variance)
- Added 2 quality-gap witness spawning tests
- Added 1 progress tracking API test

## [1.2.0] — 2026-03-29

### Added — Core Pipeline Depth
- **Witness-Weighted Evidence Scoring**: `judge.compute_evidence_score()` adjusts prosecution/defense scores based on witness verdicts (sustained: +0.1×confidence, overruled: -0.15×confidence)
- **Research Quality Scoring**: 5-dimension assessment (breadth, depth, grounding, balance, completeness) with weighted overall score in `research.score_research_quality()`
- **Synthesis Coverage Assessment**: `synthesis.assess_synthesis_coverage()` measures objection coverage %, action time-boundedness, and strength delta
- **Argument Strength Analysis**: `judge.analyze_argument_strength()` pre-cross-examination with per-side confidence stats and strength differential
- **Claim Overlap Detection**: `judge.detect_claim_overlaps()` uses keyword overlap to find opposing claims on the same topic for witness prioritization
- **Adaptive Temperature**: `_adaptive_temperature()` adjusts prosecutor/defense LLM temperature based on research quality scores — better research → more factual arguments
- **Confidence Calibration Pipeline Integration**: `_calibrate_from_witnesses()` uses witness verdicts as ground truth for per-agent ECE tracking
- **Constitutional Compliance Validation**: `_validate_constitutional_compliance()` checks that prosecution/defense arguments conform to their directives
- **Pipeline-Wide Observability**: All 7 graph nodes emit start/complete/error events via async event bus with rich payloads

### Added — Analytical Pipeline
- **Argument Dependency Graph** (`utils/argument_graph.py`): DAG construction via keyword co-occurrence, BFS cascading impact analysis, coherence scoring (connected component ratio), foundation/critical/vulnerable claim detection
- **Verdict Stability Analysis** (`utils/verdict_stability.py`): Monte Carlo perturbation testing (50 simulations, ±10% witness confidence), evidence margin computation, combined robustness scoring
- **Argument Quality Scoring** (`utils/argument_quality.py`): 6-dimension heuristic assessment (evidence specificity, claim diversity, logical structure, confidence calibration, opening coherence, actionability) with A-D letter grading
- **Analysis API Endpoint**: `GET /api/verdict/{id}/analysis` — returns quality grades, dependency graphs, and stability analysis for completed sessions

### Refactored — Code Quality (DRY)
- **Centralized All Agent Prompts**: All 6 agents now import system prompts from `agents/prompts.py` — zero inline prompt definitions remain, eliminating ~120 lines of duplicated prompt text
- **Shared LLM Helpers** (`utils/llm_helpers.py`): Extracted 4 duplicated patterns from all 6 agents into shared utilities — `parse_llm_json()`, `emit_thinking_phases()`, `create_llm()`, `retry_with_low_temperature()`
- **Circuit Breaker Wired to Production**: `call_llm_with_resilience()` routes LLM retry calls through the circuit breaker — no longer dead code
- **Human-in-the-Loop Activated**: `INTERRUPT_BEFORE_VERDICT` env var activates `interrupt_before` on the verdict review node
- **Agent Cleanup**: All 6 agents refactored to use shared helpers; removed unused `ChatGroq` and `settings` imports
- **Route DRY Cleanup**: `detect_domain` and `followup` endpoints refactored to use `create_llm()` and `parse_llm_json()`
- **Validators Wired to Production**: `validate_question_quality()`, `check_format_domain_fit()`, and `validate_research_package()` now used in API routes and graph nodes
- **Inline Analysis**: Session results now include embedded argument quality, stability, and dependency graph analysis (no separate endpoint needed)

### Testing
- 395 total tests across 22 test files (up from 172)
- Added LLM helpers tests: JSON parsing, code fence stripping, thinking phases, factory, retry (23 tests)
- Added API quality gate tests: generic rejection, format suggestion field (4 tests)
- Added graph pipeline tests: adaptive temperature, calibration wiring, constitutional compliance (31 tests)
- Added agent-level integration tests: claim overlap, research quality, synthesis coverage (31 tests)
- Added argument graph tests: DAG construction, degree metrics, cascading impact (23 tests)
- Added verdict stability tests: margin computation, Monte Carlo, flip rate bounds (17 tests)
- Added argument quality tests: specificity, diversity, calibration, grading (24 tests)
- Added event bus, calibration, validators, and session FSM tests

## [1.1.0] — 2026-03-29

### Added
- **Security Middleware**: XSS pattern detection on URLs, HTML entity sanitization, Content-Length body size limits, and security response headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy)
- **Centralized Prompt Templates**: All 7 agent prompts extracted to `agents/prompts.py` — single source of truth for constitutional directives with audit tests
- **Session Analytics Endpoint**: `GET /sessions/analytics` aggregates ruling distribution, domain breakdown, format usage, completion rate, and average confidence
- **Pipeline Graph Visualization**: Backend `graph_visualizer.py` generates structured pipeline topology with dynamic witness nodes; Frontend `PipelineGraph.jsx` renders vertical flow diagram with real-time status indicators
- **Pipeline Graph Endpoints**: `GET /{id}/graph` (session-specific) and `GET /graph/topology` (static topology) for pipeline visualization
- **Interactive Pipeline Sidebar**: Toggle pipeline view in courtroom UI showing agent execution flow with parallel branch display
- **Async Event Bus**: Topic-based pub/sub with priority ordering and fire-and-forget delivery
- **Confidence Calibration**: Bayesian ECE tracking per agent per domain with overconfidence detection
- **Session State Machine**: 5-state FSM (created→running→complete/error/expired) with transition validation
- **Domain-Aware Input Validators**: Question quality scoring, research package validation, format-domain compatibility

### Testing
- 172 total tests across 14 test files (up from 106)
- Added 22 security middleware tests (XSS detection, sanitization, headers)
- Added 22 prompt template tests (constitutional directive verification)
- Added 22 integration tests (session lifecycle, domain detection, analytics)
- Added 17 graph visualization tests (topology, witness nodes, routing paths)

---

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
- 106 unit tests across 10 test files (schemas, graph topology, API contracts, exports, resilience, cache, middleware, domain config, errors, metrics)
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
