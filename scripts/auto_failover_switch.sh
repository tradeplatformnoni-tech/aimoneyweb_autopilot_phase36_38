#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Auto Failover Switch - Proactive Usage-Based Failover            ║
# ║ Switches between Render and Google Cloud Run based on usage      ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
RUN_DIR="$ROOT/run"
LOG_FILE="$LOG_DIR/auto_failover_switch.log"
STATUS_FILE="$RUN_DIR/failover_status.json"

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
info() { log "${CYAN}🔄 $*${NC}"; }

# Configuration
RENDER_API_KEY="${RENDER_API_KEY:-}"
RENDER_SERVICE_ID="${RENDER_SERVICE_ID:-}"
CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-neolight-failover}"
CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
CLOUD_RUN_API_KEY="${CLOUD_RUN_API_KEY:-}"
CLOUD_RUN_URL="${CLOUD_RUN_URL:-}"
NL_BUCKET="${NL_BUCKET:-}"

# Load state
load_state() {
    if [[ -f "$STATUS_FILE" ]]; then
        CURRENT_PROVIDER=$(jq -r '.current_provider // "render"' "$STATUS_FILE" 2>/dev/null || echo "render")
    else
        CURRENT_PROVIDER="render"
    fi
}

save_state() {
    local provider=$1
    cat > "$STATUS_FILE" <<EOF
{
  "current_provider": "$provider",
  "last_switch": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "switch_reason": "${SWITCH_REASON:-usage_limit}"
}
EOF
}

# Suspend Render service
suspend_render() {
    if [[ -z "$RENDER_API_KEY" ]] || [[ -z "$RENDER_SERVICE_ID" ]]; then
        warn "Render API credentials not configured, skipping suspend"
        return 0
    fi
    
    info "Suspending Render service to preserve remaining hours..."
    
    local response=$(curl -s -X POST \
        "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/suspend" \
        -H "Authorization: Bearer ${RENDER_API_KEY}" \
        -H "Accept: application/json" \
        -w "\n%{http_code}")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        ok "Render service suspended"
        return 0
    else
        warn "Failed to suspend Render (HTTP $http_code): $body"
        return 1
    fi
}

# Activate Google Cloud Run
activate_cloudrun() {
    if [[ -z "$CLOUD_RUN_URL" ]] || [[ -z "$CLOUD_RUN_API_KEY" ]] || [[ -z "$NL_BUCKET" ]]; then
        err "Cloud Run configuration missing (URL, API key, or bucket)"
        return 1
    fi
    
    info "Activating Google Cloud Run..."
    
    # Scale up from 0 (if needed)
    if command -v gcloud >/dev/null 2>&1; then
        info "Scaling Cloud Run to 1 instance..."
        gcloud run services update "$CLOUD_RUN_SERVICE" \
            --region="$CLOUD_RUN_REGION" \
            --min-instances=1 \
            --max-instances=1 \
            --quiet 2>&1 | tee -a "$LOG_FILE" || {
            warn "Failed to scale Cloud Run (may already be scaled)"
        }
    fi
    
    # Activate SmartTrader
    info "Activating SmartTrader on Cloud Run..."
    local response=$(curl -s -X POST \
        "${CLOUD_RUN_URL}/activate" \
        -H "X-API-Key: ${CLOUD_RUN_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"bucket\": \"${NL_BUCKET}\", \"source\": \"auto_failover\", \"force\": true}" \
        -w "\n%{http_code}")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" ]]; then
        ok "Cloud Run activated successfully"
        return 0
    else
        err "Failed to activate Cloud Run (HTTP $http_code): $body"
        return 1
    fi
}

# Resume Render service
resume_render() {
    if [[ -z "$RENDER_API_KEY" ]] || [[ -z "$RENDER_SERVICE_ID" ]]; then
        warn "Render API credentials not configured, skipping resume"
        return 0
    fi
    
    info "Resuming Render service..."
    
    local response=$(curl -s -X POST \
        "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/resume" \
        -H "Authorization: Bearer ${RENDER_API_KEY}" \
        -H "Accept: application/json" \
        -w "\n%{http_code}")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        ok "Render service resumed"
        return 0
    else
        warn "Failed to resume Render (HTTP $http_code): $body"
        return 1
    fi
}

# Deactivate Google Cloud Run
deactivate_cloudrun() {
    if [[ -z "$CLOUD_RUN_URL" ]] || [[ -z "$CLOUD_RUN_API_KEY" ]]; then
        warn "Cloud Run configuration missing, skipping deactivate"
        return 0
    fi
    
    info "Deactivating Google Cloud Run..."
    
    # Deactivate SmartTrader
    curl -s -X POST \
        "${CLOUD_RUN_URL}/deactivate" \
        -H "X-API-Key: ${CLOUD_RUN_API_KEY}" \
        -w "\n%{http_code}" > /tmp/cloudrun_deactivate_response.txt 2>&1 || true
    
    # Scale back to 0
    if command -v gcloud >/dev/null 2>&1; then
        info "Scaling Cloud Run back to 0 (scale-to-zero)..."
        gcloud run services update "$CLOUD_RUN_SERVICE" \
            --region="$CLOUD_RUN_REGION" \
            --min-instances=0 \
            --max-instances=1 \
            --quiet 2>&1 | tee -a "$LOG_FILE" || {
            warn "Failed to scale Cloud Run to 0"
        }
    fi
    
    ok "Cloud Run deactivated and scaled to 0"
}

# Switch from Render to Cloud Run
switch_render_to_cloudrun() {
    info "🔄 Switching from Render to Google Cloud Run..."
    SWITCH_REASON="render_usage_limit"
    
    # 1. Sync state to Google Drive (if not already synced)
    if [[ -f "$ROOT/scripts/rclone_sync.sh" ]]; then
        info "Syncing state to Google Drive..."
        bash "$ROOT/scripts/rclone_sync.sh" >> "$LOG_FILE" 2>&1 || {
            warn "State sync failed, continuing anyway"
        }
    fi
    
    # 2. Suspend Render
    suspend_render || warn "Failed to suspend Render, continuing"
    
    # 3. Activate Cloud Run
    if activate_cloudrun; then
        save_state "cloudrun"
        ok "✅ Successfully switched to Google Cloud Run"
        
        # Update Cloudflare Worker routing (if configured)
        info "Note: Update Cloudflare Worker to route to Cloud Run"
        
        return 0
    else
        err "❌ Failed to activate Cloud Run, Render may still be running"
        return 1
    fi
}

# Switch from Cloud Run back to Render
switch_cloudrun_to_render() {
    info "🔄 Switching from Google Cloud Run back to Render..."
    SWITCH_REASON="render_limit_reset"
    
    # 1. Sync state to Google Drive
    if [[ -f "$ROOT/scripts/rclone_sync.sh" ]]; then
        info "Syncing state to Google Drive..."
        bash "$ROOT/scripts/rclone_sync.sh" >> "$LOG_FILE" 2>&1 || {
            warn "State sync failed, continuing anyway"
        }
    fi
    
    # 2. Deactivate Cloud Run
    deactivate_cloudrun || warn "Failed to deactivate Cloud Run, continuing"
    
    # 3. Resume Render
    if resume_render; then
        save_state "render"
        ok "✅ Successfully switched back to Render"
        
        # Update Cloudflare Worker routing (if configured)
        info "Note: Update Cloudflare Worker to route to Render"
        
        return 0
    else
        err "❌ Failed to resume Render"
        return 1
    fi
}

# Main
main() {
    load_state
    
    case "${1:-}" in
        "render_to_cloudrun")
            switch_render_to_cloudrun
            ;;
        "cloudrun_to_render")
            switch_cloudrun_to_render
            ;;
        "status")
            if [[ -f "$STATUS_FILE" ]]; then
                cat "$STATUS_FILE" | jq .
            else
                echo '{"current_provider": "render", "last_switch": null}'
            fi
            ;;
        *)
            echo "Usage: $0 {render_to_cloudrun|cloudrun_to_render|status}"
            echo ""
            echo "Commands:"
            echo "  render_to_cloudrun  - Switch from Render to Cloud Run"
            echo "  cloudrun_to_render  - Switch from Cloud Run to Render"
            echo "  status              - Show current provider status"
            exit 1
            ;;
    esac
}

main "$@"


