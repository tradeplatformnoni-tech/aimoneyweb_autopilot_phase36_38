"""
World-Class Stability Utilities
--------------------------------
Circuit breakers, retry logic, health checks, state management, and structured logging.
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState
from .health_check import (
    HealthCheck,
    HealthStatus,
    check_api_endpoint,
    check_file_exists,
    check_process_running,
)
from .retry import RetryStrategy, retry_on_api_error, retry_on_network_error, retry_with_backoff
from .state_manager import StateManager, load_state_safe, save_state_safe
from .structured_logging import (
    CorrelationFilter,
    StructuredFormatter,
    log_with_context,
    setup_structured_logging,
)

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
    # Retry
    "retry_with_backoff",
    "retry_on_network_error",
    "retry_on_api_error",
    "RetryStrategy",
    # Health check
    "HealthCheck",
    "HealthStatus",
    "check_process_running",
    "check_file_exists",
    "check_api_endpoint",
    # State management
    "StateManager",
    "load_state_safe",
    "save_state_safe",
    # Logging
    "setup_structured_logging",
    "log_with_context",
    "StructuredFormatter",
    "CorrelationFilter",
]
