#!/usr/bin/env python3
"""
World-Class Circuit Breaker Pattern Implementation
--------------------------------------------------
Prevents cascading failures by stopping requests to failing services.
Implements exponential backoff and automatic recovery.
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    World-class circuit breaker with exponential backoff and automatic recovery.

    Features:
    - Exponential backoff for recovery attempts
    - Configurable failure thresholds
    - Automatic state transitions
    - Thread-safe operations
    - Metrics tracking
    - Graceful degradation
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        expected_exception: type = Exception,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name for logging
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes in HALF_OPEN to close circuit
            timeout: Seconds to wait before attempting recovery (exponential backoff)
            expected_exception: Exception type that triggers circuit breaker
            half_open_max_calls: Max calls in HALF_OPEN state before timeout
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._last_success_time: float | None = None
        self._half_open_calls = 0
        self._lock = threading.RLock()

        # Metrics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_changes = []

        logger.info(
            f"🔌 Circuit breaker '{name}' initialized: threshold={failure_threshold}, timeout={timeout}s"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is OPEN
            Exception: Original exception from function
        """
        with self._lock:
            self._total_calls += 1
            current_time = time.time()

            # Check if circuit should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                elapsed = current_time - (self._last_failure_time or 0)
                backoff_time = self._calculate_backoff()

                if elapsed < backoff_time:
                    self._total_failures += 1
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry after {backoff_time - elapsed:.1f}s"
                    )
                else:
                    # Transition to HALF_OPEN
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                    self._state_changes.append(
                        {
                            "time": datetime.now(UTC).isoformat(),
                            "from": "OPEN",
                            "to": "HALF_OPEN",
                            "reason": "timeout_expired",
                        }
                    )
                    logger.info(f"🔄 Circuit breaker '{self.name}' → HALF_OPEN (testing recovery)")

            # Execute function
            try:
                result = func(*args, **kwargs)

                # Success handling
                with self._lock:
                    self._total_successes += 1
                    self._last_success_time = current_time

                    if self._state == CircuitState.HALF_OPEN:
                        self._success_count += 1
                        self._half_open_calls += 1

                        # Close circuit if enough successes
                        if self._success_count >= self.success_threshold:
                            self._state = CircuitState.CLOSED
                            self._failure_count = 0
                            self._success_count = 0
                            self._half_open_calls = 0
                            self._state_changes.append(
                                {
                                    "time": datetime.now(UTC).isoformat(),
                                    "from": "HALF_OPEN",
                                    "to": "CLOSED",
                                    "reason": "recovery_confirmed",
                                }
                            )
                            logger.info(f"✅ Circuit breaker '{self.name}' → CLOSED (recovered)")
                        elif self._half_open_calls >= self.half_open_max_calls:
                            # Too many calls in HALF_OPEN, go back to OPEN
                            self._state = CircuitState.OPEN
                            self._last_failure_time = current_time
                            self._state_changes.append(
                                {
                                    "time": datetime.now(UTC).isoformat(),
                                    "from": "HALF_OPEN",
                                    "to": "OPEN",
                                    "reason": "max_calls_exceeded",
                                }
                            )
                            logger.warning(
                                f"⚠️ Circuit breaker '{self.name}' → OPEN (max calls exceeded)"
                            )
                    elif self._state == CircuitState.CLOSED:
                        # Reset failure count on success
                        self._failure_count = 0

                return result

            except self.expected_exception:
                # Failure handling
                with self._lock:
                    self._total_failures += 1
                    self._failure_count += 1
                    self._last_failure_time = current_time

                    if self._state == CircuitState.HALF_OPEN:
                        # Failed in HALF_OPEN, go back to OPEN
                        self._state = CircuitState.OPEN
                        self._failure_count = self.failure_threshold
                        self._state_changes.append(
                            {
                                "time": datetime.now(UTC).isoformat(),
                                "from": "HALF_OPEN",
                                "to": "OPEN",
                                "reason": "failure_in_half_open",
                            }
                        )
                        logger.warning(
                            f"⚠️ Circuit breaker '{self.name}' → OPEN (failure in HALF_OPEN)"
                        )
                    elif self._state == CircuitState.CLOSED:
                        # Check if threshold reached
                        if self._failure_count >= self.failure_threshold:
                            self._state = CircuitState.OPEN
                            self._state_changes.append(
                                {
                                    "time": datetime.now(UTC).isoformat(),
                                    "from": "CLOSED",
                                    "to": "OPEN",
                                    "reason": "threshold_exceeded",
                                }
                            )
                            logger.error(
                                f"🔴 Circuit breaker '{self.name}' → OPEN (threshold exceeded)"
                            )

                raise

    def _calculate_backoff(self) -> float:
        """Calculate exponential backoff time based on failure count."""
        # Exponential backoff: base_timeout * 2^(failure_count / threshold)
        exponent = min(self._failure_count / max(self.failure_threshold, 1), 5)  # Cap at 5
        backoff = self.timeout * (2**exponent)
        return min(backoff, 3600)  # Cap at 1 hour

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state and metrics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": (
                    datetime.fromtimestamp(self._last_failure_time, UTC).isoformat()
                    if self._last_failure_time
                    else None
                ),
                "last_success_time": (
                    datetime.fromtimestamp(self._last_success_time, UTC).isoformat()
                    if self._last_success_time
                    else None
                ),
                "metrics": {
                    "total_calls": self._total_calls,
                    "total_successes": self._total_successes,
                    "total_failures": self._total_failures,
                    "success_rate": (
                        self._total_successes / self._total_calls * 100
                        if self._total_calls > 0
                        else 0
                    ),
                },
                "state_changes": self._state_changes[-10:],  # Last 10 changes
            }

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            logger.info(f"🔄 Circuit breaker '{self.name}' manually reset to CLOSED")


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is OPEN."""

    pass
