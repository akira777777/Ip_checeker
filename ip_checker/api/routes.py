"""
IP Checker Pro - API Routes
===========================
RESTful API endpoints with optimized response handling.
"""

import logging
import socket
from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, abort, jsonify, request, send_file

from ip_checker.core.config import get_config
from ip_checker.services.cache import get_cache
from ip_checker.services.geo import get_geo_service, GeoLocation
from ip_checker.services.security import get_security_analyzer
from ip_checker.utils.helpers import json_response, error_response
from ip_checker.utils.validators import IPValidator

logger = logging.getLogger(__name__)

# Create blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Get config
config = get_config()


@api.before_request
def check_local_access():
    """Enforce local-only access if configured."""
    if not config.LOCAL_ONLY:
        return
    
    # Get real client IP
    forwarded = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    remote = forwarded or request.remote_addr
    
    if remote not in ('127.0.0.1', '::1', 'localhost'):
        logger.warning(f"Blocked remote access from {remote}")
        abort(403, description="Local access only")


@api.route('/health')
def health_check():
    """System health check endpoint."""
    cache = get_cache()
    geo_service = get_geo_service()
    
    checks = {
        'cache': cache.get_stats(),
        'geo_service': geo_service.get_stats(),
        'config': {
            'version': config.version,
            'local_only': config.LOCAL_ONLY,
            'debug': config.FLASK_DEBUG,
        }
    }
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': checks
    })


@api.route('/myip')
def get_my_ip():
    """Get client's public IP address."""
    forwarded = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    ip = forwarded or request.remote_addr
    
    return jsonify({
        'ip': ip,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/geolocation/<ip>')
def get_geolocation(ip: str):
    """
    Get geolocation for IP address.
    
    Path Parameters:
        ip: IP address to lookup
        
    Query Parameters:
        skip_cache: Bypass cache if 'true'
    """
    # Validate IP
    is_valid, error_msg = IPValidator.validate(ip)
    if not is_valid:
        response, code = error_response(f"Invalid IP: {error_msg}", 400)
        return jsonify(response), code
    
    # Check for skip_cache
    skip_cache = request.args.get('skip_cache', '').lower() == 'true'
    
    # Get geolocation
    geo_service = get_geo_service()
    result = geo_service.get_location(ip, skip_cache=skip_cache)
    
    return jsonify(result.to_dict())


@api.route('/lookup', methods=['GET', 'POST'])
def lookup_ip():
    """
    Comprehensive IP lookup with geolocation, reverse DNS, and WHOIS.
    
    GET/POST Parameters:
        ip: IP address to lookup
    """
    # Get IP from request
    if request.method == 'GET':
        ip = request.args.get('ip', '').strip()
    else:
        data = request.get_json(silent=True) or {}
        ip = data.get('ip', '').strip()
    
    if not ip:
        response, code = error_response("IP address is required", 400)
        return jsonify(response), code
    
    # Validate IP
    is_valid, error_msg = IPValidator.validate(ip)
    if not is_valid:
        response, code = error_response(f"Invalid IP: {error_msg}", 400)
        return jsonify(response), code
    
    geo_service = get_geo_service()
    
    # Get geolocation
    geo_result = geo_service.get_location(ip)
    
    # Reverse DNS lookup
    reverse_dns = reverse_dns_lookup(ip)
    
    # WHOIS lookup (if available)
    whois_info = get_whois_info(ip)
    
    return jsonify({
        'success': True,
        'ip': ip,
        'geolocation': geo_result.to_dict(),
        'reverse_dns': reverse_dns,
        'whois': whois_info,
    })


def reverse_dns_lookup(ip: str) -> Dict[str, Any]:
    """Perform reverse DNS lookup."""
    try:
        hostname = socket.gethostbyaddr(ip)
        return {
            'status': 'success',
            'hostname': hostname[0],
            'aliases': hostname[1],
        }
    except socket.herror:
        return {
            'status': 'no_record',
            'message': 'No reverse DNS record found'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def get_whois_info(ip: str) -> Dict[str, Any]:
    """Get WHOIS information if python-whois is available."""
    try:
        import whois as whois_lib
        w = whois_lib.whois(ip)
        return {
            'status': 'success',
            'domain': w.domain_name,
            'registrar': w.registrar,
            'creation_date': str(w.creation_date) if w.creation_date else None,
            'expiration_date': str(w.expiration_date) if w.expiration_date else None,
            'name_servers': w.name_servers,
        }
    except ImportError:
        return {
            'status': 'unavailable',
            'message': 'python-whois not installed'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@api.route('/bulk_lookup', methods=['POST'])
def bulk_lookup():
    """
    Bulk IP lookup for multiple addresses.
    
    Request Body:
        {
            "ips": ["1.1.1.1", "8.8.8.8", ...],
            "max_workers": 5  # Optional
        }
    """
    data = request.get_json(silent=True) or {}
    ips = data.get('ips', [])
    max_workers = data.get('max_workers', 5)
    
    if not ips or not isinstance(ips, list):
        response, code = error_response("ips array is required", 400)
        return jsonify(response), code
    
    # Validate and limit
    valid_ips = []
    for ip in ips:
        if IPValidator.is_valid(ip):
            valid_ips.append(ip)
    
    if len(valid_ips) > 100:
        valid_ips = valid_ips[:100]
    
    # Bulk lookup
    geo_service = get_geo_service()
    results = geo_service.bulk_lookup(valid_ips, max_workers=max_workers)
    
    return jsonify({
        'success': True,
        'count': len(results),
        'results': [r.to_dict() for r in results]
    })


@api.route('/investigate')
def investigate_system():
    """
    Perform deep system investigation.
    
    Query Parameters:
        limit: Maximum connections to analyze (default: 200)
    """
    limit = request.args.get('limit', 200, type=int)
    limit = min(max(limit, 1), 500)  # Clamp between 1-500
    
    analyzer = get_security_analyzer()
    result = analyzer.scan_system(limit=limit)
    
    return jsonify({
        'success': True,
        **result
    })


@api.route('/security/scan')
def security_scan():
    """Run security scan and return findings."""
    analyzer = get_security_analyzer()
    result = analyzer.scan_system(limit=200)
    
    # Filter to just security-relevant info
    security_data = result.get('security', {})
    connections = result.get('connections', [])
    
    # Get risky connections
    findings = [
        {
            'remote': c['remote_addr'],
            'process': c['process'],
            'risk_level': c['risk_level'],
            'risks': c['risks'],
            'country': c.get('geo', {}).get('country'),
        }
        for c in connections
        if c['risk_level'] in ('warning', 'danger')
    ]
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'score': security_data.get('score', 0),
        'grade': security_data.get('grade', 'N/A'),
        'summary': {
            'warnings': security_data.get('warnings', 0),
            'threats': security_data.get('threats', 0),
            'secure': security_data.get('secure_connections', 0),
            'total': security_data.get('total_connections', 0),
        },
        'findings': findings[:50],
        'recommendations': security_data.get('recommendations', []),
    })


@api.route('/map', methods=['POST'])
def generate_map():
    """
    Generate map data for IP addresses.
    
    Request Body:
        {
            "ips": ["1.1.1.1", "8.8.8.8", ...]
        }
    """
    data = request.get_json(silent=True) or {}
    ips = data.get('ips', [])
    
    if not ips:
        response, code = error_response("ips array is required", 400)
        return jsonify(response), code
    
    # Validate and limit
    valid_ips = [ip for ip in ips if IPValidator.is_valid(ip)][:50]
    
    # Get locations
    geo_service = get_geo_service()
    results = geo_service.bulk_lookup(valid_ips, max_workers=5)
    
    # Filter to successful lookups with coordinates
    locations = [
        {
            'ip': r.ip,
            'lat': r.lat,
            'lon': r.lon,
            'country': r.country,
            'city': r.city,
            'isp': r.isp,
        }
        for r in results
        if r.status == 'success' and r.lat and r.lon
    ]
    
    return jsonify({
        'success': True,
        'count': len(locations),
        'locations': locations
    })


@api.route('/report')
def generate_report():
    """
    Generate comprehensive system report.
    
    Query Parameters:
        include_system: Include system info (default: true)
        include_connections: Include connections (default: true)
        include_security: Include security analysis (default: true)
        include_geolocation: Include geolocation data (default: true)
        format: 'json' or 'html' (default: json)
    """
    # Parse options
    include_system = request.args.get('include_system', 'true').lower() == 'true'
    include_connections = request.args.get('include_connections', 'true').lower() == 'true'
    include_security = request.args.get('include_security', 'true').lower() == 'true'
    include_geolocation = request.args.get('include_geolocation', 'true').lower() == 'true'
    fmt = request.args.get('format', 'json')
    
    # Run scan
    analyzer = get_security_analyzer()
    scan_result = analyzer.scan_system(limit=200)
    
    # Build report
    report = {
        'title': 'IP Checker Pro Report',
        'generated_at': datetime.now().isoformat(),
        'version': config.version,
    }
    
    if include_system:
        report['system'] = scan_result.get('system')
    
    if include_connections:
        report['connections'] = scan_result.get('connections', [])
    
    if include_security:
        report['security'] = scan_result.get('security')
        report['summary'] = scan_result.get('summary')
    
    if include_geolocation:
        connections = scan_result.get('connections', [])
        unique_ips = {}
        for c in connections:
            ip = c.get('remote_ip')
            geo = c.get('geo')
            if ip and geo and geo.get('status') == 'success':
                unique_ips[ip] = geo
        report['external_ips'] = list(unique_ips.values())
    
    if fmt == 'html':
        html = generate_html_report(report)
        return html, 200, {'Content-Type': 'text/html'}
    
    return jsonify(report)


def generate_html_report(report: dict) -> str:
    """Generate HTML report."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{report['title']}</title>
        <style>
            body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1, h2 {{ color: #333; }}
            pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <h1>{report['title']}</h1>
        <p>Generated: {report['generated_at']}</p>
        <p>Version: {report['version']}</p>
    """
    
    if 'system' in report:
        html += '<div class="section"><h2>System Information</h2>'
        html += f'<pre>{json.dumps(report["system"], indent=2)}</pre></div>'
    
    if 'security' in report:
        html += '<div class="section"><h2>Security Analysis</h2>'
        html += f'<pre>{json.dumps(report["security"], indent=2)}</pre></div>'
    
    if 'connections' in report:
        html += '<div class="section"><h2>Connections</h2>'
        html += f'<p>Total: {len(report["connections"])}</p></div>'
    
    html += '</body></html>'
    return html


@api.route('/cache/stats')
def cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    return jsonify(cache.get_stats())


@api.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all caches."""
    cache = get_cache()
    cache.clear()
    return jsonify({'success': True, 'message': 'Cache cleared'})


# Import json for report generation
import json
