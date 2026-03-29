"""TTL cache for expensive operations like LLM-based domain detection.

Provides a simple time-to-live cache that avoids repeated LLM calls
for identical or near-identical queries. Thread-safe for async use.

Design decisions:
- Dict-based with timestamps (no external dependency)
- Automatic eviction of expired entries on access
- Configurable TTL and max entries to bound memory usage
- Key normalization (lowercase + strip) for fuzzy matching
"""

import hashlib
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple TTL-based cache with automatic expiration.

    Usage:
        cache = TTLCache(ttl_seconds=300, max_entries=500)
        cache.set("key", {"domain": "business", "confidence": 0.9})
        result = cache.get("key")  # Returns value or None if expired
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 500):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._store: dict[str, tuple[float, Any]] = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Normalize cache key for consistent lookup.

        Strips whitespace, lowercases, and hashes long keys to bound
        memory usage from key storage.
        """
        normalized = key.strip().lower()
        if len(normalized) > 200:
            return hashlib.sha256(normalized.encode()).hexdigest()[:32]
        return normalized

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if it exists and hasn't expired.

        Args:
            key: Cache key (will be normalized)

        Returns:
            Cached value or None if missing/expired
        """
        normalized = self._normalize_key(key)
        entry = self._store.get(normalized)

        if entry is None:
            self._misses += 1
            return None

        timestamp, value = entry
        if time.monotonic() - timestamp > self.ttl:
            # Expired — remove and return None
            del self._store[normalized]
            self._misses += 1
            self._expirations += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache with the configured TTL.

        If cache is at capacity, evicts the oldest entry first.

        Args:
            key: Cache key (will be normalized)
            value: Value to cache
        """
        # Evict oldest if at capacity
        if len(self._store) >= self.max_entries:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]
            self._evictions += 1

        normalized = self._normalize_key(key)
        self._store[normalized] = (time.monotonic(), value)

    def contains(self, key: str) -> bool:
        """Check if a non-expired entry exists without affecting hit/miss stats."""
        normalized = self._normalize_key(key)
        entry = self._store.get(normalized)
        if entry is None:
            return False
        return (time.monotonic() - entry[0]) <= self.ttl

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    @property
    def stats(self) -> dict:
        """Return cache hit/miss statistics for monitoring."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
            "size": len(self._store),
            "evictions": self._evictions,
            "expirations": self._expirations,
        }
