"""
IP Checker Pro - Configuration Management
=========================================
Environment-based configuration with validation and defaults.
"""

import os
import secrets
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass(frozen=True)
class Config:
    """Application configuration with environment variable fallbacks."""
    
    # Flask settings
    SECRET_KEY: str = field(default_factory=lambda: os.environ.get('SECRET_KEY') or secrets.token_hex(32))
    FLASK_DEBUG: bool = field(default_factory=lambda: os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
    FLASK_HOST: str = field(default_factory=lambda: os.environ.get('FLASK_HOST', '127.0.0.1'))
    FLASK_PORT: int = field(default_factory=lambda: int(os.environ.get('FLASK_PORT', '5000')))
    
    # Security settings
    LOCAL_ONLY: bool = field(default_factory=lambda: os.environ.get('LOCAL_ONLY', 'true').lower() == 'true')
    FORCE_HTTPS: bool = field(default_factory=lambda: os.environ.get('FORCE_HTTPS', 'false').lower() == 'true')
    
    # Rate limiting
    RATE_LIMIT_STORAGE: str = field(default_factory=lambda: os.environ.get('RATE_LIMIT_STORAGE', 'memory://'))
    RATE_LIMIT_DEFAULT: str = field(default_factory=lambda: os.environ.get('RATE_LIMIT_DEFAULT', '200 per day,50 per hour'))
    
    # Cache settings
    CACHE_TYPE: str = field(default_factory=lambda: os.environ.get('CACHE_TYPE', 'disk'))
    CACHE_DIR: str = field(default_factory=lambda: os.environ.get('CACHE_DIR', './cache'))
    CACHE_TTL: int = field(default_factory=lambda: int(os.environ.get('CACHE_TTL', '3600')))
    CACHE_MAX_SIZE: int = field(default_factory=lambda: int(os.environ.get('CACHE_MAX_SIZE', '10000')))
    
    # Geolocation settings
    GEO_CACHE_TTL: int = field(default_factory=lambda: int(os.environ.get('GEO_CACHE_TTL', '3600')))
    GEO_LOOKUP_LIMIT: int = field(default_factory=lambda: int(os.environ.get('GEO_LOOKUP_LIMIT', '50')))
    GEO_TIMEOUT: int = field(default_factory=lambda: int(os.environ.get('GEO_TIMEOUT', '5')))
    GEO_MAX_RETRIES: int = field(default_factory=lambda: int(os.environ.get('GEO_MAX_RETRIES', '3')))
    GEO_BACKOFF_FACTOR: float = field(default_factory=lambda: float(os.environ.get('GEO_BACKOFF_FACTOR', '1.0')))
    
    # API endpoints
    GEO_API_URL: str = field(default_factory=lambda: os.environ.get(
        'GEO_API_URL',
        'https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query'
    ))
    
    # Security analysis
    SUSPICIOUS_PORTS: Set[int] = field(default_factory=lambda: {
        23, 69, 1337, 4444, 5555, 6667, 8081, 1433, 3389
    })
    SECURE_PORTS: Set[int] = field(default_factory=lambda: {
        22, 443, 993, 995, 5061
    })
    
    # Connection settings
    CONNECTION_POOL_SIZE: int = field(default_factory=lambda: int(os.environ.get('CONNECTION_POOL_SIZE', '10')))
    CONNECTION_MAX_RETRIES: int = field(default_factory=lambda: int(os.environ.get('CONNECTION_MAX_RETRIES', '3')))
    
    # Logging
    LOG_LEVEL: str = field(default_factory=lambda: os.environ.get('LOG_LEVEL', 'INFO'))
    LOG_FILE: Optional[str] = field(default_factory=lambda: os.environ.get('LOG_FILE', 'app.log'))
    LOG_FORMAT: str = field(default_factory=lambda: os.environ.get(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    ))
    
    # Feature flags
    ENABLE_METRICS: bool = field(default_factory=lambda: os.environ.get('ENABLE_METRICS', 'true').lower() == 'true')
    ENABLE_SWAGGER: bool = field(default_factory=lambda: os.environ.get('ENABLE_SWAGGER', 'false').lower() == 'true')
    
    # Content Security Policy
    CSP: dict = field(default_factory=lambda: {
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com", "data:"],
        'img-src': ["'self'", "data:", "https://*.tile.openstreetmap.org", "https://unpkg.com", "blob:"],
        'connect-src': "'self'",
        'worker-src': "'self' blob:",
    })
    
    # Local networks (CIDR notation)
    LOCAL_NETWORKS: List[str] = field(default_factory=lambda: [
        '127.0.0.0/8',
        '::1/128',
        '10.0.0.0/8',
        '172.16.0.0/12',
        '192.168.0.0/16',
        'fc00::/7',
        'fe80::/10',
    ])
    
    @property
    def version(self) -> str:
        """Get application version."""
        return "2.1.0-optimized"
    
    def to_dict(self) -> dict:
        """Convert config to dictionary (for debugging)."""
        return {
            k: list(v) if isinstance(v, set) else v
            for k, v in self.__dict__.items()
        }
    
    def get_rate_limits(self) -> List[str]:
        """Parse rate limit string into list."""
        return [limit.strip() for limit in self.RATE_LIMIT_DEFAULT.split(',')]


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Force reload configuration from environment."""
    global _config
    _config = Config()
    return _config
