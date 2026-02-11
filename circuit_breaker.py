# IP Checker Pro - Circuit Breaker Pattern Implementation
# ======================================================

import time
import threading
from enum import Enum
from typing import Any, Callable, Optional
from functools import wraps

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Fail-fast mode
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external API calls.
    Prevents cascading failures when external services are unavailable.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: tuple = (Exception,),
        fallback_function: Optional[Callable] = None
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.fallback_function = fallback_function
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.lock = threading.RLock()
        
        # Statistics
        self.total_calls = 0
        self.failed_calls = 0
        self.successful_calls = 0
        self.open_events = 0
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker logic"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            self.total_calls += 1
            
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._set_state(CircuitState.HALF_OPEN)
                else:
                    return self._handle_open_state(func, *args, **kwargs)
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure(e)
                if self.fallback_function:
                    return self.fallback_function(*args, **kwargs)
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.timeout
    
    def _handle_open_state(self, func: Callable, *args, **kwargs) -> Any:
        """Handle calls when circuit is open"""
        self.failed_calls += 1
        if self.fallback_function:
            return self.fallback_function(*args, **kwargs)
        raise CircuitBreakerOpenException(
            f"Circuit breaker is OPEN for {func.__name__}. "
            f"Last failure: {self.last_failure_time}"
        )
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self._set_state(CircuitState.CLOSED)
        self.successful_calls += 1
        self.failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        self.failed_calls += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self._set_state(CircuitState.OPEN)
        elif self.failure_count >= self.failure_threshold:
            self._set_state(CircuitState.OPEN)
    
    def _set_state(self, new_state: CircuitState):
        """Change circuit breaker state"""
        old_state = self.state
        self.state = new_state
        
        if new_state == CircuitState.OPEN:
            self.open_events += 1
            print(f"🔌 Circuit breaker OPENED: {old_state} → {new_state}")
        elif new_state == CircuitState.CLOSED:
            print(f"🔌 Circuit breaker CLOSED: {old_state} → {new_state}")
        elif new_state == CircuitState.HALF_OPEN:
            print(f"🔌 Circuit breaker HALF-OPEN: {old_state} → {new_state}")
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        total_attempts = self.successful_calls + self.failed_calls
        success_rate = (self.successful_calls / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'success_rate': round(success_rate, 2),
            'open_events': self.open_events,
            'last_failure_time': self.last_failure_time
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            print("🔌 Circuit breaker manually RESET")

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass

# Pre-configured circuit breakers for different services
class ServiceCircuitBreakers:
    """Factory for common service circuit breakers"""
    
    @staticmethod
    def geolocation_api(fallback_function=None):
        """Circuit breaker for geolocation APIs"""
        return CircuitBreaker(
            failure_threshold=3,
            timeout=30.0,
            expected_exception=(Exception,),
            fallback_function=fallback_function
        )
    
    @staticmethod
    def external_api(fallback_function=None):
        """General purpose circuit breaker for external APIs"""
        return CircuitBreaker(
            failure_threshold=5,
            timeout=60.0,
            expected_exception=(Exception,),
            fallback_function=fallback_function
        )
    
    @staticmethod
    def database_connection(fallback_function=None):
        """Circuit breaker for database connections"""
        return CircuitBreaker(
            failure_threshold=3,
            timeout=15.0,
            expected_exception=(Exception,),
            fallback_function=fallback_function
        )

# Decorators for easy usage
def geolocation_circuit_breaker(fallback_func=None):
    """Decorator for geolocation API calls"""
    cb = ServiceCircuitBreakers.geolocation_api(fallback_func)
    return cb

def external_api_circuit_breaker(fallback_func=None):
    """Decorator for external API calls"""
    cb = ServiceCircuitBreakers.external_api(fallback_func)
    return cb

# Example usage:
"""
@circuit_breaker.geolocation_circuit_breaker(
    fallback_function=lambda ip: {
        'status': 'error',
        'message': 'Service temporarily unavailable',
        'ip': ip
    }
)
def get_geolocation_from_api(ip_address):
    # Your API call logic here
    response = requests.get(f"https://api.example.com/geo/{ip_address}")
    response.raise_for_status()
    return response.json()

# Manual usage:
cb = CircuitBreaker(failure_threshold=3, timeout=30)

@cb
def risky_operation():
    # Some risky external call
    pass

# Check statistics
stats = cb.get_stats()
print(f"Circuit state: {stats['state']}")
print(f"Success rate: {stats['success_rate']}%")
"""