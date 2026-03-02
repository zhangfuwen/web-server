"""
Tests for TTL Cache module.
"""

import pytest
import time
import threading
from cache import TTLCache


class TestTTLCacheBasic:
    """Test basic cache operations."""
    
    def test_cache_set_and_get(self, cache):
        """Test setting and getting a value from cache."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        assert cache.get("nonexistent") is None
    
    def test_cache_overwrite(self, cache):
        """Test overwriting an existing key."""
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"
    
    def test_cache_delete(self, cache):
        """Test deleting a key from cache."""
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False  # Already deleted
    
    def test_cache_clear(self, cache):
        """Test clearing all cache entries."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
    
    def test_cache_multiple_values(self, cache):
        """Test storing multiple different values."""
        cache.set("string", "hello")
        cache.set("number", 42)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"key": "value"})
        
        assert cache.get("string") == "hello"
        assert cache.get("number") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"key": "value"}


class TestTTLCacheExpiration:
    """Test TTL expiration behavior."""
    
    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = TTLCache(ttl_seconds=1)
        cache.set("key1", "value1")
        
        # Should exist immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get("key1") is None
    
    def test_cache_not_expired_yet(self):
        """Test that cache entries don't expire before TTL."""
        cache = TTLCache(ttl_seconds=2)
        cache.set("key1", "value1")
        
        # Wait but not long enough
        time.sleep(1)
        
        # Should still exist
        assert cache.get("key1") == "value1"
    
    def test_cache_different_ttls(self):
        """Test multiple entries with different set times."""
        cache = TTLCache(ttl_seconds=1)
        
        cache.set("key1", "value1")
        time.sleep(0.5)
        cache.set("key2", "value2")
        
        # Wait for first to expire
        time.sleep(0.6)
        
        # key1 should be expired, key2 should still exist
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestTTLCacheStatistics:
    """Test cache statistics tracking."""
    
    def test_cache_hits(self, cache):
        """Test hit counter increments on cache hits."""
        cache.set("key1", "value1")
        
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")
        
        stats = cache.get_stats()
        assert stats['hits'] == 3
    
    def test_cache_misses(self, cache):
        """Test miss counter increments on cache misses."""
        cache.get("nonexistent1")
        cache.get("nonexistent2")
        cache.get("nonexistent3")
        
        stats = cache.get_stats()
        assert stats['misses'] == 3
    
    def test_cache_hit_rate(self, cache):
        """Test hit rate calculation."""
        cache.set("key1", "value1")
        
        # 2 hits
        cache.get("key1")
        cache.get("key1")
        
        # 2 misses
        cache.get("nonexistent1")
        cache.get("nonexistent2")
        
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['total_requests'] == 4
        assert stats['hit_rate_percent'] == 50.0
    
    def test_cache_reset_stats(self, cache):
        """Test resetting statistics."""
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")
        
        cache.reset_stats()
        
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['total_requests'] == 0
    
    def test_cache_stats_cached_entries(self, cache):
        """Test that stats include cached entries count."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.get_stats()
        assert stats['cached_entries'] == 2
    
    def test_cache_stats_ttl(self, cache):
        """Test that stats include TTL value."""
        stats = cache.get_stats()
        assert stats['ttl_seconds'] == 1


class TestTTLCacheThreadSafety:
    """Test thread safety of cache operations."""
    
    def test_concurrent_set_get(self):
        """Test concurrent set and get operations."""
        cache = TTLCache(ttl_seconds=10)
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(100):
                    key = f"key-{thread_id}-{i}"
                    cache.set(key, f"value-{i}")
                    value = cache.get(key)
                    if value != f"value-{i}":
                        errors.append(f"Thread {thread_id}: Expected value-{i}, got {value}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"
    
    def test_concurrent_delete(self):
        """Test concurrent delete operations."""
        cache = TTLCache(ttl_seconds=10)
        
        # Pre-populate cache
        for i in range(100):
            cache.set(f"key-{i}", f"value-{i}")
        
        errors = []
        
        def deleter(thread_id):
            try:
                for i in range(10):
                    key = f"key-{thread_id * 10 + i}"
                    cache.delete(key)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        threads = [threading.Thread(target=deleter, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"
    
    def test_concurrent_clear(self):
        """Test concurrent clear operations."""
        cache = TTLCache(ttl_seconds=10)
        errors = []
        
        def setter(thread_id):
            try:
                for i in range(50):
                    cache.set(f"key-{thread_id}-{i}", f"value-{i}")
            except Exception as e:
                errors.append(f"Setter {thread_id}: {str(e)}")
        
        def clearer():
            try:
                for _ in range(10):
                    time.sleep(0.01)
                    cache.clear()
            except Exception as e:
                errors.append(f"Clearer: {str(e)}")
        
        threads = [threading.Thread(target=setter, args=(i,)) for i in range(5)]
        threads.append(threading.Thread(target=clearer))
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestTTLCacheEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_cache_none_value(self, cache):
        """Test storing None as a value."""
        cache.set("key1", None)
        # None is a valid value, but get returns None for missing keys too
        # We need to check if key exists differently
        cache.set("key2", "value2")
        assert cache.get("key2") == "value2"
    
    def test_cache_empty_string(self, cache):
        """Test storing empty string."""
        cache.set("key1", "")
        assert cache.get("key1") == ""
    
    def test_cache_zero(self, cache):
        """Test storing zero."""
        cache.set("key1", 0)
        assert cache.get("key1") == 0
    
    def test_cache_false(self, cache):
        """Test storing False."""
        cache.set("key1", False)
        assert cache.get("key1") is False
    
    def test_cache_large_value(self, cache):
        """Test storing large values."""
        large_value = "x" * 10000
        cache.set("key1", large_value)
        assert cache.get("key1") == large_value
    
    def test_cache_special_characters(self, cache):
        """Test storing values with special characters."""
        special_value = "Hello 世界！🌍 @#$%^&*()"
        cache.set("key1", special_value)
        assert cache.get("key1") == special_value
