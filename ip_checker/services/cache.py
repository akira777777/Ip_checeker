"""
IP Checker Pro - High-Performance Caching Service
=================================================
Multi-tier caching with memory and disk persistence,
TTL support, and LRU eviction.
"""

import hashlib
import json
import logging
import os
import pickle
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union

logger = logging.getLogger(__name__)
T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    expires_at: float
    hits: int = 0
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at


class MemoryCache:
    """Thread-safe in-memory LRU cache with TTL."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value with TTL in seconds."""
        with self._lock:
            expires_at = time.time() + ttl
            entry = CacheEntry(value=value, expires_at=expires_at)
            
            # If key exists, update and move to end
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
                return
            
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
                self._evictions += 1
            
            self._cache[key] = entry
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired:
                del self._cache[key]
            return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': round(hit_rate, 2),
                'expired_count': sum(1 for v in self._cache.values() if v.is_expired),
            }


class DiskCache:
    """Persistent disk-based cache with TTL."""
    
    def __init__(self, cache_dir: str = './cache', max_size_mb: int = 100):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        self._index_file = self._cache_dir / '.cache_index'
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load cache index from disk."""
        try:
            if self._index_file.exists():
                with open(self._index_file, 'r') as f:
                    self._index = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache index: {e}")
            self._index = {}
    
    def _save_index(self) -> None:
        """Save cache index to disk."""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self._cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        with self._lock:
            meta = self._index.get(key)
            if not meta:
                return None
            
            if time.time() > meta['expires_at']:
                self.delete(key)
                return None
            
            cache_file = self._get_cache_file(key)
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired:
                    self.delete(key)
                    return None
                
                entry.hits += 1
                return entry.value
            except Exception as e:
                logger.debug(f"Failed to read cache file: {e}")
                self.delete(key)
                return None
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value with TTL."""
        with self._lock:
            self._cleanup_if_needed()
            
            entry = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )
            
            cache_file = self._get_cache_file(key)
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry, f)
                
                self._index[key] = {
                    'file': str(cache_file),
                    'expires_at': entry.expires_at,
                    'size': cache_file.stat().st_size if cache_file.exists() else 0,
                }
                self._save_index()
            except Exception as e:
                logger.warning(f"Failed to write cache file: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            meta = self._index.pop(key, None)
            if meta:
                try:
                    Path(meta['file']).unlink(missing_ok=True)
                except Exception:
                    pass
                self._save_index()
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            for meta in self._index.values():
                try:
                    Path(meta['file']).unlink(missing_ok=True)
                except Exception:
                    pass
            self._index.clear()
            self._save_index()
    
    def _cleanup_if_needed(self) -> None:
        """Remove old entries if cache is too large."""
        total_size = sum(m['size'] for m in self._index.values())
        
        if total_size < self._max_size_bytes * 0.8:
            return
        
        # Sort by access time and remove oldest
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1].get('accessed_at', 0)
        )
        
        target_size = self._max_size_bytes * 0.6
        while total_size > target_size and sorted_entries:
            key, meta = sorted_entries.pop(0)
            self.delete(key)
            total_size -= meta['size']
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_size = sum(m['size'] for m in self._index.values())
            expired = sum(1 for m in self._index.values() if time.time() > m['expires_at'])
            return {
                'entries': len(self._index),
                'size_mb': round(total_size / (1024 * 1024), 2),
                'max_size_mb': self._max_size_bytes / (1024 * 1024),
                'expired_entries': expired,
            }


class HybridCache:
    """
    Two-tier cache: Memory (L1) + Disk (L2).
    Hot data stays in memory, cold data on disk.
    """
    
    def __init__(self, 
                 memory_size: int = 1000,
                 disk_dir: str = './cache',
                 disk_size_mb: int = 100):
        self._memory = MemoryCache(max_size=memory_size)
        self._disk = DiskCache(cache_dir=disk_dir, max_size_mb=disk_size_mb)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get from L1, fall back to L2."""
        # Try memory first
        value = self._memory.get(key)
        if value is not None:
            return value
        
        # Try disk
        value = self._disk.get(key)
        if value is not None:
            # Promote to memory (with shorter TTL)
            self._memory.set(key, value, ttl=60)
            return value
        
        self._maybe_cleanup()
        return None
    
    def set(self, key: str, value: Any, ttl: int, 
            memory_ttl: Optional[int] = None) -> None:
        """
        Set value in both caches.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Disk cache TTL
            memory_ttl: Memory cache TTL (defaults to min(ttl, 300))
        """
        mem_ttl = memory_ttl or min(ttl, 300)
        
        self._memory.set(key, value, mem_ttl)
        self._disk.set(key, value, ttl)
        self._maybe_cleanup()
    
    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        mem_deleted = self._memory.delete(key)
        disk_deleted = self._disk.delete(key)
        return mem_deleted or disk_deleted
    
    def clear(self) -> None:
        """Clear both caches."""
        self._memory.clear()
        self._disk.clear()
    
    def _maybe_cleanup(self) -> None:
        """Periodic cleanup of expired entries."""
        with self._lock:
            if time.time() - self._last_cleanup > self._cleanup_interval:
                self._memory.cleanup_expired()
                self._last_cleanup = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        return {
            'memory': self._memory.get_stats(),
            'disk': self._disk.get_stats(),
        }
    
    def memoize(self, ttl: int = 3600, key_func: Optional[Callable] = None):
        """
        Decorator for function result caching.
        
        Args:
            ttl: Cache TTL in seconds
            key_func: Optional function to generate cache key from arguments
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.sha256(
                        ':'.join(key_parts).encode()
                    ).hexdigest()
                
                # Try cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                
                # Compute and cache
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            wrapper.cache = self
            wrapper.clear_cache = lambda: self.delete(
                hashlib.sha256(f"{func.__name__}:".encode()).hexdigest()
            )
            
            return wrapper
        return decorator


# Global cache instance
_global_cache: Optional[HybridCache] = None


def get_cache() -> HybridCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        from ip_checker.core.config import get_config
        config = get_config()
        _global_cache = HybridCache(
            memory_size=config.CACHE_MAX_SIZE,
            disk_dir=config.CACHE_DIR,
            disk_size_mb=100
        )
    return _global_cache


def init_cache() -> HybridCache:
    """Initialize and return global cache."""
    return get_cache()
