#!/bin/bash
# Background monitor for Render deployment - checks status and notifies on change

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICE_ID="${RENDER_SERVICE_ID:-srv-d4fm045rnu6s73e7ehb0}"
INTERVAL="${1:-30}"
LOG_FILE="$ROOT/logs/render_monitor.log"

# Load credentials
source <(grep -v '^#' "$ROOT/.api_credentials" | grep -v '^$' | sed 's/^/export /')
export RENDER_SERVICE_ID="$SERVICE_ID"

# Create logs directory
mkdir -p "$(dirname "$LOG_FILE")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

LAST_STATUS=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_status() {
    python3 "$ROOT/scripts/check_render_status.py" 2>/dev/null | grep -E "(Status:|LIVE|BUILDING|FAILED)" | head -1 | sed 's/.*Status: //' | sed 's/🔨 //' | sed 's/✅ //' | sed 's/❌ //' | tr -d ' ' || echo "unknown"
}

log "Starting Render deployment monitor (Service: $SERVICE_ID, Interval: ${INTERVAL}s)"

while true; do
    CURRENT_STATUS=$(check_status)
    
    if [ "$CURRENT_STATUS" != "$LAST_STATUS" ]; then
        log "Status changed: $LAST_STATUS → $CURRENT_STATUS"
        
        if [ "$CURRENT_STATUS" = "LIVE" ]; then
            log "✅ DEPLOYMENT SUCCESSFUL!"
            echo ""
            echo "═══════════════════════════════════════════════════════════════"
            echo "✅ RENDER DEPLOYMENT SUCCESSFUL!"
            echo "═══════════════════════════════════════════════════════════════"
            echo ""
            echo "Service is now LIVE at:"
            echo "https://neolight-autopilot-python.onrender.com"
            echo ""
            echo "Next steps:"
            echo "1. Test health endpoint: curl https://neolight-autopilot-python.onrender.com/health"
            echo "2. Update Cloudflare Worker"
            echo "3. Start orchestrator"
            echo ""
            echo "═══════════════════════════════════════════════════════════════"
            break
        elif [ "$CURRENT_STATUS" = "BUILDFAILED" ] || [ "$CURRENT_STATUS" = "UPDATEFAILED" ]; then
            log "❌ DEPLOYMENT FAILED!"
            echo ""
            echo "═══════════════════════════════════════════════════════════════"
            echo "❌ RENDER DEPLOYMENT FAILED!"
            echo "═══════════════════════════════════════════════════════════════"
            echo ""
            echo "Check logs at:"
            echo "https://dashboard.render.com/web/$SERVICE_ID/events"
            echo ""
            echo "Monitor log: $LOG_FILE"
            echo ""
            echo "═══════════════════════════════════════════════════════════════"
            break
        fi
        
        LAST_STATUS="$CURRENT_STATUS"
    else
        log "Status: $CURRENT_STATUS (no change)"
    fi
    
    sleep "$INTERVAL"
done

log "Monitor stopped"

