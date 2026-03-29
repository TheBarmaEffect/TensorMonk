# ADR-001: Adversarial Isolation Architecture

## Status
Accepted

## Context
Verdict's core value proposition is adversarial decision analysis — arguments FOR and AGAINST must be independently generated to prevent confirmation bias. If agents can see each other's work, they tend to agree rather than genuinely challenge.

## Decision
We enforce three isolation constraints:

1. **Authorship Blindness**: The Research Agent's output is stripped of all metadata (agent_id, model, source, timestamp, etc.) via `strip_authorship()` before reaching Prosecutor/Defense. Neither agent knows who produced the research.

2. **Adversarial Isolation**: Prosecutor and Defense run in parallel via `asyncio.gather()` and never see each other's output. The Judge is the first node in the LangGraph to receive both arguments.

3. **Constitutional Directives**: System prompts constitutionally bind Prosecutor to argue FOR and Defense to argue AGAINST, regardless of their "personal" assessment of the evidence.

## Consequences
- **Pro**: Genuinely adversarial arguments — Defense will find real weaknesses even in good ideas
- **Pro**: Eliminates groupthink bias common in multi-agent systems
- **Con**: Sometimes both sides make the same point from different angles (redundancy)
- **Con**: Parallel execution means we can't do back-and-forth rebuttal (single round)

## Implementation
- `strip_authorship()` in `graph/verdict_graph.py` removes 11 metadata fields
- LangGraph `arguments` node uses `asyncio.gather(prosecutor(), defense())`
- Constitutional overlays loaded from `config/domains.yaml` per domain
