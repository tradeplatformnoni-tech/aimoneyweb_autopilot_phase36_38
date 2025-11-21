#!/bin/bash
# Diagnose Mode Transition Issues

cd ~/neolight

echo "🔍 NeoLight Mode Transition Diagnostics"
echo "========================================"
echo ""

echo "1️⃣ Current State Files:"
echo "   trading_mode.json:"
cat state/trading_mode.json 2>/dev/null | jq '.' || echo "   ❌ Not found or invalid"
echo ""

echo "   trader_state.json (relevant fields):"
cat state/trader_state.json 2>/dev/null | jq '{trading_mode, test_sells, trade_count, test_trade_executed}' || echo "   ❌ Not found or invalid"
echo ""

echo "2️⃣ Recent Log Analysis:"
echo "   Test Sells Found:"
grep -c "TEST SELL" logs/smart_trader.log 2>/dev/null | xargs echo "   Count:" || echo "   ❌ No logs"
echo ""

echo "   Mode Transition Attempts:"
grep -c "Switching from TEST_MODE" logs/smart_trader.log 2>/dev/null | xargs echo "   Count:" || echo "   ❌ None found"
echo ""

echo "   Last 5 Test Sells:"
grep "TEST SELL" logs/smart_trader.log 2>/dev/null | tail -5 | sed 's/^/   /'
echo ""

echo "3️⃣ Transition Logic Check:"
echo "   Expected: test_sells >= 2 triggers transition"
echo "   Current: test_sells = $(cat state/trader_state.json 2>/dev/null | jq -r '.test_sells // 0')"
echo ""

echo "4️⃣ Recommendations:"
CURRENT_COUNT=$(cat state/trader_state.json 2>/dev/null | jq -r '.test_sells // 0')
if [ "$CURRENT_COUNT" -ge 2 ]; then
    echo "   ✅ Transition should trigger (test_sells=$CURRENT_COUNT >= 2)"
    echo "   → Check if transition code is executing"
    echo "   → Verify logs for transition messages"
elif [ "$CURRENT_COUNT" -eq 1 ]; then
    echo "   ⏳ Need 1 more test sell (test_sells=$CURRENT_COUNT/2)"
    echo "   → Wait for next sell or force transition"
else
    echo "   ⏳ Need $((2 - CURRENT_COUNT)) more test sells (test_sells=$CURRENT_COUNT/2)"
    echo "   → Wait for test sells to complete"
fi
echo ""

