"""
Helper utilities with performance optimizations.
"""

import atexit
import os
import platform
import socket
import tempfile
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil


class TempFileManager:
    """Singleton manager for temporary file cleanup."""
    
    _instance = None
    _files: set = set()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            atexit.register(cls._cleanup_all)
        return cls._instance
    
    def register(self, filepath: str) -> None:
        """Register a temp file for cleanup."""
        self._files.add(filepath)
    
    def unregister(self, filepath: str) -> None:
        """Unregister a file (e.g., after successful download)."""
        self._files.discard(filepath)
    
    @classmethod
    def _cleanup_all(cls):
        """Cleanup all registered temp files on exit."""
        for filepath in list(cls._files):
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except OSError:
                pass
        cls._files.clear()


# Global temp file manager instance
temp_manager = TempFileManager()


def get_system_info() -> Dict[str, Any]:
    """Get optimized system information."""
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "timestamp": datetime.now().isoformat(),
        "python_version": platform.python_version(),
    }


def get_network_interfaces() -> List[Dict[str, Any]]:
    """Get network interfaces with error handling."""
    interfaces = []
    
    try:
        for iface_name, addrs in psutil.net_if_addrs().items():
            iface = {"name": iface_name, "addresses": []}
            
            for addr in addrs:
                if addr.family not in (socket.AF_INET, socket.AF_INET6):
                    continue
                
                iface["addresses"].append({
                    "family": "IPv4" if addr.family == socket.AF_INET else "IPv6",
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                })
            
            interfaces.append(iface)
    except Exception:
        pass
    
    return interfaces


def safe_process_name(pid: Optional[int]) -> str:
    """Safely get process name by PID with caching."""
    if not pid:
        return "unknown"
    
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "unknown"


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 ** 2:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 ** 3:
        return f"{bytes_val / (1024 ** 2):.1f} MB"
    else:
        return f"{bytes_val / (1024 ** 3):.1f} GB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def get_top_items(items: List[str], n: int = 5) -> List[tuple]:
    """Get top N items with counts using Counter."""
    counter = Counter(items)
    return counter.most_common(n)


class SimpleCache:
    """Simple TTL cache implementation."""
    
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, tuple] = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            expires_at, value = self._cache[key]
            if datetime.now().timestamp() < expires_at:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        expires_at = datetime.now().timestamp() + ttl
        self._cache[key] = (expires_at, value)
    
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
    
    def keys(self) -> List[str]:
        """Get all valid keys."""
        now = datetime.now().timestamp()
        return [k for k, (expires_at, _) in self._cache.items() if now < expires_at]
    
    def __len__(self) -> int:
        """Return number of cached items."""
        return len(self.keys())
