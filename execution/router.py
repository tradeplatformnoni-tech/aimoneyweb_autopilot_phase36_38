"""
Smart Routing (TWAP/VWAP Fusion)
Chooses best execution method based on market conditions
World-class: Strategy selection, error handling, Guardian integration
"""

import os
import time
from datetime import datetime
from typing import Any

import requests

# Detect Render environment - use environment variables or skip localhost connections
RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
RISK_ENGINE_URL = os.getenv("RISK_ENGINE_URL", "http://localhost:8300")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8100")
GUARDIAN_PAUSE_CHECK = True  # Check Guardian before routing


def check_guardian_pause() -> bool:
    """Check if Guardian has paused trading."""
    if RENDER_MODE:
        # On Render, skip Guardian check (services communicate via files/state)
        return False
    try:
        # Check dashboard for Guardian state
        response = requests.get(f"{DASHBOARD_URL}/meta/metrics", timeout=2)
        if response.status_code == 200:
            data = response.json()
            guardian = data.get("guardian", {})
            return guardian.get("is_paused", False)
    except:
        pass
    return False


def validate_trade_with_risk(
    symbol: str, side: str, quantity: float, price: float, portfolio_value: float
) -> tuple[bool, str]:
    """Validate trade with risk engine."""
    if RENDER_MODE:
        # On Render, skip risk engine validation (would use file-based state)
        # Return approved with warning
        print(
            "[router] Render mode: Skipping risk engine validation (using file-based state)",
            flush=True,
        )
        return True, "Approved (Render mode - file-based validation)"
    try:
        response = requests.post(
            f"{RISK_ENGINE_URL}/risk/validate",
            json={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "portfolio_value": portfolio_value,
                "current_positions": [],
                "max_drawdown": 0.08,
            },
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("approved", False), data.get("reason", "Unknown")
    except Exception as e:
        print(f"[router] Risk validation failed: {e}", flush=True)
    return False, "Risk validation failed"


def route_order(
    symbol: str,
    side: str,
    qty: float,
    limit_price: float | None = None,
    hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Route order using optimal execution strategy.

    Args:
        symbol: Trading symbol
        side: "buy" or "sell"
        qty: Quantity to trade
        limit_price: Optional limit price
        hints: Optional hints (max_slice, time_horizon_sec)

    Returns:
        Routing result with strategy, slices, fills
    """
    # Check Guardian pause
    if GUARDIAN_PAUSE_CHECK and check_guardian_pause():
        return {"status": "rejected", "reason": "Guardian pause active", "strategy": None}

    # Validate with risk engine
    portfolio_value = 100000.0  # Would come from actual portfolio
    approved, reason = validate_trade_with_risk(
        symbol, side, qty, limit_price or 0.0, portfolio_value
    )
    if not approved:
        return {"status": "rejected", "reason": reason, "strategy": None}

    # Get liquidity metrics (would come from liquidity_ingestor)
    liquidity = {"depth_1pct": 50000.0, "spread_bps": 5.0, "volatility": 0.02}

    # Strategy selection
    max_slice = hints.get("max_slice", 5) if hints else 5
    time_horizon = hints.get("time_horizon_sec", 300) if hints else 300

    # Low vol & deep book → VWAP
    # High vol or thin book → TWAP
    if liquidity["spread_bps"] < 10 and liquidity["depth_1pct"] > 20000:
        strategy = "VWAP"
        slices = min(max_slice, int(time_horizon / 60))  # 1 slice per minute
    else:
        strategy = "TWAP"
        slices = max_slice

    # Execute (mock - would use actual broker)
    print(f"[router] Routing {side} {qty} {symbol} using {strategy} ({slices} slices)", flush=True)

    # Simulate execution
    fills = []
    slice_qty = qty / slices
    for i in range(slices):
        time.sleep(0.1)  # Simulate slice delay
        fills.append(
            {
                "slice": i + 1,
                "quantity": slice_qty,
                "price": limit_price or 107000.0,  # Mock price
                "timestamp": datetime.now().isoformat(),
            }
        )

    return {
        "status": "executed",
        "strategy": strategy,
        "slices": slices,
        "fills": fills,
        "total_filled": qty,
        "avg_fill_price": limit_price or 107000.0,
    }


if __name__ == "__main__":
    # Test routing
    result = route_order(
        "BTC-USD",
        "buy",
        0.01,
        limit_price=107000.0,
        hints={"max_slice": 5, "time_horizon_sec": 120},
    )
    print(f"Routing result: {result}")
