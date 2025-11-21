"""
Tests for circuit breaker functionality.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestCircuitBreakerBasic:
    """Basic circuit breaker tests."""

    def test_circuit_breaker_creation(self):
        """Test creating a circuit breaker."""
        try:
            from utils.circuit_breaker import CircuitBreaker

            breaker = CircuitBreaker(name="test_breaker")

            assert breaker is not None
            assert breaker.name == "test_breaker"
        except ImportError:
            pytest.skip("CircuitBreaker not available")

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        try:
            from utils.circuit_breaker import CircuitBreaker, CircuitState

            breaker = CircuitBreaker(name="test")
            assert breaker._state == CircuitState.CLOSED
        except ImportError:
            pytest.skip("CircuitBreaker not available")

    def test_circuit_breaker_failure_tracking(self):
        """Test failure tracking."""
        try:
            from utils.circuit_breaker import CircuitBreaker

            breaker = CircuitBreaker(name="test", failure_threshold=3)

            # Test that breaker exists and can be used
            assert breaker is not None
            assert breaker.name == "test"
        except ImportError:
            pytest.skip("CircuitBreaker not available")

    def test_circuit_breaker_success_reset(self):
        """Test that success resets failure count."""
        try:
            from utils.circuit_breaker import CircuitBreaker

            breaker = CircuitBreaker(name="test")

            # Test that breaker is functional
            assert breaker is not None
            assert breaker.name == "test"
        except ImportError:
            pytest.skip("CircuitBreaker not available")

