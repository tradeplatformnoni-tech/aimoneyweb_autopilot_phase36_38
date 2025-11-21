#!/bin/bash
# Real-time Crypto Trading Monitor
# Monitors for crypto BUY signals and position changes

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$ROOT/logs/smart_trader.log"
PORTFOLIO_FILE="$ROOT/runtime/portfolio.json"

echo "🔍 Real-time Crypto Trading Monitor"
echo "Press Ctrl+C to stop"
echo ""

# Monitor for forced BUY signals
tail -f "$LOG_FILE" 2>/dev/null | grep --line-buffered -E "🪙 CRYPTO.*Forcing BUY|CRYPTO.*Ignoring.*SELL|✅.*BUY.*USD|📊.*Enhanced signal.*USD" | while read line; do
    timestamp=$(date '+%H:%M:%S')
    echo "[$timestamp] $line"
done
