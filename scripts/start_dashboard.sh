#!/bin/bash
# World-Class Dashboard Startup Script
# Ensures proper startup order and health checks

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

DASHBOARD_PORT="${NEOLIGHT_DASHBOARD_PORT:-8100}"

echo "🚀 Starting NeoLight Dashboard (port $DASHBOARD_PORT)..."

# Stop any existing dashboard instances
pkill -f "uvicorn.*dashboard.*$DASHBOARD_PORT" || pkill -f "uvicorn.*$DASHBOARD_PORT" || true
sleep 2

# Start dashboard
nohup python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port "$DASHBOARD_PORT" --reload > "$LOG_DIR/dashboard.log" 2>&1 &
DASHBOARD_PID=$!

echo "⏳ Waiting for dashboard to start..."
sleep 3

# Health check with retries
MAX_RETRIES=20
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:$DASHBOARD_PORT/status" > /dev/null 2>&1; then
        echo "✅ Dashboard is running on port $DASHBOARD_PORT"
        echo "   PID: $DASHBOARD_PID"
        echo "   Health: http://localhost:$DASHBOARD_PORT/status"
        echo "   Metrics: http://localhost:$DASHBOARD_PORT/meta/metrics"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

echo "⚠️  Dashboard may still be starting (checked $MAX_RETRIES times)"
echo "   Check logs: tail -f $LOG_DIR/dashboard.log"
exit 1

