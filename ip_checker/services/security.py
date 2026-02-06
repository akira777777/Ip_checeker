"""
Security analysis service with optimized classification algorithms.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import psutil

from ip_checker.core.config import config
from ip_checker.utils.helpers import safe_process_name
from ip_checker.utils.validators import is_private_ip


@dataclass
class ConnectionRisk:
    """Data class for connection risk assessment."""
    level: str
    risks: List[str]
    score: int = 0


def classify_connection(
    remote_port: int,
    status: str,
    remote_ip: Optional[str] = None
) -> Tuple[str, List[str]]:
    """
    Classify connection risk level with optimized logic.
    Returns: (level, risks)
    """
    risks = []
    level = "info"
    
    # Fast path for private IPs
    if remote_ip and is_private_ip(remote_ip):
        return "info", []
    
    # Check suspicious ports
    if remote_port in config.SUSPICIOUS_PORTS:
        risks.append(f"Port {remote_port} commonly abused")
        level = "danger"
    
    # Check connection status
    if status not in ("ESTABLISHED", "TIME_WAIT", "CLOSE_WAIT"):
        risks.append(f"State: {status}")
        if level != "danger":
            level = "warning"
    
    return level, risks


def calculate_security_score(connections: List[Dict]) -> Dict:
    """
    Calculate comprehensive security score.
    Optimized with single-pass calculation.
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
    
    # Single-pass aggregation
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
        
        if remote_port in config.SECURE_PORTS:
            secure += 1
        if remote_port in config.SUSPICIOUS_PORTS:
            suspicious_ports += 1
    
    # Score calculation
    score = 100
    score -= warnings * 4
    score -= threats * 10
    score -= min(suspicious_ports * 3, 20)
    
    # Secure connection bonus
    secure_ratio = secure / total if total > 0 else 0
    if secure_ratio < 0.2:
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
        "secure_ratio": round(secure_ratio, 2),
    }


def analyze_connections(
    limit: int = 200,
    include_geo: bool = True
) -> Dict:
    """
    Analyze active connections with optional geolocation.
    Optimized for performance with minimal API calls.
    """
    from ip_checker.services.geo import get_ip_geolocation
    
    connections = []
    geo_cache: Dict[str, Dict] = {}
    geo_lookups = 0
    
    try:
        conns = psutil.net_connections(kind="inet")[:limit]
        
        for conn in conns:
            if not conn.raddr:
                continue
            
            remote_ip, remote_port = conn.raddr
            
            # Get geolocation if needed and within limit
            geo = {"status": "skipped"}
            if include_geo and geo_lookups < config.GEO_LOOKUP_LIMIT:
                if remote_ip not in geo_cache:
                    geo_cache[remote_ip] = get_ip_geolocation(remote_ip)
                    geo_lookups += 1
                geo = geo_cache[remote_ip]
            
            # Classify connection
            risk_level, risks = classify_connection(
                remote_port, conn.status, remote_ip
            )
            
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
    except Exception:
        pass
    
    # Calculate security metrics
    security = calculate_security_score(connections)
    
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


def generate_recommendations(security: Dict) -> List[str]:
    """Generate security recommendations based on analysis."""
    recommendations = []
    
    if security.get("threats", 0) > 0:
        recommendations.append(
            "⚠️ Critical: Terminate suspicious remote sessions immediately."
        )
    
    if security.get("warnings", 0) > 2:
        recommendations.append(
            "🔒 Review firewall rules to limit unexpected outbound connections."
        )
    
    if security.get("secure_ratio", 0) < 0.2:
        recommendations.append(
            "🔐 Prefer secure protocols (HTTPS, SSH, IMAPS) where possible."
        )
    
    if not recommendations:
        recommendations.append(
            "✅ No critical issues detected. Maintain regular monitoring."
        )
    
    return recommendations


# Need to import socket for the analyze_connections function
import socket
