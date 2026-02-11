"""
Hybrid cache service combining diskcache and PostgreSQL database.
Provides fallback mechanisms and maintains backward compatibility.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from time import time

# Try to import diskcache
try:
    from diskcache import Cache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    Cache = None

# Try to import database service
try:
    from .db_service import get_db_service, DatabaseService
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    DatabaseService = None

logger = logging.getLogger(__name__)

# Configuration
CACHE_DIR = os.environ.get('CACHE_DIR', './cache')
DATABASE_URL = os.environ.get('DATABASE_URL')

# Cache TTL settings (in seconds)
GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))
WHOIS_CACHE_TTL = int(os.environ.get('WHOIS_CACHE_TTL', 86400))
LOOKUP_HISTORY_TTL = int(os.environ.get('LOOKUP_HISTORY_TTL', 604800))  # 7 days


class HybridCacheService:
    """Hybrid caching service with database and disk fallbacks."""
    
    def __init__(self):
        self.disk_cache = None
        self.db_service = None
        self._initialized = False
        self._init_cache()
    
    def _init_cache(self):
        """Initialize cache backends."""
        if not self._initialized:
            # Initialize disk cache
            if DISKCACHE_AVAILABLE:
                try:
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    self.disk_cache = Cache(CACHE_DIR, size_limit=int(1e9))  # 1GB limit
                    logger.info("Disk cache initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize disk cache: {e}")
                    self.disk_cache = None
            else:
                logger.info("Diskcache not available, skipping disk cache initialization")
            
            # Initialize database service
            if DATABASE_AVAILABLE and DATABASE_URL:
                try:
                    self.db_service = get_db_service()
                    logger.info("Database service initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize database service: {e}")
                    self.db_service = None
            else:
                logger.info("Database not configured, using disk cache only")
            
            self._initialized = True
    
    def get_geolocation(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation data with hybrid caching."""
        # Try database first (higher priority)
        if self.db_service:
            try:
                db_result = self.db_service.get_geolocation(ip_address)
                if db_result:
                    logger.debug(f"Geolocation found in database for {ip_address}")
                    return db_result
            except Exception as e:
                logger.warning(f"Database geolocation lookup failed: {e}")
        
        # Fall back to disk cache
        if self.disk_cache:
            try:
                cache_key = f"geo_{ip_address}"
                cached = self.disk_cache.get(cache_key)
                if cached:
                    logger.debug(f"Geolocation found in disk cache for {ip_address}")
                    return cached
            except Exception as e:
                logger.warning(f"Disk cache geolocation lookup failed: {e}")
        
        return None
    
    def save_geolocation(self, ip_address: str, geo_data: Dict[str, Any]) -> bool:
        """Save geolocation data to all available caches."""
        success = True
        
        # Save to database
        if self.db_service:
            try:
                if self.db_service.save_geolocation(ip_address, geo_data):
                    logger.debug(f"Geolocation saved to database for {ip_address}")
                else:
                    success = False
            except Exception as e:
                logger.warning(f"Failed to save geolocation to database: {e}")
                success = False
        
        # Save to disk cache
        if self.disk_cache:
            try:
                cache_key = f"geo_{ip_address}"
                cache_ttl = GEO_CACHE_TTL if geo_data.get('status') == 'success' else 300
                self.disk_cache.set(cache_key, geo_data, expire=cache_ttl)
                logger.debug(f"Geolocation saved to disk cache for {ip_address}")
            except Exception as e:
                logger.warning(f"Failed to save geolocation to disk cache: {e}")
                success = False
        
        return success
    
    def get_whois(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get WHOIS data with hybrid caching."""
        # Try database first
        if self.db_service:
            try:
                db_result = self.db_service.get_whois_record(ip_address)
                if db_result:
                    logger.debug(f"WHOIS found in database for {ip_address}")
                    return db_result
            except Exception as e:
                logger.warning(f"Database WHOIS lookup failed: {e}")
        
        # Fall back to disk cache
        if self.disk_cache:
            try:
                cache_key = f"whois_{ip_address}"
                cached = self.disk_cache.get(cache_key)
                if cached:
                    logger.debug(f"WHOIS found in disk cache for {ip_address}")
                    return cached
            except Exception as e:
                logger.warning(f"Disk cache WHOIS lookup failed: {e}")
        
        return None
    
    def save_whois(self, ip_address: str, whois_data: Dict[str, Any]) -> bool:
        """Save WHOIS data to all available caches."""
        success = True
        
        # Save to database
        if self.db_service:
            try:
                if self.db_service.save_whois_record(ip_address, whois_data):
                    logger.debug(f"WHOIS saved to database for {ip_address}")
                else:
                    success = False
            except Exception as e:
                logger.warning(f"Failed to save WHOIS to database: {e}")
                success = False
        
        # Save to disk cache
        if self.disk_cache:
            try:
                cache_key = f"whois_{ip_address}"
                self.disk_cache.set(cache_key, whois_data, expire=WHOIS_CACHE_TTL)
                logger.debug(f"WHOIS saved to disk cache for {ip_address}")
            except Exception as e:
                logger.warning(f"Failed to save WHOIS to disk cache: {e}")
                success = False
        
        return success
    
    def log_lookup(self, ip_address: str, endpoint: str, success: bool = True,
                   response_time: int = None, client_ip: str = None, 
                   user_agent: str = None) -> bool:
        """Log lookup to database (disk cache doesn't support this)."""
        if self.db_service:
            try:
                return self.db_service.log_lookup(
                    ip_address, endpoint, success, response_time, client_ip, user_agent
                )
            except Exception as e:
                logger.warning(f"Failed to log lookup: {e}")
                return False
        return True  # No-op if no database
    
    def save_security_scan(self, scan_data: Dict[str, Any]) -> bool:
        """Save security scan results to database."""
        if self.db_service:
            try:
                return self.db_service.save_security_scan(scan_data)
            except Exception as e:
                logger.warning(f"Failed to save security scan: {e}")
                return False
        return True  # No-op if no database
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all cache backends."""
        health = {
            "diskcache": {"available": DISKCACHE_AVAILABLE, "enabled": self.disk_cache is not None},
            "database": {"available": DATABASE_AVAILABLE, "enabled": self.db_service is not None}
        }
        
        # Check disk cache health
        if self.disk_cache:
            try:
                cache_stats = {
                    "size": len(list(self.disk_cache.iterkeys())),
                    "directory": self.disk_cache.directory
                }
                health["diskcache"]["status"] = "healthy"
                health["diskcache"]["stats"] = cache_stats
            except Exception as e:
                health["diskcache"]["status"] = "unhealthy"
                health["diskcache"]["error"] = str(e)
        else:
            health["diskcache"]["status"] = "disabled"
        
        # Check database health
        if self.db_service:
            try:
                db_health = self.db_service.health_check()
                health["database"]["status"] = db_health["status"]
                if db_health["status"] == "healthy":
                    health["database"]["stats"] = db_health
                else:
                    health["database"]["error"] = db_health.get("error", "Unknown error")
            except Exception as e:
                health["database"]["status"] = "unhealthy"
                health["database"]["error"] = str(e)
        else:
            health["database"]["status"] = "disabled"
        
        return health
    
    def cleanup_expired_entries(self) -> Dict[str, int]:
        """Clean up expired cache entries (disk cache only)."""
        stats = {"disk_cleaned": 0, "database_cleaned": 0}
        
        if self.disk_cache:
            try:
                # DiskCache automatically handles expiration, but we can force cleanup
                cleaned = self.disk_cache.expire()
                stats["disk_cleaned"] = cleaned
                logger.info(f"Cleaned {cleaned} expired disk cache entries")
            except Exception as e:
                logger.warning(f"Failed to clean disk cache: {e}")
        
        # Database cleanup would be handled by retention policies or separate jobs
        return stats


# Global cache service instance
cache_service = None


def get_cache_service() -> HybridCacheService:
    """Get singleton cache service instance."""
    global cache_service
    if cache_service is None:
        cache_service = HybridCacheService()
    return cache_service


def init_cache_service() -> HybridCacheService:
    """Initialize and return cache service."""
    global cache_service
    cache_service = HybridCacheService()
    return cache_service