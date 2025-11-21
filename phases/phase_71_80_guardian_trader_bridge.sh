#!/usr/bin/env bash
set -Eeuo pipefail
PHASE_LABEL="phase_71_80_guardian_trader_bridge"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/${PHASE_LABEL}_${STAMP}.log"
HEALTH_URL="http://127.0.0.1:5050/healthz"

TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT="YOUR_CHAT_ID"

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_FILE"; }

notify(){
  local msg="$1"
  [[ -n "$TELEGRAM_TOKEN" && -n "$TELEGRAM_CHAT" ]] && \
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT}" -d text="${msg}" >/dev/null 2>&1 || true
}

log "🧠 Phase 71–80 Bridge starting..."
notify "🧩 Guardian ↔ Trader Bridge activated on $(hostname)"

while true; do
  sleep 10
  status=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo 000)
  trader_pid=$(pgrep -f "smart_trader.py" || true)

  if [[ "$status" == "200" && -z "$trader_pid" ]]; then
    log "🟢 System healthy – starting SmartTrader"
    notify "🚀 SmartTrader auto-started"
    nohup python3 "$ROOT_DIR/trader/smart_trader.py" > "$LOG_DIR/trader_bridge_${STAMP}.log" 2>&1 &
  elif [[ "$status" != "200" && -n "$trader_pid" ]]; then
    log "🔴 System unhealthy – pausing SmartTrader"
    notify "⏸ SmartTrader paused (dashboard down)"
    pkill -f "smart_trader.py" || true
  fi
done

