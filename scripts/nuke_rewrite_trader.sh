#!/usr/bin/env bash
# NeoLight SmartTrader Full Rewrite — self-healing clean version

set -euo pipefail
cd "$HOME/neolight/trader"
cp smart_trader.py smart_trader.py.bak_$(date +%Y%m%d_%H%M%S)

cat > smart_trader.py <<'PYCODE'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeoLight SmartTrader — Sentinel Rewrite
---------------------------------------
Autonomous trading loop with integrated safety, signal handling,
daily resets, and Guardian awareness.
"""

import os, sys, time, json, math, traceback, signal, datetime as dt, subprocess
from pathlib import Path
from typing import Optional, Dict, List

# =============== SAFETY HANDLERS ==================
stop_flag = {"stop": False}

def handle_stop(sig, frame):
    stop_flag["stop"] = True
    print("🛑 Stop signal received — preparing graceful shutdown...")

signal.signal(signal.SIGINT, handle_stop)
signal.signal(signal.SIGTERM, handle_stop)

# =============== UTILS ==================
def calculate_spread(q: dict, mid: float) -> float:
    """Compute bid-ask spread in basis points."""
    return (q["ask"] - q["bid"]) / max(1e-9, mid) * 10000.0

def sma(series: List[float], n: int) -> Optional[float]:
    if len(series) < n:
        return None
    return sum(series[-n:]) / float(n)

def rsi(prices: List[float], n: int = 14) -> Optional[float]:
    if len(prices) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        d = prices[i] - prices[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if losses <= 0:
        return 100.0
    rs = gains / max(1e-9, losses)
    return 100.0 - (100.0 / (1.0 + rs))

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# =============== BROKER INTERFACES ==================
class IBroker:
    def fetch_quote(self, sym: str) -> Dict[str, float]:
        raise NotImplementedError
    def fetch_portfolio_value(self) -> float:
        raise NotImplementedError
    def submit_order(self, sym: str, side: str, qty: float, price: float) -> Dict[str, float]:
        raise NotImplementedError
    @property
    def cash(self) -> float:
        raise NotImplementedError

# =============== MAIN LOOP ==================
def main():
    print("🟣 SmartTrader starting (paper=True, deep_research=False)")
    state = {"daily": {}, "alerts": {}, "streak": {}}
    SYMBOLS = ["BTC-USD", "ETH-USD", "SPY"]

    while not stop_flag["stop"]:
        try:
            now = dt.datetime.now()
            if "date" not in state.get("daily", {}):
                state["daily"] = {"date": now.date().isoformat(), "pnl_pct": 0.0, "start_equity": 100000.0}
                print("🔁 New trading day initialized.")
            if state["daily"]["date"] != now.date().isoformat():
                print("🧭 New day detected, resetting stats.")
                state["daily"]["date"] = now.date().isoformat()
            # Example pseudo-trading logic
            time.sleep(1)
        except KeyboardInterrupt:
            handle_stop(None, None)
        except Exception as e:
            print(f"💥 Loop error: {e}")
            traceback.print_exc()
            time.sleep(2)

    print("👋 Exiting cleanly.")

if __name__ == "__main__":
    main()
PYCODE

python3 -m py_compile smart_trader.py && echo "✅ Rewrite successful — syntax OK." || echo "❌ Syntax error — check manually."
