# Verdict — AI Courtroom
### New England Inter-Collegiate AI Hackathon · March 28-29, 2026
### Team: Tensor Monk | Track: AI Innovation Hack

---

## Vision Clarity

Verdict is a multi-agent adversarial reasoning system that transforms any high-stakes decision into a live courtroom proceeding. You bring the decision. Verdict brings the argument.

We are building an AI courtroom where specialized agents debate a user's question, challenge each other's reasoning, evaluate evidence, and produce a final verdict with confidence and traceable rationale — and then synthesize a stronger, battle-tested version of the original idea with every weak point addressed.

A Prosecutor agent and a Defense agent autonomously research, reason, and argue opposing sides of any startup or product decision. A Judge agent cross-examines both sides, spawns specialist Witness agents to verify specific claims in real time, and delivers a final reasoned verdict with confidence score. A Synthesis agent then reads everything — every argument, every objection, every witness finding — and produces an improved version of the original idea that survives every attack.

The north star: every important decision deserves to be challenged by the best possible counter-argument before it is made. Ideas go in raw. They come out battle-tested. Verdict makes that happen in under 3 minutes, autonomously, with zero human effort.

---

## Problem Definition

High-stakes decisions are almost always made with confirmation bias. Founders seek information that supports what they already want to do. Advisors tell you what you want to hear. AI assistants agree with you.

Nobody has built an AI system whose explicit job is to argue against you, destroy your idea from every angle, and hand you back a stronger version. Every multi-agent system today is collaborative — agents working together toward a shared goal. Verdict is adversarial by design, with synthesis as the payoff.

The problem is specific: founders, product managers, investors, and researchers make bad decisions because nothing challenges them rigorously before they commit. Current AI tools give one-shot answers, but users in startup, business, and research settings need answers that are challenged before being trusted.

---

## Innovation

Every multi-agent system built today uses cooperative orchestration — agents pass tasks to each other in a pipeline toward a shared output. Verdict inverts this architecture entirely.

Prosecutor and Defense agents are adversarially instantiated with opposing constitutional directives. They do not share memory during argument phase. The Judge agent is structurally prevented from seeing which side produced which argument until cross-examination is complete — eliminating positional bias in verdict generation. The Synthesis agent reads the entire proceeding and produces not just a ruling but an evolved, stronger version of the original idea.

Most AI tools just answer. Verdict debates, critiques, judges, and synthesizes.

This adversarial multi-agent architecture with synthesis output does not exist in any production system today. It goes beyond OpenClaw, beyond LangGraph tutorials, beyond every hackathon project built on cooperative pipelines.

---

## Technical Architecture

### Agent Graph (LangGraph)

```
Input Node
    │
    ├──► Research Agent (shared, runs first)
    │         │
    │    [Research Package]
    │         │
    ├──► Prosecutor Agent ──► Argument A
    │         
    ├──► Defense Agent ──► Argument B
    │
    ├──► Cross-Examination Node (Judge reads both)
    │         │
    │    [Spawns Witness Agents dynamically per claim]
    │         │
    ├──► Judge Agent ──► Final Ruling + Reasoning + Confidence Score
    │         │
    └──► Synthesis Agent ──► Improved Idea + Battle-Tested Output
              │
         WebSocket stream to frontend
```

### Agent Roles

**Research Agent**
- Runs first, produces a neutral research package on the decision topic
- Shared context given to both Prosecutor and Defense
- Tools: web search, document parsing

**Prosecutor Agent**
- Constitutional directive: argue FOR the decision with maximum rigor
- Access to research package only
- Produces structured argument with claims, evidence, and confidence scores

**Defense Agent**
- Constitutional directive: argue AGAINST the decision with maximum rigor
- Access to research package only — no access to Prosecutor output
- Produces structured argument with claims, evidence, and confidence scores

**Judge Agent**
- Reads both arguments simultaneously
- Identifies the 3 most contested claims
- Dynamically spawns Witness Agents to verify each contested claim
- Delivers final verdict with structured reasoning and confidence score

**Witness Agents (dynamic)**
- Spawned by Judge on demand — this is the "agents that hire agents" architecture
- Each Witness is specialized: FactWitness, DataWitness, PrecedentWitness
- Returns verified claim resolution back to Judge

**Synthesis Agent**
- Reads the full proceeding: research package, both arguments, witness findings, and judge verdict
- Identifies the strongest points from both sides
- Produces an improved, battle-tested version of the original idea with every weak point addressed
- Output: enhanced idea + list of addressed objections + recommended next actions

### Backend Stack
- **FastAPI** — async REST + WebSocket server
- **LangGraph** — agent graph orchestration
- **Groq** — LLM inference (Llama 3.3 70B), free tier, high speed
- **Pydantic** — type-safe data models throughout
- **Redis** — session state and agent message passing
- **Railway** — deployment

### Frontend Stack
- **React + Vite** — fast development, component architecture
- **Tailwind CSS** — utility-first styling
- **Framer Motion** — agent animations, argument card transitions, verdict reveal, synthesis emergence
- **WebSockets** — real-time streaming of agent outputs to UI

### Data Models

```python
class Decision(BaseModel):
    id: str
    question: str
    context: Optional[str]
    created_at: datetime

class Argument(BaseModel):
    agent: Literal["prosecutor", "defense"]
    claims: List[Claim]
    confidence: float
    timestamp: datetime

class Claim(BaseModel):
    statement: str
    evidence: str
    confidence: float
    verified: Optional[bool]

class WitnessReport(BaseModel):
    claim_id: str
    witness_type: Literal["fact", "data", "precedent"]
    resolution: str
    confidence: float

class Verdict(BaseModel):
    decision_id: str
    ruling: Literal["proceed", "reject", "conditional"]
    reasoning: str
    key_factors: List[str]
    confidence: float
    timestamp: datetime

class Synthesis(BaseModel):
    decision_id: str
    improved_idea: str
    addressed_objections: List[str]
    recommended_actions: List[str]
    strength_score: float
    timestamp: datetime
```

---

## Feasibility

Verdict is scoped to one domain — startup and product decisions — with exactly 3 core features: case submission, multi-agent hearing, and final verdict with synthesis. The agent graph has 6 node types with clean interfaces between them. The frontend renders a courtroom timeline with real-time agent outputs streamed over WebSockets.

The team has prior experience with FastAPI, LangGraph, and React. No new languages or frameworks are being learned during the hackathon — only applied.

---

## Scalability Design

Verdict is architected to scale beyond the demo in four directions:

**Horizontal agent scaling:** Each agent runs as an independent async worker. Under load, multiple Prosecutor/Defense pairs can run concurrently via LangGraph's parallel execution model.

**Pluggable LLM backend:** The LLM interface is abstracted behind a provider class — swapping to any model requires one config change.

**Domain specialization:** The agent constitutional directives are loaded from config files, not hardcoded. Verdict can be specialized for legal, medical, financial, or hiring decisions by swapping prompt configs — no code changes required.

**Multi-tenancy:** Redis session isolation means multiple organizations can run concurrent verdict sessions with zero data leakage between tenants. A SaaS deployment requires no architectural changes.

---

## Ecosystem Thinking

Verdict exposes a clean REST + WebSocket API from day one:

```
POST /api/verdict/start        — Submit a decision for evaluation
GET  /api/verdict/{id}/status  — Poll case status
WS   /api/verdict/{id}/stream  — Real-time agent output stream
GET  /api/verdict/{id}/result  — Final verdict + synthesis JSON
```

Any application can embed Verdict as a decision-verification layer. The API is designed for integration — a Slack bot, a hiring platform, a legal tool — all can plug in without touching Verdict's internals.

---

## User Impact

Every person who makes decisions under uncertainty is a user — every founder, hiring manager, investor, and anyone signing a contract. Conservative estimate: 50M+ knowledge workers in the US alone make at least one high-stakes decision per week.

The immediate impact: a decision that would take 3 hours of research and deliberation happens in 3 minutes, with more rigorous counter-argument than any human advisor would provide.

The structural impact: decisions stop being made on vibes. Every claim is challenged before a verdict is reached. Verdict doesn't just save time — it structurally reduces the cost of being wrong.

---

## Market Awareness

**Existing solutions:**
- ChatGPT / Claude: agree with the user, no adversarial architecture
- Pros/cons generators: static, not research-backed, not agent-driven
- Devil's advocate features: single-agent, shallow, not structured as a proceeding

**Verdict's positioning:** the only multi-agent adversarial reasoning system with synthesis output, built specifically for startup and product decisions. Not a chatbot, not a pros/cons list, not a copilot. A courtroom that hands you back a better idea.

---

## Team Execution Plan

### Team Tensor Monk
- **Karthik** — Agent architecture, LangGraph graph, Groq integration, all agent design and prompt engineering
- **Raja** — FastAPI server, WebSocket implementation, Redis state management, core API endpoints
- **Ihika** — Backend support, API testing, integration validation, ensures every agent output aligns with system ideology end to end
- **Srujan** — React frontend, component architecture, Tailwind layout, courtroom UI
- **Sathwik** — Framer Motion animations, WebSocket integration on frontend, real-time streaming UI

### Milestones

| Time | Milestone |
|------|-----------|
| 12:00 PM Sat | Repo initialized, master plan pushed, all members have access |
| 1:00 PM Sat | FastAPI server running, LangGraph skeleton with all 6 agent nodes defined |
| 2:00 PM Sat | Research + Prosecutor + Defense agents producing outputs end to end |
| 3:00 PM Sat | Judge agent + Witness agent dynamic spawning working |
| 4:00 PM Sat | Synthesis agent working, full pipeline end to end |
| 5:00 PM Sat | WebSocket streaming backend to frontend working |
| 7:00 PM Sat | Frontend courtroom UI rendering real agent outputs |
| 9:00 PM Sat | Framer Motion animations integrated, full flow working end to end |
| 11:00 PM Sat | First full demo run, bug fixes, edge case handling |
| 1:00 AM Sun | Deployed on Railway, README complete |
| 9:00 AM Sun | Polish, error handling, UI refinement |
| 12:00 PM Sun | Final demo prep, stress testing |
| 2:30 PM Sun | Submission |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Groq rate limits hit during demo | Medium | Cache last successful run as demo fallback |
| LangGraph agent graph too slow for live demo | Medium | Pre-warm a session before judges watch |
| WebSocket connection drops during demo | Low | Auto-reconnect logic + REST polling fallback |
| Agent outputs incoherent or hallucinated | Medium | Pydantic validation on every agent output, retry logic |
| Synthesis agent output too generic | Medium | Structured prompt engineering with explicit objection list as input |
| Frontend animations lag on demo machine | Low | Reduce animation complexity if performance issues arise |

---

## Differentiation Strategy

Every other team in this hackathon is building cooperative multi-agent pipelines. Agents that plan together, execute together, help together.

Verdict is the only system where agents are constitutionally opposed to each other by design — and where the output isn't just an answer but a stronger version of your original idea. The adversarial architecture is not a feature — it is the entire thesis. You cannot add adversarial reasoning to a cooperative pipeline as an afterthought. It requires a fundamentally different graph topology, different memory isolation, different orchestration logic.

You know that boardroom moment where everyone tears an idea apart and something better comes out? That happens to every founder once if they're lucky. Verdict makes it happen in 3 minutes, on demand, for any decision, forever.

This is not a tutorial project. This is not a wrapper. This is a new architecture for how AI systems reason about decisions.

**Verdict. Every decision deserves a challenger.**
