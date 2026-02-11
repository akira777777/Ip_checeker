"""
Reports API endpoints.
Handles report generation and export functionality.
"""

from flask import Blueprint, jsonify, request
import json
from datetime import datetime

from ..api.network import get_local_network_info
from ..extensions import limiter

report_bp = Blueprint('reports', __name__)


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


@report_bp.route("/report", methods=["GET"])
@limiter.limit("30 per minute")
def generate_report():
    """Generate comprehensive system report."""
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


@report_bp.route("/health")
def health():
    """Health check endpoint."""
    import platform
    from diskcache import Cache
    import os
    
    try:
        cache_dir = os.environ.get('CACHE_DIR', './cache')
        cache = Cache(cache_dir)
        cache_entries = len(list(cache.iterkeys()))
        cache.close()
    except Exception:
        cache_entries = 0
    
    try:
        import ipapi
        ipapi_available = True
    except ImportError:
        ipapi_available = False
        
    try:
        import whois as whois_lib
        whois_available = True
    except ImportError:
        whois_available = False
    
    return jsonify({
        "status": "ok",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "cache_entries": cache_entries,
        "ipapi_available": ipapi_available,
        "whois_available": whois_available,
        "local_only": os.environ.get('LOCAL_ONLY', 'True').lower() == 'true',
    })