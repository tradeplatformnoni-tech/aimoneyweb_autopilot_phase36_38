#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ 🚀 NeoLight Fly.io Failover Monitor - Enterprise Edition         ║
# ║ World-class failover system - activates only when local is down ║
# ║ Follows same pattern as Google Drive sync (rclone/neo_remote)   ║
# ╚══════════════════════════════════════════════════════════════════╝

set -Eeuo pipefail
umask 027

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
LOG_DIR="$ROOT/logs"
RUN_DIR="$ROOT/run"
LOCKFILE="/tmp/neolight_flyio_failover.lock"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/flyio_failover_${STAMP}.log"
STATUS_FILE="$RUN_DIR/flyio_failover.status"
mkdir -p "$LOG_DIR" "$RUN_DIR"

# ── Color + logging helpers ───────────────────────────────────────────────
GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; CYAN=$'\033[0;36m'; RESET=$'\033[0m'
log(){ printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG_FILE"; }
ok(){ log "${GREEN}✅ $*${RESET}"; }
warn(){ log "${YELLOW}⚠️  $*${RESET}"; }
err(){ log "${RED}❌ $*${RESET}"; }
info(){ log "${CYAN}📊 $*${RESET}"; }

# ── Configuration (env overridable, same pattern as rclone) ──────────────
FLY_APPS="${FLY_APPS:-neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk}"
FLY_API_TOKEN="${FLY_API_TOKEN:-}"
LOCAL_HEALTH_URL="${LOCAL_HEALTH_URL:-http://localhost:8100/status}"
# Use first app as primary health check
PRIMARY_APP="${FLY_APPS%% *}"
FLY_HEALTH_URL="${FLY_HEALTH_URL:-https://${PRIMARY_APP}.fly.dev/health}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"           # Check every 60 seconds
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"      # 3 consecutive failures = failover
RCLONE_REMOTE="${RCLONE_REMOTE:-neo_remote}"
RCLONE_PATH="${RCLONE_PATH:-NeoLight}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# ── Lock file management (same as rclone sync) ────────────────────────────
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    err "Another failover monitor already running — aborting."
    exit 0
fi

# ── Telegram notification (same pattern as rclone) ───────────────────────
send_telegram(){
    local msg="$1"
    [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return 0
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="$msg" >/dev/null 2>&1 || true
}

# ── Health check (same pattern as Google Drive sync) ──────────────────────
check_local_health(){
    # Check local dashboard health
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$LOCAL_HEALTH_URL" 2>/dev/null || echo "000")
    
    # Also check internet connectivity (required for trading)
    # If internet is down, we should failover even if local dashboard is up
    local internet_check
    internet_check=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://www.google.com" 2>/dev/null || echo "000")
    
    # Both must be healthy for system to be considered healthy
    [[ "$response" == "200" ]] && [[ "$internet_check" == "200" ]]
}

# ── Sync state to Fly.io (same pattern as Google Drive) ───────────────────
sync_state_to_flyio(){
    info "☁️ Syncing state to Fly.io for failover..."
    
    if ! command -v rclone >/dev/null 2>&1; then
        warn "rclone not installed; skipping state sync"
        return 1
    fi
    
    # Sync to Google Drive first (existing pattern)
    rclone copy "$ROOT/state" "${RCLONE_REMOTE}:${RCLONE_PATH}/state" \
        --create-empty-src-dirs --fast-list --transfers=4 \
        --log-file="$LOG_FILE" --log-level=INFO >/dev/null 2>&1 || {
        warn "Google Drive sync failed (non-fatal)"
    }
    
    # Sync runtime snapshot (same as rclone_sync.sh)
    local tmp_dir="$ROOT/tmp_flyio_sync_$(date +%s)"
    mkdir -p "$tmp_dir/runtime_snapshot"
    
    rsync -a --delete-excluded \
        --exclude='*.lock' --exclude='*.pid' --exclude='*.sock' \
        --exclude='*.tmp' --exclude='*.sqlite-*' \
        "$ROOT/runtime/" "$tmp_dir/runtime_snapshot/" 2>/dev/null || true
    
    rclone copy "$tmp_dir/runtime_snapshot" "${RCLONE_REMOTE}:${RCLONE_PATH}/runtime" \
        --create-empty-src-dirs --fast-list \
        --log-file="$LOG_FILE" --log-level=INFO >/dev/null 2>&1 || {
        warn "Runtime sync failed (non-fatal)"
    }
    
    rm -rf "$tmp_dir" 2>/dev/null || true
    ok "State synced to cloud (available for Fly.io)"
    return 0
}

# ── Activate Fly.io failover ──────────────────────────────────────────────
activate_flyio_failover(){
    info "🚀 Activating Fly.io failover (all apps)..."
    
    if [[ -z "$FLY_API_TOKEN" ]]; then
        err "FLY_API_TOKEN not set - cannot activate failover"
        send_telegram "❌ Fly.io Failover: FLY_API_TOKEN missing"
        return 1
    fi
    
    local activated_count=0
    local failed_apps=""
    local total_apps=0
    
    # Count total apps
    for app in $FLY_APPS; do
        total_apps=$((total_apps + 1))
    done
    
    # Activate each app
    for app in $FLY_APPS; do
        info "Activating $app..."
        
        if command -v flyctl >/dev/null 2>&1; then
            # Try new format first, fallback to old format
            if flyctl scale count app=1 --app "$app" --yes >/dev/null 2>&1; then
                ok "$app scaled up"
                activated_count=$((activated_count + 1))
            else
                # Try using machines API
                local machine_id=$(flyctl machines list --app "$app" --json 2>/dev/null | jq -r '.[0].id' 2>/dev/null || echo "")
                if [ -n "$machine_id" ]; then
                    if flyctl machines start "$machine_id" --app "$app" >/dev/null 2>&1; then
                        ok "$app machine started"
                        activated_count=$((activated_count + 1))
                    else
                        warn "Failed to activate $app"
                        failed_apps="$failed_apps $app"
                    fi
                else
                    # Try to scale up again (might need to create machines)
                    if flyctl scale count app=1 --app "$app" --yes >/dev/null 2>&1; then
                        ok "$app scaled up (new machine)"
                        activated_count=$((activated_count + 1))
                    else
                        warn "Failed to activate $app"
                        failed_apps="$failed_apps $app"
                    fi
                fi
            fi
        else
            warn "flyctl not installed - cannot activate $app"
            failed_apps="$failed_apps $app"
        fi
        
        # Small delay between activations
        sleep 2
    done
    
    # Wait for health checks (check primary app)
    local primary_app="${FLY_APPS%% *}"  # First app in list
    local health_url="https://${primary_app}.fly.dev/health"
    
    local attempts=0
    while [ $attempts -lt 15 ]; do
        sleep 5
        if curl -s -f "$health_url" >/dev/null 2>&1; then
            ok "Fly.io failover active ($activated_count/$total_apps apps activated)"
            if [ -n "$failed_apps" ]; then
                send_telegram "✅ Fly.io Failover Activated\n$activated_count/$total_apps apps running\nFailed: $failed_apps"
            else
                send_telegram "✅ Fly.io Failover Activated\nAll $total_apps apps running on Fly.io"
            fi
            echo "active" > "$STATUS_FILE"
            return 0
        fi
        attempts=$((attempts + 1))
    done
    
    if [ $activated_count -gt 0 ]; then
        ok "Fly.io failover partially active ($activated_count/$total_apps apps)"
        send_telegram "⚠️ Fly.io Failover: $activated_count/$total_apps apps activated\nFailed: $failed_apps"
        echo "active" > "$STATUS_FILE"
        return 0
    else
        err "Fly.io failover activation failed"
        send_telegram "❌ Fly.io Failover: All activations failed"
        return 1
    fi
}

# ── Deactivate Fly.io failover ───────────────────────────────────────────
deactivate_flyio_failover(){
    info "🔄 Deactivating Fly.io failover (local system recovered)..."
    
    if [[ -z "$FLY_API_TOKEN" ]]; then
        return 0
    fi
    
    local deactivated_count=0
    local total_apps=0
    
    # Count total apps
    for app in $FLY_APPS; do
        total_apps=$((total_apps + 1))
    done
    
    # Deactivate each app
    for app in $FLY_APPS; do
        info "Deactivating $app..."
        
        if command -v flyctl >/dev/null 2>&1; then
            if flyctl scale count app=0 --app "$app" --yes >/dev/null 2>&1; then
                ok "$app scaled down"
                deactivated_count=$((deactivated_count + 1))
            else
                # Try using machines API to stop
                local machine_id=$(flyctl machines list --app "$app" --json 2>/dev/null | jq -r '.[0].id' 2>/dev/null || echo "")
                if [ -n "$machine_id" ]; then
                    flyctl machines stop "$machine_id" --app "$app" >/dev/null 2>&1 || true
                    ok "$app stopped"
                    deactivated_count=$((deactivated_count + 1))
                fi
            fi
        fi
        
        sleep 1
    done
    
    ok "Fly.io failover deactivated ($deactivated_count/$total_apps apps scaled down)"
    send_telegram "✅ Fly.io Failover Deactivated\nAll apps in standby mode\nLocal system recovered"
    echo "standby" > "$STATUS_FILE"
}

# ── Graceful shutdown flag ───────────────────────────────────────────────
SHUTDOWN_FLAG=false

# ── Main monitoring loop ─────────────────────────────────────────────────
main(){
    info "🛡️ Fly.io Failover Monitor starting @ $(date '+%F %T')"
    info "📋 Configuration:"
    info "   Local Health: $LOCAL_HEALTH_URL"
    info "   Fly.io Health: $FLY_HEALTH_URL"
    info "   Apps to activate: $FLY_APPS"
    info "   Check Interval: ${CHECK_INTERVAL}s"
    info "   Failure Threshold: $FAILURE_THRESHOLD"
    info "🧾 Log → $LOG_FILE"
    
    local failure_count=0
    local failover_active=false
    
    while [ "$SHUTDOWN_FLAG" = false ]; do
        if check_local_health; then
            # Local system is healthy
            if [ $failure_count -gt 0 ]; then
                ok "Local system recovered (was down for ${failure_count} checks)"
                failure_count=0
            fi
            
            if [ "$failover_active" = true ]; then
                deactivate_flyio_failover
                failover_active=false
            fi
            
            echo "healthy" > "$STATUS_FILE"
        else
            # Local system is down
            failure_count=$((failure_count + 1))
            warn "Local system down (failure count: $failure_count/$FAILURE_THRESHOLD)"
            
            if [ $failure_count -ge $FAILURE_THRESHOLD ] && [ "$failover_active" = false ]; then
                err "Local system down for ${failure_count} checks - activating Fly.io failover"
                send_telegram "⚠️ Local System Down\nActivating Fly.io failover..."
                
                # Sync state before failover
                sync_state_to_flyio
                
                # Activate failover
                if activate_flyio_failover; then
                    failover_active=true
                else
                    err "Failed to activate Fly.io failover"
                fi
            fi
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# ── Signal handlers ──────────────────────────────────────────────────────
graceful_shutdown(){
    SHUTDOWN_FLAG=true
    info "Monitor shutting down gracefully..."
    # Deactivation will be handled by EXIT trap
}

cleanup_and_exit(){
    # Always deactivate on exit (handles both graceful and unexpected exits)
    deactivate_flyio_failover
    exit 0
}

trap 'graceful_shutdown' INT TERM
trap 'cleanup_and_exit' EXIT

# ── Run ─────────────────────────────────────────────────────────────────
main

