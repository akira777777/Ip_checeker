"""
Security API endpoints.
Handles security scanning and analysis.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List

from ..api.network import get_local_network_info, aggregate_security
from ..extensions import limiter

sec_bp = Blueprint('security', __name__)


@sec_bp.route("/security/scan")
@limiter.limit("30 per minute")
def security_scan():
    """Perform a lightweight security scan based on active connections."""
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