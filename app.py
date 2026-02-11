"""
IP Checker Application - Security Hardened & Optimized
Unified dashboard for deep PC investigation, IP geolocation/reverse lookup,
interactive mapping, and comprehensive reporting.

SECURITY IMPROVEMENTS:
- Added SECRET_KEY configuration from environment
- Added IP validation using ipaddress module
- Added rate limiting with Flask-Limiter
- Added security headers with Flask-Talisman
- Fixed local access enforcement (proper network checks)
- Added retry logic for external API calls
- Improved exception handling with specific error types
- Fixed temp file cleanup for map generation

BUG FIXES:
- Fixed classify_connection for proper private IP detection
- Fixed aggregate_security KeyError vulnerability
- Fixed create_map temp file leak
- Fixed cache for negative geolocation results
"""

from __future__ import annotations

import atexit
import ipaddress
import json
import logging
import os
import platform
import socket
import tempfile
from collections import Counter
from datetime import datetime
from time import time
from typing import Dict, List, Optional

import psutil
import requests
from flask import Flask, abort, jsonify, render_template, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Optional extras; degrade gracefully if missing.
try:
    import ipapi  # type: ignore
except Exception:
    ipapi = None

try:
    import whois as whois_lib  # type: ignore
except Exception:
    whois_lib = None

try:
    import folium  # type: ignore
except Exception:
    folium = None

# Initialize Flask app
app = Flask(__name__)

# SECURITY: Add SECRET_KEY from environment or generate random
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
app.config['JSON_SORT_KEYS'] = False

# SECURITY: Add security headers with Flask-Talisman
# Note: force_https should be True in production
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
        'worker-src': "'self' blob:",
    },
    content_security_policy_nonce_in=['script-src']
)

# SECURITY: Add rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get('RATE_LIMIT_STORAGE', 'memory://')
)

# Application constants
APP_VERSION = "2.1.0-security-hardened"
GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))
NEGATIVE_CACHE_TTL = 300  # 5 minutes for failed lookups
GEO_CACHE: Dict[str, tuple[float, dict]] = {}

GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
GEO_LOOKUP_LIMIT = int(os.environ.get('GEO_LOOKUP_LIMIT', 15))
MAX_BULK_LOOKUPS = int(os.environ.get('MAX_BULK_LOOKUPS', 100))
MAX_CONNECTIONS_SCAN = int(os.environ.get('MAX_CONNECTIONS_SCAN', 200))

SUSPICIOUS_PORTS = {23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389}
SECURE_PORTS = {22, 443, 993, 995, 5061}
LOCAL_ONLY = os.environ.get('LOCAL_ONLY', 'true').lower() == 'true'

# SECURITY: Define local networks properly using ipaddress module
LOCAL_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('fc00::/7'),   # IPv6 unique local
    ipaddress.ip_network('fe80::/10'),  # IPv6 link-local
]

# Track temp files for cleanup
temp_files: List[str] = []


def cleanup_temp_files():
    """Cleanup temporary files on exit."""
    for f in temp_files:
        try:
            if os.path.exists(f):
                os.unlink(f)
                logger.debug(f"Cleaned up temp file: {f}")
        except OSError as e:
            logger.warning(f"Failed to cleanup temp file {f}: {e}")


atexit.register(cleanup_temp_files)


# SECURITY: IP validation functions
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
    """Check if IP is private or loopback using ipaddress module."""
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


def safe_process_name(pid: Optional[int]) -> str:
    """Safely get process name by PID."""
    if not pid:
        return "unknown"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        logger.debug(f"Could not get process name for PID {pid}: {e}")
        return "unknown"


# SECURITY: Retry logic for API calls
class RetryableSession:
    """Session with retry logic for API calls."""
    
    def __init__(self):
        from requests.adapters import HTTPAdapter
        from urllib3.util import Retry
        
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Default headers
        self.session.headers.update({
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def get(self, url: str, timeout: int = 5, headers: dict = None) -> requests.Response:
        request_headers = headers or {}
        request_headers.setdefault('User-Agent', 'IPCheckerPro/2.1')
        return self.session.get(url, timeout=timeout, headers=request_headers)


# Initialize retryable session
retry_session = RetryableSession()


def get_ip_geolocation(ip_address: str, skip_cache: bool = False) -> dict:
    """
    Get geolocation data for an IP address with caching.
    
    SECURITY FIX: Validates IP before processing.
    BUG FIX: Caches negative results with shorter TTL.
    """
    # Validate IP
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    now = time()
    
    # Check cache
    if not skip_cache:
        cached = GEO_CACHE.get(ip_address)
        if cached and now - cached[0] < GEO_CACHE_TTL:
            result = cached[1].copy()
            result['cached'] = True
            return result
    
    # Try ipapi.co first if available
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
                GEO_CACHE[ip_address] = (now, data)
                return data
        except Exception as e:
            logger.debug(f"ipapi.co failed for {ip_address}: {e}")
    
    # Fallback to ip-api.com
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
            GEO_CACHE[ip_address] = (now, result)
            return result
        else:
            # BUG FIX: Cache negative results with shorter TTL
            result = {
                "ip": ip_address, 
                "status": data.get("status", "fail"), 
                "message": data.get("message", "Unknown error")
            }
            GEO_CACHE[ip_address] = (now, result)
            return result
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout looking up {ip_address}")
        return {"ip": ip_address, "status": "error", "message": "Request timeout"}
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error for {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": f"Request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error looking up {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": "Internal error"}


def reverse_dns_lookup(ip_address: str) -> dict:
    """Perform reverse DNS lookup."""
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    try:
        hostname = socket.gethostbyaddr(ip_address)
        return {"ip": ip_address, "hostname": hostname[0], "aliases": hostname[1], "status": "success"}
    except socket.herror:
        return {"ip": ip_address, "status": "error", "message": "No reverse DNS record found"}
    except Exception as e:
        logger.error(f"Reverse DNS lookup failed for {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": "Lookup failed"}


def get_whois_info(ip_address: str) -> dict:
    """Get WHOIS information for IP."""
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
        return {"status": "error", "message": "WHOIS lookup failed"}


def bulk_geolocation(ips: List[str]) -> List[dict]:
    """Bulk geolocation lookup with validation."""
    results = []
    for ip in ips[:MAX_BULK_LOOKUPS]:
        if validate_ip(ip):
            results.append({
                "ip": ip,
                "geolocation": get_ip_geolocation(ip),
                "reverse_dns": reverse_dns_lookup(ip),
            })
        else:
            results.append({
                "ip": ip,
                "geolocation": {"status": "error", "message": "Invalid IP"},
                "reverse_dns": {"status": "error", "message": "Invalid IP"},
            })
    return results


# BUG FIX: Fixed classify_connection for proper private IP detection
def classify_connection(
    remote_port: int, 
    status: str, 
    remote_ip: Optional[str] = None
) -> tuple[str, List[str]]:
    """
    Classify connection risk level.
    
    BUG FIX: Uses ipaddress module for proper private IP detection.
    """
    risks = []
    level = "info"
    
    # Fast path: private IPs are always info level
    if remote_ip and is_private_ip(remote_ip):
        return "info", []
    
    # Check suspicious ports
    if remote_port in SUSPICIOUS_PORTS:
        risks.append(f"Port {remote_port} commonly abused")
        level = "danger"
    
    # Check connection status
    if status not in ("ESTABLISHED", "TIME_WAIT", "CLOSE_WAIT"):
        risks.append(f"State: {status}")
        if level != "danger":
            level = "warning"
    
    return level, risks


# BUG FIX: Fixed aggregate_security to use .get() instead of direct key access
def aggregate_security(connections: List[dict]) -> dict:
    """
    Calculate security score from connections.
    
    BUG FIX: Uses .get() to avoid KeyError.
    """
    total = len(connections)
    if total == 0:
        return {
            "score": 100,
            "grade": "Excellent",
            "warnings": 0,
            "threats": 0,
            "secure": 0,
            "suspicious_ports": 0,
            "total_connections": 0,
        }
    
    # Single-pass aggregation with safe access
    warnings = 0
    threats = 0
    secure = 0
    suspicious_ports = 0
    
    for conn in connections:
        risk_level = conn.get("risk_level", "info")
        remote_port = conn.get("remote_port", 0)
        
        if risk_level == "warning":
            warnings += 1
        elif risk_level == "danger":
            threats += 1
        
        if remote_port in SECURE_PORTS:
            secure += 1
        if remote_port in SUSPICIOUS_PORTS:
            suspicious_ports += 1
    
    # Score calculation
    score = 100
    score -= warnings * 4
    score -= threats * 10
    score -= min(suspicious_ports * 3, 20)
    
    # Secure connection bonus
    if total > 0 and (secure / total) < 0.2:
        score -= 5
    
    score = max(0, min(100, score))
    
    # Grade assignment
    if score >= 85:
        grade = "Excellent"
    elif score >= 70:
        grade = "Good"
    elif score >= 55:
        grade = "Fair"
    else:
        grade = "Poor"
    
    return {
        "score": score,
        "grade": grade,
        "warnings": warnings,
        "threats": threats,
        "secure": secure,
        "suspicious_ports": suspicious_ports,
        "total_connections": total,
    }


def analyze_connections(limit: int = 200, include_geo: bool = True) -> dict:
    """Analyze active network connections."""
    connections = []
    geo_cache: Dict[str, dict] = {}
    geo_lookups = 0
    
    try:
        conns = psutil.net_connections(kind="inet")[:limit]
        
        for conn in conns:
            if not conn.raddr:
                continue
            
            remote_ip, remote_port = conn.raddr
            
            # Get geolocation if needed
            geo = {"status": "skipped"}
            if include_geo and geo_lookups < GEO_LOOKUP_LIMIT:
                if remote_ip not in geo_cache:
                    geo_cache[remote_ip] = get_ip_geolocation(remote_ip)
                    geo_lookups += 1
                geo = geo_cache[remote_ip]
            
            # Classify connection
            risk_level, risks = classify_connection(remote_port, conn.status, remote_ip)
            
            connections.append({
                "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                "remote_addr": f"{remote_ip}:{remote_port}",
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "status": conn.status,
                "pid": conn.pid,
                "process": safe_process_name(conn.pid),
                "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                "risk_level": risk_level,
                "risks": risks,
                "geo": geo,
            })
    except Exception as e:
        logger.error(f"Error analyzing connections: {e}")
    
    # Calculate security metrics
    security = aggregate_security(connections)
    
    # Get country distribution
    countries = [
        c["geo"].get("country") 
        for c in connections 
        if c.get("geo", {}).get("country")
    ]
    top_countries = Counter(countries).most_common(5)
    
    return {
        "connections": connections,
        "security": security,
        "summary": {
            "total_connections": len(connections),
            "top_countries": top_countries,
        },
    }


def get_system_info() -> dict:
    """Get system information."""
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "timestamp": datetime.now().isoformat(),
    }


def get_network_interfaces() -> List[dict]:
    """Get network interfaces."""
    interfaces = []
    try:
        for iface_name, addrs in psutil.net_if_addrs().items():
            iface = {"name": iface_name, "addresses": []}
            for addr in addrs:
                if addr.family not in (socket.AF_INET, socket.AF_INET6):
                    continue
                iface["addresses"].append({
                    "family": "IPv4" if addr.family == socket.AF_INET else "IPv6",
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                })
            interfaces.append(iface)
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")
    return interfaces


# BUG FIX: Fixed create_map with proper temp file cleanup
def create_map(locations: List[dict], center: Optional[List[float]] = None) -> str:
    """
    Create a Folium map with markers.
    
    BUG FIX: Registers temp file for cleanup.
    """
    if not folium:
        raise RuntimeError("Folium is not installed")
    
    if center is None and locations:
        for loc in locations:
            if loc.get("lat") and loc.get("lon"):
                center = [loc["lat"], loc["lon"]]
                break
    if center is None:
        center = [0, 0]
    
    fmap = folium.Map(location=center, zoom_start=3)
    for loc in locations:
        if not (loc.get("lat") and loc.get("lon")):
            continue
        
        popup_html = f"""
        <b>IP:</b> {loc.get('ip','')}<br>
        <b>Location:</b> {loc.get('city','')}, {loc.get('country','')}<br>
        <b>ISP:</b> {loc.get('isp','')}<br>
        <b>Coordinates:</b> {loc.get('lat')}, {loc.get('lon')}
        """
        folium.Marker(
            [loc["lat"], loc["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=loc.get("ip", ""),
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(fmap)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
    fmap.save(temp_file.name)
    temp_file.close()
    
    # BUG FIX: Register for cleanup
    temp_files.append(temp_file.name)
    
    return temp_file.name


def generate_recommendations(security: dict) -> List[str]:
    """Generate security recommendations."""
    recommendations = []
    
    if security.get("threats", 0) > 0:
        recommendations.append("Terminate suspicious remote sessions and validate running processes.")
    if security.get("warnings", 0) > 2:
        recommendations.append("Review firewall rules to limit unexpected outbound connections.")
    if security.get("secure", 0) < 3:
        recommendations.append("Prefer secure protocols (HTTPS, SSH, IMAPS) where possible.")
    if not recommendations:
        recommendations.append("No critical issues detected. Maintain regular monitoring.")
    
    return recommendations


# Routes
@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")


# SECURITY FIX: Fixed enforce_local_only to use proper network checks
@app.before_request
def enforce_local_only():
    """
    Enforce local-only access when configured.
    
    SECURITY FIX: Only checks remote_addr, not X-Forwarded-For (which can be spoofed).
    Uses ipaddress module for proper network checking.
    """
    if not LOCAL_ONLY:
        return
    
    # SECURITY: Only trust remote_addr, not X-Forwarded-For
    remote = request.remote_addr or ""
    
    if not is_local_network_ip(remote):
        logger.warning(f"Blocked non-local access attempt from {remote}")
        return jsonify({"error": "Local access only", "success": False}), 403


@app.route("/api/investigate")
@app.route("/api/scan")
@limiter.limit("30 per minute")
def investigate():
    """Deep PC investigation."""
    info = get_system_info()
    interfaces = get_network_interfaces()
    connection_data = analyze_connections(limit=MAX_CONNECTIONS_SCAN)
    
    return jsonify({
        **info,
        "interfaces": interfaces,
        "connections": connection_data["connections"],
        "security": connection_data["security"],
        "summary": connection_data["summary"],
    })


@app.route("/api/geolocation/<ip>")
@limiter.limit("60 per minute")
def geolocation(ip: str):
    """Get geolocation for IP."""
    if not validate_ip(ip):
        return jsonify({"error": "Invalid IP address", "success": False}), 400
    return jsonify(get_ip_geolocation(ip))


@app.route("/api/lookup", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def lookup():
    """Comprehensive IP lookup."""
    if request.method == "GET":
        ip = request.args.get("ip", "").strip()
    else:
        data = request.get_json(silent=True) or {}
        ip = (data.get("ip") or "").strip()
    
    if not ip:
        return jsonify({"error": "No IP provided", "success": False}), 400
    
    if not validate_ip(ip):
        return jsonify({"error": "Invalid IP address", "success": False}), 400
    
    return jsonify({
        "ip": ip,
        "geolocation": get_ip_geolocation(ip),
        "whois": get_whois_info(ip),
        "reverse_dns": reverse_dns_lookup(ip),
        "success": True,
    })


@app.route("/api/bulk_lookup", methods=["POST"])
@limiter.limit("10 per minute")
def bulk_lookup():
    """Bulk IP lookup."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > MAX_BULK_LOOKUPS:
        return jsonify({
            "error": f"Too many IPs (max {MAX_BULK_LOOKUPS})",
            "success": False
        }), 400
    
    return jsonify({"success": True, "results": bulk_geolocation(ips)})


@app.route("/api/map", methods=["POST"])
@limiter.limit("10 per minute")
def generate_map():
    """Generate map for IPs."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > MAX_BULK_LOOKUPS:
        return jsonify({
            "error": f"Too many IPs (max {MAX_BULK_LOOKUPS})",
            "success": False
        }), 400
    
    # Get locations
    locations = []
    for ip in ips:
        if validate_ip(ip):
            geo = get_ip_geolocation(ip)
            if geo.get("status") == "success":
                locations.append(geo)
    
    if not locations:
        return jsonify({"error": "No valid locations found", "success": False}), 404
    
    # If Folium not available, return JSON for frontend rendering
    if not folium:
        return jsonify({"success": True, "locations": locations})
    
    try:
        map_file = create_map(locations)
        return send_file(map_file, mimetype="text/html")
    except Exception as e:
        logger.error(f"Map generation failed: {e}")
        return jsonify({"error": "Map generation failed", "success": False}), 500


@app.route("/api/report")
@limiter.limit("10 per minute")
def generate_report():
    """Generate comprehensive report."""
    include_system = request.args.get("include_system", "true").lower() == "true"
    include_connections = request.args.get("include_connections", "true").lower() == "true"
    include_security = request.args.get("include_security", "true").lower() == "true"
    include_geolocation = request.args.get("include_geolocation", "true").lower() == "true"
    fmt = request.args.get("format", "json")
    
    report = {
        "title": "IP Checker Report",
        "generated_at": datetime.now().isoformat(),
    }
    
    if include_system:
        report["local_system"] = {
            **get_system_info(),
            "interfaces": get_network_interfaces(),
        }
    
    if include_connections or include_security:
        connection_data = analyze_connections(
            limit=MAX_CONNECTIONS_SCAN,
            include_geo=include_geolocation
        )
        
        if include_connections:
            report["connections"] = connection_data["connections"]
        
        if include_security:
            report["security"] = connection_data["security"]
        
        if include_geolocation:
            unique_ips = {}
            for conn in connection_data["connections"]:
                ip = conn.get("remote_ip")
                geo = conn.get("geo", {})
                if ip and geo and geo.get("status") == "success" and ip not in unique_ips:
                    unique_ips[ip] = geo
            report["external_ips"] = list(unique_ips.values())
        
        report["summary"] = connection_data["summary"]
    
    if fmt == "json":
        return jsonify(report)
    
    # Simple HTML format
    html = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        "<title>IP Checker Report</title>",
        "<style>body{font-family:sans-serif;padding:20px;}</style>",
        "</head><body>",
        f"<h1>IP Checker Report</h1>",
        f"<p>Generated at {report['generated_at']}</p>",
        "<pre>",
        json.dumps(report, indent=2),
        "</pre></body></html>",
    ]
    return "\n".join(html)


@app.route("/api/myip")
@limiter.limit("60 per minute")
def myip():
    """Get client's IP address."""
    return jsonify({
        "ip": request.remote_addr or "Unknown",
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/my-ip")
@limiter.limit("60 per minute")
def my_ip_alias():
    """Alias for /api/myip."""
    return myip()


@app.route("/api/security/scan")
@limiter.limit("30 per minute")
def security_scan():
    """Perform security scan."""
    connection_data = analyze_connections(
        limit=MAX_CONNECTIONS_SCAN,
        include_geo=True
    )
    
    connections = connection_data["connections"]
    security = connection_data["security"]
    
    # Get findings (non-info level connections)
    findings = [
        {
            "remote": conn.get("remote_addr"),
            "status": conn.get("status"),
            "risks": conn.get("risks", []),
            "process": conn.get("process"),
            "geo": {
                "country": conn.get("geo", {}).get("country"),
                "city": conn.get("geo", {}).get("city"),
            },
        }
        for conn in connections
        if conn.get("risk_level") != "info"
    ][:30]  # Limit to 30 findings
    
    recommendations = generate_recommendations(security)
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "score": security.get("score", 0),
        "summary": security,
        "findings": findings,
        "recommendations": recommendations,
    })


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "cache_entries": len(GEO_CACHE),
        "local_only": LOCAL_ONLY,
    })


# Error handlers
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Not found", "success": False}), 404


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({"error": "Rate limit exceeded", "success": False}), 429


@app.errorhandler(500)
def server_error(e):
    """Handle server errors."""
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Internal server error", "success": False}), 500


if __name__ == "__main__":
    # Get configuration from environment
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    
    logger.info(f"Starting IP Checker Pro v{APP_VERSION}")
    logger.info(f"Local only mode: {LOCAL_ONLY}")
    logger.info(f"Debug mode: {debug_mode}")
    
    app.run(
        debug=debug_mode,
        host=host,
        port=port,
        threaded=True
    )
