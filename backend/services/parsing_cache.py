"""
Caching system for parsed decisions to reduce API costs.
Stores parsed results with TTL and provides statistics.
"""
from typing import Dict, Any, Optional
import hashlib
import time
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class ParsingCache:
    """Simple in-memory cache for parsed decisions."""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize parsing cache.
        
        Args:
            ttl_seconds: Time to live for cache entries (default 1 hour)
            max_size: Maximum number of entries in cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0,
        }
    
    def _generate_key(self, content: str, parsing_type: str) -> str:
        """
        Generate cache key from content and parsing type.
        
        Args:
            content: The content to parse
            parsing_type: Type of parsing (vote, response, mediator, etc.)
            
        Returns:
            Hash key for caching
        """
        # Create a hash of the content + type
        combined = f"{parsing_type}:{content}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, content: str, parsing_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached parsing result if available and not expired.
        
        Args:
            content: The content that was parsed
            parsing_type: Type of parsing
            
        Returns:
            Cached result or None if not found/expired
        """
        self._stats["total_requests"] += 1
        
        key = self._generate_key(content, parsing_type)
        
        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self._cache[key]
            self._stats["misses"] += 1
            logger.debug("cache_expired", key=key[:16])
            return None
        
        self._stats["hits"] += 1
        logger.debug("cache_hit", key=key[:16], parsing_type=parsing_type)
        return entry["result"]
    
    def set(self, content: str, parsing_type: str, result: Dict[str, Any]):
        """
        Store parsing result in cache.
        
        Args:
            content: The content that was parsed
            parsing_type: Type of parsing
            result: Parsed result to cache
        """
        key = self._generate_key(content, parsing_type)
        
        # Evict oldest entry if cache is full
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        self._cache[key] = {
            "result": result,
            "timestamp": time.time(),
            "parsing_type": parsing_type,
        }
        
        logger.debug("cache_set", key=key[:16], parsing_type=parsing_type)
    
    def _evict_oldest(self):
        """Evict the oldest entry from cache."""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
        del self._cache[oldest_key]
        self._stats["evictions"] += 1
        logger.debug("cache_evicted", key=oldest_key[:16])
    
    def clear(self):
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info("cache_cleared", entries_removed=count)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit rate, size, and other metrics
        """
        total_requests = self._stats["total_requests"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._cache),
            "max_size": self.max_size,
            "evictions": self._stats["evictions"],
            "ttl_seconds": self.ttl_seconds,
        }
    
    def reset_stats(self):
        """Reset statistics counters."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0,
        }
        logger.info("cache_stats_reset")


# Global cache instance
_global_cache: Optional[ParsingCache] = None


def get_parsing_cache() -> ParsingCache:
    """Get or create the global parsing cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ParsingCache()
        logger.info("parsing_cache_initialized")
    return _global_cache
