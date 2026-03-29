"""Tests for pipeline metrics tracking."""

import pytest
from utils.metrics import PipelineMetrics


class TestPipelineMetrics:
    def test_track_agent_success(self):
        m = PipelineMetrics()
        with m.track_agent("research", "session-1"):
            pass  # Simulates successful execution
        stats = m.summary()
        assert stats["agents"]["research"]["successes"] == 1
        assert stats["agents"]["research"]["failures"] == 0

    def test_track_agent_failure(self):
        m = PipelineMetrics()
        with pytest.raises(ValueError):
            with m.track_agent("prosecutor", "session-2"):
                raise ValueError("LLM timeout")
        stats = m.summary()
        assert stats["agents"]["prosecutor"]["failures"] == 1

    def test_duration_tracking(self):
        m = PipelineMetrics()
        import time
        with m.track_agent("defense", "session-3"):
            time.sleep(0.01)
        stats = m.summary()
        assert stats["agents"]["defense"]["avg_duration_ms"] > 0
        assert stats["agents"]["defense"]["max_duration_ms"] > 0

    def test_pipeline_complete(self):
        m = PipelineMetrics()
        m.record_pipeline_complete(5.2)
        m.record_pipeline_complete(3.8)
        stats = m.summary()
        assert stats["pipeline"]["total_runs"] == 2
        assert stats["pipeline"]["avg_duration_ms"] > 0

    def test_multiple_agents(self):
        m = PipelineMetrics()
        with m.track_agent("research"):
            pass
        with m.track_agent("prosecutor"):
            pass
        with m.track_agent("defense"):
            pass
        stats = m.summary()
        assert len(stats["agents"]) == 3

    def test_reset(self):
        m = PipelineMetrics()
        with m.track_agent("research"):
            pass
        m.record_pipeline_complete(1.0)
        m.reset()
        stats = m.summary()
        assert len(stats["agents"]) == 0
        assert stats["pipeline"]["total_runs"] == 0

    def test_empty_summary(self):
        m = PipelineMetrics()
        stats = m.summary()
        assert stats["agents"] == {}
        assert stats["pipeline"]["total_runs"] == 0
        assert stats["pipeline"]["avg_duration_ms"] == 0
