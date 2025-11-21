#!/bin/bash
# Quick status check for soak test

cd ~/neolight

echo "🔍 Soak Test Status Check"
echo "=========================="
echo ""

# Check if monitor is running
if pgrep -f "soak_test_monitor.sh" > /dev/null; then
    SOAK_PID=$(pgrep -f "soak_test_monitor.sh" | head -1)
    echo "✅ Soak Test Monitor: RUNNING (PID: $SOAK_PID)"
    
    # Check how long it's been running
    START_TIME=$(ps -o lstart= -p $SOAK_PID 2>/dev/null)
    if [ ! -z "$START_TIME" ]; then
        echo "   Started: $START_TIME"
    fi
else
    echo "❌ Soak Test Monitor: NOT RUNNING"
fi

echo ""

# Check SmartTrader
if pgrep -f "smart_trader.py" > /dev/null; then
    ST_PID=$(pgrep -f "smart_trader.py" | head -1)
    MODE=$(cat state/trading_mode.json 2>/dev/null | jq -r '.mode // "UNKNOWN"' || echo "UNKNOWN")
    echo "✅ SmartTrader: RUNNING (PID: $ST_PID)"
    echo "   Mode: $MODE"
    
    # Memory usage
    MEM=$(ps -o rss= -p $ST_PID 2>/dev/null | awk '{print $1/1024}')
    if [ ! -z "$MEM" ]; then
        echo "   Memory: ${MEM}MB"
    fi
else
    echo "❌ SmartTrader: NOT RUNNING"
fi

echo ""

# Check recent activity
echo "📊 Recent Activity:"
if [ -f "/tmp/soak_test.out" ]; then
    echo "   Last 5 checks:"
    tail -5 /tmp/soak_test.out | sed 's/^/   /'
else
    echo "   No activity log yet"
fi

echo ""

# Check for errors
if [ -f "logs/smart_trader.log" ]; then
    ERROR_COUNT=$(grep -c "ERROR\|Exception\|Traceback" logs/smart_trader.log 2>/dev/null || echo "0")
    TRADE_COUNT=$(grep -c "PAPER BUY\|PAPER SELL" logs/smart_trader.log 2>/dev/null || echo "0")
    echo "📈 Statistics:"
    echo "   Errors: $ERROR_COUNT"
    echo "   Trades: $TRADE_COUNT"
fi

echo ""
echo "📁 Full log: tail -f /tmp/soak_test.out"
echo ""

