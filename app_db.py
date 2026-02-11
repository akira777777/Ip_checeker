"""
IP Checker Application with PostgreSQL Database Integration
Enhanced version with hybrid caching (database + diskcache) and improved performance.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import tempfile
import logging
import ipaddress
from collections import Counter, defaultdict
from datetime import datetime
from time import time
from typing import Dict, List, Optional
import atexit

import psutil
import requests
from flask import Flask, abort, jsonify, render_template, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from diskcache import Cache

# Try to import database support
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import QueuePool
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Optional extras; degrade gracefully if missing.
try:  # pragma: no cover - optional dependency
    import ipapi  # type: ignore
except Exception:  # noqa: BLE001
    ipapi = None

try:  # pragma: no cover - optional dependency
    import whois as whois_lib  # type: ignore
except Exception:  # noqa: BLE001
    whois_lib = None

try:  # pragma: no cover - optional dependency
    import folium  # type: ignore
except Exception:  # noqa: BLE001
    folium = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application configuration
app = Flask(__name__)
app.config.update(
    JSON_SORT_KEYS=False,
    SECRET_KEY=os.environ.get('SECRET_KEY') or os.urandom(32)
)

# Security configuration
Talisman(app, force_https=False)  # Set to True for production

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Cache configuration
CACHE_DIR = os.environ.get('CACHE_DIR', './cache')
cache = Cache(CACHE_DIR, size_limit=int(1e9))  # 1GB limit
atexit.register(cache.close)

# Database configuration (optional)
DATABASE_URL = os.environ.get('DATABASE_URL')
db_engine = None
if DATABASE_AVAILABLE and DATABASE_URL:
    try:
        db_engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        # Test connection
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
        db_engine = None

APP_VERSION = "2.2.0"  # Updated version
GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))  # seconds
GEO_LOOKUP_LIMIT = int(os.environ.get('GEO_LOOKUP_LIMIT', 15))
SUSPICIOUS_PORTS = {23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389}
SECURE_PORTS = {22, 443, 993, 995, 5061}
LOCAL_ONLY = os.environ.get('LOCAL_ONLY', 'True').lower() == 'true'

# Trusted networks for local access
LOCAL_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
]

# Temporary files tracking for cleanup
temp_files = []


def cleanup_temp_files():
    """Clean up temporary files on exit."""
    for f in temp_files:
        try:
            os.unlink(f)
        except OSError:
            pass


atexit.register(cleanup_temp_files)


def is_local_ip(ip: str) -> bool:
    """Check if IP is from local/trusted network."""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return any(addr in network for network in LOCAL_NETWORKS)
    except ValueError:
        return False


def validate_ip(ip: str) -> bool:
    """Validate IP address format."""
    if not ip or not isinstance(ip, str):
        return False
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False


def is_private_ip(ip: str) -> bool:
    """Check if IP is private or loopback."""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def safe_process_name(pid: Optional[int]) -> str:
    if not pid:
        return "unknown"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "unknown"


def db_save_geolocation(ip_address: str, geo_data: dict) -> bool:
    """Save geolocation data to database."""
    if not db_engine:
        return False
    
    try:
        with db_engine.connect() as conn:
            # Check if record exists
            result = conn.execute(
                text("SELECT id FROM geolocations WHERE ip_address = :ip"),
                {"ip": ip_address}
            ).fetchone()
            
            if result:
                # Update existing record
                conn.execute(
                    text("""
                        UPDATE geolocations 
                        SET city = :city, region = :region, country = :country,
                            country_code = :country_code, latitude = :lat, longitude = :lon,
                            timezone = :timezone, isp = :isp, asn = :asn, org = :org,
                            status = :status, updated_at = NOW(), lookup_count = lookup_count + 1
                        WHERE ip_address = :ip
                    """),
                    {
                        "ip": ip_address,
                        "city": geo_data.get('city'),
                        "region": geo_data.get('region'),
                        "country": geo_data.get('country'),
                        "country_code": geo_data.get('country_code'),
                        "lat": geo_data.get('lat'),
                        "lon": geo_data.get('lon'),
                        "timezone": geo_data.get('timezone'),
                        "isp": geo_data.get('isp'),
                        "asn": geo_data.get('asn'),
                        "org": geo_data.get('org'),
                        "status": geo_data.get('status', 'success')
                    }
                )
            else:
                # Insert new record
                conn.execute(
                    text("""
                        INSERT INTO geolocations 
                        (ip_address, city, region, country, country_code, latitude, longitude,
                         timezone, isp, asn, org, status, created_at, updated_at, lookup_count)
                        VALUES 
                        (:ip, :city, :region, :country, :country_code, :lat, :lon,
                         :timezone, :isp, :asn, :org, :status, NOW(), NOW(), 1)
                    """),
                    {
                        "ip": ip_address,
                        "city": geo_data.get('city'),
                        "region": geo_data.get('region'),
                        "country": geo_data.get('country'),
                        "country_code": geo_data.get('country_code'),
                        "lat": geo_data.get('lat'),
                        "lon": geo_data.get('lon'),
                        "timezone": geo_data.get('timezone'),
                        "isp": geo_data.get('isp'),
                        "asn": geo_data.get('asn'),
                        "org": geo_data.get('org'),
                        "status": geo_data.get('status', 'success')
                    }
                )
            conn.commit()
        return True
    except Exception as e:
        logger.warning(f"Failed to save geolocation to database: {e}")
        return False


def db_get_geolocation(ip_address: str) -> Optional[dict]:
    """Get geolocation data from database."""
    if not db_engine:
        return None
    
    try:
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT city, region, country, country_code, latitude, longitude,
                           timezone, isp, asn, org, status, updated_at
                    FROM geolocations 
                    WHERE ip_address = :ip
                """),
                {"ip": ip_address}
            ).fetchone()
            
            if result:
                # Check if expired (1 hour default)
                updated_at = result.updated_at
                if updated_at and (datetime.utcnow() - updated_at).total_seconds() > GEO_CACHE_TTL:
                    return None
                
                return {
                    "ip": ip_address,
                    "city": result.city,
                    "region": result.region,
                    "country": result.country,
                    "country_code": result.country_code,
                    "lat": result.latitude,
                    "lon": result.longitude,
                    "timezone": result.timezone,
                    "isp": result.isp,
                    "asn": result.asn,
                    "org": result.org,
                    "status": result.status,
                    "cached": True
                }
    except Exception as e:
        logger.warning(f"Failed to get geolocation from database: {e}")
    
    return None


def get_ip_geolocation(ip_address: str) -> dict:
    """Get geolocation data for an IP address with hybrid caching."""
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}

    # Try database cache first
    db_result = db_get_geolocation(ip_address)
    if db_result:
        return db_result

    # Try disk cache
    cached = cache.get(f"geo_{ip_address}")
    if cached:
        return cached

    # First try ipapi.co if installed.
    if ipapi:
        try:
            location = ipapi.location(ip_address)
            if location and "error" not in location:
                data = {
                    "ip": ip_address,
                    "city": location.get("city"),
                    "region": location.get("region"),
                    "country": location.get("country_name") or location.get("country"),
                    "country_code": location.get("country_code"),
                    "lat": location.get("latitude"),
                    "lon": location.get("longitude"),
                    "timezone": location.get("timezone"),
                    "isp": location.get("org"),
                    "asn": location.get("asn"),
                    "status": "success",
                }
                # Save to both caches
                cache.set(f"geo_{ip_address}", data, expire=GEO_CACHE_TTL)
                db_save_geolocation(ip_address, data)
                return data
        except Exception as e:
            logger.warning(f"ipapi.co failed for {ip_address}: {e}")

    # Fallback to ip-api.com with retry logic
    GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    
    try:
        # Session with retry strategy
        session = requests.Session()
        from requests.adapters import HTTPAdapter
        from urllib3.util import Retry
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        
        resp = session.get(GEO_API_URL.format(ip=ip_address), timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "success":
            result = {
                "ip": ip_address,
                "city": data.get("city"),
                "region": data.get("regionName"),
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "asn": data.get("as"),
                "org": data.get("org"),
                "status": "success",
            }
        else:
            result = {
                "ip": ip_address,
                "status": data.get("status", "fail"),
                "message": data.get("message", "Unknown error")
            }
        
        # Cache with different TTL for success vs failure
        cache_ttl = GEO_CACHE_TTL if result["status"] == "success" else 300
        cache.set(f"geo_{ip_address}", result, expire=cache_ttl)
        if result["status"] == "success":
            db_save_geolocation(ip_address, result)
        return result
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {ip_address}: {e}")
        error_result = {"ip": ip_address, "status": "error", "message": "Service temporarily unavailable"}
        cache.set(f"geo_{ip_address}", error_result, expire=300)
        return error_result


# ... (rest of the functions remain the same as in app_secure.py)
# I'll include the key modified parts below:

def reverse_dns_lookup(ip_address: str) -> dict:
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    try:
        hostname = socket.gethostbyaddr(ip_address)
        return {"ip": ip_address, "hostname": hostname[0], "aliases": hostname[1], "status": "success"}
    except Exception as e:
        logger.warning(f"Reverse DNS lookup failed for {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": str(e)}


def get_whois_info(ip_address: str) -> dict:
    if not validate_ip(ip_address):
        return {"status": "error", "message": "Invalid IP address"}
        
    if not whois_lib:
        return {"status": "unavailable", "message": "python-whois not installed"}
    try:
        w = whois_lib.whois(ip_address)
        return {
            "status": "success",
            "domain": w.domain_name,
            "registrar": w.registrar,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "name_servers": w.name_servers,
            "status_raw": w.status,
        }
    except Exception as e:
        logger.warning(f"WHOIS lookup failed for {ip_address}: {e}")
        return {"status": "error", "message": str(e)}


def classify_connection(remote_port: int, status: str, geo: dict, remote_ip: str = None) -> tuple[str, List[str]]:
    risks = []
    level = "info"
    
    # Skip localhost/loopback connections - these are normal
    if remote_ip and is_private_ip(remote_ip):
        return "info", []
    
    if remote_port in SUSPICIOUS_PORTS:
        risks.append(f"Remote port {remote_port} is commonly abused")
        level = "danger"
    if status not in ("ESTABLISHED", "TIME_WAIT"):
        risks.append(f"State {status}")
        level = "warning" if level != "danger" else level
    if geo.get("status") not in (None, "success"):
        risks.append("Geolocation lookup failed")
    return level, risks


# ... (remaining functions are identical to app_secure.py)

@app.route("/api/health")
def health():
    """Enhanced health check with database status."""
    try:
        cache_entries = len(list(cache.iterkeys()))
    except Exception:
        cache_entries = 0
    
    db_status = "unavailable"
    if db_engine:
        try:
            with db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                db_status = "connected"
        except Exception:
            db_status = "disconnected"
    
    return jsonify(
        {
            "status": "ok",
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
            "platform": platform.platform(),
            "cache_entries": cache_entries,
            "ipapi_available": bool(ipapi),
            "whois_available": bool(whois_lib),
            "local_only": LOCAL_ONLY,
            "database": {
                "available": DATABASE_AVAILABLE,
                "status": db_status,
                "url_configured": bool(DATABASE_URL)
            }
        }
    )


# Database initialization endpoint
@app.route("/api/db/init")
def init_database():
    """Initialize database tables."""
    if not DATABASE_AVAILABLE or not DATABASE_URL:
        return jsonify({"error": "Database not configured", "success": False}), 400
    
    try:
        with db_engine.connect() as conn:
            # Create geolocations table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS geolocations (
                    id SERIAL PRIMARY KEY,
                    ip_address VARCHAR(45) UNIQUE NOT NULL,
                    city VARCHAR(100),
                    region VARCHAR(100),
                    country VARCHAR(100),
                    country_code VARCHAR(10),
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    timezone VARCHAR(50),
                    isp VARCHAR(200),
                    asn VARCHAR(50),
                    org VARCHAR(200),
                    status VARCHAR(20) DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    lookup_count INTEGER DEFAULT 1
                )
            """))
            
            # Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geolocation_ip ON geolocations(ip_address)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geolocation_country ON geolocations(country)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_geolocation_created ON geolocations(created_at)"))
            
            conn.commit()
        
        return jsonify({"success": True, "message": "Database tables created"})
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


# Include all other routes from app_secure.py...
# (The remaining route definitions would be identical to app_secure.py)

if __name__ == "__main__":
    # Create cache directory if it doesn't exist
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Initialize database tables if configured
    if DATABASE_AVAILABLE and DATABASE_URL and db_engine:
        try:
            init_database()
        except Exception as e:
            logger.warning(f"Could not initialize database tables: {e}")
    
    app.run(debug=False, host="127.0.0.1", port=5000)