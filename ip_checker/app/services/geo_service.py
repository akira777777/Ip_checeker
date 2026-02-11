"""
Geolocation service.
Handles IP geolocation lookups, caching, and related functionality.
"""

import ipaddress
import logging
from time import time
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from diskcache import Cache
import os

# Optional imports
try:
    import ipapi
except ImportError:
    ipapi = None

try:
    import whois as whois_lib
except ImportError:
    whois_lib = None

# Configure logging
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DIR = os.environ.get('CACHE_DIR', './cache')
cache = Cache(CACHE_DIR, size_limit=int(1e9))  # 1GB limit

# Constants
GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))
GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"


class RetryableSession:
    """Session with retry logic."""
    
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def get(self, url: str, timeout: int = 5) -> requests.Response:
        return self.session.get(url, timeout=timeout)


retry_session = RetryableSession()


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


def get_ip_geolocation(ip_address: str) -> dict:
    """Get geolocation data for an IP address with caching."""
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}

    # Check cache first
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
                cache.set(f"geo_{ip_address}", data, expire=GEO_CACHE_TTL)
                return data
        except Exception as e:
            logger.warning(f"ipapi.co failed for {ip_address}: {e}")

    # Fallback to ip-api.com with retry logic
    try:
        resp = retry_session.get(GEO_API_URL.format(ip=ip_address), timeout=5)
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
        return result
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {ip_address}: {e}")
        error_result = {"ip": ip_address, "status": "error", "message": "Service temporarily unavailable"}
        cache.set(f"geo_{ip_address}", error_result, expire=300)
        return error_result


def get_whois_info(ip_address: str) -> dict:
    """Get WHOIS information."""
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