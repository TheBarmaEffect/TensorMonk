# Contributing to Verdict

## Project Structure

```
verdict/
├── backend/                 # FastAPI + LangGraph backend
│   ├── agents/             # 6 AI agent implementations + prompt templates
│   ├── api/                # REST + WebSocket endpoint definitions
│   ├── config/             # Settings + domain-specific YAML overlays
│   ├── graph/              # LangGraph StateGraph orchestration
│   ├── middleware/         # Rate limiting, security, request timing
│   ├── models/             # Pydantic v2 schemas with field validators
│   ├── services/           # Export pipeline, graph viz, session FSM
│   ├── utils/              # Cache, errors, logging, metrics, resilience
│   └── tests/              # 212+ tests across 15 files (pytest)
├── frontend/               # React 18 + Vite SPA
│   ├── src/components/     # 15+ React components
│   ├── src/hooks/          # Custom hooks (useVerdict, useVoiceInput, useKeyboardShortcuts)
│   └── src/store/          # Zustand state management
├── docs/                   # Architecture Decision Records (ADRs)
├── MASTER_PLAN.md          # Project vision, delivery tiers, test strategy
└── CHANGELOG.md            # Release history
```

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your-key" > .env
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

## Architecture Principles

1. **Adversarial Isolation** (ADR-001): Prosecutor and Defense never see each other's output
2. **Confidence-Based Routing** (ADR-002): Three verdict paths based on witness confidence
3. **Domain-Aware Overlays** (ADR-003): Per-domain constitutional directives from YAML

## Code Quality Standards

- All Python functions have docstrings with Args/Returns sections
- Pydantic models validate all inputs with field_validator
- Frontend components have JSDoc module documentation
- New features must include tests
- Constitutional directives (MUST argue FOR/AGAINST) are audited via test_prompts.py

## Commit Messages

Follow conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
