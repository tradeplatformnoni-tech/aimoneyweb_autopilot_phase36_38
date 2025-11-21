#!/usr/bin/env bash
# fix_smart_trader.sh — fixes indentation & replaces broken block in smart_trader.py

set -euo pipefail
cd "$HOME/neolight/trader"

# 1. Backup
cp smart_trader.py smart_trader.py.bak_$(date +%Y%m%d_%H%M%S)
echo "🧩 Backed up smart_trader.py"

# 2. Define the clean block
CLEAN_BLOCK=$(cat <<'BLOCK'
def calculate_spread(q: dict, mid: float) -> float:
    """Compute bid-ask spread in basis points."""
    return (q["ask"] - q["bid"]) / max(1e-9, mid) * 10000.0

def sma(series: list, n: int):
    """Simple moving average."""
    if len(series) < n:
        return None
    return sum(series[-n:]) / float(n)

def rsi(prices: list, n: int = 14):
    """Relative Strength Index."""
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
    """Clamp value v between lo and hi."""
    return max(lo, min(hi, v))
BLOCK
)

# 3. Delete broken lines (around 110–136) and insert the clean block
awk -v block="$CLEAN_BLOCK" 'NR==110{print block} NR<110 || NR>136' smart_trader.py > tmp && mv tmp smart_trader.py
echo "✅ Replaced faulty function block."

# 4. Verify syntax
if python3 -m py_compile smart_trader.py 2>/tmp/err.log; then
  echo "✅ smart_trader.py syntax OK — ready to launch."
else
  echo "❌ Syntax still invalid:"
  cat /tmp/err.log
fi
