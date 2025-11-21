#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ ☁️ NeoLight CloudSync v10 — World-Class Edition                 ║
# ║ Fixed: MD5 mismatches, permission errors, active file writes    ║
# ╚══════════════════════════════════════════════════════════════════╝

set -Eeuo pipefail
umask 027
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
LOG_DIR="$ROOT/logs"
RUN_DIR="$ROOT/run"
TMP_DIR="$ROOT/tmp_sync_$(date +%s)"
LOCKFILE="/tmp/neolight_sync.lock"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/drive_sync_${STAMP}.log"
STATUS_FILE="$RUN_DIR/cloudsync.status"
mkdir -p "$LOG_DIR" "$RUN_DIR" "$TMP_DIR"

# ── Color + logging helpers ───────────────────────────────────────────────
GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; CYAN=$'\033[0;36m'; RESET=$'\033[0m'
log(){ printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG_FILE"; }
ok(){ log "${GREEN}✅ $*${RESET}"; }
warn(){ log "${YELLOW}⚠️  $*${RESET}"; }
err(){ log "${RED}❌ $*${RESET}"; }
info(){ log "${CYAN}☁️  $*${RESET}"; }

# ── Configurable parameters (env overridable) ─────────────────────────────
RCLONE_REMOTE="${RCLONE_REMOTE:-neo_remote}"
RCLONE_PATH="${RCLONE_PATH:-NeoLight}"
BANDWIDTH_LIMIT="${BANDWIDTH_LIMIT:-10M}"
TRANSFERS="${TRANSFERS:-8}"
CHECKERS="${CHECKERS:-8}"
RETRY_LIMIT="${RETRY_LIMIT:-3}"
MAX_BACKOFF="${MAX_BACKOFF:-15}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
LOG_AGE_MINUTES="${LOG_AGE_MINUTES:-5}"  # Only sync logs older than this
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# ── Dependency check ──────────────────────────────────────────────────────
need() { command -v "$1" >/dev/null 2>&1 || { err "Missing dependency: $1"; exit 1; }; }
need rclone
need rsync

# ── Notifications (Telegram / Healthchecks) ──────────────────────────────
send_alert(){
  [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return
  local msg="☁️ NeoLight CloudSync: $*"
  curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" --data-urlencode text="$msg" >/dev/null || true
}
hc_ping(){ [[ -z "$HEALTHCHECK_URL" ]] && return 0; curl -fsS -m 10 --retry 2 "$1" >/dev/null || true; }

# ── Lock to avoid parallel syncs ─────────────────────────────────────────
exec 9>"$LOCKFILE" || true
if ! flock -n 9 2>/dev/null; then
  warn "Another CloudSync instance already running — exiting safely."
  exit 0
fi

# ── Enhanced cleanup handler (fixes permission denied errors) ─────────────
cleanup() {
  local retries=3
  local backoff=1
  
  while [[ $retries -gt 0 ]]; do
    # Restore write permissions recursively
    if [[ -d "$TMP_DIR" ]]; then
      find "$TMP_DIR" -type f -exec chmod u+w {} + 2>/dev/null || true
      find "$TMP_DIR" -type d -exec chmod u+w {} + 2>/dev/null || true
    fi
    
    # Try to remove
    if rm -rf "$TMP_DIR" 2>/dev/null; then
      break
    fi
    
    # Check if files are in use
    if command -v lsof >/dev/null 2>&1; then
      local in_use=$(lsof +D "$TMP_DIR" 2>/dev/null | wc -l)
      if [[ $in_use -gt 0 ]]; then
        warn "Files in use, waiting ${backoff}s before retry..."
        sleep "$backoff"
      fi
    fi
    
    retries=$((retries - 1))
    backoff=$((backoff * 2))
  done
  
  # Final attempt - force remove if still exists
  [[ -d "$TMP_DIR" ]] && rm -rf "$TMP_DIR" 2>/dev/null || true
  echo "idle" > "$STATUS_FILE"
}
trap cleanup EXIT INT TERM

# ── Pre-clean old temp sync dirs (safety sweep) ─────────────────────────
find "$ROOT" -maxdepth 1 -type d -name "tmp_sync_*" -mmin +10 -exec rm -rf {} + 2>/dev/null || true

# ── Log rotation (compress >7d, delete >14d) ────────────────────────────
find "$LOG_DIR" -type f -name "drive_sync_*.log" -mtime +7 ! -name "*.gz" -print0 | xargs -0r gzip -9 2>/dev/null || true
find "$LOG_DIR" -type f -name "drive_sync_*.log.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# ── Improved runtime snapshot (no read-only, use tar.gz) ──────────────────
prepare_runtime_snapshot(){
  local src="$ROOT/runtime" dst="$TMP_DIR/runtime_snapshot" archive="${TMP_DIR}/runtime_snapshot.tar.gz"
  
  # Clean up any existing snapshot
  rm -rf "$dst" "$archive" 2>/dev/null || true
  mkdir -p "$dst"
  
  # Copy runtime files (exclude locks, pids, temp files)
  rsync -a --delete-excluded \
    --exclude='*.lock' --exclude='*.pid' --exclude='*.sock' \
    --exclude='*.tmp' --exclude='*.sqlite-*' \
    "$src/" "$dst/" 2>/dev/null || true
  
  # Create tar.gz archive (don't make read-only - causes cleanup issues)
  if tar -czf "$archive" -C "$TMP_DIR" "runtime_snapshot" 2>/dev/null; then
    # Remove directory, keep only archive
    rm -rf "$dst" 2>/dev/null || true
    echo "$archive"
  else
    # Fallback: return directory if tar fails
  echo "$dst"
  fi
}

# ── Sync immutable data (state, snapshots) with checksums ──────────────────
rclone_sync_immutable(){
  local src="$1" dest="$2" label="$3"
  [[ ! -d "$src" ]] && { warn "Skipping missing: $src"; return 0; }
  info "Syncing $label → ${RCLONE_REMOTE}:${RCLONE_PATH}/${dest} (with checksums)"
  rclone copy "$src" "${RCLONE_REMOTE}:${RCLONE_PATH}/${dest}" \
    --create-empty-src-dirs --fast-list \
    --transfers="$TRANSFERS" --checkers="$CHECKERS" \
    --bwlimit="$BANDWIDTH_LIMIT" \
    --tpslimit=6 --tpslimit-burst=12 \
    --drive-chunk-size=64M --timeout=5m \
    --low-level-retries=10 --checksum \
    --exclude="*.lock" --exclude="*.pid" --exclude="*.sock" --exclude="*.tmp" \
    --log-file="$LOG_FILE" --log-level=INFO --stats=20s --stats-one-line \
    --ignore-errors 2>&1 | tee -a "$LOG_FILE"
  return ${PIPESTATUS[0]}
}

# ── Sync mutable data (logs) without checksums, size-only ─────────────────
rclone_sync_logs(){
  local src="$1" dest="$2" label="$3"
  [[ ! -d "$src" ]] && { warn "Skipping missing: $src"; return 0; }
  
  # Create temporary directory for old logs only
  local old_logs_dir="${TMP_DIR}/old_logs"
  rm -rf "$old_logs_dir" 2>/dev/null || true
  mkdir -p "$old_logs_dir"
  
  # Find and copy only old log files (older than LOG_AGE_MINUTES)
  local old_count=0
  while IFS= read -r -d '' file; do
    cp "$file" "$old_logs_dir/" 2>/dev/null && old_count=$((old_count + 1)) || true
  done < <(find "$src" -type f -name "*.log" ! -name "*.gz" -mmin +$LOG_AGE_MINUTES -print0 2>/dev/null)
  
  # Also include compressed logs (they're immutable)
  while IFS= read -r -d '' file; do
    cp "$file" "$old_logs_dir/" 2>/dev/null && old_count=$((old_count + 1)) || true
  done < <(find "$src" -type f -name "*.log.gz" -print0 2>/dev/null)
  
  if [[ $old_count -eq 0 ]]; then
    info "No old log files to sync (all newer than ${LOG_AGE_MINUTES} minutes)"
    return 0
  fi
  
  info "Syncing $label → ${RCLONE_REMOTE}:${RCLONE_PATH}/${dest} (${old_count} old files, size-only)"
  rclone copy "$old_logs_dir" "${RCLONE_REMOTE}:${RCLONE_PATH}/${dest}" \
    --create-empty-src-dirs --fast-list \
    --transfers=4 --checkers=4 \
    --bwlimit="$BANDWIDTH_LIMIT" \
    --tpslimit=6 --tpslimit-burst=12 \
    --drive-chunk-size=64M --timeout=5m \
    --low-level-retries=10 \
    --size-only --ignore-checksum --update \
    --exclude="*.lock" --exclude="*.pid" --exclude="*.sock" \
    --log-file="$LOG_FILE" --log-level=INFO --stats=20s --stats-one-line \
    --ignore-errors 2>&1 | tee -a "$LOG_FILE"
  local result=${PIPESTATUS[0]}
  
  # Clean up temp old logs dir
  rm -rf "$old_logs_dir" 2>/dev/null || true
  return $result
}

# ── Sync archive file (tar.gz) ────────────────────────────────────────────
rclone_sync_archive(){
  local archive="$1" dest="$2" label="$3"
  [[ ! -f "$archive" ]] && { warn "Skipping missing archive: $archive"; return 0; }
  info "Syncing $label archive → ${RCLONE_REMOTE}:${RCLONE_PATH}/${dest}"
  rclone copy "$archive" "${RCLONE_REMOTE}:${RCLONE_PATH}/${dest}/" \
    --fast-list \
    --transfers=2 --checkers=2 \
    --bwlimit="$BANDWIDTH_LIMIT" \
    --drive-chunk-size=64M --timeout=5m \
    --low-level-retries=10 --checksum \
    --log-file="$LOG_FILE" --log-level=INFO --stats=20s --stats-one-line \
    --ignore-errors 2>&1 | tee -a "$LOG_FILE"
  return ${PIPESTATUS[0]}
}

# ── Execution header ───────────────────────────────────────────────────
echo "running" > "$STATUS_FILE"
hc_ping "${HEALTHCHECK_URL}/start" || true
info "CloudSync initiated @ $(date '+%F %T')"
info "🧾 Log → $LOG_FILE"
info "📊 Configuration: LOG_AGE_MINUTES=${LOG_AGE_MINUTES}, RETRY_LIMIT=${RETRY_LIMIT}"

SUCCESS=false
BACKOFF=2
SYNC_RESULTS=()

# ── Main orchestration loop with partial success handling ─────────────────
for ATTEMPT in $(seq 1 "$RETRY_LIMIT"); do
  info "Attempt $ATTEMPT of $RETRY_LIMIT"
  
  # Prepare runtime snapshot (returns archive path)
  SNAPSHOT_ARCHIVE="$(prepare_runtime_snapshot)"

  # Track individual sync results
  SYNC_RESULTS=()
  
  # Sync immutable data (with checksums)
  if rclone_sync_immutable "$ROOT/snapshots" "snapshots" "Snapshots"; then
    SYNC_RESULTS+=("snapshots:✅")
  else
    SYNC_RESULTS+=("snapshots:❌")
    warn "Snapshots sync failed (non-fatal)"
  fi
  
  if rclone_sync_immutable "$ROOT/state" "state" "State"; then
    SYNC_RESULTS+=("state:✅")
  else
    SYNC_RESULTS+=("state:❌")
    warn "State sync failed (non-fatal)"
  fi
  
  # Sync runtime snapshot (archive file)
  if [[ -f "$SNAPSHOT_ARCHIVE" ]]; then
    if rclone_sync_archive "$SNAPSHOT_ARCHIVE" "runtime" "Runtime Snapshot"; then
      SYNC_RESULTS+=("runtime:✅")
    else
      SYNC_RESULTS+=("runtime:❌")
      warn "Runtime snapshot sync failed (non-fatal)"
    fi
  elif [[ -d "$SNAPSHOT_ARCHIVE" ]]; then
    # Fallback: sync directory if archive creation failed
    if rclone_sync_immutable "$SNAPSHOT_ARCHIVE" "runtime" "Runtime Snapshot"; then
      SYNC_RESULTS+=("runtime:✅")
    else
      SYNC_RESULTS+=("runtime:❌")
      warn "Runtime snapshot sync failed (non-fatal)"
    fi
  fi
  
  # Sync logs (size-only, old files only)
  if rclone_sync_logs "$ROOT/logs" "logs" "Logs"; then
    SYNC_RESULTS+=("logs:✅")
  else
    SYNC_RESULTS+=("logs:❌")
    warn "Logs sync failed (non-fatal - logs are actively written)"
  fi
  
  # Consider success if at least state and snapshots synced
  local critical_success=true
  for result in "${SYNC_RESULTS[@]}"; do
    if [[ "$result" == "state:❌" ]] || [[ "$result" == "snapshots:❌" ]]; then
      critical_success=false
      break
    fi
  done
  
  if $critical_success; then
    SUCCESS=true
    info "Sync summary: ${SYNC_RESULTS[*]}"
      break
  else
      warn "Attempt $ATTEMPT failed. Backing off ${BACKOFF}s..."
      sleep "$BACKOFF"
      BACKOFF=$(( BACKOFF * 2 )); [[ $BACKOFF -gt $MAX_BACKOFF ]] && BACKOFF=$MAX_BACKOFF
  fi
done

# ── Outcome Handling ───────────────────────────────────────────────────
if $SUCCESS; then
  ok "CloudSync completed successfully"
  info "Final results: ${SYNC_RESULTS[*]}"
  send_alert "✅ CloudSync successful on $(hostname) @ $(date '+%H:%M:%S')"
  hc_ping "$HEALTHCHECK_URL" || true
  echo "ok $(date '+%F %T')" > "$STATUS_FILE"
else
  err "CloudSync failed after $RETRY_LIMIT attempts"
  info "Final results: ${SYNC_RESULTS[*]}"
  send_alert "❌ CloudSync failed after $RETRY_LIMIT attempts on $(hostname)"
  hc_ping "${HEALTHCHECK_URL}/fail" || true
  echo "failed $(date '+%F %T')" > "$STATUS_FILE"
fi

# ── Cleanup + log tail ─────────────────────────────────────────────────
cleanup
info "🗂 Log saved → $LOG_FILE"
info "💠 CloudSync finished in $(ps -o etime= -p $$ 2>/dev/null || echo 'N/A') (PID $$)"
