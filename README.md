# Verdict

## Hackathon Submission

- Master Plan: [MASTER_PLAN.md](./MASTER_PLAN.md)  
- Architecture: [docs/architecture.md](./docs/architecture.md)

Verdict is a multi-agent adversarial reasoning system that transforms any high-stakes decision into a live courtroom proceeding.

You bring the decision. Verdict brings the argument.

---

## Vision

Every important decision deserves to be challenged by the strongest possible counter-argument before it is made.

Verdict makes that happen in minutes.

---

## What is Verdict

Verdict is an AI courtroom where specialized agents debate a decision, challenge each other, verify claims, and deliver a final ruling with confidence and reasoning.

- A Prosecutor agent argues for the decision  
- A Defense agent argues against it  
- A Judge agent evaluates both sides and delivers a verdict  
- Witness agents verify contested claims dynamically  

A Synthesis agent produces a stronger, battle-tested version of the original idea by incorporating all arguments and objections.

---

## Problem

High-stakes decisions are often made with confirmation bias.

People:
- look for supporting information  
- avoid opposing viewpoints  
- rely on advisors who agree with them  
- use AI tools that reinforce their thinking  

Current AI systems generate answers, but they do not challenge decisions rigorously.

Verdict is built to challenge decisions before they are made.

---

## What Makes Verdict Different

- Adversarial multi-agent architecture instead of cooperative pipelines  
- Prosecutor and Defense agents are structurally opposed  
- Memory isolation between opposing agents  
- Blinded judgment to reduce bias  
- Dynamic Witness agents spawned to verify contested claims  
- Synthesis agent that improves the original idea after debate  
- Config-driven agent behavior using YAML prompt files  

---

## Core Flow

1. User submits a decision  
2. Research Agent prepares a neutral research package  
3. Prosecutor Agent argues for the decision  
4. Defense Agent argues against the decision  
5. Judge Agent cross-examines both sides  
6. Witness Agents verify disputed claims  
7. Verdict is produced with reasoning and confidence  
8. Synthesis Agent outputs an improved, battle-tested idea  

---

## Example Use Cases

- Hiring decisions  
- Startup or product decisions  
- Investment evaluation  
- Contract review  
- Strategic planning  

---

## Tech Stack

### Backend
- FastAPI  
- LangGraph  
- Groq  
- Pydantic  
- Redis  

### Frontend
- React + Vite  
- Tailwind CSS  
- Framer Motion  
- WebSockets  

---

## API

- POST `/api/verdict/start`  
- GET `/api/verdict/{id}/status`  
- WS `/api/verdict/{id}/stream`  
- GET `/api/verdict/{id}/result`  

---

## Project Structure

```text
app/
  agents/
  graph/
  prompts/
  routes/
  services/
docs/
frontend/