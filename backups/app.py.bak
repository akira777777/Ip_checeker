"""
IP Checker Application
Unified dashboard for deep PC investigation, IP geolocation/reverse lookup,
interactive mapping, and comprehensive reporting.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from time import time
from typing import Dict, List, Optional

import psutil
import requests
from flask import Flask, abort, jsonify, render_template, request, send_file

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


app = Flask(__name__)
app.config.update(JSON_SORT_KEYS=False)

APP_VERSION = "2.0.0"
GEO_CACHE_TTL = 3600  # seconds
GEO_CACHE: Dict[str, tuple[float, dict]] = {}

GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
GEO_LOOKUP_LIMIT = 15
SUSPICIOUS_PORTS = {23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389}
SECURE_PORTS = {22, 443, 993, 995, 5061}
LOCAL_ONLY = True
LOCAL_ADDRS = {"127.0.0.1", "::1"}


def safe_process_name(pid: Optional[int]) -> str:
    if not pid:
        return "unknown"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "unknown"


def get_ip_geolocation(ip_address: str) -> dict:
    """Get geolocation data for an IP address."""
    now = time()
    cached = GEO_CACHE.get(ip_address)
    if cached and now - cached[0] < GEO_CACHE_TTL:
        return cached[1]

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
        except Exception:  # noqa: BLE001
            pass

    # Fallback to ip-api.com
    try:
        resp = requests.get(GEO_API_URL.format(ip=ip_address), timeout=2)
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
        return {"ip": ip_address, "status": data.get("status", "fail"), "message": data.get("message")}
    except Exception as exc:  # noqa: BLE001
        return {"ip": ip_address, "status": "error", "message": str(exc)}


def reverse_dns_lookup(ip_address: str) -> dict:
    try:
        hostname = socket.gethostbyaddr(ip_address)
        return {"ip": ip_address, "hostname": hostname[0], "aliases": hostname[1], "status": "success"}
    except Exception as exc:  # noqa: BLE001
        return {"ip": ip_address, "status": "error", "message": str(exc)}


def get_whois_info(ip_address: str) -> dict:
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
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}


def geo_with_cache(ip: str, cache: Dict[str, dict]) -> dict:
    if ip not in cache:
        cache[ip] = get_ip_geolocation(ip)
    return cache[ip]


def classify_connection(remote_port: int, status: str, geo: dict, remote_ip: str = None) -> tuple[str, List[str]]:
    risks = []
    level = "info"
    
    # Skip localhost/loopback connections - these are normal
    if remote_ip and (remote_ip.startswith("127.") or remote_ip == "::1"):
        return "info", []
    # Private LAN ranges are low risk
    if remote_ip and (
        remote_ip.startswith("10.")
        or remote_ip.startswith("192.168.")
        or remote_ip.startswith("172.") and 16 <= int(remote_ip.split(".")[1]) <= 31
    ):
        level = "info"
    
    if remote_port in SUSPICIOUS_PORTS:
        risks.append(f"Remote port {remote_port} is commonly abused")
        level = "danger"
    if status not in ("ESTABLISHED", "TIME_WAIT"):
        risks.append(f"State {status}")
        level = "warning" if level != "danger" else level
    if geo.get("status") not in (None, "success"):
        risks.append("Geolocation lookup failed")
    return level, risks


def aggregate_security(connections: List[dict]) -> dict:
    warnings = sum(1 for c in connections if c["risk_level"] == "warning")
    threats = sum(1 for c in connections if c["risk_level"] == "danger")
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
                iface["addresses"].append(
                    {
                        "family": "IPv4" if addr.family == socket.AF_INET else "IPv6",
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                    }
                )
            info["interfaces"].append(iface)
    except Exception as exc:  # noqa: BLE001
        info["interface_error"] = str(exc)

    # Connections
    try:
        for conn in psutil.net_connections(kind="inet")[:limit_connections]:
            if not conn.raddr:
                continue
            remote_ip, remote_port = conn.raddr
            if geo_lookups < GEO_LOOKUP_LIMIT:
                geo = geo_with_cache(remote_ip, geo_cache)
                geo_lookups += 1
            else:
                geo = {"status": "skipped"}
            risk_level, risks = classify_connection(remote_port, conn.status, geo, remote_ip)
            info["connections"].append(
                {
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
                }
            )
    except Exception as exc:  # noqa: BLE001
        info["connections_error"] = str(exc)

    # Summary
    geo_countries = Counter([c["geo"].get("country") for c in info["connections"] if c.get("geo", {}).get("country")])
    info["summary"] = {
        "total_connections": len(info["connections"]),
        "top_countries": geo_countries.most_common(5),
    }
    info["security"] = aggregate_security(info["connections"])
    return info


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

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
    fmap.save(temp_file.name)
    temp_file.close()
    return temp_file.name


def build_report(include_system=True, include_connections=True, include_security=True, include_geolocation=True) -> dict:
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


@app.route("/")
def index():
    return render_template("index.html")


@app.before_request
def enforce_local_only():
    """Allow requests only from the local machine when LOCAL_ONLY is True."""
    if not LOCAL_ONLY:
        return
    remote = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or request.remote_addr or ""
    if remote not in LOCAL_ADDRS:
        return jsonify({"error": "Local access only", "success": False}), 403


@app.route("/api/investigate", methods=["GET"])
@app.route("/api/scan", methods=["GET"])
def investigate():
    return jsonify(get_local_network_info())


@app.route("/api/geolocation/<ip>", methods=["GET"])
def geolocation(ip: str):
    return jsonify(get_ip_geolocation(ip))


@app.route("/api/lookup", methods=["GET", "POST"])
def lookup():
    if request.method == "GET":
        ip = request.args.get("ip", "").strip()
    else:
        data = request.get_json(silent=True) or {}
        ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"error": "No IP provided", "success": False}), 400

    return jsonify(
        {
            "ip": ip,
            "geolocation": get_ip_geolocation(ip),
            "whois": get_whois_info(ip),
            "reverse_dns": reverse_dns_lookup(ip),
            "success": True,
        }
    )


@app.route("/api/bulk_lookup", methods=["POST"])
def bulk_lookup():
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    lookups = []
    for ip in ips:
        lookups.append(
            {
                "ip": ip,
                "geolocation": get_ip_geolocation(ip),
                "reverse_dns": reverse_dns_lookup(ip),
            }
        )
    return jsonify({"success": True, "results": lookups})


@app.route("/api/map", methods=["POST"])
def generate_map():
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400

    locations = []
    for ip in ips:
        geo = get_ip_geolocation(ip)
        if geo.get("status") == "success":
            locations.append(geo)

    if not locations:
        return jsonify({"error": "No valid locations found", "success": False}), 404

    # If Folium missing, return JSON to let frontend render with Leaflet.
    if not folium:
        return jsonify({"success": True, "locations": locations})

    map_file = create_map(locations)
    return send_file(map_file, mimetype="text/html")


@app.route("/api/report", methods=["GET"])
def generate_report():
    include_system = request.args.get("include_system", "true").lower() == "true"
    include_connections = request.args.get("include_connections", "true").lower() == "true"
    include_security = request.args.get("include_security", "true").lower() == "true"
    include_geolocation = request.args.get("include_geolocation", "true").lower() == "true"

    fmt = request.args.get("format", "json")
    report = build_report(include_system, include_connections, include_security, include_geolocation)

    if fmt == "json":
        return jsonify(report)

    # simple HTML fallback
    html = ["<html><head><meta charset='utf-8'><title>IP Checker Report</title></head><body>"]
    html.append(f"<h1>IP Checker Report</h1><p>Generated at {report['generated_at']}</p>")
    html.append(f"<h2>Summary</h2><pre>{json.dumps(report['summary'], indent=2)}</pre>")
    if include_system:
        html.append(f"<h2>System</h2><pre>{json.dumps(report.get('local_system', {}), indent=2)}</pre>")
    if include_connections:
        html.append(f"<h2>Connections</h2><pre>{json.dumps(report.get('connections', []), indent=2)}</pre>")
    if include_security:
        html.append(f"<h2>Security</h2><pre>{json.dumps(report.get('security', {}), indent=2)}</pre>")
    if include_geolocation:
        html.append(f"<h2>External IPs</h2><pre>{json.dumps(report.get('external_ips', []), indent=2)}</pre>")
    html.append("</body></html>")
    return "\n".join(html)


@app.route("/api/myip")
def myip():
    """Get client's public IP address."""
    # Local-only mode returns the request source; avoids external calls for privacy.
    public_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "Unknown"
    return jsonify({
        "ip": public_ip,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/my-ip")
def my_ip_alias():
    """Alias for /api/myip."""
    return myip()


@app.route("/api/security/scan")
def security_scan():
    """Perform a lightweight security scan based on active connections."""
    info = get_local_network_info()
    connections = info.get("connections", [])
    security = info.get("security", {})

    findings = []
    for conn in connections:
        if conn.get("risk_level") == "info":
            continue
        findings.append(
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
        )

    recommendations = []
    if security.get("threats", 0) > 0:
        recommendations.append("Terminate suspicious remote sessions and validate running processes.")
    if security.get("warnings", 0) > 2:
        recommendations.append("Review firewall rules to limit unexpected outbound connections.")
    if security.get("secure", 0) < 3:
        recommendations.append("Prefer secure protocols (HTTPS, SSH, IMAPS) where possible.")
    if not recommendations:
        recommendations.append("No critical issues detected. Maintain regular monitoring.")

    return jsonify(
        {
            "timestamp": datetime.now().isoformat(),
            "score": security.get("score", 0),
            "summary": security,
            "findings": findings[:30],  # keep payload small
            "recommendations": recommendations,
        }
    )


@app.route("/api/health")
def health():
    """Simple health check with cache stats."""
    try:
        cache_entries = len(GEO_CACHE)
    except Exception:
        cache_entries = 0
    return jsonify(
        {
            "status": "ok",
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
            "platform": platform.platform(),
            "geo_cache_entries": cache_entries,
            "ipapi_available": bool(ipapi),
            "whois_available": bool(whois_lib),
        }
    )


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
