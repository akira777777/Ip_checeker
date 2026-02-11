"""
Network service.
Handles network-related functionality like reverse DNS lookup.
"""

import logging
import socket
import ipaddress
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def validate_ip(ip: str) -> bool:
    """Validate IP address format."""
    if not ip or not isinstance(ip, str):
        return False
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False


def reverse_dns_lookup(ip_address: str) -> dict:
    """Perform reverse DNS lookup for an IP address."""
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    try:
        hostname = socket.gethostbyaddr(ip_address)
        return {
            "ip": ip_address, 
            "hostname": hostname[0], 
            "aliases": hostname[1], 
            "status": "success"
        }
    except Exception as e:
        logger.warning(f"Reverse DNS lookup failed for {ip_address}: {e}")
        return {"ip": ip_address, "status": "error", "message": str(e)}


def safe_process_name(pid: Optional[int]) -> str:
    """Get process name safely."""
    if not pid:
        return "unknown"
    try:
        import psutil
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "unknown"