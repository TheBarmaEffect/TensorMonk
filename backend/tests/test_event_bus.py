"""Tests for the async event bus — pub/sub, topic matching, and delivery."""

import asyncio
import pytest
from utils.event_bus import (
    EventBus,
    PipelineEvent,
    EventPriority,
    Subscription,
    pipeline_event_bus,
)


@pytest.fixture
def bus():
    return EventBus()


class TestEventCreation:
    """Test PipelineEvent creation and immutability."""

    def test_creates_with_defaults(self):
        event = PipelineEvent(topic="test.event")
        assert event.topic == "test.event"
        assert event.payload == {}
        assert event.priority == EventPriority.NORMAL
        assert event.source == "pipeline"

    def test_creates_with_payload(self):
        event = PipelineEvent(topic="agent.done", payload={"duration": 1.5})
        assert event.payload["duration"] == 1.5

    def test_has_timestamp(self):
        event = PipelineEvent(topic="test")
        assert event.timestamp > 0

    def test_immutable(self):
        event = PipelineEvent(topic="test")
        with pytest.raises(AttributeError):
            event.topic = "changed"


class TestSubscription:
    """Test subscription topic matching."""

    def test_matches_exact_prefix(self):
        sub = Subscription("test", "agent.", lambda e: None)
        assert sub.matches("agent.research.complete") is True

    def test_does_not_match_wrong_prefix(self):
        sub = Subscription("test", "agent.", lambda e: None)
        assert sub.matches("pipeline.start") is False

    def test_matches_empty_prefix(self):
        sub = Subscription("test", "", lambda e: None)
        assert sub.matches("anything") is True

    def test_stats_initial(self):
        sub = Subscription("test", "x.", lambda e: None)
        stats = sub.stats
        assert stats["delivered"] == 0
        assert stats["errors"] == 0


class TestPublishSubscribe:
    """Test event bus pub/sub mechanics."""

    @pytest.mark.asyncio
    async def test_subscriber_receives_matching_event(self, bus):
        received = []
        async def handler(event):
            received.append(event)

        bus.subscribe("test", "agent.", handler)
        await bus.publish(PipelineEvent(topic="agent.research.complete"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscriber_ignores_non_matching(self, bus):
        received = []
        async def handler(event):
            received.append(event)

        bus.subscribe("test", "agent.", handler)
        await bus.publish(PipelineEvent(topic="pipeline.start"))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        received_a = []
        received_b = []

        async def handler_a(event):
            received_a.append(event)
        async def handler_b(event):
            received_b.append(event)

        bus.subscribe("a", "agent.", handler_a)
        bus.subscribe("b", "agent.", handler_b)
        await bus.publish(PipelineEvent(topic="agent.done"))
        assert len(received_a) == 1
        assert len(received_b) == 1

    @pytest.mark.asyncio
    async def test_publish_returns_delivery_count(self, bus):
        async def handler(event): pass
        bus.subscribe("a", "test.", handler)
        bus.subscribe("b", "test.", handler)
        count = await bus.publish(PipelineEvent(topic="test.x"))
        assert count == 2

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_propagate(self, bus):
        async def bad_handler(event):
            raise ValueError("boom")

        bus.subscribe("bad", "test.", bad_handler)
        # Should not raise
        count = await bus.publish(PipelineEvent(topic="test.x"))
        assert count == 0  # Failed delivery doesn't count


class TestUnsubscribe:
    """Test subscriber removal."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_subscriber(self, bus):
        received = []
        async def handler(event):
            received.append(event)

        bus.subscribe("test", "x.", handler)
        assert bus.subscriber_count == 1
        bus.unsubscribe("test")
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_returns_false(self, bus):
        assert bus.unsubscribe("nonexistent") is False


class TestBatchPublish:
    """Test batch event publishing with priority ordering."""

    @pytest.mark.asyncio
    async def test_batch_delivers_all(self, bus):
        received = []
        async def handler(event):
            received.append(event)

        bus.subscribe("test", "x.", handler)
        events = [
            PipelineEvent(topic="x.a"),
            PipelineEvent(topic="x.b"),
            PipelineEvent(topic="x.c"),
        ]
        total = await bus.publish_batch(events)
        assert total == 3
        assert len(received) == 3

    @pytest.mark.asyncio
    async def test_batch_respects_priority(self, bus):
        order = []
        async def handler(event):
            order.append(event.priority)

        bus.subscribe("test", "x.", handler)
        events = [
            PipelineEvent(topic="x.low", priority=EventPriority.LOW),
            PipelineEvent(topic="x.critical", priority=EventPriority.CRITICAL),
            PipelineEvent(topic="x.high", priority=EventPriority.HIGH),
        ]
        await bus.publish_batch(events)
        assert order[0] == EventPriority.CRITICAL
        assert order[-1] == EventPriority.LOW


class TestStats:
    """Test event bus statistics."""

    @pytest.mark.asyncio
    async def test_stats_track_events(self, bus):
        async def handler(event): pass
        bus.subscribe("test", "x.", handler)
        await bus.publish(PipelineEvent(topic="x.a"))
        await bus.publish(PipelineEvent(topic="x.b"))

        stats = bus.stats
        assert stats["total_events_published"] == 2
        assert stats["active_subscribers"] == 1

    @pytest.mark.asyncio
    async def test_shutdown_clears_subscribers(self, bus):
        async def handler(event): pass
        bus.subscribe("test", "x.", handler)
        await bus.shutdown()
        assert bus.subscriber_count == 0


class TestGlobalSingleton:
    """Test the global pipeline_event_bus singleton."""

    def test_singleton_exists(self):
        assert pipeline_event_bus is not None
        assert isinstance(pipeline_event_bus, EventBus)
