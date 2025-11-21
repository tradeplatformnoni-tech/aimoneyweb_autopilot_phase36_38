#!/bin/bash
# 🧪 Failover Test Monitor
# Watches monitor logs and Fly.io status during failover test

echo "🧪 Failover Test Monitor"
echo "========================"
echo ""
echo "This will watch:"
echo "  1. Monitor logs (local health checks)"
echo "  2. Fly.io app status (failover activation)"
echo ""
echo "📋 Instructions:"
echo "  1. Turn off WiFi now"
echo "  2. Monitor will detect failures (3 checks = 3 minutes)"
echo "  3. After 3 failures, all 7 apps should activate"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

LOG_FILE=$(ls -t logs/flyio_failover_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "❌ No monitor log file found"
    exit 1
fi

echo "📊 Watching log: $LOG_FILE"
echo ""

# Watch for failures and activations
tail -f "$LOG_FILE" | while read line; do
    echo "$line"
    
    # Check for activation
    if echo "$line" | grep -q "Activating.*app"; then
        echo ""
        echo "🚀 ACTIVATION DETECTED! Checking Fly.io status..."
        for app in neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk; do
            count=$(flyctl machines list --app "$app" 2>&1 | grep -c "started" || echo "0")
            if [ "$count" -gt 0 ]; then
                echo "  ✅ $app: $count machine(s) running"
            fi
        done
        echo ""
    fi
done
