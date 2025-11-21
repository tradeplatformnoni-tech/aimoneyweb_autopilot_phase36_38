#!/usr/bin/env bash
# fix_smart_trader_final.sh — universal self-healing for indentation and logic blocks

set -euo pipefail
cd "$HOME/neolight/trader"
cp smart_trader.py smart_trader.py.bak_$(date +%Y%m%d_%H%M%S)

python3 - <<'PYCODE'
from pathlib import Path
import textwrap, subprocess, re

path = Path('~/neolight/trader/smart_trader.py').expanduser()
src = path.read_text().splitlines()

# --- Step 1: Normalize leading spaces (no tabs)
src = [l.replace("\t", "    ") for l in src]

# --- Step 2: Auto-fix blank / half-indented blocks (common cause of line 37 errors)
for i, line in enumerate(src[:-1]):
    if re.match(r"^\s*def\s+\w+\(.*\):\s*$", line):
        nxt = src[i+1]
        if nxt.strip() == "" or not nxt.startswith(" "):
            src.insert(i+1, "    pass")

# --- Step 3: Clean imports and stop_flag block (dedent fully)
fixed = []
for line in src:
    if re.match(r"^\s+import\s", line):  # unindent imports
        fixed.append(line.lstrip())
    else:
        fixed.append(line)
src = fixed

# --- Step 4: Re-inject clean helper block if missing
if not any("def calculate_spread" in l for l in src):
    inject = textwrap.dedent("""\
    def calculate_spread(q: dict, mid: float) -> float:
        \"\"\"Compute bid-ask spread in basis points.\"\"\"
        return (q["ask"] - q["bid"]) / max(1e-9, mid) * 10000.0

    def sma(series: list, n: int):
        \"\"\"Simple moving average.\"\"\"
        if len(series) < n:
            return None
        return sum(series[-n:]) / float(n)

    def rsi(prices: list, n: int = 14):
        \"\"\"Relative Strength Index.\"\"\"
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
        \"\"\"Clamp value v between lo and hi.\"\"\"
        return max(lo, min(hi, v))
    """).splitlines()
    # place before Broker Interfaces header
    idx = next((i for i, l in enumerate(src) if "Broker Interfaces" in l), len(src)//2)
    src = src[:idx] + inject + [""] + src[idx:]

# --- Step 5: Write back
path.write_text("\n".join(src))
print("🧠 Clean rewrite applied. Checking syntax…")

res = subprocess.run(["python3", "-m", "py_compile", str(path)], capture_output=True, text=True)
if res.returncode == 0:
    print("✅ smart_trader.py syntax OK — ready to launch!")
else:
    print("❌ Syntax still invalid:")
    print(res.stderr)
PYCODE
