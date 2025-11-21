#!/bin/bash
# Quick launcher for Fly.io failover monitor
# ===========================================
cd "$(dirname "$0")/.."

# Set configuration
export FLY_APP="${FLY_APP:-neolight-failover}"
export RCLONE_REMOTE="${RCLONE_REMOTE:-neo_remote}"
export RCLONE_PATH="${RCLONE_PATH:-NeoLight}"
export CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
export FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"
export LOCAL_HEALTH_URL="${LOCAL_HEALTH_URL:-http://localhost:8100/status}"

echo "🚀 Starting Fly.io Failover Monitor..."
echo "   App: $FLY_APP"
echo "   Check Interval: ${CHECK_INTERVAL}s"
echo "   Failure Threshold: $FAILURE_THRESHOLD"
echo ""

./scripts/flyio_failover_monitor.sh


