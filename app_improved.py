"""
IP Checker Application - Improved Version
Unified dashboard for deep PC investigation, IP geolocation/reverse lookup,
interactive mapping, and comprehensive reporting.

SECURITY IMPROVEMENTS:
- Added SECRET_KEY configuration
- Added IP validation
- Added rate limiting
- Added security headers
- Improved exception handling
- Fixed local access enforcement

BUG FIXES:
- Fixed classify_connection for private IPs
- Fixed aggregate_security KeyError
- Fixed create_map temp file cleanup
- Fixed cache for negative results
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

# Initialize Flask app
app = Flask(__name__)

# SECURITY FIX: Add SECRET_KEY from environment or generate random
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
app.config['JSON_SORT_KEYS'] = False

# SECURITY FIX: Add security headers with Flask-Talisman
# Note: force_https should be True in production
talisman = Talisman(
    app,
    force_https=False,  # Set to True in production
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://unpkg.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com"],
        'img-src': ["'self'", "data:", "https://*.tile.openstreetmap.org", "https://unpkg.com"],
        'connect-src': "'self'",
    }
)

# SECURITY FIX: Add rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

APP_VERSION = "2.0.1"  # Bumped version for improvements
GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))  # seconds
GEO_CACHE: Dict[str, tuple[float, dict]] = {}

GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
GEO_LOOKUP_LIMIT = int(os.environ.get('GEO_LOOKUP_LIMIT', 15))
SUSPICIOUS_PORTS = {23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389}
SECURE_PORTS = {22, 443, 993, 995, 5061}
LOCAL_ONLY = os.environ.get('LOCAL_ONLY', 'True').lower() == 'true'

# SECURITY FIX: Define local networks properly using ipaddress module
LOCAL_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('fc00::/7'),  # IPv6 unique local addresses
    ipaddress.ip_network('fe80::/10'),  # IPv6 link-local addresses
]

# Track temp files for cleanup
temp_files: List[str] = []


def cleanup_temp_files():
    """Cleanup temporary files on exit."""
    for f in temp_files:
        try:
            os.unlink(f)
            logger.debug(f"Cleaned up temp file: {f}")
        except OSError as e:
            logger.warning(f"Failed to cleanup temp file {f}: {e}")


atexit.register(cleanup_temp_files)


# SECURITY FIX: Add IP validation
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


def safe_process_name(pid: Optional[int]) -> str:
    """Safely get process name by PID."""
    if not pid:
        return "unknown"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        logger.debug(f"Could not get process name for PID {pid}: {e}")
        return "unknown"


# SECURITY FIX: Add retry logic for API calls
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
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def get(self, url: str, timeout: int = 5) -> requests.Response:
        return self.session.get(url, timeout=timeout)


# Initialize retryable session
retry_session = RetryableSession()


def get_ip_geolocation(ip_address: str) -> dict:
    """Get geolocation data for an IP address with caching."""
    # SECURITY FIX: Validate IP before processing
    if not validate_ip(ip_address):
        logger.warning(f"Invalid IP address attempted: {ip_address}")
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    now = time()
    cached = GEO_CACHE.get(ip_address)
    if cached and now - cached[0] < GEO_CACHE_TTL:
        logger.debug(f"Cache hit for IP: {ip_address}")
        return cached[1]
    
    logger.info(f"Fetching geolocation for IP: {ip_address}")
    
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
                GEO_CACHE[ip_address] = (now, data)
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
            GEO_CACHE[ip_address] = (now, result)
            logger.info(f"Successfully geolocated IP: {ip_address}")
            return result
        else:
            # BUG FIX: Cache negative results with shorter TTL
            result = {
                "ip": ip_address,
                "status": data.get("status", "fail"),
                "message": data.get("message", "Unknown error")
            }
            GEO_CACHE[ip_address] = (now - GEO_CACHE_TTL + 300, result)  # 5 min cache for failures
            logger.warning(f"Geolocation failed for {ip_address}: {result['message']}")
            return result
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": "Service temporarily unavailable"}
    except Exception as e:
        logger.error(f"Unexpected error geolocating {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": "Internal error"}


def reverse_dns_lookup(ip_address: str) -> dict:
    """Perform reverse DNS lookup."""
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    try:
        hostname = socket.gethostbyaddr(ip_address)
        logger.info(f"Reverse DNS successful for {ip_address}: {hostname[0]}")
        return {
            "ip": ip_address,
            "hostname": hostname[0],
            "aliases": hostname[1],
            "status": "success"
        }
    except socket.herror:
        logger.debug(f"Reverse DNS failed for {ip_address}: No PTR record")
        return {"ip": ip_address, "status": "error", "message": "No PTR record found"}
    except Exception as e:
        logger.error(f"Reverse DNS error for {ip_address}: {e}")
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


def geo_with_cache(ip: str, cache: Dict[str, dict]) -> dict:
    """Get geolocation with local cache."""
    if ip not in cache:
        cache[ip] = get_ip_geolocation(ip)
    return cache[ip]


# BUG FIX: Fixed classify_connection with proper private IP handling
def classify_connection(remote_port: int, status: str, geo: dict, remote_ip: str = None) -> tuple[str, List[str]]:
    """Classify connection risk level."""
    risks = []
    level = "info"
    
    # Skip private/loopback connections
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
        if level == "info":
            level = "warning"
    
    return level, risks


# BUG FIX: Fixed aggregate_security with .get() to prevent KeyError
def aggregate_security(connections: List[dict]) -> dict:
    """Aggregate security metrics from connections."""
    # Use .get() to prevent KeyError
    warnings = sum(1 for c in connections if c.get("risk_level") == "warning")
    threats = sum(1 for c in connections if c.get("risk_level") == "danger")
    total = len(connections)
    secure = sum(1 for c in connections if c.get("remote_port") in SECURE_PORTS)
    suspicious_ports = sum(1 for c in connections if c.get("remote_port") in SUSPICIOUS_PORTS)
    geo_fail = sum(1 for c in connections if c.get("geo", {}).get("status") not in (None, "success"))
    
    # Score calculation with clamped penalties
    score = 100
    score -= warnings * 4
    score -= threats * 10
    score -= min(suspicious_ports * 3, 20)
    score -= min(geo_fail, 10)
    if total and (secure / total) < 0.2:
        score -= 5
    score = max(0, min(100, score))
    
    if score >= 85:
        grade = "Excellent"
    elif score >= 70:
        grade = "Good"
    elif score >= 55:
        grade = "Fair"
    else:
        grade = "Poor"
    
    return {
        "warnings": warnings,
        "threats": threats,
        "secure": secure,
        "suspicious_ports": suspicious_ports,
        "geo_failures": geo_fail,
        "total_connections": total,
        "score": score,
        "grade": grade,
    }


def get_local_network_info(limit_connections: int = 200) -> dict:
    """Deep PC investigation: interfaces + active connections with geo and risk."""
    geo_cache: Dict[str, dict] = {}
    geo_lookups = 0
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "timestamp": datetime.now().isoformat(),
        "interfaces": [],
        "connections": [],
    }
    
    # Interfaces
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
            info["interfaces"].append(iface)
    except Exception as e:
        logger.error(f"Failed to get interface info: {e}")
        info["interface_error"] = "Failed to retrieve interface information"
    
    # Connections
    try:
        connections = psutil.net_connections(kind="inet")
        for conn in connections[:limit_connections]:
            if not conn.raddr:
                continue
            remote_ip, remote_port = conn.raddr
            
            if geo_lookups < GEO_LOOKUP_LIMIT:
                geo = geo_with_cache(remote_ip, geo_cache)
                geo_lookups += 1
            else:
                geo = {"status": "skipped"}
            
            risk_level, risks = classify_connection(remote_port, conn.status, geo, remote_ip)
            
            info["connections"].append({
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
        logger.error(f"Failed to get connections: {e}")
        info["connections_error"] = "Failed to retrieve connection information"
    
    # Summary
    geo_countries = Counter([c["geo"].get("country") for c in info["connections"] if c.get("geo", {}).get("country")])
    info["summary"] = {
        "total_connections": len(info["connections"]),
        "top_countries": geo_countries.most_common(5),
    }
    info["security"] = aggregate_security(info["connections"])
    
    logger.info(f"Network info collected: {info['summary']['total_connections']} connections")
    return info


# BUG FIX: Fixed create_map with proper temp file cleanup
def create_map(locations: List[dict], center: Optional[List[float]] = None) -> str:
    """Create a Folium map with markers; returns path to temp HTML."""
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
    
    # Create temp file and track for cleanup
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
    fmap.save(temp_file.name)
    temp_file.close()
    temp_files.append(temp_file.name)
    
    logger.debug(f"Created map with {len(locations)} markers")
    return temp_file.name


def build_report(include_system=True, include_connections=True, include_security=True, include_geolocation=True) -> dict:
    """Build comprehensive report."""
    info = get_local_network_info()
    report = {
        "title": "IP Checker Report",
        "generated_at": datetime.now().isoformat(),
        "summary": info.get("summary", {}),
    }
    
    if include_system:
        report["local_system"] = {
            "hostname": info.get("hostname"),
            "platform": info.get("platform"),
            "timestamp": info.get("timestamp"),
            "interfaces": info.get("interfaces", []),
        }
    
    if include_connections:
        report["connections"] = info.get("connections", [])
    
    if include_security:
        report["security"] = info.get("security", {})
    
    if include_geolocation:
        unique_ips = {}
        for c in info.get("connections", []):
            ip = c.get("remote_ip")
            geo = c.get("geo", {})
            if ip and geo and geo.get("status") == "success" and ip not in unique_ips:
                unique_ips[ip] = geo
        report["external_ips"] = list(unique_ips.values())
    
    return report


# Routes
@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")


# SECURITY FIX: Improved local access enforcement
@app.before_request
def enforce_local_only():
    """Allow requests only from local networks when LOCAL_ONLY is True."""
    if not LOCAL_ONLY:
        return
    
    # Only check remote_addr, ignore X-Forwarded-For (can be spoofed)
    remote = request.remote_addr or ""
    
    if not is_private_ip(remote):
        logger.warning(f"Blocked non-local access from: {remote}")
        return jsonify({"error": "Local access only", "success": False}), 403


@app.route("/api/investigate", methods=["GET"])
@app.route("/api/scan", methods=["GET"])
@limiter.limit("30 per minute")
def investigate():
    """Get local network information."""
    return jsonify(get_local_network_info())


@app.route("/api/geolocation/<ip>", methods=["GET"])
@limiter.limit("60 per minute")
def geolocation(ip: str):
    """Get geolocation for specific IP."""
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
    
    logger.info(f"Lookup requested for IP: {ip}")
    
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
    
    # Limit bulk lookup size
    if len(ips) > 50:
        return jsonify({"error": "Too many IPs (max 50)", "success": False}), 400
    
    logger.info(f"Bulk lookup for {len(ips)} IPs")
    
    lookups = []
    for ip in ips:
        if validate_ip(ip):
            lookups.append({
                "ip": ip,
                "geolocation": get_ip_geolocation(ip),
                "reverse_dns": reverse_dns_lookup(ip),
            })
    
    return jsonify({"success": True, "results": lookups})


@app.route("/api/map", methods=["POST"])
@limiter.limit("10 per minute")
def generate_map():
    """Generate map for IPs."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > 50:
        return jsonify({"error": "Too many IPs (max 50)", "success": False}), 400
    
    locations = []
    for ip in ips:
        if validate_ip(ip):
            geo = get_ip_geolocation(ip)
            if geo.get("status") == "success":
                locations.append(geo)
    
    if not locations:
        return jsonify({"error": "No valid locations found", "success": False}), 404
    
    # If Folium missing, return JSON to let frontend render with Leaflet.
    if not folium:
        return jsonify({"success": True, "locations": locations})
    
    try:
        map_file = create_map(locations)
        return send_file(map_file, mimetype="text/html")
    except Exception as e:
        logger.error(f"Map generation failed: {e}")
        return jsonify({"error": "Map generation failed", "success": False}), 500


@app.route("/api/report", methods=["GET"])
@limiter.limit("10 per minute")
def generate_report():
    """Generate report."""
    include_system = request.args.get("include_system", "true").lower() == "true"
    include_connections = request.args.get("include_connections", "true").lower() == "true"
    include_security = request.args.get("include_security", "true").lower() == "true"
    include_geolocation = request.args.get("include_geolocation", "true").lower() == "true"
    
    fmt = request.args.get("format", "json")
    
    try:
        report = build_report(include_system, include_connections, include_security, include_geolocation)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({"error": "Report generation failed", "success": False}), 500
    
    if fmt == "json":
        return jsonify(report)
    
    # Simple HTML fallback
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>IP Checker Report</title></head><body>",
        f"<h1>IP Checker Report</h1><p>Generated at {report['generated_at']}</p>",
        f"<h2>Summary</h2><pre>{json.dumps(report['summary'], indent=2)}</pre>",
    ]
    
    if include_system:
        html_parts.append(f"<h2>System</h2><pre>{json.dumps(report.get('local_system', {}), indent=2)}</pre>")
    if include_connections:
        html_parts.append(f"<h2>Connections</h2><pre>{json.dumps(report.get('connections', []), indent=2)}</pre>")
    if include_security:
        html_parts.append(f"<h2>Security</h2><pre>{json.dumps(report.get('security', {}), indent=2)}</pre>")
    if include_geolocation:
        html_parts.append(f"<h2>External IPs</h2><pre>{json.dumps(report.get('external_ips', []), indent=2)}</pre>")
    
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


@app.route("/api/myip")
@limiter.limit("30 per minute")
def myip():
    """Get client's public IP address."""
    public_ip = request.remote_addr or "Unknown"
    return jsonify({
        "ip": public_ip,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/my-ip")
@limiter.limit("30 per minute")
def my_ip_alias():
    """Alias for /api/myip."""
    return myip()


@app.route("/api/security/scan")
@limiter.limit("30 per minute")
def security_scan():
    """Perform a lightweight security scan based on active connections."""
    try:
        info = get_local_network_info()
        connections = info.get("connections", [])
        security = info.get("security", {})
        
        findings = []
        for conn in connections:
            if conn.get("risk_level") == "info":
                continue
            findings.append({
                "remote": conn.get("remote_addr"),
                "status": conn.get("status"),
                "risks": conn.get("risks", []),
                "process": conn.get("process"),
                "geo": {
                    "country": conn.get("geo", {}).get("country"),
                    "city": conn.get("geo", {}).get("city"),
                },
            })
        
        recommendations = []
        if security.get("threats", 0) > 0:
            recommendations.append("Terminate suspicious remote sessions and validate running processes.")
        if security.get("warnings", 0) > 2:
            recommendations.append("Review firewall rules to limit unexpected outbound connections.")
        if security.get("secure", 0) < 3:
            recommendations.append("Prefer secure protocols (HTTPS, SSH, IMAPS) where possible.")
        if not recommendations:
            recommendations.append("No critical issues detected. Maintain regular monitoring.")
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "score": security.get("score", 0),
            "summary": security,
            "findings": findings[:30],  # keep payload small
            "recommendations": recommendations,
        })
    except Exception as e:
        logger.error(f"Security scan failed: {e}")
        return jsonify({"error": "Security scan failed", "success": False}), 500


@app.route("/api/health")
def health():
    """Simple health check with cache stats."""
    try:
        cache_entries = len(GEO_CACHE)
    except Exception:
        cache_entries = 0
    
    return jsonify({
        "status": "ok",
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "geo_cache_entries": cache_entries,
        "ipapi_available": bool(ipapi),
        "whois_available": bool(whois_lib),
        "local_only": LOCAL_ONLY,
    })


# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({"error": "Rate limit exceeded", "success": False}), 429


@app.errorhandler(404)
def not_found_handler(e):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found", "success": False}), 404


@app.errorhandler(500)
def server_error_handler(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Internal server error", "success": False}), 500


if __name__ == "__main__":
    # SECURITY: Never use debug=True in production
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    logger.info(f"Starting IP Checker Pro v{APP_VERSION}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Local only: {LOCAL_ONLY}")
    
    app.run(debug=debug_mode, host=host, port=port)
