#!/bin/bash
# 24-Hour Soak Test Monitor for PAPER_TRADING_MODE

cd ~/neolight

DURATION=${1:-86400}  # Default 24 hours (86400 seconds)
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))

echo "🧪 Starting 24-Hour Soak Test"
echo "=============================="
echo ""
echo "Start Time: $(date)"
echo "End Time: $(date -r $END_TIME)"
echo "Duration: $((DURATION / 3600)) hours"
echo ""

# Create monitoring log
MONITOR_LOG="logs/soak_test_$(date +%Y%m%d_%H%M%S).log"
echo "Monitoring log: $MONITOR_LOG"
echo ""

# Initial state
INITIAL_ERRORS=$(grep -c "ERROR\|Exception\|Traceback" logs/smart_trader.log 2>/dev/null || echo "0")
INITIAL_TRADES=$(grep -c "PAPER BUY\|PAPER SELL" logs/smart_trader.log 2>/dev/null || echo "0")

echo "Initial State:"
echo "  Errors: $INITIAL_ERRORS"
echo "  Trades: $INITIAL_TRADES"
echo ""

# Check every 5 minutes
CHECK_INTERVAL=300
CHECK_COUNT=0

while [ $(date +%s) -lt $END_TIME ]; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    CURRENT_TIME=$(date)
    ELAPSED=$((($(date +%s) - START_TIME) / 60))
    
    echo "[$CURRENT_TIME] Check #$CHECK_COUNT (Elapsed: ${ELAPSED} minutes)" >> $MONITOR_LOG
    
    # Check if SmartTrader is running
    if ! pgrep -f "smart_trader.py" > /dev/null; then
        echo "[$CURRENT_TIME] ❌ CRITICAL: SmartTrader process not found!" | tee -a $MONITOR_LOG
        echo "Attempting restart..."
        cd trader && ALPACA_API_KEY="PKFMRWR2GQKENN4ARPHYMCGIBH" ALPACA_API_SECRET="5VNKFg2aiaECmjsUDZseBkbq8WH8Ancmd3nKMiXzDTh1" NEOLIGHT_USE_ALPACA_QUOTES="true" python3 smart_trader.py > /tmp/smart_trader_run.log 2>&1 &
        sleep 5
    else
        echo "[$CURRENT_TIME] ✅ SmartTrader running" >> $MONITOR_LOG
    fi
    
    # Count errors (new since start)
    CURRENT_ERRORS=$(grep -c "ERROR\|Exception\|Traceback" logs/smart_trader.log 2>/dev/null || echo "0")
    NEW_ERRORS=$((CURRENT_ERRORS - INITIAL_ERRORS))
    
    # Count trades
    CURRENT_TRADES=$(grep -c "PAPER BUY\|PAPER SELL" logs/smart_trader.log 2>/dev/null || echo "0")
    NEW_TRADES=$((CURRENT_TRADES - INITIAL_TRADES))
    
    # Check mode
    MODE=$(cat state/trading_mode.json 2>/dev/null | jq -r '.mode // "UNKNOWN"' || echo "UNKNOWN")
    
    # Log status
    echo "[$CURRENT_TIME] Status: Mode=$MODE, Errors=$NEW_ERRORS, Trades=$NEW_TRADES" >> $MONITOR_LOG
    
    # Check for critical errors
    if [ $NEW_ERRORS -gt 0 ]; then
        echo "[$CURRENT_TIME] ⚠️ Warning: $NEW_ERRORS new error(s) detected" | tee -a $MONITOR_LOG
        tail -5 logs/smart_trader.log | grep -E "ERROR\|Exception" >> $MONITOR_LOG
    fi
    
    # Check mode consistency
    if [ "$MODE" != "PAPER_TRADING_MODE" ]; then
        echo "[$CURRENT_TIME] ⚠️ Warning: Mode is $MODE (expected PAPER_TRADING_MODE)" | tee -a $MONITOR_LOG
    fi
    
    # Memory check
    if pgrep -f "smart_trader.py" > /dev/null; then
        PID=$(pgrep -f "smart_trader.py" | head -1)
        MEM=$(ps -o rss= -p $PID 2>/dev/null | awk '{print $1/1024}')
        if [ ! -z "$MEM" ]; then
            echo "[$CURRENT_TIME] Memory: ${MEM}MB" >> $MONITOR_LOG
        fi
    fi
    
    # Progress update every hour
    if [ $((CHECK_COUNT % 12)) -eq 0 ]; then  # Every hour (12 * 5min = 60min)
        HOURS=$((ELAPSED / 60))
        echo ""
        echo "⏱️  Progress: ${HOURS} hour(s) elapsed"
        echo "   Mode: $MODE"
        echo "   Errors: $NEW_ERRORS"
        echo "   Trades: $NEW_TRADES"
        echo "   Memory: ${MEM}MB"
        echo ""
    fi
    
    sleep $CHECK_INTERVAL
done

# Final report
echo ""
echo "=========================================="
echo "✅ Soak Test Complete"
echo "=========================================="
echo ""
echo "Final Statistics:"
echo "  Duration: $((DURATION / 3600)) hours"
echo "  Total Checks: $CHECK_COUNT"
echo "  New Errors: $NEW_ERRORS"
echo "  New Trades: $NEW_TRADES"
echo "  Final Mode: $MODE"
echo ""
echo "Full log: $MONITOR_LOG"
echo ""

# Check for issues
if [ $NEW_ERRORS -gt 0 ]; then
    echo "⚠️  WARNING: $NEW_ERRORS error(s) detected during soak test"
    echo "   Review logs for details"
else
    echo "✅ SUCCESS: Zero errors during soak test!"
fi

if [ "$MODE" != "PAPER_TRADING_MODE" ]; then
    echo "⚠️  WARNING: Mode changed during test (was PAPER_TRADING_MODE, now $MODE)"
else
    echo "✅ SUCCESS: Mode remained PAPER_TRADING_MODE throughout"
fi

echo ""
echo "📊 Review full report: $MONITOR_LOG"
echo ""

