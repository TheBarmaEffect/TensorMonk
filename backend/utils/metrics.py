"""Lightweight performance metrics for agent pipeline monitoring.

Tracks per-agent execution times, success/failure counts, and pipeline
throughput without external dependencies. Metrics are exposed via the
/health endpoint for monitoring and debugging.

Design decisions:
- In-memory counters (no Prometheus/StatsD dependency)
- Thread-safe via simple atomic operations on primitives
- Per-agent and per-pipeline granularity
- Reset capability for testing
"""

import logging
import time
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineMetrics:
    """Track execution metrics for the verdict pipeline.

    Usage:
        metrics = PipelineMetrics()
        with metrics.track_agent("research", "session-123"):
            await research_agent.run(...)

        stats = metrics.summary()
    """

    def __init__(self):
        self._agent_durations: dict[str, list[float]] = defaultdict(list)
        self._agent_success: dict[str, int] = defaultdict(int)
        self._agent_failure: dict[str, int] = defaultdict(int)
        self._pipeline_count: int = 0
        self._pipeline_durations: list[float] = []

    class _AgentTimer:
        """Context manager for timing agent execution."""

        def __init__(self, metrics: "PipelineMetrics", agent_name: str, session_id: str):
            self.metrics = metrics
            self.agent_name = agent_name
            self.session_id = session_id
            self.start_time: float = 0.0

        def __enter__(self):
            self.start_time = time.monotonic()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.monotonic() - self.start_time
            self.metrics._agent_durations[self.agent_name].append(duration)

            if exc_type is None:
                self.metrics._agent_success[self.agent_name] += 1
                logger.debug(
                    "[Metrics] %s completed in %.2fs [%s]",
                    self.agent_name, duration, self.session_id,
                )
            else:
                self.metrics._agent_failure[self.agent_name] += 1
                logger.warning(
                    "[Metrics] %s failed after %.2fs [%s]: %s",
                    self.agent_name, duration, self.session_id, exc_val,
                )
            return False  # Don't suppress exceptions

    def track_agent(self, agent_name: str, session_id: str = "") -> _AgentTimer:
        """Create a context manager to track agent execution time.

        Args:
            agent_name: Name of the agent (research, prosecutor, etc.)
            session_id: Session ID for log correlation
        """
        return self._AgentTimer(self, agent_name, session_id)

    def record_pipeline_complete(self, duration: float) -> None:
        """Record a complete pipeline execution."""
        self._pipeline_count += 1
        self._pipeline_durations.append(duration)

    def summary(self) -> dict:
        """Generate a metrics summary for monitoring.

        Returns:
            Dict with per-agent stats and pipeline-level aggregates.
        """
        agent_stats = {}
        for agent_name in set(
            list(self._agent_durations.keys())
            + list(self._agent_success.keys())
            + list(self._agent_failure.keys())
        ):
            durations = self._agent_durations.get(agent_name, [])
            agent_stats[agent_name] = {
                "invocations": len(durations),
                "successes": self._agent_success.get(agent_name, 0),
                "failures": self._agent_failure.get(agent_name, 0),
                "avg_duration_ms": round(
                    sum(durations) / len(durations) * 1000, 1
                ) if durations else 0,
                "max_duration_ms": round(max(durations) * 1000, 1) if durations else 0,
            }

        pipeline_durations = self._pipeline_durations
        return {
            "agents": agent_stats,
            "pipeline": {
                "total_runs": self._pipeline_count,
                "avg_duration_ms": round(
                    sum(pipeline_durations) / len(pipeline_durations) * 1000, 1
                ) if pipeline_durations else 0,
            },
        }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._agent_durations.clear()
        self._agent_success.clear()
        self._agent_failure.clear()
        self._pipeline_count = 0
        self._pipeline_durations.clear()


# Global singleton for application-wide metrics
pipeline_metrics = PipelineMetrics()
