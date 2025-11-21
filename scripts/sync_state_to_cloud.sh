#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ NeoLight State Sync to Cloud - World-Class Edition              ║
# ║ Syncs state to GCS with retries, validation, and error handling ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail
umask 027

# ── Configuration ───────────────────────────────────────────────────
MAX_RETRIES="${MAX_RETRIES:-3}"
SYNC_TIMEOUT="${SYNC_TIMEOUT:-180}"
RETRY_DELAY="${RETRY_DELAY:-5}"

# ── Paths ──────────────────────────────────────────────────────────
ROOT="${HOME}/neolight"
STATE_DIR="$ROOT/state"
RUNTIME_DIR="$ROOT/runtime"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/state_sync_$(date +%Y%m%d).log"
LOCKFILE="/tmp/neolight_state_sync.lock"

mkdir -p "$LOG_DIR"

# ── Lock ───────────────────────────────────────────────────────────
exec 9>"$LOCKFILE" || true
if ! flock -n 9 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] Another sync running — exiting"
    exit 0
fi

# ── Cleanup ────────────────────────────────────────────────────────
cleanup() {
    flock -u 9
    rm -f "$LOCKFILE"
}
trap cleanup EXIT INT TERM

# ── Validation ─────────────────────────────────────────────────────
require() {
    command -v "$1" >/dev/null 2>&1 || { echo "Missing $1"; exit 1; }
}

require gsutil

if [[ -z "${NL_BUCKET:-}" ]]; then
    echo "❌ NL_BUCKET not set. export NL_BUCKET=gs://<your-bucket>"
    exit 1
fi

if [[ ! "$NL_BUCKET" =~ ^gs:// ]]; then
    echo "❌ NL_BUCKET must start with gs://"
    exit 1
fi

# ── Sync with retries ──────────────────────────────────────────────
sync_with_retry() {
    local retries=0
    local success=false
    
    echo "[$(date '+%H:%M:%S')] ☁️ Syncing state to $NL_BUCKET/state..."
    
    while [[ $retries -lt $MAX_RETRIES ]]; do
        if timeout "$SYNC_TIMEOUT" gsutil -m rsync -r -d \
            --exclude="*.lock" \
            --exclude="*.pid" \
            --exclude="*.sock" \
            --exclude="*.tmp" \
            --exclude="*.log" \
            "$STATE_DIR" "$NL_BUCKET/state" >> "$LOG_FILE" 2>&1; then
            success=true
            break
        else
            retries=$((retries + 1))
            echo "[$(date '+%H:%M:%S')] ⚠️ Sync attempt $retries/$MAX_RETRIES failed, retrying in ${RETRY_DELAY}s..."
            sleep "$RETRY_DELAY"
        fi
    done
    
    if $success; then
        echo "[$(date '+%H:%M:%S')] ✅ State synced successfully"
        
        # Optional: sync to external disk if mounted
        if [[ -d "/Volumes" ]]; then
            for disk in /Volumes/*/; do
                if [[ -d "${disk}NeoLight" ]]; then
                    echo "[$(date '+%H:%M:%S')] 💾 Also syncing to ${disk}NeoLight/state..."
                    rsync -a --delete "$STATE_DIR/" "${disk}NeoLight/state/" 2>/dev/null || true
                fi
            done
        fi
        
        return 0
    else
        echo "[$(date '+%H:%M:%S')] ❌ State sync failed after $MAX_RETRIES attempts"
        return 1
    fi
}

# ── Main ───────────────────────────────────────────────────────────
sync_with_retry

