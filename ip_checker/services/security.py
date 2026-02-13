"""
IP Checker Pro - Security Analysis Service
==========================================
Advanced security scanning, threat detection, and risk scoring.
"""

import ipaddress
import logging
import socket
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

import psutil

from ip_checker.core.config import get_config
from ip_checker.services.geo import get_geo_service

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Network connection with security metadata."""
    local_addr: Optional[str]
    remote_addr: str
    remote_ip: str
    remote_port: int
    status: str
    protocol: str
    pid: Optional[int]
    process: str
    risk_level: str = 'info'
    risks: List[str] = field(default_factory=list)
    geo: Dict[str, Any] = field(default_factory=dict)
    is_private: bool = False


@dataclass
class SecurityScore:
    """Security assessment results."""
    score: int
    grade: str
    warnings: int
    threats: int
    secure: int
    suspicious_ports: int
    geo_failures: int
    total_connections: int
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class SecurityAnalyzer:
    """
    Advanced security analyzer for network connections.
    Detects threats, calculates security scores, and provides recommendations.
    """
    
    # Risk scoring weights
    WEIGHTS = {
        'warning': 4,
        'threat': 10,
        'suspicious_port': 3,
        'geo_fail': 1,
        'insecure_protocol': 2,
    }
    
    def __init__(self):
        self.config = get_config()
        self.geo_service = get_geo_service()
        self._suspicious_ports: Set[int] = self.config.SUSPICIOUS_PORTS
        self._secure_ports: Set[int] = self.config.SECURE_PORTS
    
    def analyze_connection(self, conn: psutil._psplatform.Connection,
                          geo_data: Optional[Dict] = None) -> ConnectionInfo:
        """
        Analyze a single connection for security risks.
        
        Args:
            conn: psutil connection object
            geo_data: Optional pre-fetched geolocation data
            
        Returns:
            ConnectionInfo with risk assessment
        """
        if not conn.raddr:
            return None
        
        remote_ip, remote_port = conn.raddr
        
        # Determine if private
        is_private = self._is_private_ip(remote_ip)
        
        # Get process name
        process_name = self._get_process_name(conn.pid)
        
        # Classify risk
        risk_level, risks = self._classify_risk(
            remote_port, conn.status, geo_data, remote_ip, is_private
        )
        
        return ConnectionInfo(
            local_addr=f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
            remote_addr=f"{remote_ip}:{remote_port}",
            remote_ip=remote_ip,
            remote_port=remote_port,
            status=conn.status,
            protocol='TCP' if conn.type == socket.SOCK_STREAM else 'UDP',
            pid=conn.pid,
            process=process_name,
            risk_level=risk_level,
            risks=risks,
            geo=geo_data or {},
            is_private=is_private
        )
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/local."""
        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return False
    
    def _get_process_name(self, pid: Optional[int]) -> str:
        """Safely get process name."""
        if not pid:
            return "unknown"
        try:
            return psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return "unknown"
    
    def _classify_risk(self, remote_port: int, status: str, 
                      geo: Optional[Dict], remote_ip: str, 
                      is_private: bool) -> Tuple[str, List[str]]:
        """
        Classify connection risk level.
        
        Returns:
            Tuple of (risk_level, risk_descriptions)
        """
        risks = []
        
        # Private/local connections are low risk
        if is_private:
            return 'info', []
        
        # Check for suspicious ports
        if remote_port in self._suspicious_ports:
            risks.append(f"Port {remote_port} is commonly used by malware")
            return 'danger', risks
        
        # Check connection state
        if status not in ('ESTABLISHED', 'TIME_WAIT', 'CLOSE_WAIT'):
            risks.append(f"Unusual state: {status}")
        
        # Check geolocation issues
        if geo and geo.get('status') not in (None, 'success'):
            risks.append("Geolocation lookup failed")
        
        # Determine level based on risks
        if not risks:
            return 'info', []
        
        # Check if any are warnings vs info
        if any('Unusual' in r for r in risks):
            return 'warning', risks
        
        return 'info', risks
    
    def calculate_security_score(self, connections: List[ConnectionInfo]) -> SecurityScore:
        """
        Calculate overall security score.
        
        Args:
            connections: List of analyzed connections
            
        Returns:
            SecurityScore with detailed assessment
        """
        if not connections:
            return SecurityScore(
                score=100,
                grade='Excellent',
                warnings=0,
                threats=0,
                secure=0,
                suspicious_ports=0,
                geo_failures=0,
                total_connections=0,
                recommendations=["No active connections detected"]
            )
        
        # Count by risk level
        warnings = sum(1 for c in connections if c.risk_level == 'warning')
        threats = sum(1 for c in connections if c.risk_level == 'danger')
        secure = sum(1 for c in connections 
                    if c.remote_port in self._secure_ports)
        suspicious_ports = sum(1 for c in connections 
                              if c.remote_port in self._suspicious_ports)
        geo_failures = sum(1 for c in connections 
                          if c.geo.get('status') not in (None, 'success'))
        
        # Calculate score (0-100)
        score = 100
        score -= warnings * self.WEIGHTS['warning']
        score -= threats * self.WEIGHTS['threat']
        score -= min(suspicious_ports * self.WEIGHTS['suspicious_port'], 20)
        score -= min(geo_failures * self.WEIGHTS['geo_fail'], 10)
        
        # Bonus for secure connections
        external_conns = [c for c in connections if not c.is_private]
        if external_conns:
            secure_ratio = secure / len(external_conns)
            if secure_ratio < 0.2:
                score -= 5
        
        score = max(0, min(100, score))
        
        # Determine grade
        grade = self._score_to_grade(score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            score, threats, warnings, secure, suspicious_ports, connections
        )
        
        # Risk factors
        risk_factors = self._identify_risk_factors(connections)
        
        return SecurityScore(
            score=score,
            grade=grade,
            warnings=warnings,
            threats=threats,
            secure=secure,
            suspicious_ports=suspicious_ports,
            geo_failures=geo_failures,
            total_connections=len(connections),
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _generate_recommendations(self, score: int, threats: int, 
                                   warnings: int, secure: int, 
                                   suspicious_ports: int,
                                   connections: List[ConnectionInfo]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        if threats > 0:
            recommendations.append(
                f"CRITICAL: {threats} threat(s) detected. "
                "Review suspicious connections immediately."
            )
        
        if warnings > 3:
            recommendations.append(
                f"WARNING: {warnings} connections flagged. "
                "Consider reviewing firewall rules."
            )
        
        if suspicious_ports > 0:
            recommendations.append(
                f"{suspicious_ports} connection(s) using suspicious ports. "
                "Verify these are legitimate."
            )
        
        external = [c for c in connections if not c.is_private]
        if external and secure / len(external) < 0.3:
            recommendations.append(
                "Few secure connections detected. "
                "Consider using HTTPS/SSL where possible."
            )
        
        # High-risk countries check
        countries = Counter(c.geo.get('country') for c in connections 
                          if c.geo and c.geo.get('country'))
        if countries:
            top_country = countries.most_common(1)[0]
            if top_country[1] > len(connections) * 0.5:
                recommendations.append(
                    f"Many connections to {top_country[0]}. "
                    "Verify this is expected behavior."
                )
        
        if not recommendations:
            if score >= 90:
                recommendations.append(
                    "Excellent security posture! Keep monitoring regularly."
                )
            else:
                recommendations.append(
                    "No critical issues detected. Continue monitoring."
                )
        
        return recommendations
    
    def _identify_risk_factors(self, connections: List[ConnectionInfo]) -> List[str]:
        """Identify specific risk factors."""
        risk_factors = []
        
        # Check for unusual processes
        processes = Counter(c.process for c in connections if c.process != 'unknown')
        for proc, count in processes.most_common(3):
            risk_factors.append(f"{count} connections from {proc}")
        
        # Check for port scanning behavior
        unique_ports_per_ip = {}
        for c in connections:
            if not c.is_private:
                unique_ports_per_ip.setdefault(c.remote_ip, set()).add(c.remote_port)
        
        for ip, ports in unique_ports_per_ip.items():
            if len(ports) > 10:
                risk_factors.append(f"{ip} connected to {len(ports)} different ports")
        
        return risk_factors
    
    def scan_system(self, limit: int = 200) -> Dict[str, Any]:
        """
        Perform full system security scan.
        
        Args:
            limit: Maximum connections to analyze
            
        Returns:
            Dictionary with scan results
        """
        timestamp = datetime.now().isoformat()
        
        # Get system info
        system_info = {
            'hostname': socket.gethostname(),
            'platform': __import__('platform').platform(),
            'timestamp': timestamp,
            'interfaces': self._get_interfaces(),
        }
        
        # Get and analyze connections
        connections = []
        geo_cache = {}
        geo_lookups = 0
        
        try:
            for conn in psutil.net_connections(kind='inet')[:limit]:
                if not conn.raddr:
                    continue
                
                remote_ip = conn.raddr[0]
                
                # Get geolocation (with limit)
                geo = None
                if geo_lookups < self.config.GEO_LOOKUP_LIMIT and not self._is_private_ip(remote_ip):
                    if remote_ip not in geo_cache:
                        geo_cache[remote_ip] = self.geo_service.get_location(remote_ip).to_dict()
                        geo_lookups += 1
                    geo = geo_cache[remote_ip]
                
                info = self.analyze_connection(conn, geo)
                if info:
                    connections.append(info)
        
        except Exception as e:
            logger.error(f"Error scanning connections: {e}")
        
        # Calculate security score
        security = self.calculate_security_score(connections)
        
        # Get top countries
        countries = Counter(c.geo.get('country') for c in connections 
                          if c.geo and c.geo.get('country'))
        
        return {
            'system': system_info,
            'connections': [self._conn_to_dict(c) for c in connections],
            'security': {
                'score': security.score,
                'grade': security.grade,
                'warnings': security.warnings,
                'threats': security.threats,
                'secure_connections': security.secure,
                'suspicious_ports': security.suspicious_ports,
                'total_connections': security.total_connections,
                'recommendations': security.recommendations,
                'risk_factors': security.risk_factors,
            },
            'summary': {
                'top_countries': countries.most_common(5),
                'external_connections': len([c for c in connections if not c.is_private]),
                'private_connections': len([c for c in connections if c.is_private]),
            },
            'scan_metadata': {
                'timestamp': timestamp,
                'connections_scanned': len(connections),
                'geo_lookups': geo_lookups,
            }
        }
    
    def _get_interfaces(self) -> List[Dict]:
        """Get network interface information."""
        interfaces = []
        try:
            for name, addrs in psutil.net_if_addrs().items():
                addresses = []
                for addr in addrs:
                    if addr.family in (socket.AF_INET, socket.AF_INET6):
                        addresses.append({
                            'family': 'IPv4' if addr.family == socket.AF_INET else 'IPv6',
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast,
                        })
                interfaces.append({'name': name, 'addresses': addresses})
        except Exception as e:
            logger.warning(f"Error getting interfaces: {e}")
        return interfaces
    
    def _conn_to_dict(self, conn: ConnectionInfo) -> Dict[str, Any]:
        """Convert ConnectionInfo to dictionary."""
        return {
            'local_addr': conn.local_addr,
            'remote_addr': conn.remote_addr,
            'remote_ip': conn.remote_ip,
            'remote_port': conn.remote_port,
            'status': conn.status,
            'protocol': conn.protocol,
            'pid': conn.pid,
            'process': conn.process,
            'risk_level': conn.risk_level,
            'risks': conn.risks,
            'geo': conn.geo,
            'is_private': conn.is_private,
        }


# Global analyzer instance
_analyzer: Optional[SecurityAnalyzer] = None


def get_security_analyzer() -> SecurityAnalyzer:
    """Get or create global security analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SecurityAnalyzer()
    return _analyzer
