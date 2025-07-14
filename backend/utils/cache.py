"""In-memory caching system for HDI platform"""

from functools import lru_cache, wraps
from datetime import datetime, timedelta
import hashlib
import json
from typing import Any, Optional, Dict
import time

class InMemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_count = 0
        self._hit_count = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        self._access_count += 1
        
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry['expires_at']:
                self._hit_count += 1
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set value in cache with TTL"""
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl_seconds),
            'created_at': datetime.now()
        }
    
    def clear_expired(self):
        """Remove all expired entries"""
        now = datetime.now()
        expired_keys = [k for k, v in self._cache.items() if now >= v['expires_at']]
        for key in expired_keys:
            del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'total_entries': len(self._cache),
            'access_count': self._access_count,
            'hit_count': self._hit_count,
            'hit_rate': self._hit_count / self._access_count if self._access_count > 0 else 0,
            'memory_estimate_mb': len(str(self._cache)) / 1024 / 1024
        }

# Global cache instances
property_cache = InMemoryCache()
perplexity_cache = InMemoryCache()

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached_property(ttl_seconds: int = 3600):
    """Decorator for caching property data"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_key(*args, **kwargs)
            
            # Check cache
            cached_value = property_cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                property_cache.set(key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator

def cached_perplexity(ttl_seconds: int = 86400):  # 24 hours default
    """Decorator for caching Perplexity responses"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from prompt
            key = cache_key(*args, **kwargs)
            
            # Check cache
            cached_value = perplexity_cache.get(key)
            if cached_value is not None:
                # Add flag to indicate cached response
                cached_value['metadata']['from_cache'] = True
                cached_value['metadata']['cache_savings'] = 0.006  # $0.006 saved
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            if result and result.get('success'):
                perplexity_cache.set(key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator

# Cleanup task to run periodically
def cleanup_caches():
    """Remove expired entries from all caches"""
    property_cache.clear_expired()
    perplexity_cache.clear_expired()

# Cache statistics endpoint data
def get_cache_statistics():
    """Get statistics for all caches"""
    return {
        'property_cache': property_cache.get_stats(),
        'perplexity_cache': perplexity_cache.get_stats(),
        'estimated_cost_savings': perplexity_cache._hit_count * 0.006
    }