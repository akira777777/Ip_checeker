# IP Checker Pro - Performance Monitoring Dashboard
# =================================================

import time
import psutil
import threading
from datetime import datetime
from collections import deque
from prometheus_client import Gauge, Histogram, Counter, start_http_server

class PerformanceMonitor:
    """Real-time performance monitoring for IP Checker Pro"""
    
    def __init__(self, port=9090):
        self.port = port
        self.metrics_enabled = True
        
        # Performance metrics
        self.request_duration = Histogram(
            'ipchecker_request_duration_seconds',
            'Request duration in seconds',
            ['endpoint', 'method']
        )
        
        self.active_connections = Gauge(
            'ipchecker_active_connections',
            'Number of active connections'
        )
        
        self.memory_usage = Gauge(
            'ipchecker_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.cpu_usage = Gauge(
            'ipchecker_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.cache_hit_ratio = Gauge(
            'ipchecker_cache_hit_ratio',
            'Cache hit ratio'
        )
        
        self.requests_total = Counter(
            'ipchecker_requests_total',
            'Total number of requests',
            ['endpoint', 'status']
        )
        
        self.errors_total = Counter(
            'ipchecker_errors_total',
            'Total number of errors',
            ['type']
        )
        
        # Data collections for moving averages
        self.response_times = deque(maxlen=1000)
        self.memory_samples = deque(maxlen=100)
        self.cpu_samples = deque(maxlen=100)
        
        # Start monitoring threads
        self._start_monitoring()
        
    def _start_monitoring(self):
        """Start background monitoring threads"""
        # System metrics collector
        system_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        system_thread.start()
        
        # Start Prometheus exporter
        if self.metrics_enabled:
            try:
                start_http_server(self.port)
                print(f"Prometheus metrics available at http://localhost:{self.port}")
            except Exception as e:
                print(f"Failed to start Prometheus server: {e}")
                self.metrics_enabled = False
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        process = psutil.Process()
        
        while True:
            try:
                # Memory usage
                memory_info = process.memory_info()
                self.memory_usage.set(memory_info.rss)
                self.memory_samples.append(memory_info.rss)
                
                # CPU usage
                cpu_percent = process.cpu_percent()
                self.cpu_usage.set(cpu_percent)
                self.cpu_samples.append(cpu_percent)
                
                # Active connections (approximate)
                connections = len(process.connections())
                self.active_connections.set(connections)
                
                time.sleep(5)  # Collect every 5 seconds
                
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                time.sleep(10)
    
    def record_request(self, endpoint, method, duration, status_code):
        """Record request metrics"""
        # Record duration histogram
        self.request_duration.labels(endpoint=endpoint, method=method).observe(duration)
        
        # Record total requests
        self.requests_total.labels(endpoint=endpoint, status=str(status_code)).inc()
        
        # Store for moving average calculation
        self.response_times.append(duration)
    
    def record_error(self, error_type):
        """Record error metrics"""
        self.errors_total.labels(type=error_type).inc()
    
    def update_cache_stats(self, hits, misses):
        """Update cache hit ratio"""
        total = hits + misses
        if total > 0:
            ratio = hits / total
            self.cache_hit_ratio.set(ratio)
    
    def get_performance_report(self):
        """Generate comprehensive performance report"""
        process = psutil.Process()
        
        # Calculate moving averages
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        avg_memory = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        
        # Safely get current values from Prometheus metrics
        try:
            active_connections_value = list(self.active_connections.collect())[0].samples[0].value
        except (IndexError, AttributeError):
            active_connections_value = 0
            
        try:
            cache_hit_ratio_value = list(self.cache_hit_ratio.collect())[0].samples[0].value
        except (IndexError, AttributeError):
            cache_hit_ratio_value = 0.0

        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': {
                'memory_mb': round(avg_memory / 1024 / 1024, 2),
                'cpu_percent': round(avg_cpu, 2),
                'active_connections': int(active_connections_value),
                'uptime_seconds': time.time() - process.create_time()
            },
            'performance_metrics': {
                'avg_response_time_ms': round(avg_response_time * 1000, 2),
                'requests_per_second': len(self.response_times) / 60 if self.response_times else 0,
                'cache_hit_ratio': round(cache_hit_ratio_value, 4)
            },
            'error_metrics': {
                'total_errors': self._get_metric_value(self.errors_total),
                'error_rate': self._calculate_error_rate()
            }
        }
    
    def _get_metric_value(self, metric):
        """Safely get value from Prometheus metric"""
        try:
            return list(metric.collect())[0].samples[0].value
        except (IndexError, AttributeError):
            return 0

    def _calculate_error_rate(self):
        """Calculate error rate percentage"""
        try:
            total_requests = self._get_metric_value(self.requests_total)
            total_errors = self._get_metric_value(self.errors_total)
            
            if total_requests > 0:
                return round((total_errors / total_requests) * 100, 2)
            return 0
        except:
            # Fallback in case of collection issues
            return 0

# Usage example:
# monitor = PerformanceMonitor(port=9090)
# 
# # In your Flask routes:
# @app.before_request
# def before_request():
#     request.start_time = time.time()
# 
# @app.after_request
# def after_request(response):
#     duration = time.time() - request.start_time
#     monitor.record_request(
#         endpoint=request.endpoint or 'unknown',
#         method=request.method,
#         duration=duration,
#         status_code=response.status_code
#     )
#     return response