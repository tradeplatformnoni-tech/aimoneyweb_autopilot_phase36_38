#!/bin/bash
# Real-time health monitoring for SmartTrader

cd ~/neolight

echo "🏥 SmartTrader Health Monitor"
echo "============================"
echo ""

# Check process
if ! pgrep -f smart_trader.py > /dev/null; then
    echo "❌ CRITICAL: SmartTrader is NOT RUNNING!"
    echo "   Restart with: cd trader && python3 smart_trader.py"
    exit 1
fi

ST_PID=$(pgrep -f smart_trader.py | head -1)
MODE=$(cat state/trading_mode.json 2>/dev/null | jq -r '.mode // "UNKNOWN"' || echo "UNKNOWN")

echo "✅ Process Status:"
echo "   PID: $ST_PID"
echo "   Mode: $MODE"
echo "   Memory: $(ps -o rss= -p $ST_PID 2>/dev/null | awk '{printf "%.1f", $1/1024}')MB"
echo "   CPU: $(ps -o %cpu= -p $ST_PID 2>/dev/null | tr -d ' ')%"
echo ""

# Check for recent errors (last 5 minutes)
RECENT_ERRORS=$(tail -500 logs/smart_trader.log 2>/dev/null | grep -E "ERROR|Exception|Traceback" | wc -l | tr -d ' ')
if [ "$RECENT_ERRORS" -gt 0 ]; then
    echo "⚠️  Recent Errors (last 500 lines): $RECENT_ERRORS"
    tail -500 logs/smart_trader.log 2>/dev/null | grep -E "ERROR|Exception|Traceback" | tail -3 | sed 's/^/   /'
else
    echo "✅ No recent errors"
fi
echo ""

# Check trades
RECENT_TRADES=$(tail -500 logs/smart_trader.log 2>/dev/null | grep -E "PAPER BUY|PAPER SELL" | wc -l | tr -d ' ')
if [ "$RECENT_TRADES" -gt 0 ]; then
    echo "📈 Recent PAPER Trades: $RECENT_TRADES"
    tail -500 logs/smart_trader.log 2>/dev/null | grep -E "PAPER BUY|PAPER SELL" | tail -3 | sed 's/^/   /'
else
    echo "⏳ No PAPER trades yet (waiting for signals)"
fi
echo ""

# Check mode consistency
if [ "$MODE" != "PAPER_TRADING_MODE" ]; then
    echo "⚠️  Mode Warning: Expected PAPER_TRADING_MODE, found: $MODE"
else
    echo "✅ Mode: PAPER_TRADING_MODE (correct)"
fi
echo ""

# Check quote service
if grep -q "QuoteService initialized" logs/smart_trader.log 2>/dev/null; then
    echo "✅ QuoteService: Active"
else
    echo "⚠️  QuoteService: Status unknown"
fi
echo ""

# System time
echo "🕐 System Time: $(date)"
echo ""

