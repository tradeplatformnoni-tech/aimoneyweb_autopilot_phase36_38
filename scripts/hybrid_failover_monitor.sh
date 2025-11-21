#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ NeoLight Hybrid Failover Monitor v2.1 - Hybrid Edition         ║
# ║ Combines Claude's security + Auto's reliability                ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail
umask 027

# ── Configuration ───────────────────────────────────────────────────
LOCAL_HEALTH_URL="${LOCAL_HEALTH_URL:-http://localhost:8100/health}"
LOCAL_HEALTH_ALT="${LOCAL_HEALTH_ALT:-http://localhost:5050/healthz}"  # Auto's fallback
CLOUD_RUN_SERVICE_URL="${CLOUD_RUN_SERVICE_URL:-}"
CLOUD_RUN_API_KEY="${CLOUD_RUN_API_KEY:-}"  # Claude's security
CHECK_EVERY_SEC="${CHECK_EVERY_SEC:-15}"
RETRY_AFTER_TRIGGER_SEC="${RETRY_AFTER_TRIGGER_SEC:-90}"
MAX_SYNC_RETRIES="${MAX_SYNC_RETRIES:-3}"
SYNC_TIMEOUT="${SYNC_TIMEOUT:-120}"

# ── Circuit Breaker (Claude's) ─────────────────────────────────────
CONSECUTIVE_FAILURES=0
CIRCUIT_BREAKER_THRESHOLD=3
CIRCUIT_BREAKER_RESET_SEC=300
CIRCUIT_BREAKER_OPEN=false
LAST_FAILURE_TIMESTAMP=0

# ── Alert Throttling (Claude's) ─────────────────────────────────────
LAST_ALERT_TIMESTAMP=0
ALERT_THROTTLE_SEC=300  # Max 1 alert per 5 minutes

# ── Paths ──────────────────────────────────────────────────────────
ROOT="${HOME}/neolight"
STATE_DIR="$ROOT/state"
RUNTIME_DIR="$ROOT/runtime"
LOG_DIR="$ROOT/logs"
LOCKFILE="/tmp/neolight_failover_monitor.lock"
LOG_FILE="$LOG_DIR/hybrid_failover_monitor.log"

mkdir -p "$LOG_DIR" "$STATE_DIR" "$RUNTIME_DIR"

# ── Colors & Logging ───────────────────────────────────────────────
GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; 
CYAN=$'\033[0;36m'; RESET=$'\033[0m'

log() {
    local level="${1:-INFO}" msg="${*:2}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local line="[$timestamp] [$level] $msg"
    echo "$line" | tee -a "$LOG_FILE"
}

ok() { log "OK" "${GREEN}$*${RESET}"; }
warn() { log "WARN" "${YELLOW}$*${RESET}"; }
err() { log "ERROR" "${RED}$*${RESET}"; }
info() { log "INFO" "${CYAN}$*${RESET}"; }

# ── Lock to prevent multiple instances ──────────────────────────────
exec 9>"$LOCKFILE" || true
if ! flock -n 9 2>/dev/null; then
    err "Another monitor instance running — exiting"
    exit 0
fi

# ── Dependency checks ──────────────────────────────────────────────
require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        err "Missing dependency: $1. Install it first."
        exit 1
    fi
}

require curl
require gsutil

# ── Environment validation ────────────────────────────────────────
if [[ -z "${NL_BUCKET:-}" ]]; then
    err "NL_BUCKET not set. export NL_BUCKET=gs://<your-bucket>"
    exit 1
fi

if [[ ! "$NL_BUCKET" =~ ^gs:// ]]; then
    err "NL_BUCKET must start with gs://. Got: $NL_BUCKET"
    exit 1
fi

if [[ -z "$CLOUD_RUN_SERVICE_URL" ]]; then
    err "CLOUD_RUN_SERVICE_URL not set. export CLOUD_RUN_SERVICE_URL=https://<cloud-run-url>"
    exit 1
fi

# ── Telegram Alert (Claude's optional feature) ──────────────────────
send_telegram_alert() {
    local msg="$1"
    local now=$(date +%s)
    
    # Throttle alerts (Claude's)
    if (( now - LAST_ALERT_TIMESTAMP < ALERT_THROTTLE_SEC )); then
        return 0
    fi
    
    LAST_ALERT_TIMESTAMP=$now
    
    if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] || [[ -z "${TELEGRAM_CHAT_ID:-}" ]]; then
        return 0  # Telegram not configured
    fi
    
    local url="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
    local payload=$(jq -n --arg text "$msg" --arg chat_id "$TELEGRAM_CHAT_ID" \
        '{chat_id: $chat_id, text: $text}' 2>/dev/null || echo "{\"chat_id\":\"$TELEGRAM_CHAT_ID\",\"text\":\"$msg\"}")
    
    curl -sS -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$payload" >/dev/null 2>&1 || true
}

# ── Health check (Auto's multi-endpoint version) ─────────────────────
is_local_healthy() {
    # Try primary endpoint
    if curl -fsS --max-time 3 --retry 1 "$LOCAL_HEALTH_URL" >/dev/null 2>&1; then
        return 0
    fi
    
    # Try alternate endpoint (Auto's fallback)
    if curl -fsS --max-time 3 --retry 1 "$LOCAL_HEALTH_ALT" >/dev/null 2>&1; then
        return 0
    fi
    
    # Check if SmartTrader process is running (Auto's process check)
    if pgrep -f "smart_trader.py" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# ── Circuit Breaker Check (Claude's) ────────────────────────────────
check_circuit_breaker() {
    local now=$(date +%s)
    
    if [[ "$CIRCUIT_BREAKER_OPEN" == "true" ]]; then
        local elapsed=$((now - LAST_FAILURE_TIMESTAMP))
        if (( elapsed >= CIRCUIT_BREAKER_RESET_SEC )); then
            info "Circuit breaker reset after cooldown"
            CIRCUIT_BREAKER_OPEN=false
            CONSECUTIVE_FAILURES=0
            return 0
        else
            warn "Circuit breaker open (${elapsed}s / ${CIRCUIT_BREAKER_RESET_SEC}s)"
            return 1
        fi
    fi
    
    return 0
}

# ── State sync with retries (Auto's improved version) ───────────────
sync_to_gcs() {
    local retries=0
    local success=false
    
    info "☁️ Syncing state to $NL_BUCKET/state (timeout: ${SYNC_TIMEOUT}s)..."
    
    while [[ $retries -lt $MAX_SYNC_RETRIES ]]; do
        if timeout "$SYNC_TIMEOUT" gsutil -m rsync -r -d \
            --exclude="*.lock" \
            --exclude="*.pid" \
            --exclude="*.sock" \
            --exclude="*.tmp" \
            "$STATE_DIR" "$NL_BUCKET/state" >> "$LOG_FILE" 2>&1; then
            success=true
            break
        else
            retries=$((retries + 1))
            warn "Sync attempt $retries/$MAX_SYNC_RETRIES failed, retrying in 5s..."
            sleep 5
        fi
    done
    
    if $success; then
        ok "State synced successfully"
        return 0
    else
        err "State sync failed after $MAX_SYNC_RETRIES attempts"
        return 1
    fi
}

# ── Activate cloud failover (Claude's auth + Auto's reliability) ────
activate_cloud() {
    info "🌐 Triggering Cloud Run activation..."
    
    local payload=$(cat <<EOF
{
    "bucket": "${NL_BUCKET}",
    "ts": "$(date -u +%FT%TZ)",
    "source": "local_failover_monitor",
    "hostname": "$(hostname)",
    "force": false
}
EOF
)
    
    local headers=(-H "Content-Type: application/json")
    if [[ -n "$CLOUD_RUN_API_KEY" ]]; then
        headers+=(-H "X-API-Key: $CLOUD_RUN_API_KEY")  # Claude's security
    fi
    
    if curl -fsS -X POST "$CLOUD_RUN_SERVICE_URL/activate" \
        "${headers[@]}" \
        -d "$payload" \
        --max-time 10 \
        --retry 2 \
        >> "$LOG_FILE" 2>&1; then
        ok "Cloud Run activation triggered"
        return 0
    else
        warn "Cloud activation call failed (non-fatal)"
        return 1
    fi
}

# ── Cleanup handler ────────────────────────────────────────────────
cleanup() {
    flock -u 9
    rm -f "$LOCKFILE"
}

trap cleanup EXIT INT TERM

# ── Main monitoring loop ───────────────────────────────────────────
info "🛰️ Hybrid monitor started (v2.1-hybrid)"
info "   Local health: $LOCAL_HEALTH_URL (fallback: $LOCAL_HEALTH_ALT)"
info "   Cloud failover: $CLOUD_RUN_SERVICE_URL"
info "   State bucket: $NL_BUCKET"
info "   Check interval: ${CHECK_EVERY_SEC}s"
info "   Circuit breaker threshold: ${CIRCUIT_BREAKER_THRESHOLD}"
if [[ -n "$CLOUD_RUN_API_KEY" ]]; then
    info "   API key authentication: ✅ Enabled"
else
    warn "   API key authentication: ⚠️ Not configured"
fi

local_unhealthy_count=0
local_healthy_count=0

while true; do
    if is_local_healthy; then
        local_healthy_count=$((local_healthy_count + 1))
        local_unhealthy_count=0
        
        # Reset circuit breaker on success (Claude's)
        if [[ "$CIRCUIT_BREAKER_OPEN" == "true" ]]; then
            info "Local recovered, resetting circuit breaker"
            CIRCUIT_BREAKER_OPEN=false
            CONSECUTIVE_FAILURES=0
        fi
        
        if (( local_healthy_count % 20 == 0 )); then
            ok "Local healthy (${local_healthy_count} consecutive checks)"
        fi
    else
        local_unhealthy_count=$((local_unhealthy_count + 1))
        err "Local unhealthy (consecutive failures: $local_unhealthy_count)"
        
        # Check circuit breaker (Claude's)
        if ! check_circuit_breaker; then
            warn "Circuit breaker open, skipping activation"
            sleep "$CHECK_EVERY_SEC"
            continue
        fi
        
        # Trigger failover after 2 consecutive failures (30s)
        if (( local_unhealthy_count >= 2 )); then
            CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
            err "⚠️ Local system down — initiating failover (failure #$CONSECUTIVE_FAILURES)"
            
            # Send alert (Claude's)
            send_telegram_alert "🚨 NeoLight: Local system down, triggering cloud failover"
            
            if sync_to_gcs; then
                if activate_cloud; then
                    # Reset on success
                    CONSECUTIVE_FAILURES=0
                else
                    # Record failure (Claude's)
                    LAST_FAILURE_TIMESTAMP=$(date +%s)
                    if (( CONSECUTIVE_FAILURES >= CIRCUIT_BREAKER_THRESHOLD )); then
                        CIRCUIT_BREAKER_OPEN=true
                        err "Circuit breaker opened after $CONSECUTIVE_FAILURES failures"
                        send_telegram_alert "🚨 NeoLight: Circuit breaker opened - too many failures"
                    fi
                fi
            else
                err "⚠️ State sync failed — cloud may start with stale state"
                activate_cloud  # Still try to activate
                LAST_FAILURE_TIMESTAMP=$(date +%s)
            fi
            
            info "⏳ Cooldown ${RETRY_AFTER_TRIGGER_SEC}s to prevent flapping"
            sleep "$RETRY_AFTER_TRIGGER_SEC"
            local_unhealthy_count=0
        fi
    fi
    
    sleep "$CHECK_EVERY_SEC"
done

