"""Tests for pipeline metrics tracking."""

import pytest
from utils.metrics import PipelineMetrics, _percentile


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


class TestPercentileComputation:
    """Verify percentile calculation accuracy."""

    def test_percentile_empty_list(self):
        assert _percentile([], 50) == 0.0

    def test_percentile_single_value(self):
        assert _percentile([5.0], 50) == 5.0
        assert _percentile([5.0], 99) == 5.0

    def test_percentile_p50_median(self):
        values = sorted([1.0, 2.0, 3.0, 4.0, 5.0])
        assert _percentile(values, 50) == 3.0

    def test_percentile_p95_interpolation(self):
        values = sorted([float(i) for i in range(1, 101)])
        p95 = _percentile(values, 95)
        assert 95.0 <= p95 <= 96.0

    def test_percentile_p99(self):
        values = sorted([float(i) for i in range(1, 101)])
        p99 = _percentile(values, 99)
        assert p99 >= 99.0


class TestMetricsPercentiles:
    """Verify per-agent and pipeline percentile stats."""

    def test_agent_percentiles_in_summary(self):
        m = PipelineMetrics()
        # Simulate 10 agent runs with known durations
        for _ in range(10):
            with m.track_agent("research"):
                pass
        stats = m.summary()
        agent = stats["agents"]["research"]
        assert "p50_duration_ms" in agent
        assert "p95_duration_ms" in agent
        assert "p99_duration_ms" in agent
        assert agent["p50_duration_ms"] >= 0
        assert agent["p95_duration_ms"] >= agent["p50_duration_ms"]

    def test_pipeline_percentiles_in_summary(self):
        m = PipelineMetrics()
        for d in [1.0, 2.0, 3.0, 4.0, 5.0]:
            m.record_pipeline_complete(d)
        stats = m.summary()
        pipeline = stats["pipeline"]
        assert "p50_duration_ms" in pipeline
        assert "p95_duration_ms" in pipeline
        assert pipeline["p50_duration_ms"] == round(_percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) * 1000, 1)

    def test_error_rate_computed(self):
        m = PipelineMetrics()
        with m.track_agent("research"):
            pass
        with pytest.raises(ValueError):
            with m.track_agent("research"):
                raise ValueError("fail")
        stats = m.summary()
        agent = stats["agents"]["research"]
        assert agent["error_rate"] == 0.5  # 1 success, 1 failure

    def test_overall_error_rate(self):
        m = PipelineMetrics()
        with m.track_agent("research"):
            pass
        with m.track_agent("prosecutor"):
            pass
        stats = m.summary()
        assert stats["pipeline"]["overall_error_rate"] == 0.0

    def test_bottleneck_agent_detected(self):
        import time
        m = PipelineMetrics()
        with m.track_agent("research"):
            pass  # Fast
        with m.track_agent("prosecutor"):
            time.sleep(0.01)  # Slower
        stats = m.summary()
        assert stats["bottleneck_agent"] == "prosecutor"

    def test_bottleneck_none_when_empty(self):
        m = PipelineMetrics()
        stats = m.summary()
        assert stats["bottleneck_agent"] is None
