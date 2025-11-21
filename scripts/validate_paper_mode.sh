#!/bin/bash
# Validate PAPER_TRADING_MODE is working correctly

cd ~/neolight

echo "🔍 PAPER_TRADING_MODE Validation"
echo "=================================="
echo ""

# Check mode files
echo "1️⃣ Mode Files:"
if [ -f "state/trading_mode.json" ]; then
    MODE=$(cat state/trading_mode.json | jq -r '.mode // "NOT_SET"')
    echo "   trading_mode.json: $MODE"
    if [ "$MODE" = "PAPER_TRADING_MODE" ]; then
        echo "   ✅ Mode file correct"
    else
        echo "   ⚠️ Expected PAPER_TRADING_MODE, found: $MODE"
    fi
else
    echo "   ❌ trading_mode.json not found"
fi

STATE_MODE=$(cat state/trader_state.json 2>/dev/null | jq -r '.trading_mode // "NOT_SET"')
echo "   trader_state.json: $STATE_MODE"
if [ "$STATE_MODE" = "PAPER_TRADING_MODE" ]; then
    echo "   ✅ State file correct"
else
    echo "   ⚠️ Expected PAPER_TRADING_MODE, found: $STATE_MODE"
fi

echo ""

# Check running process
echo "2️⃣ SmartTrader Process:"
if pgrep -f "smart_trader.py" > /dev/null; then
    PID=$(pgrep -f "smart_trader.py" | head -1)
    echo "   ✅ Running (PID: $PID)"
    
    # Check recent logs
    echo ""
    echo "3️⃣ Recent Activity (last 20 lines):"
    tail -20 /tmp/smart_trader_run.log 2>/dev/null | grep -E "PAPER|Mode|TEST|Transition" | tail -5 || echo "   No recent activity"
else
    echo "   ❌ Not running"
fi

echo ""
echo "4️⃣ Recent Trades:"
grep -E "PAPER BUY|PAPER SELL|TEST BUY|TEST SELL" logs/smart_trader.log 2>/dev/null | tail -5 | sed 's/^/   /' || echo "   No trades found"

echo ""
echo "5️⃣ Performance Metrics:"
if curl -s http://localhost:8100/meta/metrics > /dev/null 2>&1; then
    echo "   ✅ Dashboard accessible"
    curl -s http://localhost:8100/meta/metrics | jq '.' 2>/dev/null | head -10 || echo "   ⚠️ Could not parse metrics"
else
    echo "   ⚠️ Dashboard not accessible (may be normal if not running)"
fi

echo ""
echo "✅ Validation complete!"
echo ""

