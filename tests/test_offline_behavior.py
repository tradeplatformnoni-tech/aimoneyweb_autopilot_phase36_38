#!/usr/bin/env python3
"""
Offline Behavior Tests for QuoteService
Tests that QuoteService gracefully handles network failures and uses stale cache
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from trader.quote_service import QuoteService, ValidatedQuote


def create_test_quote(symbol: str, price: float, minutes_ago: int = 0) -> ValidatedQuote:
    """Create a test ValidatedQuote with specified age"""
    timestamp = datetime.now() - timedelta(minutes=minutes_ago)
    spread_pct = 0.0005
    ask_price = price * (1 + spread_pct / 2)
    bid_price = price * (1 - spread_pct / 2)

    return ValidatedQuote(
        symbol=symbol,
        last_price=price,
        ask_price=ask_price,
        bid_price=bid_price,
        timestamp=timestamp,
        source="alpaca",
        sequence_id=1,
    )


def test_offline_with_stale_cache():
    """Test that stale cache is used when APIs fail"""
    print("\n=== Test 1: Offline with Stale Cache ===")

    # Setup
    quote_service = QuoteService()

    # Pre-populate cache with old quote (10 minutes old)
    cached_quote = create_test_quote("BTC-USD", 107000.0, minutes_ago=10)

    with quote_service._lock:
        quote_service._cache["BTC-USD"] = cached_quote

    print("✅ Cache pre-populated with 10-minute-old quote")

    # Mock ALL external APIs to fail
    with patch.object(quote_service, "_fetch_fresh", side_effect=Exception("Network unreachable")):
        # Test: Should return stale cache when use_stale_cache=True
        result = quote_service.get_quote("BTC-USD", max_age=60, use_stale_cache=True)

        assert result is not None, "Should return stale cache when offline"
        assert result.last_price == 107000.0, f"Expected price 107000.0, got {result.last_price}"
        assert result.source == "alpaca", f"Expected source 'alpaca', got {result.source}"

        print("✅ Test passed: Stale cache used when offline")
        print(f"   Price: ${result.last_price:,.2f}")
        print(f"   Age: {result.age_seconds:.0f} seconds")
        print(f"   Source: {result.source}")


def test_fresh_cache_preferred():
    """Test that fresh cache is always returned when available"""
    print("\n=== Test 2: Fresh Cache Preferred ===")

    # Setup
    quote_service = QuoteService()

    # Pre-populate cache with fresh quote (30 seconds old, less than max_age=60)
    fresh_quote = create_test_quote("ETH-USD", 3500.0, minutes_ago=0.5)  # 30 seconds

    with quote_service._lock:
        quote_service._cache["ETH-USD"] = fresh_quote

    print("✅ Cache pre-populated with fresh quote (30s old)")

    # Even if fetch would fail, fresh cache should be returned
    with patch.object(quote_service, "_fetch_fresh", side_effect=Exception("Network unreachable")):
        result = quote_service.get_quote("ETH-USD", max_age=60, use_stale_cache=True)

        assert result is not None, "Should return fresh cache"
        assert result.last_price == 3500.0, f"Expected price 3500.0, got {result.last_price}"
        assert not result.is_stale(60), "Quote should not be stale"

        print("✅ Test passed: Fresh cache returned immediately")
        print(f"   Price: ${result.last_price:,.2f}")
        print(f"   Age: {result.age_seconds:.0f} seconds (fresh)")


def test_no_cache_with_network_failure():
    """Test that None is returned when no cache and network fails"""
    print("\n=== Test 3: No Cache with Network Failure ===")

    # Setup
    quote_service = QuoteService()

    # Clear cache
    with quote_service._lock:
        quote_service._cache.clear()

    print("✅ Cache cleared")

    # Mock network failure
    with patch.object(quote_service, "_fetch_fresh", side_effect=Exception("Network unreachable")):
        result = quote_service.get_quote("SOL-USD", max_age=60, use_stale_cache=True)

        assert result is None, "Should return None when no cache and network fails"

        print("✅ Test passed: None returned when no cache available")


def test_no_stale_cache_when_disabled():
    """Test that stale cache is NOT used when use_stale_cache=False"""
    print("\n=== Test 4: Stale Cache Disabled ===")

    # Setup
    quote_service = QuoteService()

    # Pre-populate cache with stale quote (10 minutes old)
    stale_quote = create_test_quote("SPY", 450.0, minutes_ago=10)

    with quote_service._lock:
        quote_service._cache["SPY"] = stale_quote

    print("✅ Cache pre-populated with stale quote (10 minutes old)")

    # Mock network failure
    with patch.object(quote_service, "_fetch_fresh", side_effect=Exception("Network unreachable")):
        # With use_stale_cache=False, should return None even if stale cache exists
        result = quote_service.get_quote("SPY", max_age=60, use_stale_cache=False)

        assert result is None, "Should return None when use_stale_cache=False and quote is stale"

        print("✅ Test passed: Stale cache ignored when use_stale_cache=False")


def test_circuit_breaker_with_cache():
    """Test that circuit breaker doesn't open when cache is available"""
    print("\n=== Test 5: Circuit Breaker with Cache ===")

    # Setup
    quote_service = QuoteService()

    # Pre-populate cache
    cached_quote = create_test_quote("AAPL", 180.0, minutes_ago=5)

    with quote_service._lock:
        quote_service._cache["AAPL"] = cached_quote

    print("✅ Cache pre-populated")

    # Simulate 10 failures (would normally trigger issues)
    print("   Simulating 10 consecutive network failures...")

    with patch.object(quote_service, "_fetch_fresh", side_effect=Exception("Network unreachable")):
        for i in range(10):
            result = quote_service.get_quote("AAPL", max_age=60, use_stale_cache=True)
            assert result is not None, f"Failed on attempt {i+1} - cache should be returned"

            if i == 0:
                print(f"   Attempt {i+1}: ✅ Cache returned (price: ${result.last_price:.2f})")
            elif i == 9:
                print(
                    f"   Attempt {i+10}: ✅ Cache still returned (price: ${result.last_price:.2f})"
                )

    print("✅ Test passed: Circuit breaker didn't prevent cache usage")
    print("   System continues operating with stale cache")


def test_cache_age_tracking():
    """Test that cache age is tracked correctly"""
    print("\n=== Test 6: Cache Age Tracking ===")

    # Setup
    quote_service = QuoteService()

    # Create quote with known age (5 minutes = 300 seconds)
    cached_quote = create_test_quote("NVDA", 500.0, minutes_ago=5)

    with quote_service._lock:
        quote_service._cache["NVDA"] = cached_quote

    # Get quote and check age
    result = quote_service.get_quote("NVDA", max_age=60, use_stale_cache=True)

    assert result is not None
    age_seconds = result.age_seconds

    # Age should be approximately 300 seconds (5 minutes), allow 10 second tolerance
    assert 290 <= age_seconds <= 310, f"Expected age ~300s, got {age_seconds:.1f}s"

    print("✅ Test passed: Cache age tracked correctly")
    print("   Expected: ~300 seconds")
    print(f"   Actual: {age_seconds:.1f} seconds")


def run_all_tests():
    """Run all offline behavior tests"""
    print("=" * 70)
    print("Offline Behavior Test Suite")
    print("=" * 70)

    tests = [
        test_offline_with_stale_cache,
        test_fresh_cache_preferred,
        test_no_cache_with_network_failure,
        test_no_stale_cache_when_disabled,
        test_circuit_breaker_with_cache,
        test_cache_age_tracking,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ Test failed: {test_func.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Test error: {test_func.__name__}")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
