"""
IP Checker Pro - Utility Helpers
================================
Common utility functions and helpers.
"""

import json
import logging
import platform
import socket
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


class Timer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: float = 0
        self.elapsed: float = 0
    
    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args) -> None:
        self.elapsed = time.perf_counter() - self.start_time
        logger.debug(f"{self.name} took {self.elapsed:.4f}s")
    
    @property
    def milliseconds(self) -> float:
        return self.elapsed * 1000


@dataclass
class HealthStatus:
    """System health status."""
    status: str
    version: str
    timestamp: str
    uptime: float
    platform: str
    hostname: str
    checks: Dict[str, Any]


class HealthChecker:
    """System health checker."""
    
    def __init__(self):
        self.start_time = time.time()
        self._checks: Dict[str, Callable[[], tuple[bool, str]]] = {}
    
    def register(self, name: str, check_func: Callable[[], tuple[bool, str]]) -> None:
        """Register a health check."""
        self._checks[name] = check_func
    
    def check(self) -> HealthStatus:
        """Run all health checks."""
        checks = {}
        all_healthy = True
        
        for name, check_func in self._checks.items():
            try:
                healthy, message = check_func()
                checks[name] = {'healthy': healthy, 'message': message}
                if not healthy:
                    all_healthy = False
            except Exception as e:
                checks[name] = {'healthy': False, 'message': str(e)}
                all_healthy = False
        
        return HealthStatus(
            status='healthy' if all_healthy else 'degraded',
            version='2.1.0-optimized',
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            uptime=time.time() - self.start_time,
            platform=platform.platform(),
            hostname=socket.gethostname(),
            checks=checks
        )


def json_response(data: Any, status: str = 'success', 
                 message: str = None, code: int = 200) -> tuple[dict, int]:
    """Create standardized JSON response."""
    response = {
        'success': status == 'success',
        'status': status,
        'data': data if status == 'success' else None,
        'message': message,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    return response, code


def error_response(message: str, code: int = 400, 
                  details: dict = None) -> tuple[dict, int]:
    """Create standardized error response."""
    response = {
        'success': False,
        'status': 'error',
        'message': message,
        'details': details,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    return response, code


def rate_limit_key(request) -> str:
    """Generate rate limit key from request."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def format_bytes(size: float) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format seconds to human readable."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str, max_requests: int, window: int) -> bool:
        """Check if request is allowed."""
        with self._lock:
            now = time.time()
            
            # Get or create request list
            requests = self._requests.get(key, [])
            
            # Remove old requests
            requests = [r for r in requests if now - r < window]
            
            # Check limit
            if len(requests) >= max_requests:
                self._requests[key] = requests
                return False
            
            # Add current request
            requests.append(now)
            self._requests[key] = requests
            return True
    
    def get_remaining(self, key: str, max_requests: int, window: int) -> int:
        """Get remaining requests in window."""
        with self._lock:
            now = time.time()
            requests = self._requests.get(key, [])
            requests = [r for r in requests if now - r < window]
            return max(0, max_requests - len(requests))


# Import threading for RateLimiter
import threading


def retry(max_attempts: int = 3, delay: float = 1.0, 
         backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
            
            return None  # Should never reach here
        return wrapper
    return decorator


@contextmanager
def suppress_exceptions(*exceptions, default=None, log_msg: str = None):
    """Context manager to suppress exceptions."""
    try:
        yield
    except exceptions as e:
        if log_msg:
            logger.warning(f"{log_msg}: {e}")
        return default


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result
