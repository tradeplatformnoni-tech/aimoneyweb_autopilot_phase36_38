#!/usr/bin/env python3
"""
Force Trade Script - Bypass all conditions and execute a trade immediately
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))

try:
    from backend.ledger_engine import record_fill
    from trader.smart_trader import PaperBroker, send_telegram
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def force_trade(symbol: str, side: str, quantity: float = None, value: float = None):
    """
    Force execute a trade, bypassing all conditions.

    Args:
        symbol: Trading symbol (e.g., "BTC-USD", "ETH-USD")
        side: "buy" or "sell"
        quantity: Quantity to trade (optional if value provided)
        value: Dollar value to trade (optional if quantity provided)
    """
    print(f"🚀 FORCE TRADE: {side.upper()} {symbol}")

    # Initialize broker
    broker = PaperBroker()

    # Get current price
    quote = broker.fetch_quote(symbol)
    if not quote:
        print(f"❌ Failed to fetch quote for {symbol}")
        return False

    price = (
        quote.get("mid")
        or quote.get("last")
        or quote.get("regularMarketPrice")
        or quote.get("currentPrice")
    )
    if not price:
        print(f"❌ No valid price found for {symbol}")
        return False

    # Calculate quantity if value provided
    if value and not quantity:
        quantity = value / price
    elif not quantity:
        # Default: 1% of portfolio
        portfolio_value = broker.fetch_portfolio_value()
        value = portfolio_value * 0.01
        quantity = value / price

    print(f"📊 Price: ${price:.2f}")
    print(f"📊 Quantity: {quantity:.6f}")
    print(f"📊 Value: ${quantity * price:,.2f}")

    try:
        # Execute trade
        result = broker.submit_order(symbol, side, quantity, price)

        # Record in ledger
        try:
            record_fill(
                symbol,
                side,
                float(quantity),
                float(price),
                float(result.get("fee", 0)),
                note="forced_trade",
            )
        except Exception as e:
            print(f"⚠️ Failed to record in ledger: {e}")

        # Send Telegram notification
        send_telegram(
            f"🚀 FORCED TRADE EXECUTED\n"
            f"{side.upper()} {quantity:.6f} {symbol} @ ${price:.2f}\n"
            f"Value: ${quantity * price:,.2f}\n"
            f"Fee: ${result.get('fee', 0):.2f}",
            include_mode=False,
        )

        print("✅ Trade executed successfully!")
        print(f"   Portfolio Value: ${broker.fetch_portfolio_value():,.2f}")
        print(f"   Cash: ${broker.cash:,.2f}")

        # Update state file
        state_file = ROOT / "state" / "trader_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                state["last_trade"][symbol] = datetime.now(UTC).timestamp()
                state["trade_count"] = state.get("trade_count", 0) + 1
                with open(state_file, "w") as f:
                    json.dump(state, f, indent=2)
                print("✅ State file updated")
            except Exception as e:
                print(f"⚠️ Failed to update state: {e}")

        return True

    except Exception as e:
        print(f"❌ Trade failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 force_trade.py <symbol> <buy|sell> [quantity] [value]")
        print("\nExamples:")
        print("  python3 force_trade.py BTC-USD buy 0.001")
        print("  python3 force_trade.py ETH-USD buy --value 1000")
        print("  python3 force_trade.py SOL-USD sell 1.0")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    side = sys.argv[2].lower()

    if side not in ["buy", "sell"]:
        print(f"❌ Invalid side: {side}. Must be 'buy' or 'sell'")
        sys.exit(1)

    quantity = None
    value = None

    if len(sys.argv) > 3:
        if sys.argv[3] == "--value" and len(sys.argv) > 4:
            value = float(sys.argv[4])
        else:
            quantity = float(sys.argv[3])

    success = force_trade(symbol, side, quantity, value)
    sys.exit(0 if success else 1)
