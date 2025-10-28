#!/bin/bash
echo "🚀 Starting Phase 1651–1700: Unified AI Strategy Engine"
echo "-----------------------------------------"

# Step 1: Create config directory and symbols list
mkdir -p config

cat > config/symbols.json <<EOF
[
  "BTC/USD", "ETH/USD", "USDT/USD", "BNB/USD", "XRP/USD", "SOL/USD",
  "GOLD", "NVDA", "AAPL", "MSFT", "GOOGL", "SILVER", "AMZN"
]
EOF
echo "📦 Updated config/symbols.json with unified asset list."

# Step 2: Patch strategy daemon if not already patched
DAEMON=tools/strategy_daemon.py

if ! grep -q 'for symbol in symbols' $DAEMON; then
cat > $DAEMON <<EOF
import json
from ai.strategy_engine import run_once

with open("config/symbols.json") as f:
    symbols = json.load(f)

for symbol in symbols:
    run_once(symbol=symbol)
EOF
echo "🛠️ Patched strategy_daemon.py to support multi-asset loop."
else
echo "✔️ strategy_daemon.py already supports multi-asset mode."
fi

# Step 3: Ensure permissions
chmod +x *.sh tools/*.sh
echo "🔐 Script permissions fixed."

# Step 4: Restart backend
pkill -f uvicorn
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted."

# Step 5: Notify user
if [ -f tools/alert_notify.py ]; then
  python3 tools/alert_notify.py "📈 NeoLight Multi-Asset Strategy Activated!"
fi

echo "✅ Unified Multi-Asset Autopilot Complete"

