"""
Geolocation API endpoints.
Handles IP geolocation lookups and related functionality.
"""

from flask import Blueprint, jsonify, request
from flask_limiter import Limiter

from ..services.geo_service import (
    get_ip_geolocation, 
    get_whois_info, 
    validate_ip
)
from ..services.net_service import reverse_dns_lookup
from ..extensions import limiter

geo_bp = Blueprint('geolocation', __name__)


@geo_bp.route("/geolocation/<ip>", methods=["GET"])
@limiter.limit("60 per minute")
def geolocation(ip: str):
    """Get geolocation for specific IP."""
    if not validate_ip(ip):
        return jsonify({"error": "Invalid IP address", "success": False}), 400
    return jsonify(get_ip_geolocation(ip))


@geo_bp.route("/lookup", methods=["GET", "POST"])
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


@geo_bp.route("/bulk_lookup", methods=["POST"])
@limiter.limit("10 per minute")
def bulk_lookup():
    """Bulk IP lookup."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > 50:
        return jsonify({"error": "Too many IPs (max 50)", "success": False}), 400
    
    lookups = []
    for ip in ips:
        if validate_ip(ip):
            lookups.append({
                "ip": ip,
                "geolocation": get_ip_geolocation(ip),
                "reverse_dns": reverse_dns_lookup(ip),
            })
    
    return jsonify({"success": True, "results": lookups})