"""
Optimized API routes with proper error handling and rate limiting.
"""

import os
import tempfile
from datetime import datetime

from flask import Blueprint, abort, jsonify, render_template, request, send_file

from ip_checker.core.config import config
from ip_checker.services.geo import (
    bulk_geolocation,
    get_cache_stats,
    get_ip_geolocation,
    get_whois_info,
    reverse_dns_lookup,
)
from ip_checker.services.security import (
    analyze_connections,
    calculate_security_score,
    generate_recommendations,
)
from ip_checker.utils.helpers import (
    get_network_interfaces,
    get_system_info,
    temp_manager,
)
from ip_checker.utils.validators import validate_ip

# Optional imports
try:
    import folium
except ImportError:
    folium = None

api_bp = Blueprint('api', __name__)


# Local access enforcement
@api_bp.before_request
def enforce_local_only():
    """Enforce local-only access when configured."""
    if not config.LOCAL_ONLY:
        return
    
    from ip_checker.utils.validators import is_local_network
    remote = request.remote_addr or ""
    
    if not is_local_network(remote):
        return jsonify({"error": "Local access only", "success": False}), 403


@api_bp.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "version": config.VERSION,
        "timestamp": datetime.now().isoformat(),
        "cache_stats": get_cache_stats(),
        "local_only": config.LOCAL_ONLY,
    })


@api_bp.route('/investigate')
def investigate():
    """Deep PC investigation endpoint."""
    info = get_system_info()
    interfaces = get_network_interfaces()
    connection_data = analyze_connections(
        limit=config.MAX_CONNECTIONS_SCAN,
        include_geo=True
    )
    
    return jsonify({
        **info,
        "interfaces": interfaces,
        "connections": connection_data["connections"],
        "security": connection_data["security"],
        "summary": connection_data["summary"],
    })


@api_bp.route('/geolocation/<ip>')
def geolocation(ip: str):
    """Get geolocation for specific IP."""
    result = get_ip_geolocation(ip)
    return jsonify(result)


@api_bp.route('/lookup', methods=['GET', 'POST'])
def lookup():
    """Comprehensive IP lookup."""
    if request.method == 'GET':
        ip = request.args.get('ip', '').strip()
    else:
        data = request.get_json(silent=True) or {}
        ip = (data.get('ip') or '').strip()
    
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


@api_bp.route('/bulk_lookup', methods=['POST'])
def bulk_lookup():
    """Bulk IP lookup endpoint."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get('ips', []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > config.MAX_BULK_LOOKUPS:
        return jsonify({
            "error": f"Too many IPs (max {config.MAX_BULK_LOOKUPS})",
            "success": False
        }), 400
    
    results = bulk_geolocation(ips)
    return jsonify({"success": True, "results": results})


@api_bp.route('/map', methods=['POST'])
def generate_map():
    """Generate map for IP addresses."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get('ips', []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > config.MAX_BULK_LOOKUPS:
        return jsonify({
            "error": f"Too many IPs (max {config.MAX_BULK_LOOKUPS})",
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
    
    # Create Folium map
    try:
        center = [locations[0].get("lat", 0), locations[0].get("lon", 0)]
        fmap = folium.Map(location=center, zoom_start=3)
        
        for loc in locations:
            if not (loc.get("lat") and loc.get("lon")):
                continue
            
            popup_html = f"""
            <b>IP:</b> {loc.get('ip', '')}<br>
            <b>Location:</b> {loc.get('city', '')}, {loc.get('country', '')}<br>
            <b>ISP:</b> {loc.get('isp', '')}<br>
            <b>Coordinates:</b> {loc.get('lat')}, {loc.get('lon')}
            """
            
            folium.Marker(
                [loc["lat"], loc["lon"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=loc.get("ip", ""),
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(fmap)
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".html", mode="w", encoding="utf-8"
        )
        fmap.save(temp_file.name)
        temp_file.close()
        
        temp_manager.register(temp_file.name)
        
        return send_file(temp_file.name, mimetype="text/html")
        
    except Exception as e:
        return jsonify({"error": "Map generation failed", "success": False}), 500


@api_bp.route('/report', methods=['GET'])
def generate_report():
    """Generate comprehensive report."""
    include_system = request.args.get("include_system", "true").lower() == "true"
    include_connections = request.args.get("include_connections", "true").lower() == "true"
    include_security = request.args.get("include_security", "true").lower() == "true"
    include_geo = request.args.get("include_geolocation", "true").lower() == "true"
    fmt = request.args.get("format", "json")
    
    # Build report
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
            limit=config.MAX_CONNECTIONS_SCAN,
            include_geo=include_geo
        )
        
        if include_connections:
            report["connections"] = connection_data["connections"]
        
        if include_security:
            report["security"] = connection_data["security"]
        
        if include_geo:
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
    html_parts = [
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
    
    return "\n".join(html_parts)


@api_bp.route('/myip')
def myip():
    """Get client's public IP address."""
    return jsonify({
        "ip": request.remote_addr or "Unknown",
        "timestamp": datetime.now().isoformat(),
    })


@api_bp.route('/security/scan')
def security_scan():
    """Perform security scan."""
    connection_data = analyze_connections(
        limit=config.MAX_CONNECTIONS_SCAN,
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


# Need to import json for report generation
import json
