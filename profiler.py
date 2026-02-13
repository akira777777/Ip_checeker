# IP Checker Pro - Performance Profiling and Optimization Tools
# ==============================================================

import time
import cProfile
import pstats
import io
import psutil
import threading
from functools import wraps
from typing import Any, Callable, Dict, Optional
from collections import defaultdict, deque
from datetime import datetime

class PerformanceProfiler:
    """Advanced performance profiler for monitoring application performance"""
    
    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.profiles = {}
        self.metrics = defaultdict(list)
        self.sampling_thread = None
        self.is_sampling = False
        self.function_timings = defaultdict(lambda: deque(maxlen=1000))
        
    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile individual functions"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                end_memory = psutil.Process().memory_info().rss
                
                # Record timing
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                self.function_timings[func.__name__].append({
                    'execution_time': execution_time,
                    'memory_delta': memory_used,
                    'timestamp': datetime.now()
                })
                
                # Store in metrics
                self.metrics[f'{func.__name__}_time'].append(execution_time)
                self.metrics[f'{func.__name__}_memory'].append(memory_used)
        
        return wrapper
    
    def start_continuous_sampling(self):
        """Start continuous system sampling in background thread"""
        if self.is_sampling:
            return
            
        self.is_sampling = True
        self.sampling_thread = threading.Thread(target=self._sampling_worker, daemon=True)
        self.sampling_thread.start()
        print("📊 Continuous performance sampling started")
    
    def stop_continuous_sampling(self):
        """Stop continuous sampling"""
        self.is_sampling = False
        if self.sampling_thread:
            self.sampling_thread.join(timeout=2)
        print("📊 Continuous performance sampling stopped")
    
    def _sampling_worker(self):
        """Background worker for continuous sampling"""
        process = psutil.Process()
        
        while self.is_sampling:
            try:
                # Sample system metrics
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                connections = len(process.connections())
                
                # Store samples
                self.metrics['cpu_percent'].append(cpu_percent)
                self.metrics['memory_rss'].append(memory_info.rss)
                self.metrics['memory_vms'].append(memory_info.vms)
                self.metrics['active_connections'].append(connections)
                
                time.sleep(self.sample_interval)
                
            except Exception as e:
                print(f"Sampling error: {e}")
                time.sleep(self.sample_interval)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        process = psutil.Process()
        
        # Calculate function statistics
        function_stats = {}
        for func_name, timings in self.function_timings.items():
            if timings:
                times = [t['execution_time'] for t in timings]
                memory_changes = [t['memory_delta'] for t in timings]
                
                function_stats[func_name] = {
                    'call_count': len(timings),
                    'avg_execution_time': sum(times) / len(times),
                    'min_execution_time': min(times),
                    'max_execution_time': max(times),
                    'avg_memory_delta': sum(memory_changes) / len(memory_changes),
                    'total_time': sum(times)
                }
        
        # Calculate system metrics
        system_stats = {}
        for metric_name, values in self.metrics.items():
            if values:
                system_stats[metric_name] = {
                    'current': values[-1] if values else 0,
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'samples': len(values)
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'function_statistics': function_stats,
            'system_metrics': system_stats,
            'process_info': {
                'pid': process.pid,
                'threads': process.num_threads(),
                'uptime': time.time() - process.create_time(),
                'status': process.status()
            }
        }
    
    def export_profile_data(self, filename: str = None) -> str:
        """Export profiling data to file"""
        if not filename:
            filename = f"profile_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        report = self.get_performance_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📈 Profile data exported to {filename}")
        return filename

class MemoryProfiler:
    """Memory usage profiler and leak detector"""
    
    def __init__(self):
        self.baseline_memory = None
        self.checkpoints = {}
        self.object_counts = defaultdict(int)
        
    def set_baseline(self):
        """Set baseline memory usage"""
        process = psutil.Process()
        self.baseline_memory = process.memory_info().rss
        print(f"🎯 Memory baseline set: {self.baseline_memory / 1024 / 1024:.2f} MB")
    
    def create_checkpoint(self, name: str):
        """Create memory usage checkpoint"""
        process = psutil.Process()
        current_memory = process.memory_info().rss
        memory_diff = current_memory - (self.baseline_memory or 0)
        
        self.checkpoints[name] = {
            'memory_usage': current_memory,
            'memory_diff': memory_diff,
            'timestamp': datetime.now()
        }
        
        print(f"📍 Checkpoint '{name}': {current_memory / 1024 / 1024:.2f} MB "
              f"(Δ: {memory_diff / 1024 / 1024:+.2f} MB)")
    
    def detect_memory_leaks(self, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """Detect potential memory leaks"""
        leaks = {}
        threshold_bytes = threshold_mb * 1024 * 1024
        
        for name, checkpoint in self.checkpoints.items():
            if checkpoint['memory_diff'] > threshold_bytes:
                leaks[name] = {
                    'memory_increase_mb': checkpoint['memory_diff'] / 1024 / 1024,
                    'timestamp': checkpoint['timestamp']
                }
        
        return leaks

# Global profiler instances
performance_profiler = PerformanceProfiler()
memory_profiler = MemoryProfiler()

# Convenience decorators
def profile(func: Callable) -> Callable:
    """Convenience decorator for function profiling"""
    return performance_profiler.profile_function(func)

def timed(func: Callable) -> Callable:
    """Simple timing decorator"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            end = time.perf_counter()
            print(f"⏱️  {func.__name__}: {(end - start) * 1000:.2f}ms")
    return wrapper

# Context manager for profiling blocks
class profile_block:
    """Context manager for profiling code blocks"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.start_memory = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        self.start_memory = psutil.Process().memory_info().rss
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_memory = psutil.Process().memory_info().rss
        
        execution_time = (end_time - self.start_time) * 1000  # ms
        memory_delta = (end_memory - self.start_memory) / 1024 / 1024  # MB
        
        print(f"📊 {self.name}: {execution_time:.2f}ms, ΔMemory: {memory_delta:+.2f}MB")

# Example usage:
"""
# Profile a function
@profile
def expensive_operation():
    # Your code here
    pass

# Time a function
@timed
def quick_operation():
    # Your code here
    pass

# Profile a code block
with profile_block("data_processing"):
    # Your processing code here
    pass

# Monitor memory usage
memory_profiler.set_baseline()
# ... some operations ...
memory_profiler.create_checkpoint("after_processing")
leaks = memory_profiler.detect_memory_leaks()
"""