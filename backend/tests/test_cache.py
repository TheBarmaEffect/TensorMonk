"""Tests for TTL cache — verifying expiration, normalization, and eviction."""

import time
import pytest
from utils.cache import TTLCache


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("test_key", {"value": 42})
        result = cache.get("test_key")
        assert result == {"value": 42}

    def test_returns_none_for_missing_key(self):
        cache = TTLCache(ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_expires_after_ttl(self):
        cache = TTLCache(ttl_seconds=0)  # Instant expiration
        cache.set("key", "value")
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_key_normalization_case_insensitive(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("Should We Pivot?", "result")
        assert cache.get("should we pivot?") == "result"

    def test_key_normalization_strips_whitespace(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("  test  ", "result")
        assert cache.get("test") == "result"

    def test_long_keys_are_hashed(self):
        cache = TTLCache(ttl_seconds=60)
        long_key = "x" * 300
        cache.set(long_key, "result")
        assert cache.get(long_key) == "result"

    def test_evicts_oldest_when_at_capacity(self):
        cache = TTLCache(ttl_seconds=60, max_entries=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_stats_tracking(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        cache.get("key")       # hit
        cache.get("key")       # hit
        cache.get("missing")   # miss
        stats = cache.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.667, abs=0.01)
        assert stats["size"] == 1

    def test_clear(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.stats["size"] == 0

    def test_contains_without_stats_impact(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        # contains should not affect hit/miss counters
        hits_before = cache.stats["hits"]
        assert cache.contains("key") is True
        assert cache.contains("missing") is False
        assert cache.stats["hits"] == hits_before  # Unchanged

    def test_contains_expired_returns_false(self):
        cache = TTLCache(ttl_seconds=0)  # Immediate expiry
        cache.set("key", "value")
        import time
        time.sleep(0.01)
        assert cache.contains("key") is False
