#!/usr/bin/env bash
set -Eeuo pipefail

# ╔══════════════════════════════════════════════════════════════════════════╗
# 🌍 NeoLight Guardian Daemon v8.0 — World-Class 24/7 Autonomous Supervisor
# ╚══════════════════════════════════════════════════════════════════════════╝
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
DAEMON_LOG="${LOG_DIR}/daemon_${STAMP}.log"
PHASE_SCRIPT="${ROOT_DIR}/phases/phase_41_50_atlas_dashboard.sh"
HEALTH_URL="http://127.0.0.1:5050/healthz"

# Optional integrations
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID:-}"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

# ── Colors ────────────────────────────────────────────────────────────────
GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; CYAN=$'\033[0;36m'; RESET=$'\033[0m'

# ── Logging & Notifications ───────────────────────────────────────────────
log()   { printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$DAEMON_LOG"; }
ok()    { log "${GREEN}$*${RESET}"; }
warn()  { log "${YELLOW}$*${RESET}"; }
err()   { log "${RED}$*${RESET}"; }

notify(){
  local msg="$1"
  [[ -n "$TELEGRAM_TOKEN" && -n "$TELEGRAM_CHAT" ]] && \
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
      -d chat_id="${TELEGRAM_CHAT}" -d text="${msg}" >/dev/null 2>&1 || true
  [[ -n "$DISCORD_WEBHOOK" ]] && \
    curl -s -H "Content-Type: application/json" -X POST \
      -d "{\"content\": \"${msg}\"}" "${DISCORD_WEBHOOK}" >/dev/null 2>&1 || true
}

# ── Safety Trap & Auto-Restart ────────────────────────────────────────────
restart_guardian(){
  warn "💥 Guardian restarting after crash..."
  notify "Guardian auto-restarted on $(hostname)"
  exec nohup bash "$0" >>"$DAEMON_LOG" 2>&1 &
  exit 0
}
trap 'err "Unhandled error occurred."; restart_guardian' ERR INT TERM

# ── Start Banner ─────────────────────────────────────────────────────────
ok "🧠 NeoLight Guardian Daemon initialized @ $(date)"
warn "Logs → $DAEMON_LOG"

# ── Daily Log Rotation ──────────────────────────────────────────────────
(
  while true; do
    sleep 86400
    mv "$DAEMON_LOG" "${DAEMON_LOG%.log}_$(date +%H%M).log" 2>/dev/null || true
    touch "$DAEMON_LOG"
    ok "📜 Log rotated successfully"
  done
) &

# ── Dashboard Launch Helper ─────────────────────────────────────────────
launch_dashboard(){
  warn "🚀 Launching dashboard manually..."
  cd "${ROOT_DIR}/dashboard" || { err "Dashboard directory missing"; return 1; }
  nohup uvicorn app:app --host 0.0.0.0 --port 5050 --reload > "${LOG_DIR}/dashboard_${STAMP}.log" 2>&1 &
  DASH_PID=$!
  sleep 3
  ok "✅ Dashboard started (PID: $DASH_PID)"
}

# ── Watchdog Loop ───────────────────────────────────────────────────────
while true; do
  sleep 10

  # Verify phase script presence
  if [[ ! -f "$PHASE_SCRIPT" ]]; then
    err "Missing phase script — attempting recovery"
    notify "Phase script missing on $(hostname)"
    sleep 30
    continue
  fi

  # Health check dashboard
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo 000)
  if [[ "$STATUS" != "200" ]]; then
    warn "🔴 Dashboard unhealthy ($STATUS) — initiating fix"
    notify "Dashboard unhealthy ($STATUS) on $(hostname)"

    # Attempt clean restart
    pkill -f "uvicorn app:app" >/dev/null 2>&1 || true
    sleep 3
    bash "$ROOT_DIR/neo_light_fix.sh" >>"$DAEMON_LOG" 2>&1 &
    sleep 15

    # Second-pass: if still unhealthy → invoke Smart Auto-Repair
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo 000)
    if [[ "$STATUS" != "200" ]]; then
      warn "🧩 Invoking Smart Auto-Repair Companion..."
      ~/.neolight_env/neo_guardian_autorepair.sh --verbose >> "$LOG_DIR/guardian_autorepair.log" 2>&1 || true
      sleep 20
      STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo 000)
      if [[ "$STATUS" != "200" ]]; then
        warn "Dashboard still unhealthy ($STATUS) — launching manual fallback."
        launch_dashboard
      fi
    fi
  else
    ok "🟢 Dashboard healthy ($STATUS)"
  fi

  # Lightweight System Telemetry
  CPU=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
  MEM=$(ps -A -o %mem | awk '{s+=$1} END {printf "%.1f", s}')
  log "📊 System load: CPU ${CPU}% | MEM ${MEM}%"

  # Health snapshot every 10 minutes
  if (( $(date +%s) % 600 < 10 )); then
    SNAP="${LOG_DIR}/snapshot_$(date +%Y%m%d_%H%M).json"
    echo "{\"timestamp\":\"$(date)\",\"cpu\":${CPU},\"mem\":${MEM},\"status\":${STATUS}}" > "$SNAP"
    v "💾 Saved snapshot → $SNAP"
  fi
done

