#!/usr/bin/env python3
"""
Force a test PAPER trade immediately
This bypasses signal generation and directly executes a trade
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))


def force_test_trade():
    """Force a test PAPER trade by directly calling broker"""

    print("🧪 Force Test PAPER Trade")
    print("=" * 50)
    print("")

    # Import after path setup
    try:
        from trader.quote_service import atomic_trade_context, get_quote_service
        from trader.smart_trader import PaperBroker, safe_float_convert
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running from neolight directory")
        return False

    # Initialize broker
    print("💰 Initializing broker...")
    broker = PaperBroker()

    # Check mode
    mode_file = ROOT / "state" / "trading_mode.json"
    if mode_file.exists():
        with open(mode_file) as f:
            mode_data = json.load(f)
        current_mode = mode_data.get("mode", "UNKNOWN")
        print(f"✅ Mode: {current_mode}")
    else:
        print("⚠️  Mode file not found")

    # Choose symbol
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "SPY", "QQQ", "AAPL"]
    print("")
    print("Available symbols:")
    for i, sym in enumerate(symbols, 1):
        print(f"  {i}. {sym}")

    choice = input("\nSelect symbol (1-6, default BTC-USD): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(symbols):
        test_symbol = symbols[int(choice) - 1]
    else:
        test_symbol = symbols[0]  # Default BTC-USD

    print(f"✅ Selected: {test_symbol}")
    print("")

    # Get quote - use broker's method (more reliable)
    print("📊 Fetching quote...")
    quote = broker.fetch_quote(test_symbol)
    if not quote:
        print(f"❌ Could not fetch quote for {test_symbol}")
        print("   Trying quote service...")
        try:
            quote_service = get_quote_service()
            if quote_service:
                with atomic_trade_context(
                    quote_service, test_symbol, max_age=60
                ) as validated_quote:
                    test_price = float(validated_quote.last_price)
                    print(f"✅ Quote (QuoteService): ${test_price:,.2f}")
            else:
                print("❌ QuoteService not available")
                return False
        except Exception as e:
            print(f"❌ QuoteService failed: {e}")
            return False
    else:
        test_price = safe_float_convert(
            quote.get("mid")
            or quote.get("last")
            or quote.get("regularMarketPrice")
            or quote.get("currentPrice"),
            symbol=test_symbol,
            context="force test trade",
        )
        if test_price is None:
            print(f"❌ Invalid price from quote: {quote}")
            return False
        print(f"✅ Quote (Broker): ${test_price:,.2f}")

    # Calculate quantity
    if test_symbol == "BTC-USD":
        test_qty = 0.001
    elif test_symbol == "ETH-USD":
        test_qty = 0.01
    else:
        test_qty = max(0.001, 50.0 / test_price)  # $50 worth

    print(f"📊 Quantity: {test_qty:.4f}")
    print(f"💰 Trade Value: ${test_qty * test_price:,.2f}")
    print("")

    # Confirm
    confirm = input("Execute PAPER BUY trade? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled")
        return False

    print("")
    print("🚀 Executing PAPER BUY trade...")

    try:
        result = broker.submit_order(test_symbol, "buy", test_qty, test_price)

        print("")
        print("✅ TRADE EXECUTED!")
        print(f"   Symbol: {test_symbol}")
        print("   Side: BUY")
        print(f"   Quantity: {test_qty:.4f}")
        print(f"   Price: ${test_price:,.2f}")
        print(f"   Fee: ${result.get('fee', 0):.2f}")
        print(f"   Total Cost: ${test_qty * test_price + result.get('fee', 0):,.2f}")
        print("")
        print("📊 Portfolio Status:")
        print(f"   Cash: ${broker.cash:,.2f}")
        print(f"   Equity: ${broker.equity:,.2f}")
        print(f"   Position: {broker.get_position(test_symbol)}")
        print("")
        print("✅ Test trade successful!")

        return True

    except Exception as e:
        print(f"❌ Trade execution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    force_test_trade()
