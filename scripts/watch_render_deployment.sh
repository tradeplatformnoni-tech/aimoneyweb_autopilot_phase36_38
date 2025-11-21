#!/bin/bash
# Watch Render deployment status with auto-refresh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICE_ID="${RENDER_SERVICE_ID:-srv-d4fm045rnu6s73e7ehb0}"

# Load credentials
source <(grep -v '^#' "$ROOT/.api_credentials" | grep -v '^$' | sed 's/^/export /')
export RENDER_SERVICE_ID="$SERVICE_ID"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

INTERVAL="${1:-30}"  # Default 30 seconds

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}👀 Watching Render Deployment (refresh every ${INTERVAL}s)${NC}"
echo -e "${CYAN}   Press Ctrl+C to stop${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

while true; do
    clear
    echo -e "${CYAN}📊 Render Deployment Status - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
    
    python3 "$ROOT/scripts/check_render_status.py" 2>/dev/null || {
        echo -e "${RED}❌ Error checking status${NC}"
    }
    
    echo ""
    echo -e "${YELLOW}Refreshing in ${INTERVAL} seconds... (Ctrl+C to stop)${NC}"
    sleep "$INTERVAL"
done

