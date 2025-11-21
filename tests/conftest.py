"""
Pytest configuration and shared fixtures for NeoLight tests.
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return ROOT


@pytest.fixture
def test_data_dir(project_root):
    """Return the test data directory."""
    test_data = project_root / "tests" / "data"
    test_data.mkdir(exist_ok=True)
    return test_data


@pytest.fixture
def sample_state():
    """Sample trading state for testing."""
    return {
        "price_history": {},
        "last_trade": {},
        "trade_count": 0,
        "daily": {
            "start_equity": 100000.0,
        },
    }


@pytest.fixture
def sample_allocations():
    """Sample allocations for testing."""
    return {
        "BTC-USD": 0.15,
        "ETH-USD": 0.10,
        "SOL-USD": 0.08,
        "SPY": 0.20,
        "NVDA": 0.05,
    }
