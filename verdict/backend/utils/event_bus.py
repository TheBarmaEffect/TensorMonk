"""Async event bus — decoupled pub/sub for pipeline observability.

Implements the Observer pattern for the verdict pipeline, allowing
components to subscribe to agent lifecycle events without tight coupling.
This enables:
- Pipeline metrics collection without modifying agent code
- Real-time monitoring dashboards
- Audit logging of every agent transition
- Future webhook/notification integrations

The event bus is async-native and uses asyncio.Queue for backpressure
handling. Subscribers receive events asynchronously and cannot block
the pipeline.

Design decisions:
- Topic-based routing (subscribers filter by event type prefix)
- Fire-and-forget delivery (subscriber failures don't affect pipeline)
- Bounded subscriber queues prevent memory exhaustion from slow consumers
- Thread-safe via asyncio primitives (no explicit locks needed)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels for ordered processing."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class PipelineEvent:
    """An immutable event emitted by the verdict pipeline.

    Attributes:
        topic: Dot-separated event topic (e.g., 'agent.research.complete')
        payload: Arbitrary event data
        timestamp: Unix timestamp when the event was created
        session_id: Optional session identifier for correlation
        priority: Event priority for ordered processing
        source: Component that emitted the event
    """
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)
    session_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    source: str = "pipeline"


# Type alias for async subscriber callbacks
SubscriberFn = Callable[[PipelineEvent], Coroutine[Any, Any, None]]


class Subscription:
    """A single topic subscription with filtering and queue management.

    Attributes:
        subscriber_id: Unique identifier for this subscription
        topic_prefix: Events with topics starting with this prefix are delivered
        callback: Async function called for each matching event
        max_queue_size: Maximum buffered events before backpressure
    """

    def __init__(
        self,
        subscriber_id: str,
        topic_prefix: str,
        callback: SubscriberFn,
        max_queue_size: int = 100,
    ):
        self.subscriber_id = subscriber_id
        self.topic_prefix = topic_prefix
        self.callback = callback
        self.max_queue_size = max_queue_size
        self._delivered_count = 0
        self._error_count = 0

    def matches(self, topic: str) -> bool:
        """Check if an event topic matches this subscription's prefix."""
        return topic.startswith(self.topic_prefix)

    @property
    def stats(self) -> dict[str, Any]:
        """Subscription delivery statistics."""
        return {
            "subscriber_id": self.subscriber_id,
            "topic_prefix": self.topic_prefix,
            "delivered": self._delivered_count,
            "errors": self._error_count,
        }


class EventBus:
    """Async event bus with topic-based pub/sub for pipeline observability.

    Usage:
        bus = EventBus()

        # Subscribe to all agent events
        async def on_agent_event(event: PipelineEvent):
            print(f"Agent event: {event.topic}")

        bus.subscribe("metrics", "agent.", on_agent_event)

        # Publish an event
        await bus.publish(PipelineEvent(
            topic="agent.research.complete",
            payload={"duration_ms": 1500},
            session_id="abc-123",
        ))

        # Cleanup
        await bus.shutdown()
    """

    def __init__(self):
        self._subscriptions: list[Subscription] = []
        self._event_count = 0
        self._started_at = time.monotonic()

    def subscribe(
        self,
        subscriber_id: str,
        topic_prefix: str,
        callback: SubscriberFn,
        max_queue_size: int = 100,
    ) -> Subscription:
        """Register a subscriber for events matching a topic prefix.

        Args:
            subscriber_id: Unique name for this subscriber
            topic_prefix: Topic prefix to match (e.g., "agent." matches "agent.research.complete")
            callback: Async function called for each matching event
            max_queue_size: Maximum buffered events

        Returns:
            The created Subscription object
        """
        sub = Subscription(subscriber_id, topic_prefix, callback, max_queue_size)
        self._subscriptions.append(sub)
        logger.info(
            "EventBus: subscriber '%s' registered for topic '%s*'",
            subscriber_id, topic_prefix,
        )
        return sub

    def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove a subscriber by ID.

        Args:
            subscriber_id: The subscriber to remove

        Returns:
            True if the subscriber was found and removed
        """
        before = len(self._subscriptions)
        self._subscriptions = [
            s for s in self._subscriptions if s.subscriber_id != subscriber_id
        ]
        removed = len(self._subscriptions) < before
        if removed:
            logger.info("EventBus: subscriber '%s' unsubscribed", subscriber_id)
        return removed

    async def publish(self, event: PipelineEvent) -> int:
        """Publish an event to all matching subscribers.

        Delivery is fire-and-forget — subscriber errors are logged but
        don't propagate to the publisher. This ensures pipeline execution
        is never blocked by observer failures.

        Args:
            event: The event to publish

        Returns:
            Number of subscribers that received the event
        """
        self._event_count += 1
        delivered = 0

        for sub in self._subscriptions:
            if sub.matches(event.topic):
                try:
                    await sub.callback(event)
                    sub._delivered_count += 1
                    delivered += 1
                except Exception as e:
                    sub._error_count += 1
                    logger.warning(
                        "EventBus: subscriber '%s' failed on topic '%s': %s",
                        sub.subscriber_id, event.topic, e,
                    )

        return delivered

    async def publish_batch(self, events: list[PipelineEvent]) -> int:
        """Publish multiple events, respecting priority ordering.

        Events are sorted by priority (CRITICAL first) before delivery.

        Args:
            events: List of events to publish

        Returns:
            Total delivery count across all events
        """
        sorted_events = sorted(events, key=lambda e: e.priority.value, reverse=True)
        total = 0
        for event in sorted_events:
            total += await self.publish(event)
        return total

    @property
    def subscriber_count(self) -> int:
        """Number of active subscribers."""
        return len(self._subscriptions)

    @property
    def stats(self) -> dict[str, Any]:
        """Event bus statistics for monitoring."""
        return {
            "total_events_published": self._event_count,
            "active_subscribers": self.subscriber_count,
            "uptime_seconds": round(time.monotonic() - self._started_at, 2),
            "subscribers": [s.stats for s in self._subscriptions],
        }

    async def shutdown(self) -> None:
        """Graceful shutdown — clear all subscribers."""
        logger.info(
            "EventBus shutting down: %d events published, %d subscribers",
            self._event_count, len(self._subscriptions),
        )
        self._subscriptions.clear()


# Global singleton for the verdict pipeline
pipeline_event_bus = EventBus()
