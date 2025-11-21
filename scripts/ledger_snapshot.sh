#!/usr/bin/env bash
# ╔════════════════════════════════════════════════════════════════╗
# ║  NeoLight Ledger Snapshot v3.0  —  "Atlas Keeper"              ║
# ║  Secure, reliable daily equity snapshots + cloud sync.         ║
# ╚════════════════════════════════════════════════════════════════╝

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
LOG_DIR="$ROOT/logs"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/ledger_snapshot_${STAMP}.log"
mkdir -p "$LOG_DIR"

# ────────────────────────────────────────────────────────────────
# 🎨 COLORS
# ────────────────────────────────────────────────────────────────
GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; CYAN=$'\033[0;36m'; RESET=$'\033[0m'
log()   { printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE"; }
ok()    { log "${GREEN}$*${RESET}"; }
warn()  { log "${YELLOW}$*${RESET}"; }
err()   { log "${RED}$*${RESET}"; }
info()  { log "${CYAN}$*${RESET}"; }

# ────────────────────────────────────────────────────────────────
# ⚙️ ENVIRONMENT VALIDATION
# ────────────────────────────────────────────────────────────────
VENV_PATH="$ROOT/.venv"
PYTHON_BIN="$VENV_PATH/bin/python"
LEDGER_SCRIPT="$ROOT/backend/ledger_engine.py"

if [[ ! -f "$LEDGER_SCRIPT" ]]; then
  err "Ledger engine missing: $LEDGER_SCRIPT"
  exit 1
fi

if [[ -d "$VENV_PATH" ]]; then
  source "$VENV_PATH/bin/activate"
else
  warn "⚠️ No .venv found — using system Python"
fi

# ────────────────────────────────────────────────────────────────
# 🧠 TELEGRAM ALERTS (optional)
# ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
send_alert() {
  [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return
  local msg="💾 NeoLight Ledger Snapshot: $*"
  curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" --data-urlencode text="$msg" >/dev/null || true
}

# ────────────────────────────────────────────────────────────────
# ☁️ GOOGLE DRIVE SYNC (optional, requires rclone)
# ────────────────────────────────────────────────────────────────
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
RCLONE_PATH="${RCLONE_PATH:-NeoLight}"
sync_to_drive() {
  if command -v rclone >/dev/null 2>&1; then
    info "☁️ Syncing snapshots → Google Drive"
    rclone copy "$ROOT/snapshots" "${RCLONE_REMOTE}:${RCLONE_PATH}/snapshots" --create-empty-src-dirs >/dev/null 2>&1 || warn "⚠️ Rclone snapshot sync failed"
    rclone copy "$ROOT/state" "${RCLONE_REMOTE}:${RCLONE_PATH}/state" --create-empty-src-dirs >/dev/null 2>&1 || true
  else
    warn "rclone not installed; skipping cloud sync"
  fi
}

# ────────────────────────────────────────────────────────────────
# 🧾 SNAPSHOT EXECUTION
# ────────────────────────────────────────────────────────────────
info "🧭 Starting ledger snapshot at $(date '+%F %T')"
{
  $PYTHON_BIN "$LEDGER_SCRIPT" --snapshot
} >>"$LOG_FILE" 2>&1 || {
  err "❌ Snapshot failed — check logs"
  send_alert "Snapshot failed ❌ — check ${LOG_FILE}"
  exit 2
}

ok "✅ Snapshot complete — stored in snapshots/ledger_$(date +%Y%m%d).json"
sync_to_drive
send_alert "Snapshot complete ✅ — $(hostname) @ $(date '+%H:%M:%S')"
ok "📦 Log saved → $LOG_FILE"

