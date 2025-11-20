#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Monthly Reset Handler - Automatic Provider Switch                 ║
# ║ Detects month boundary and switches back to Render                ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
RUN_DIR="$ROOT/run"
LOG_FILE="$LOG_DIR/monthly_reset.log"
STATUS_FILE="$RUN_DIR/render_usage_status.json"
FAILOVER_STATUS="$RUN_DIR/failover_status.json"

mkdir -p "$LOG_DIR" "$RUN_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
ok() { log "${GREEN}✅ $*${NC}"; }
warn() { log "${YELLOW}⚠️  $*${NC}"; }
err() { log "${RED}❌ $*${NC}"; }
info() { log "${CYAN}📅 $*${NC}"; }

# Get current month
CURRENT_MONTH=$(date -u +%Y-%m)

# Check if month has changed
check_month_change() {
    if [[ ! -f "$STATUS_FILE" ]]; then
        info "No previous status file, assuming first run"
        return 0
    fi
    
    if command -v jq >/dev/null 2>&1; then
        LAST_MONTH=$(jq -r '.month // "unknown"' "$STATUS_FILE" 2>/dev/null || echo "unknown")
    else
        # Fallback: grep for month
        LAST_MONTH=$(grep -o '"month": "[^"]*"' "$STATUS_FILE" 2>/dev/null | cut -d'"' -f4 || echo "unknown")
    fi
    
    if [[ "$LAST_MONTH" != "$CURRENT_MONTH" ]] && [[ "$LAST_MONTH" != "unknown" ]]; then
        info "Month changed: $LAST_MONTH -> $CURRENT_MONTH"
        return 0
    else
        return 1
    fi
}

# Check current provider
get_current_provider() {
    if [[ -f "$FAILOVER_STATUS" ]] && command -v jq >/dev/null 2>&1; then
        jq -r '.current_provider // "render"' "$FAILOVER_STATUS" 2>/dev/null || echo "render"
    else
        echo "render"
    fi
}

# Reset usage tracking
reset_usage_tracking() {
    info "Resetting Render usage tracking for new month..."
    
    if command -v jq >/dev/null 2>&1; then
        # Update status file with new month
        if [[ -f "$STATUS_FILE" ]]; then
            jq --arg month "$CURRENT_MONTH" \
               '.month = $month | .hours_used = 0 | .switches_this_month = 0' \
               "$STATUS_FILE" > "$STATUS_FILE.tmp" && \
            mv "$STATUS_FILE.tmp" "$STATUS_FILE"
        else
            cat > "$STATUS_FILE" <<EOF
{
  "month": "$CURRENT_MONTH",
  "hours_used": 0,
  "last_check": null,
  "last_switch": null,
  "switches_this_month": 0,
  "current_provider": "render"
}
EOF
        fi
        ok "Usage tracking reset for $CURRENT_MONTH"
    else
        warn "jq not available, cannot update status file automatically"
    fi
}

# Switch back to Render
switch_to_render() {
    info "Switching back to Render (month reset detected)..."
    
    if [[ -f "$ROOT/scripts/auto_failover_switch.sh" ]]; then
        bash "$ROOT/scripts/auto_failover_switch.sh" cloudrun_to_render
        return $?
    else
        err "Auto-switch script not found"
        return 1
    fi
}

# Send notification
send_notification() {
    local message=$1
    local telegram_token="${TELEGRAM_BOT_TOKEN:-}"
    local telegram_chat_id="${TELEGRAM_CHAT_ID:-}"
    
    if [[ -n "$telegram_token" ]] && [[ -n "$telegram_chat_id" ]]; then
        curl -s -X POST \
            "https://api.telegram.org/bot${telegram_token}/sendMessage" \
            -d "chat_id=${telegram_chat_id}" \
            -d "text=📅 Monthly Reset: ${message}" \
            -d "parse_mode=HTML" \
            >/dev/null 2>&1 || true
    fi
    
    info "NOTIFICATION: $message"
}

# Main
main() {
    info "Monthly Reset Handler - Checking for month change..."
    
    if check_month_change; then
        CURRENT_PROVIDER=$(get_current_provider)
        
        info "Month boundary detected, current provider: $CURRENT_PROVIDER"
        
        # Reset usage tracking
        reset_usage_tracking
        
        # If currently on Cloud Run, switch back to Render
        if [[ "$CURRENT_PROVIDER" == "cloudrun" ]]; then
            if switch_to_render; then
                ok "Successfully switched back to Render for new month"
                send_notification "Switched back to Render. Usage reset for $CURRENT_MONTH"
            else
                err "Failed to switch back to Render"
                send_notification "⚠️ Failed to switch back to Render. Manual intervention may be needed."
            fi
        else
            info "Already on Render, no switch needed"
            send_notification "Render usage reset for $CURRENT_MONTH"
        fi
    else
        info "No month change detected (current: $CURRENT_MONTH)"
    fi
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi


