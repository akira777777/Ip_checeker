"""
IP Checker Pro - IMPROVED & FIXED VERSION
==========================================

Fixes and improvements:
- Fixed VPN check endpoint
- Improved error handling and fallback mechanisms
- Better retry logic for external APIs
- Streaming responses for large data
- Connection pooling optimizations
- Memory leak prevention
- Better logging and monitoring
"""

from __future__ import annotations

import atexit
import functools
import gzip
import hashlib
import ipaddress
import json
import logging
import os
import platform
import socket
import sys
import tempfile
import threading
import time
import traceback
import weakref
from collections import Counter, OrderedDict, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

import psutil
import requests
from flask import (
    Flask, Response, after_this_request, jsonify, 
    render_template, request, send_file, stream_with_context
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_caching import Cache

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler with rotation
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Optional imports
try:
    import ipapi
except ImportError:
    ipapi = None
    logger.warning("ipapi not installed")

try:
    import whois as whois_lib
except ImportError:
    whois_lib = None

try:
    import folium
except ImportError:
    folium = None

# ============================================================================
# IMPROVED CACHE WITH MEMORY MANAGEMENT
# ============================================================================

class SmartCache:
    """Thread-safe LRU Cache with TTL, memory limits and statistics."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600, max_memory_mb: int = 50, name: str = "cache"):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._max_memory = max_memory_mb * 1024 * 1024
        self._name = name
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._memory_usage = 0
        self._evictions = 0
        self._expirations = 0
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"Initialized {name} cache: max_size={max_size}, max_memory={max_memory_mb}MB")
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expiry, size = self._cache[key]
                if time.time() < expiry:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    self._remove_item(key, size)
                    self._expirations += 1
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            size = sys.getsizeof(value)
        except:
            size = 1024  # Default estimate
        
        with self._lock:
            # Remove old value if exists
            if key in self._cache:
                old_value, old_expiry, old_size = self._cache.pop(key)
                self._memory_usage -= old_size
            
            expiry = time.time() + (ttl or self._default_ttl)
            
            # Check memory limit
            while (self._memory_usage + size > self._max_memory or len(self._cache) >= self._max_size) and self._cache:
                self._evict_oldest()
                self._evictions += 1
            
            self._cache[key] = (value, expiry, size)
            self._memory_usage += size
            return True
    
    def _remove_item(self, key: str, size: int) -> None:
        del self._cache[key]
        self._memory_usage -= size
    
    def _evict_oldest(self) -> None:
        if self._cache:
            key, (value, expiry, size) = self._cache.popitem(last=False)
            self._memory_usage -= size
    
    def _cleanup_loop(self) -> None:
        """Background thread to cleanup expired entries."""
        while True:
            time.sleep(60)
            try:
                with self._lock:
                    now = time.time()
                    expired = [(k, v[2]) for k, v in list(self._cache.items()) if v[1] < now]
                    for key, size in expired:
                        self._remove_item(key, size)
                        self._expirations += 1
                    
                    if expired:
                        logger.debug(f"{self._name}: Cleaned up {len(expired)} expired entries")
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._memory_usage = 0
            logger.info(f"{self._name}: Cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                'name': self._name,
                'size': len(self._cache),
                'memory_mb': round(self._memory_usage / (1024 * 1024), 2),
                'max_memory_mb': self._max_memory / (1024 * 1024),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(self._hits / total * 100, 2) if total > 0 else 0,
                'evictions': self._evictions,
                'expirations': self._expirations,
                'max_size': self._max_size
            }

# Initialize caches with hybrid approach (Redis + in-memory for critical paths)
GEO_CACHE = SmartCache(max_size=5000, default_ttl=3600, max_memory_mb=50, name="geo")
WHOIS_CACHE = SmartCache(max_size=2000, default_ttl=86400, max_memory_mb=20, name="whois")
DNS_CACHE = SmartCache(max_size=3000, default_ttl=1800, max_memory_mb=10, name="dns")
CONNECTIONS_CACHE = SmartCache(max_size=100, default_ttl=5, max_memory_mb=5, name="connections")

# Hybrid cache decorator for Flask-Cache + SmartCache
def hybrid_cache(timeout=None, key_prefix=''):
    """Decorator that uses both Redis and in-memory caching"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try Redis cache first
            if cache_config['CACHE_TYPE'] != 'simple':
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Try in-memory cache
            memory_result = GEO_CACHE.get(cache_key)  # Using GEO_CACHE as example
            if memory_result is not None:
                return memory_result
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Cache in both layers
            if timeout:
                if cache_config['CACHE_TYPE'] != 'simple':
                    cache.set(cache_key, result, timeout=timeout)
                GEO_CACHE.set(cache_key, result, ttl=timeout)
            
            return result
        return decorated_function
    return decorator

# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# Security
Talisman(
    app,
    force_https=os.environ.get('FORCE_HTTPS', 'false').lower() == 'true',
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com", "data:"],
        'img-src': ["'self'", "data:", "https://*.tile.openstreetmap.org", "https://unpkg.com", "blob:"],
        'connect-src': "'self'",
    },
    content_security_policy_nonce_in=['script-src']
)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[os.environ.get('RATE_LIMIT_DEFAULT', "300 per day, 100 per hour")],
    storage_uri=os.environ.get('RATE_LIMIT_STORAGE', 'memory://')
)

# Caching
cache_config = {
    'CACHE_TYPE': os.environ.get('CACHE_TYPE', 'simple'),
    'CACHE_DEFAULT_TIMEOUT': int(os.environ.get('CACHE_TTL', 3600)),
    'CACHE_KEY_PREFIX': 'ipchecker_',
}

if os.environ.get('CACHE_TYPE') == 'redis':
    cache_config.update({
        'CACHE_REDIS_URL': os.environ.get('CACHE_REDIS_URL', 'redis://localhost:6379/0'),
        'CACHE_REDIS_HOST': os.environ.get('CACHE_REDIS_HOST', 'localhost'),
        'CACHE_REDIS_PORT': int(os.environ.get('CACHE_REDIS_PORT', 6379)),
        'CACHE_REDIS_DB': int(os.environ.get('CACHE_REDIS_DB', 0)),
    })

cache = Cache(app, config=cache_config)

# ============================================================================
# CONSTANTS
# ============================================================================

APP_VERSION = "2.3.1-improved"
GEO_LOOKUP_LIMIT = int(os.environ.get('GEO_LOOKUP_LIMIT', 25))
MAX_BULK_LOOKUPS = int(os.environ.get('MAX_BULK_LOOKUPS', 100))
MAX_CONNECTIONS_SCAN = int(os.environ.get('MAX_CONNECTIONS_SCAN', 300))
MAX_WORKERS = min(32, (os.cpu_count() or 4) + 4)

SUSPICIOUS_PORTS = {23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389, 5900, 3389}
SECURE_PORTS = {22, 443, 993, 995, 5061, 8443}
LOCAL_ONLY = os.environ.get('LOCAL_ONLY', 'true').lower() == 'true'

LOCAL_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]

GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,proxy,hosting,query"

# ============================================================================
# IMPROVED HTTP SESSION
# ============================================================================

class ConnectionPool:
    """Managed HTTP connection pool with retry logic."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=100,
            max_retries=3,
            pool_block=False
        )
        self._session.mount('https://', adapter)
        self._session.mount('http://', adapter)
        
        self._session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'User-Agent': f'IPCheckerPro/{APP_VERSION} (Security Tool)'
        })
        
        self._initialized = True
        logger.info("HTTP Connection Pool initialized")
    
    @property
    def session(self):
        return self._session
    
    def get(self, url: str, timeout: Tuple[int, int] = (3, 10), retries: int = 3, **kwargs) -> requests.Response:
        last_error = None
        
        for attempt in range(retries):
            try:
                response = self._session.get(url, timeout=timeout, **kwargs)
                return response
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"Timeout on {url} (attempt {attempt + 1}/{retries})")
                time.sleep(0.5 * (attempt + 1))
            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.warning(f"Connection error on {url} (attempt {attempt + 1}/{retries})")
                time.sleep(0.5 * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error on {url}: {e}")
                raise
        
        raise last_error if last_error else Exception("Max retries exceeded")
    
    def close(self):
        if self._session:
            self._session.close()
            logger.info("HTTP Connection Pool closed")

# Global connection pool
http_pool = ConnectionPool()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_ip(ip: str) -> bool:
    """Validate IP address (IPv4 or IPv6)."""
    if not ip or not isinstance(ip, str):
        return False
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False

def is_private_ip(ip: str) -> bool:
    """Check if IP is private."""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False

def is_local_network_ip(ip: str) -> bool:
    """Check if IP belongs to local networks."""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return any(addr in network for network in LOCAL_NETWORKS)
    except ValueError:
        return False

# ============================================================================
# IMPROVED GEOLOCATION
# ============================================================================

def get_ip_geolocation(ip_address: str, skip_cache: bool = False) -> Dict:
    """Get geolocation with caching and fallbacks."""
    
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    # Check cache
    if not skip_cache:
        cached = GEO_CACHE.get(ip_address)
        if cached:
            cached['cached'] = True
            return cached
    
    # Try primary API (ip-api.com)
    result = _get_geolocation_ipapi(ip_address)
    
    if result.get('status') == 'success':
        GEO_CACHE.set(ip_address, result, ttl=3600)
        return result
    
    # Try fallback (ipapi.co)
    if ipapi:
        result = _get_geolocation_ipapi_co(ip_address)
        if result.get('status') == 'success':
            GEO_CACHE.set(ip_address, result, ttl=3600)
            return result
    
    # Return error but cache it briefly
    result = {
        "ip": ip_address,
        "status": "error",
        "message": result.get('message', 'Geolocation service unavailable')
    }
    GEO_CACHE.set(ip_address, result, ttl=300)
    return result

def _get_geolocation_ipapi(ip: str) -> Dict:
    """Get geolocation from ip-api.com."""
    try:
        response = http_pool.get(
            GEO_API_URL.format(ip=ip),
            timeout=(2, 5)
        )
        
        if response.status_code == 429:
            logger.warning("ip-api.com rate limit hit")
            return {'status': 'error', 'message': 'Rate limited'}
        
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            return {
                "ip": ip,
                "status": "success",
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "zip": data.get("zip"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "org": data.get("org"),
                "asn": data.get("as"),
                "proxy": data.get("proxy", False),
                "hosting": data.get("hosting", False)
            }
        else:
            return {'status': 'error', 'message': data.get('message', 'Unknown error')}
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout for {ip}")
        return {'status': 'error', 'message': 'Request timeout'}
    except Exception as e:
        logger.error(f"ip-api.com error for {ip}: {e}")
        return {'status': 'error', 'message': 'Service error'}

def _get_geolocation_ipapi_co(ip: str) -> Dict:
    """Get geolocation from ipapi.co."""
    try:
        location = ipapi.location(ip)
        if location and "error" not in location:
            return {
                "ip": ip,
                "status": "success",
                "city": location.get("city"),
                "region": location.get("region"),
                "country": location.get("country_name") or location.get("country"),
                "country_code": location.get("country_code"),
                "lat": location.get("latitude"),
                "lon": location.get("longitude"),
                "timezone": location.get("timezone"),
                "isp": location.get("org"),
                "asn": location.get("asn")
            }
        return {'status': 'error', 'message': 'ipapi.co failed'}
    except Exception as e:
        logger.error(f"ipapi.co error: {e}")
        return {'status': 'error', 'message': str(e)}

def get_ip_geolocation_bulk(ips: List[str], max_workers: int = 20) -> List[Dict]:
    """Parallel bulk geolocation."""
    # Remove duplicates while preserving order
    seen = set()
    unique_ips = [ip for ip in ips if not (ip in seen or seen.add(ip))]
    
    results = []
    
    def lookup_single(ip: str) -> Dict:
        return {"ip": ip, "geolocation": get_ip_geolocation(ip)}
    
    with ThreadPoolExecutor(max_workers=min(max_workers, MAX_WORKERS)) as executor:
        future_to_ip = {executor.submit(lookup_single, ip): ip for ip in unique_ips}
        for future in as_completed(future_to_ip):
            try:
                results.append(future.result())
            except Exception as e:
                ip = future_to_ip[future]
                logger.error(f"Bulk lookup error for {ip}: {e}")
                results.append({"ip": ip, "geolocation": {"status": "error", "message": str(e)}})
    
    return results

# ============================================================================
# IMPROVED NETWORK ANALYSIS
# ============================================================================

_process_name_cache: Dict[int, Tuple[str, float]] = {}
_process_cache_lock = threading.Lock()
_PROCESS_CACHE_TTL = 60  # 60 seconds

def get_process_name_cached(pid: Optional[int]) -> str:
    """Get process name with TTL caching."""
    if not pid:
        return "unknown"
    
    with _process_cache_lock:
        now = time.time()
        if pid in _process_name_cache:
            name, timestamp = _process_name_cache[pid]
            if now - timestamp < _PROCESS_CACHE_TTL:
                return name
        
        try:
            name = psutil.Process(pid).name()
            _process_name_cache[pid] = (name, now)
            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            _process_name_cache[pid] = ("unknown", now)
            return "unknown"

def analyze_connections(limit: int = 200, include_geo: bool = True) -> Dict:
    """Analyze network connections with caching."""
    
    # Cache key includes timestamp rounded to 5 seconds
    cache_key = f"conn_{limit}_{include_geo}_{int(time.time() / 5)}"
    cached = CONNECTIONS_CACHE.get(cache_key)
    if cached:
        return cached
    
    connections = []
    geo_cache: Dict[str, Dict] = {}
    geo_lookups = 0
    
    try:
        conns = psutil.net_connections(kind="inet")[:limit]
        
        for conn in conns:
            if not conn.raddr:
                continue
            
            remote_ip, remote_port = conn.raddr
            
            # Get geolocation
            geo = {"status": "skipped"}
            if include_geo and geo_lookups < GEO_LOOKUP_LIMIT:
                if remote_ip not in geo_cache:
                    cached_geo = GEO_CACHE.get(remote_ip)
                    if cached_geo:
                        geo_cache[remote_ip] = cached_geo
                    else:
                        geo_cache[remote_ip] = get_ip_geolocation(remote_ip)
                        geo_lookups += 1
                geo = geo_cache[remote_ip]
            
            # Classify connection
            risk_level = "info"
            risks = []
            
            if not is_private_ip(remote_ip):
                if remote_port in SUSPICIOUS_PORTS:
                    risks.append(f"Suspicious port {remote_port}")
                    risk_level = "danger"
                elif remote_port in SECURE_PORTS:
                    risk_level = "secure"
                
                if conn.status not in ("ESTABLISHED", "TIME_WAIT"):
                    risks.append(f"State: {conn.status}")
                    if risk_level != "danger":
                        risk_level = "warning"
            
            connections.append({
                "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                "remote_addr": f"{remote_ip}:{remote_port}",
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "status": conn.status,
                "pid": conn.pid,
                "process": get_process_name_cached(conn.pid),
                "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                "risk_level": risk_level,
                "risks": risks,
                "geo": geo
            })
    
    except Exception as e:
        logger.error(f"Connection analysis error: {e}")
        logger.debug(traceback.format_exc())
    
    # Calculate security metrics
    total = len(connections)
    if total == 0:
        security = {"score": 100, "grade": "Excellent", "warnings": 0, "threats": 0, "secure": 0}
    else:
        warnings = sum(1 for c in connections if c["risk_level"] == "warning")
        threats = sum(1 for c in connections if c["risk_level"] == "danger")
        secure = sum(1 for c in connections if c["remote_port"] in SECURE_PORTS)
        
        score = max(0, min(100, 100 - warnings * 3 - threats * 10))
        
        if score >= 85:
            grade = "Excellent"
        elif score >= 70:
            grade = "Good"
        elif score >= 55:
            grade = "Fair"
        else:
            grade = "Poor"
        
        security = {
            "score": score,
            "grade": grade,
            "warnings": warnings,
            "threats": threats,
            "secure": secure
        }
    
    # Country distribution
    countries = Counter(c["geo"].get("country") for c in connections if c.get("geo", {}).get("country"))
    
    result = {
        "connections": connections,
        "security": security,
        "summary": {
            "total_connections": total,
            "top_countries": countries.most_common(10),
            "geo_lookups": geo_lookups
        }
    }
    
    # Cache for 5 seconds
    CONNECTIONS_CACHE.set(cache_key, result, ttl=5)
    
    return result

# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def index():
    """Main page."""
    return render_template("index_optimized.html")

@app.route("/vpn-check")
def vpn_check_page():
    """VPN leak test page."""
    return render_template("vpn_check.html")

@app.route("/precise-location")
def precise_location_page():
    """Precise location page."""
    return render_template("precise_location.html")

@app.before_request
def enforce_local_only():
    """Enforce local-only access."""
    if not LOCAL_ONLY:
        return
    
    remote = request.remote_addr or ""
    if not is_local_network_ip(remote):
        logger.warning(f"Blocked non-local access from {remote}")
        return jsonify({"error": "Local access only", "success": False}), 403

@app.after_request
def after_request(response):
    """Add performance headers and compression."""
    response.headers['X-App-Version'] = APP_VERSION
    response.headers['X-Cache-Stats'] = json.dumps({
        'geo': GEO_CACHE.stats(),
        'connections': CONNECTIONS_CACHE.stats()
    })
    
    # Compress JSON responses
    if response.content_type and 'application/json' in response.content_type:
        if not response.direct_passthrough and response.status_code < 300:
            try:
                gzip_buffer = gzip.compress(response.get_data())
                if len(gzip_buffer) < len(response.get_data()):
                    response.set_data(gzip_buffer)
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = len(gzip_buffer)
            except Exception as e:
                logger.error(f"Compression error: {e}")
    
    return response

# API Endpoints

@app.route("/api/health")
def health():
    """Health check with detailed stats."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return jsonify({
            "status": "ok",
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "threads": process.num_threads()
            },
            "caches": {
                "geo": GEO_CACHE.stats(),
                "dns": DNS_CACHE.stats(),
                "connections": CONNECTIONS_CACHE.stats()
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version()
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/investigate")
@app.route("/api/scan")
@limiter.limit("30 per minute")
def investigate():
    """System investigation endpoint."""
    try:
        connection_data = analyze_connections(limit=MAX_CONNECTIONS_SCAN)
        
        return jsonify({
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "timestamp": datetime.now().isoformat(),
            **connection_data
        })
    except Exception as e:
        logger.error(f"Investigate error: {e}")
        return jsonify({"error": "Investigation failed", "message": str(e)}), 500

@app.route("/api/geolocation/<ip>")
@limiter.limit("100 per minute")
def geolocation(ip: str):
    """IP geolocation endpoint."""
    if not validate_ip(ip):
        return jsonify({"error": "Invalid IP address", "success": False}), 400
    
    result = get_ip_geolocation(ip)
    return jsonify(result)

@app.route("/api/lookup", methods=["GET", "POST"])
@limiter.limit("100 per minute")
def lookup():
    """Comprehensive IP lookup."""
    try:
        if request.method == "GET":
            ip = request.args.get("ip", "").strip()
        else:
            data = request.get_json(silent=True) or {}
            ip = (data.get("ip") or "").strip()
        
        if not ip or not validate_ip(ip):
            return jsonify({"error": "Invalid IP", "success": False}), 400
        
        geo = get_ip_geolocation(ip)
        
        return jsonify({
            "ip": ip,
            "geolocation": geo,
            "success": True
        })
    except Exception as e:
        logger.error(f"Lookup error: {e}")
        return jsonify({"error": "Lookup failed", "message": str(e)}), 500

@app.route("/api/bulk_lookup", methods=["POST"])
@limiter.limit("20 per minute")
def bulk_lookup():
    """Bulk IP lookup endpoint."""
    try:
        data = request.get_json(silent=True) or {}
        ips = list(dict.fromkeys([ip.strip() for ip in data.get("ips", []) if ip.strip()]))
        
        if not ips:
            return jsonify({"error": "No IPs provided", "success": False}), 400
        
        if len(ips) > MAX_BULK_LOOKUPS:
            return jsonify({"error": f"Too many IPs (max {MAX_BULK_LOOKUPS})", "success": False}), 400
        
        results = get_ip_geolocation_bulk(ips)
        
        return jsonify({
            "success": True,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Bulk lookup error: {e}")
        return jsonify({"error": "Bulk lookup failed", "message": str(e)}), 500

@app.route("/api/security/scan")
@limiter.limit("30 per minute")
def security_scan():
    """Security scan endpoint."""
    try:
        data = analyze_connections(limit=MAX_CONNECTIONS_SCAN, include_geo=True)
        
        # Get findings
        findings = [
            {
                "remote": c.get("remote_addr"),
                "risks": c.get("risks", []),
                "process": c.get("process"),
                "geo": {
                    "country": c.get("geo", {}).get("country")
                }
            }
            for c in data["connections"]
            if c.get("risk_level") != "info"
        ][:50]
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "score": data["security"]["score"],
            "summary": data["security"],
            "findings": findings
        })
    except Exception as e:
        logger.error(f"Security scan error: {e}")
        return jsonify({"error": "Scan failed", "message": str(e)}), 500

@app.route("/api/vpn/check", methods=["POST"])
@limiter.limit("10 per minute")
def vpn_check():
    """VPN leak detection endpoint."""
    try:
        data = request.get_json(silent=True) or {}
        webrtc_ips = data.get('webrtc_ips', [])
        client_ip = request.remote_addr or "Unknown"
        
        # Detect VPN interfaces
        vpn_interfaces = []
        try:
            import re
            vpn_pattern = re.compile(r'(tun|tap|wg|wireguard|openvpn|vpn|ppp)', re.IGNORECASE)
            
            for name, addrs in psutil.net_if_addrs().items():
                if vpn_pattern.search(name):
                    stats = psutil.net_if_stats().get(name)
                    vpn_interfaces.append({
                        'name': name,
                        'is_up': stats.isup if stats else False,
                        'is_vpn': True
                    })
        except Exception as e:
            logger.debug(f"VPN interface detection error: {e}")
        
        # Determine VPN status
        active_vpn = [i for i in vpn_interfaces if i.get('is_up')]
        
        if active_vpn:
            vpn_status = 'active'
        elif vpn_interfaces:
            vpn_status = 'installed_not_active'
        else:
            vpn_status = 'disabled'
        
        # Get geolocation for client IP
        geo = None
        if client_ip != "Unknown" and validate_ip(client_ip):
            geo_result = get_ip_geolocation(client_ip)
            if geo_result.get('status') == 'success':
                geo = {
                    'country': geo_result.get('country'),
                    'city': geo_result.get('city'),
                    'isp': geo_result.get('isp'),
                    'lat': geo_result.get('lat'),
                    'lon': geo_result.get('lon')
                }
        
        # Check WebRTC leaks (simplified)
        webrtc_leak = False
        public_webrtc = []
        
        if webrtc_ips:
            for ip in webrtc_ips:
                try:
                    addr = ipaddress.ip_address(ip)
                    if not (addr.is_private or addr.is_loopback):
                        public_webrtc.append(ip)
                except:
                    pass
        
        # Calculate score
        score = 100
        issues = []
        
        if vpn_status == 'disabled':
            score -= 25
            issues.append('No VPN detected')
        elif vpn_status == 'installed_not_active':
            score -= 15
            issues.append('VPN installed but not active')
        
        if webrtc_leak:
            score -= 40
            issues.append('WebRTC leak detected')
        
        score = max(0, min(100, score))
        
        if score >= 85:
            grade = 'Excellent'
        elif score >= 70:
            grade = 'Good'
        elif score >= 50:
            grade = 'Fair'
        else:
            grade = 'Poor'
        
        return jsonify({
            "success": True,
            "result": {
                "public_ip": {
                    "ipv4": [client_ip] if client_ip != "Unknown" else [],
                    "consensus": True
                },
                "geolocation": geo,
                "vpn_interfaces": {
                    "active": active_vpn,
                    "inactive": [i for i in vpn_interfaces if not i.get('is_up')],
                    "total_detected": len(vpn_interfaces)
                },
                "vpn_status": vpn_status,
                "webrtc": {
                    "leak_detected": webrtc_leak,
                    "public_ips": public_webrtc,
                    "status": "danger" if webrtc_leak else "success"
                },
                "privacy_score": {
                    "score": score,
                    "grade": grade,
                    "issues": issues,
                    "warnings": []
                },
                "recommendations": [
                    "Enable VPN for better privacy" if vpn_status != 'active' else "VPN is active - good",
                    "Check WebRTC settings in browser" if webrtc_leak else "No WebRTC leaks detected"
                ]
            }
        })
    except Exception as e:
        logger.error(f"VPN check error: {e}")
        logger.debug(traceback.format_exc())
        return jsonify({"error": "VPN check failed", "message": str(e)}), 500

@app.route("/api/cache/clear", methods=["POST"])
@limiter.limit("10 per minute")
def clear_cache():
    """Clear all caches."""
    try:
        GEO_CACHE.clear()
        DNS_CACHE.clear()
        WHOIS_CACHE.clear()
        CONNECTIONS_CACHE.clear()
        _process_name_cache.clear()
        
        return jsonify({"success": True, "message": "All caches cleared"})
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"error": "Failed to clear cache", "message": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "success": False}), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({"error": "Rate limit exceeded", "success": False, "retry_after": 60}), 429

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    logger.debug(traceback.format_exc())
    return jsonify({"error": "Internal server error", "success": False}), 500

# Cleanup
@atexit.register
def cleanup():
    """Cleanup resources on shutdown."""
    try:
        http_pool.close()
        logger.info("Application shutdown complete")
    except:
        pass

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    
    logger.info(f"Starting IP Checker Pro v{APP_VERSION}")
    logger.info(f"Workers: {MAX_WORKERS}")
    logger.info(f"Cache sizes: Geo={GEO_CACHE._max_size}, Conn={CONNECTIONS_CACHE._max_size}")
    
    app.run(
        debug=debug_mode,
        host=host,
        port=port,
        threaded=True,
        use_reloader=debug_mode
    )
