# Verdict Architecture

Verdict is a multi-agent adversarial reasoning system designed to evaluate high-stakes decisions through structured opposition.

## High-Level Flow

1. A user submits a decision question and optional context
2. The Research Agent prepares a neutral research package
3. The Prosecutor Agent argues for the decision
4. The Defense Agent argues against the decision
5. The Judge Agent reads both arguments in blinded fashion
6. The Judge identifies contested claims
7. Witness Agents are spawned dynamically to verify those claims
8. A final verdict is returned with reasoning and confidence
9. Agent output is streamed to the frontend over WebSockets

## Agent Roles

### Research Agent
- Produces a neutral research package
- Gathers facts, sources, and context summary
- Shared by both Prosecutor and Defense

### Prosecutor Agent
- Argues for the decision with maximum rigor
- Uses only the research package
- Cannot see Defense reasoning during argument phase

### Defense Agent
- Argues against the decision with maximum rigor
- Uses only the research package
- Cannot see Prosecutor reasoning during argument phase

### Judge Agent
- Reads both arguments without knowing which side produced which output
- Cross-examines the strongest contested claims
- Spawns Witness agents when verification is needed
- Produces the final verdict

### Witness Agents
- Instantiated dynamically per contested claim
- Can act as Fact Witness, Data Witness, or Precedent Witness
- Return narrow verification results back to the Judge

## Core Architectural Principles

- Adversarial reasoning instead of cooperative orchestration
- Memory isolation between opposing agents
- Blinded judgment to reduce bias
- Dynamic witness spawning
- Config-driven constitutions using YAML prompt files
- Structured outputs using Pydantic models

## Backend Stack

- FastAPI for API and WebSocket endpoints
- LangGraph for agent graph orchestration
- Groq for low-latency inference
- Redis for session state and agent communication
- Pydantic for typed models and validation

## Frontend Stack

- React and Vite for UI
- Tailwind CSS for layout and styling
- Framer Motion for animations
- WebSockets for live agent output streaming

## API Surface

- POST `/api/verdict/start`
- GET `/api/verdict/{id}/status`
- WS `/api/verdict/{id}/stream`
- GET `/api/verdict/{id}/result`

## Why This Architecture Matters

Most multi-agent systems are cooperative. Verdict is adversarial by design.

That means the system is not trying to help a single answer get produced faster. It is designed to challenge the decision from both sides before a final ruling is made. That adversarial structure is the core thesis of the project.