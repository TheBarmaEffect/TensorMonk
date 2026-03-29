# Contributing to Verdict

## Development Setup

1. Clone the repository
2. Install backend dependencies: `cd backend && pip install -r requirements.txt`
3. Install frontend dependencies: `cd frontend && npm install`
4. Set environment variables (see README.md)
5. Run tests: `cd backend && pytest tests/`

## Code Style

- Python: Follow PEP 8, use type hints
- All agent prompts in `agents/prompts.py` (single source of truth)
- Tests required for all new features
