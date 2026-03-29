# ADR-004: Event-Driven Pipeline Observability

## Status
Accepted

## Context
The verdict pipeline involves 6+ agents executing in sequence and parallel. Monitoring, metrics collection, and audit logging need to observe these agent transitions without modifying agent code. Tight coupling between agents and monitoring would make the system fragile and hard to extend.

## Decision
We implement an async event bus (`utils/event_bus.py`) using the Observer pattern with topic-based pub/sub:

1. **Topic-Based Routing**: Events use dot-separated topics (e.g., `agent.research.complete`, `pipeline.start`). Subscribers filter by prefix matching.

2. **Fire-and-Forget Delivery**: Subscriber failures are isolated — they cannot block or crash the pipeline. Errors are logged but not propagated.

3. **Priority-Ordered Batch Publishing**: Events can be published individually or in batches. Batch mode sorts by priority (CRITICAL > HIGH > NORMAL > LOW) before delivery.

4. **Immutable Events**: `PipelineEvent` is a frozen dataclass — events cannot be modified after creation, preventing subtle data corruption.

5. **Session Correlation**: Every event carries an optional `session_id` for distributed tracing across the full pipeline.

## Integration Points
- `verdict_graph.py` emits `pipeline.start`, `pipeline.complete`, `pipeline.error`
- Future: individual agent nodes can emit `agent.{name}.start/complete`
- Future: webhook subscribers for external monitoring (PagerDuty, Datadog)

## Consequences
- **Pro**: Zero coupling between agents and monitoring — new subscribers added without code changes
- **Pro**: Built-in backpressure via bounded subscriber queues
- **Pro**: Comprehensive delivery statistics for debugging
- **Con**: Additional abstraction layer — event topics must be documented
- **Con**: Fire-and-forget means missed events are not retried

## Alternatives Considered
- **Direct function calls**: Simpler but tightly couples agents to monitors
- **Redis Pub/Sub**: Adds infrastructure dependency for a feature that works in-process
- **Logging-only**: Loses structured event data and subscriber flexibility
