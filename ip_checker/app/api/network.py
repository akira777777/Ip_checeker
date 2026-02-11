"""
Network analysis API endpoints.
Handles system network information and connection analysis.
"""

from flask import Blueprint, jsonify, request
import psutil
import socket
import platform
from datetime import datetime
from collections import Counter
from typing import List
import ipaddress

from ..services.net_service import safe_process_name
from ..services.geo_service import get_ip_geolocation, is_private_ip
from ..extensions import limiter

net_bp = Blueprint('network', __name__)

# Constants
SUSPICIOUS_PORTS = {23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389}
SECURE_PORTS = {22, 443, 993, 995, 5061}
GEO_LOOKUP_LIMIT = 15


def classify_connection(remote_port: int, status: str, geo: dict, remote_ip: str = None) -> tuple[str, List[str]]:
    """Classify network connection risk level."""
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


def aggregate_security(connections: List[dict]) -> dict:
    """Calculate security metrics from connections."""
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
    """Get detailed local network information."""
    geo_cache = {}
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
        info["interface_error"] = str(e)

    # Connections
    try:
        for conn in psutil.net_connections(kind="inet")[:limit_connections]:
            if not conn.raddr:
                continue
            remote_ip, remote_port = conn.raddr
            if geo_lookups < GEO_LOOKUP_LIMIT:
                geo = get_ip_geolocation(remote_ip)
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
        info["connections_error"] = str(e)

    # Summary
    geo_countries = Counter([
        c["geo"].get("country") for c in info["connections"] 
        if c.get("geo", {}).get("country")
    ])
    info["summary"] = {
        "total_connections": len(info["connections"]),
        "top_countries": geo_countries.most_common(5),
    }
    info["security"] = aggregate_security(info["connections"])
    return info


@net_bp.route("/investigate", methods=["GET"])
@net_bp.route("/scan", methods=["GET"])
@limiter.limit("30 per minute")
def investigate():
    """Get local network investigation data."""
    return jsonify(get_local_network_info())


@net_bp.route("/myip")
@limiter.limit("100 per minute")
def myip():
    """Get client's public IP address."""
    public_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "Unknown"
    return jsonify({
        "ip": public_ip,
        "timestamp": datetime.now().isoformat()
    })


@net_bp.route("/my-ip")
def my_ip_alias():
    """Alias for /myip."""
    return myip()