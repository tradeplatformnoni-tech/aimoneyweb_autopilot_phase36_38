#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
RUNTIME_DIR="${ROOT_DIR}/runtime"; mkdir -p "$RUNTIME_DIR"
ARCHIVE_DIR="${ROOT_DIR}/archive"; mkdir -p "$ARCHIVE_DIR"
LOG_FILE="${LOG_DIR}/telemetry.log"
STATE_JSON="${RUNTIME_DIR}/atlas_learning.json"
PNL_CSV="${ROOT_DIR}/state/pnl_history.csv"

notify(){
  local msg="$1"
  [[ -n "$TELEGRAM_TOKEN" && -n "$TELEGRAM_CHAT" ]] && \
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
      -d chat_id="${TELEGRAM_CHAT}" -d text="${msg}" >/dev/null 2>&1 || true
}

log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE"; }

log "📡 Telemetry online"

LAST_HOUR=""
while true; do
  sleep 30
  [[ -f "$STATE_JSON" ]] || continue

  hour="$(date +%Y-%m-%dT%H)"
  if [[ "$hour" != "$LAST_HOUR" ]]; then
    LAST_HOUR="$hour"
    WR=$(jq -r '.win_rate // 0.5' "$STATE_JSON" 2>/dev/null || echo 0.5)
    RF=$(jq -r '.risk_factor // 1.0' "$STATE_JSON" 2>/dev/null || echo 1.0)
    TT=$(jq -r '.total_trades // 0' "$STATE_JSON" 2>/dev/null || echo 0)
    msg="🕰️ Hourly | Win $(printf '%.0f' "$(echo "$WR*100" | bc -l)")%% | Risk $(printf '%.2f' "$RF") | Trades $TT"
    log "$msg"; notify "$msg"

    # snapshot CSV/STATE hourly
    TS="$(date +%Y%m%d_%H%M)"
    cp -f "$STATE_JSON" "${ARCHIVE_DIR}/atlas_state_${TS}.json" 2>/dev/null || true
    [[ -f "$PNL_CSV" ]] && cp -f "$PNL_CSV" "${ARCHIVE_DIR}/pnl_${TS}.csv" 2>/dev/null || true
  fi
done

