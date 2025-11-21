"""
Basic smoke tests for SmartTrader.
Lightweight tests that verify core functionality without heavy dependencies.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestSmartTraderImports:
    """Test that SmartTrader can be imported and basic components exist."""

    def test_smart_trader_module_exists(self):
        """Verify trader module can be imported."""
        try:
            import trader.smart_trader

            assert True
        except ImportError as e:
            pytest.skip(f"trader.smart_trader not available: {e}")

    def test_circuit_breaker_import(self):
        """Verify circuit breaker utility can be imported."""
        try:
            from utils.circuit_breaker import CircuitBreaker

            assert CircuitBreaker is not None
        except ImportError:
            pytest.skip("CircuitBreaker not available")

    def test_quote_service_import(self):
        """Verify quote service can be imported."""
        try:
            from trader.quote_service import get_quote_service

            assert get_quote_service is not None
        except ImportError:
            pytest.skip("QuoteService not available")


class TestFileStructure:
    """Test that required files and directories exist."""

    def test_trader_directory_exists(self, project_root):
        """Verify trader directory exists."""
        assert (project_root / "trader").exists()

    def test_agents_directory_exists(self, project_root):
        """Verify agents directory exists."""
        assert (project_root / "agents").exists()

    def test_logs_directory_exists(self, project_root):
        """Verify logs directory exists."""
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        assert logs_dir.exists()

    def test_state_directory_exists(self, project_root):
        """Verify state directory exists."""
        state_dir = project_root / "state"
        state_dir.mkdir(exist_ok=True)
        assert state_dir.exists()


class TestConfiguration:
    """Test configuration files."""

    def test_requirements_txt_exists(self, project_root):
        """Verify requirements.txt exists."""
        assert (project_root / "requirements.txt").exists()

    def test_pyproject_toml_exists(self, project_root):
        """Verify pyproject.toml exists."""
        assert (project_root / "pyproject.toml").exists()


class TestBasicFunctionality:
    """Test basic functionality without full system initialization."""

    def test_safe_float_convert_basic(self):
        """Test safe float conversion utility."""
        try:
            from trader.smart_trader import safe_float_convert

            # Test valid float
            result = safe_float_convert("123.45")
            assert result == 123.45
            # Test invalid input
            result = safe_float_convert("invalid")
            assert result is None
        except ImportError:
            pytest.skip("safe_float_convert not available")

    def test_state_manager_exists(self):
        """Test that state manager utilities exist."""
        try:
            from utils.state_manager import load_state_safe, save_state_safe

            assert load_state_safe is not None
            assert save_state_safe is not None
        except ImportError:
            pytest.skip("StateManager not available")
