"""
TTL-based caching module for system metrics.

Provides thread-safe caching with configurable time-to-live (TTL) for reducing
CPU-intensive operations like system monitoring.
"""

import time
from threading import Lock


class TTLCache:
    """
    Thread-safe TTL (Time-To-Live) cache implementation.
    
    Automatically expires entries after a configurable time period.
    Uses a lock for thread-safe access.
    """
    
    def __init__(self, ttl_seconds=5):
        """
        Initialize the cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds for cached entries (default: 5)
        """
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl_seconds
        self.lock = Lock()
        # Statistics tracking
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        """
        Get a value from the cache.
        
        Returns None if the key doesn't exist or has expired.
        Automatically removes expired entries.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value, or None if not found/expired
        """
        with self.lock:
            if key in self.cache:
                if time.time() - self.timestamps[key] < self.ttl:
                    self.hits += 1
                    return self.cache[key]
                else:
                    # Entry expired, remove it
                    del self.cache[key]
                    del self.timestamps[key]
            self.misses += 1
            return None
    
    def set(self, key, value):
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
        """
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def delete(self, key):
        """
        Delete a specific key from the cache.
        
        Args:
            key: The cache key to delete
            
        Returns:
            True if the key was deleted, False if it didn't exist
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
                return True
            return False
    
    def clear(self):
        """Clear all entries from the cache."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_stats(self):
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hits, misses, total requests, and hit rate
        """
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total,
                'hit_rate_percent': round(hit_rate, 2),
                'cached_entries': len(self.cache),
                'ttl_seconds': self.ttl
            }
    
    def reset_stats(self):
        """Reset cache statistics (hits/misses counters)."""
        with self.lock:
            self.hits = 0
            self.misses = 0
