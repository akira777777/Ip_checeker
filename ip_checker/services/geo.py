"""
IP Checker Pro - Optimized Geolocation Service
==============================================
High-performance IP geolocation with connection pooling,
retry logic, circuit breaker pattern, and intelligent caching.
"""

import ipaddress
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ip_checker.core.config import get_config
from ip_checker.services.cache import get_cache

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Structured geolocation data."""
    ip: str
    status: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    message: Optional[str] = None
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'ip': self.ip,
            'status': self.status,
            'country': self.country,
            'country_code': self.country_code,
            'region': self.region,
            'city': self.city,
            'zip': self.zip_code,
            'lat': self.lat,
            'lon': self.lon,
            'timezone': self.timezone,
            'isp': self.isp,
            'org': self.org,
            'asn': self.asn,
            'message': self.message,
            'cached': self.cached,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeoLocation':
        """Create from dictionary."""
        return cls(
            ip=data['ip'],
            status=data.get('status', 'unknown'),
            country=data.get('country'),
            country_code=data.get('country_code'),
            region=data.get('region'),
            city=data.get('city'),
            zip_code=data.get('zip'),
            lat=data.get('lat'),
            lon=data.get('lon'),
            timezone=data.get('timezone'),
            isp=data.get('isp'),
            org=data.get('org'),
            asn=data.get('asn'),
            message=data.get('message'),
            cached=data.get('cached', False),
        )


class CircuitBreaker:
    """
    Circuit breaker pattern for external API calls.
    Prevents cascading failures when service is down.
    """
    
    STATE_CLOSED = 'closed'      # Normal operation
    STATE_OPEN = 'open'          # Failing, reject requests
    STATE_HALF_OPEN = 'half_open'  # Testing if recovered
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        with self._lock:
            if self._state == self.STATE_CLOSED:
                return True
            
            if self._state == self.STATE_OPEN:
                if time.time() - (self._last_failure_time or 0) > self.recovery_timeout:
                    self._state = self.STATE_HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
                return False
            
            # Half-open state
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
    
    def record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            if self._state == self.STATE_HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = self.STATE_CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info("Circuit breaker closed")
            else:
                self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed execution."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == self.STATE_HALF_OPEN:
                self._state = self.STATE_OPEN
                logger.warning("Circuit breaker opened (half-open failure)")
            elif self._failure_count >= self.failure_threshold:
                self._state = self.STATE_OPEN
                logger.warning(f"Circuit breaker opened ({self._failure_count} failures)")
    
    @property
    def state(self) -> str:
        return self._state


class GeoService:
    """
    Optimized geolocation service with:
    - Connection pooling
    - Retry logic with exponential backoff
    - Circuit breaker pattern
    - Intelligent caching
    - IPv4/IPv6 support
    """
    
    def __init__(self):
        self.config = get_config()
        self.cache = get_cache()
        self.circuit_breaker = CircuitBreaker()
        
        # Initialize session with connection pooling
        self.session = self._create_session()
        
        # Stats
        self._stats = {
            'requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'circuit_breaker_blocks': 0,
        }
        self._stats_lock = threading.Lock()
        
        # Optional: ipapi library
        try:
            import ipapi
            self._ipapi = ipapi
        except ImportError:
            self._ipapi = None
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.GEO_MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=self.config.GEO_BACKOFF_FACTOR,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            pool_connections=self.config.CONNECTION_POOL_SIZE,
            pool_maxsize=self.config.CONNECTION_POOL_SIZE * 2,
            max_retries=retry_strategy,
        )
        
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Default headers
        session.headers.update({
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def validate_ip(self, ip: str) -> bool:
        """Validate IP address (IPv4 or IPv6)."""
        if not ip or not isinstance(ip, str):
            return False
        try:
            ipaddress.ip_address(ip.strip())
            return True
        except ValueError:
            return False
    
    def is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/local."""
        try:
            addr = ipaddress.ip_address(ip.strip())
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return False
    
    def get_location(self, ip: str, skip_cache: bool = False) -> GeoLocation:
        """
        Get geolocation for IP address.
        
        Args:
            ip: IP address to lookup
            skip_cache: Bypass cache if True
            
        Returns:
            GeoLocation object with results
        """
        # Validate IP
        if not self.validate_ip(ip):
            return GeoLocation(
                ip=ip,
                status='error',
                message='Invalid IP address'
            )
        
        # Check cache first
        cache_key = f"geo:{ip}"
        if not skip_cache:
            cached = self.cache.get(cache_key)
            if cached:
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
                cached['cached'] = True
                return GeoLocation.from_dict(cached)
        
        with self._stats_lock:
            self._stats['cache_misses'] += 1
            self._stats['requests'] += 1
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            with self._stats_lock:
                self._stats['circuit_breaker_blocks'] += 1
            return GeoLocation(
                ip=ip,
                status='error',
                message='Service temporarily unavailable (circuit breaker open)'
            )
        
        # Try primary provider (ipapi.co if available)
        result = self._get_from_ipapi(ip)
        
        # Fallback to ip-api.com
        if result.status != 'success':
            result = self._get_from_ip_api_com(ip)
        
        # Cache successful results and negative results (shorter TTL)
        if result.status == 'success':
            self.cache.set(cache_key, result.to_dict(), self.config.GEO_CACHE_TTL)
            self.circuit_breaker.record_success()
        elif result.status == 'fail':
            # Cache negative results for 5 minutes
            self.cache.set(cache_key, result.to_dict(), 300)
            self.circuit_breaker.record_success()
        else:
            with self._stats_lock:
                self._stats['errors'] += 1
            self.circuit_breaker.record_failure()
        
        return result
    
    def _get_from_ipapi(self, ip: str) -> GeoLocation:
        """Query ipapi.co (if library available)."""
        if not self._ipapi:
            return GeoLocation(ip=ip, status='skip')
        
        try:
            location = self._ipapi.location(ip)
            if location and 'error' not in location:
                return GeoLocation(
                    ip=ip,
                    status='success',
                    country=location.get('country_name') or location.get('country'),
                    country_code=location.get('country_code'),
                    region=location.get('region'),
                    city=location.get('city'),
                    zip_code=location.get('postal'),
                    lat=location.get('latitude'),
                    lon=location.get('longitude'),
                    timezone=location.get('timezone'),
                    isp=location.get('org'),
                    org=location.get('org'),
                    asn=location.get('asn'),
                )
        except Exception as e:
            logger.debug(f"ipapi.co failed: {e}")
        
        return GeoLocation(ip=ip, status='fail')
    
    def _get_from_ip_api_com(self, ip: str) -> GeoLocation:
        """Query ip-api.com with optimized request."""
        try:
            url = self.config.GEO_API_URL.format(ip=ip)
            
            response = self.session.get(
                url,
                timeout=self.config.GEO_TIMEOUT,
                headers={'User-Agent': 'IPCheckerPro/2.1'}
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                return GeoLocation(
                    ip=ip,
                    status='success',
                    country=data.get('country'),
                    country_code=data.get('countryCode'),
                    region=data.get('regionName'),
                    city=data.get('city'),
                    zip_code=data.get('zip'),
                    lat=data.get('lat'),
                    lon=data.get('lon'),
                    timezone=data.get('timezone'),
                    isp=data.get('isp'),
                    org=data.get('org'),
                    asn=data.get('as'),
                )
            else:
                return GeoLocation(
                    ip=ip,
                    status=data.get('status', 'fail'),
                    message=data.get('message', 'Unknown error')
                )
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout looking up {ip}")
            return GeoLocation(ip=ip, status='error', message='Request timeout')
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error for {ip}: {e}")
            return GeoLocation(ip=ip, status='error', message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error looking up {ip}: {e}")
            return GeoLocation(ip=ip, status='error', message=str(e))
    
    def bulk_lookup(self, ips: List[str], max_workers: int = 5) -> List[GeoLocation]:
        """
        Bulk geolocation lookup with concurrent processing.
        
        Args:
            ips: List of IP addresses
            max_workers: Maximum concurrent requests
            
        Returns:
            List of GeoLocation results
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Deduplicate IPs
        unique_ips = list(set(ip.strip() for ip in ips if self.validate_ip(ip.strip())))
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(self.get_location, ip): ip 
                for ip in unique_ips[:self.config.GEO_LOOKUP_LIMIT]
            }
            
            for future in as_completed(future_to_ip):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    ip = future_to_ip[future]
                    logger.error(f"Error in bulk lookup for {ip}: {e}")
                    results.append(GeoLocation(
                        ip=ip, 
                        status='error', 
                        message=str(e)
                    ))
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        total = stats['cache_hits'] + stats['cache_misses']
        hit_rate = (stats['cache_hits'] / total * 100) if total > 0 else 0
        
        return {
            **stats,
            'cache_hit_rate': round(hit_rate, 2),
            'circuit_breaker_state': self.circuit_breaker.state,
        }
    
    def get_country_flag(self, country_code: str) -> str:
        """Get flag emoji for country code."""
        if not country_code or len(country_code) != 2:
            return '🏳️'
        
        # Convert country code to regional indicator symbols
        code = country_code.upper()
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)


# Global service instance
_geo_service: Optional[GeoService] = None


def get_geo_service() -> GeoService:
    """Get or create global geolocation service."""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoService()
    return _geo_service
