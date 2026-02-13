"""
IP Checker Pro - Input Validators
=================================
Input validation and sanitization utilities.
"""

import ipaddress
import re
from typing import List, Optional, Tuple


class ValidationError(Exception):
    """Validation error with message."""
    pass


class IPValidator:
    """IP address validation utilities."""
    
    # Regex patterns for quick validation
    IPV4_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    IPV6_PATTERN = re.compile(r'^[0-9a-fA-F:]+$')
    
    @classmethod
    def validate(cls, ip: str, allow_private: bool = True) -> Tuple[bool, str]:
        """
        Validate IP address.
        
        Args:
            ip: IP address string
            allow_private: Whether to allow private IPs
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ip or not isinstance(ip, str):
            return False, "IP address is required"
        
        ip = ip.strip()
        
        if not ip:
            return False, "IP address cannot be empty"
        
        # Check length
        if len(ip) > 45:  # Max IPv6 length
            return False, "IP address too long"
        
        try:
            addr = ipaddress.ip_address(ip)
            
            if not allow_private:
                if addr.is_private or addr.is_loopback or addr.is_link_local:
                    return False, "Private IP addresses not allowed"
            
            # Check for reserved addresses
            if addr.is_reserved:
                return False, "Reserved IP addresses not allowed"
            
            # Check for multicast
            if addr.is_multicast:
                return False, "Multicast addresses not allowed"
            
            return True, ""
            
        except ValueError as e:
            return False, f"Invalid IP address: {str(e)}"
    
    @classmethod
    def is_valid(cls, ip: str) -> bool:
        """Quick validation check."""
        valid, _ = cls.validate(ip)
        return valid
    
    @classmethod
    def get_version(cls, ip: str) -> Optional[int]:
        """Get IP version (4 or 6) or None if invalid."""
        try:
            addr = ipaddress.ip_address(ip.strip())
            return addr.version
        except ValueError:
            return None
    
    @classmethod
    def is_private(cls, ip: str) -> bool:
        """Check if IP is private/local."""
        try:
            addr = ipaddress.ip_address(ip.strip())
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return False
    
    @classmethod
    def sanitize(cls, ip: str) -> str:
        """Sanitize IP address string."""
        return ip.strip().lower()
    
    @classmethod
    def parse_list(cls, ips: str, delimiter: str = None) -> List[str]:
        """
        Parse a string of IP addresses.
        
        Args:
            ips: String containing IPs (comma, newline, or space separated)
            delimiter: Optional explicit delimiter
            
        Returns:
            List of valid IP addresses
        """
        if not ips:
            return []
        
        # Auto-detect delimiter
        if delimiter is None:
            if '\n' in ips:
                delimiter = '\n'
            elif ',' in ips:
                delimiter = ','
            else:
                delimiter = ' '
        
        valid_ips = []
        for ip in ips.split(delimiter):
            ip = ip.strip()
            if ip and cls.is_valid(ip):
                valid_ips.append(ip)
        
        return valid_ips


class PortValidator:
    """Port number validation utilities."""
    
    VALID_RANGE = range(1, 65536)
    
    @classmethod
    def validate(cls, port: int) -> Tuple[bool, str]:
        """Validate port number."""
        if not isinstance(port, int):
            try:
                port = int(port)
            except (ValueError, TypeError):
                return False, "Port must be a number"
        
        if port not in cls.VALID_RANGE:
            return False, f"Port must be between 1 and 65535"
        
        return True, ""
    
    @classmethod
    def is_valid(cls, port: int) -> bool:
        """Quick validation check."""
        valid, _ = cls.validate(port)
        return valid


class DomainValidator:
    """Domain name validation utilities."""
    
    DOMAIN_PATTERN = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    
    @classmethod
    def validate(cls, domain: str) -> Tuple[bool, str]:
        """Validate domain name."""
        if not domain or not isinstance(domain, str):
            return False, "Domain is required"
        
        domain = domain.strip().lower()
        
        if len(domain) > 253:
            return False, "Domain name too long"
        
        if not cls.DOMAIN_PATTERN.match(domain):
            return False, "Invalid domain name format"
        
        return True, ""
    
    @classmethod
    def is_valid(cls, domain: str) -> bool:
        """Quick validation check."""
        valid, _ = cls.validate(domain)
        return valid


class Sanitizer:
    """Input sanitization utilities."""
    
    @staticmethod
    def text(value: str, max_length: int = 1000) -> str:
        """Sanitize text input."""
        if not value:
            return ""
        
        value = str(value).strip()
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @staticmethod
    def alphanumeric(value: str, allow_spaces: bool = True, 
                     allow_dashes: bool = True) -> str:
        """Sanitize to alphanumeric characters."""
        if not value:
            return ""
        
        allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        if allow_spaces:
            allowed += ' '
        if allow_dashes:
            allowed += '-_'
        
        return ''.join(c for c in str(value) if c in allowed)
    
    @staticmethod
    def boolean(value: any) -> bool:
        """Convert value to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
