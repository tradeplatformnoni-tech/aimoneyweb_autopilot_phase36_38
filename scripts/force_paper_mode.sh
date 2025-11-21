#!/bin/bash
# Force transition to PAPER_TRADING_MODE (safe if test sells already completed)

cd ~/neolight

echo "🔧 Force Paper Trading Mode Transition"
echo "======================================="
echo ""

# Check current state
CURRENT_MODE=$(cat state/trader_state.json 2>/dev/null | jq -r '.trading_mode // "TEST_MODE"')
TEST_SELLS=$(cat state/trader_state.json 2>/dev/null | jq -r '.test_sells // 0')

echo "Current mode: $CURRENT_MODE"
echo "Test sells: $TEST_SELLS"
echo ""

if [ "$CURRENT_MODE" = "PAPER_TRADING_MODE" ]; then
    echo "✅ Already in PAPER_TRADING_MODE"
    exit 0
fi

if [ "$TEST_SELLS" -lt 1 ]; then
    echo "⚠️ Warning: Only $TEST_SELLS test sell(s) recorded"
    echo "   Recommended: Complete at least 1 test sell first"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🔄 Updating mode to PAPER_TRADING_MODE..."
echo ""

# Update trading_mode.json
cat > state/trading_mode.json << EOF
{
  "mode": "PAPER_TRADING_MODE",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "reason": "Manual transition (force)",
  "test_sell_count": $TEST_SELLS
}
EOF

# Update trader_state.json
python3 << 'PYEOF'
import json
from pathlib import Path
from datetime import datetime, timezone

state_file = Path("state/trader_state.json")
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)
    
    state["trading_mode"] = "PAPER_TRADING_MODE"
    state["mode_transition_timestamp"] = datetime.now(timezone.utc).isoformat()
    state["mode_transition_reason"] = "Manual transition (force)"
    
    with open(state_file, "w") as f:
        json.dump(state, f, indent=4)
    
    print("✅ Updated trader_state.json")
else:
    print("❌ trader_state.json not found")
PYEOF

echo ""
echo "✅ Mode transition complete!"
echo ""
echo "Next steps:"
echo "1. Restart SmartTrader: pkill -f smart_trader.py && python3 trader/smart_trader.py"
echo "2. Verify mode: cat state/trading_mode.json"
echo ""

