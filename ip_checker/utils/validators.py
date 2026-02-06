"""
Optimized validation utilities with caching for repeated checks.
"""

import ipaddress
import re
from functools import lru_cache
from typing import Union


# Compile regex patterns once for better performance
IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

IPV6_PATTERN = re.compile(
    r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
    r'^::1$|^::$|'
    r'^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$'
)


@lru_cache(maxsize=1024)
def validate_ip(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6) with caching.
    Uses LRU cache for O(1) repeated lookups.
    """
    if not ip or not isinstance(ip, str):
        return False
    
    ip = ip.strip()
    if not ip:
        return False
    
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


@lru_cache(maxsize=1024)
def is_private_ip(ip: str) -> bool:
    """
    Check if IP is private/loopback/link-local with caching.
    """
    if not validate_ip(ip):
        return False
    
    try:
        addr = ipaddress.ip_address(ip.strip())
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except (ValueError, AttributeError):
        return False


def is_valid_port(port: Union[int, str]) -> bool:
    """Validate port number."""
    try:
        port_num = int(port)
        return 0 < port_num <= 65535
    except (ValueError, TypeError):
        return False


@lru_cache(maxsize=256)
def is_local_network(ip: str, networks: tuple = None) -> bool:
    """
    Check if IP belongs to local networks with caching.
    """
    if not validate_ip(ip):
        return False
    
    try:
        addr = ipaddress.ip_address(ip.strip())
        
        if networks is None:
            from ip_checker.core.config import config
            networks = config.LOCAL_NETWORKS
        
        for network_str in networks:
            if addr in ipaddress.ip_network(network_str, strict=False):
                return True
        return False
    except (ValueError, TypeError):
        return False
