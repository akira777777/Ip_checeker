"""
IP Checker Pro - Optimized Package
==================================
A high-performance IP geolocation and network investigation platform.

Usage:
    from ip_checker import create_app
    app = create_app()
    
Environment Variables:
    - SECRET_KEY: Flask secret key (auto-generated if not set)
    - LOCAL_ONLY: Restrict to local access (default: true)
    - FLASK_DEBUG: Enable debug mode (default: false)
    - FLASK_HOST: Server host (default: 127.0.0.1)
    - FLASK_PORT: Server port (default: 5000)
    - GEO_CACHE_TTL: Cache TTL in seconds (default: 3600)
    - GEO_LOOKUP_LIMIT: Max geo lookups per scan (default: 50)
"""

__version__ = "2.1.0-optimized"
__author__ = "IP Checker Team"
__license__ = "MIT"

from ip_checker.core.app import create_app
from ip_checker.core.config import get_config
from ip_checker.services.cache import get_cache
from ip_checker.services.geo import get_geo_service
from ip_checker.services.security import get_security_analyzer

__all__ = [
    "create_app",
    "get_config",
    "get_cache", 
    "get_geo_service",
    "get_security_analyzer",
    "__version__"
]

def get_version_info() -> dict:
    """Get detailed version information."""
    import sys
    import platform
    
    return {
        "version": __version__,
        "python": sys.version,
        "platform": platform.platform(),
        "node": platform.node(),
    }
