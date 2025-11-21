#!/bin/bash
# Quick status check for failover test

echo "📊 Failover Status Check"
echo "========================"
echo ""

echo "Monitor Process:"
if ps aux | grep -v grep | grep -q flyio_failover_monitor; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi
echo ""

echo "Latest Monitor Log:"
LOG_FILE=$(ls -t logs/flyio_failover_*.log 2>/dev/null | head -1)
if [ -n "$LOG_FILE" ]; then
    tail -3 "$LOG_FILE"
else
    echo "No log file"
fi
echo ""

echo "Fly.io App Status (running machines):"
for app in neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk; do
    count=$(flyctl machines list --app "$app" 2>&1 | grep -c "started" 2>/dev/null || echo "0")
    # Clean count (remove any whitespace/newlines)
    count=$(echo "$count" | xargs)
    if [ -z "$count" ]; then
        count=0
    fi
    # Compare as numbers
    if [ "${count:-0}" -gt 0 ] 2>/dev/null; then
        echo "  ✅ $app: $count machine(s) RUNNING"
    else
        echo "  ⏸️  $app: 0 machines (standby)"
    fi
done
echo ""

echo "Local Health Check:"
local_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:8100/status 2>/dev/null || echo "000")
if [ "$local_status" = "200" ]; then
    echo "  ✅ Local dashboard: healthy"
else
    echo "  ❌ Local dashboard: down ($local_status)"
fi

echo "Internet Connectivity:"
internet_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 https://www.google.com 2>/dev/null || echo "000")
if [ "$internet_status" = "200" ]; then
    echo "  ✅ Internet: connected"
else
    echo "  ❌ Internet: disconnected ($internet_status)"
fi
