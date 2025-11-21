#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/runtime"; mkdir -p "$RUNTIME_DIR"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/risk_governor.log"
STATE_JSON="${RUNTIME_DIR}/atlas_learning.json"
PARAMS_JSON="${RUNTIME_DIR}/smart_params.json"
GUARD_FILE="${RUNTIME_DIR}/risk_gate.json"

green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE"; }

jqget(){ jq -r "$2" "$1" 2>/dev/null || echo ""; }

log "🛡️  Risk Governor v2 online"
: > "$GUARD_FILE"

while true; do
  sleep 10
  [[ -f "$STATE_JSON" ]] || { log "$(yellow "waiting for state...")"; continue; }
  [[ -f "$PARAMS_JSON" ]] || { log "$(yellow "waiting for params...")"; continue; }

  WR=$(jqget "$STATE_JSON" '.win_rate // 0.5')
  TRADES=$(jqget "$STATE_JSON" '.total_trades // 0')
  RF=$(jqget "$STATE_JSON" '.risk_factor // 1.0')

  MAX_PCT=$(jqget "$PARAMS_JSON" '.MAX_PCT_RISK // 0.008')
  # Hard brakes: daily/weekly drawdown caps (percent-of-equity)
  DAILY_CAP=0.020   # 2% daily
  WEEKLY_CAP=0.050  # 5% weekly

  # Convert to gates. Here we just signal to SmartTrader/bridge via risk_gate.json
  # You can expand to call broker throttle endpoints if available.
  PHASE="NORMAL"
  if (( $(echo "$WR < 0.45" | bc -l) )); then
    MAX_PCT=$(echo "$MAX_PCT * 0.85" | bc -l)
    PHASE="DEFENSIVE"
  elif (( $(echo "$WR > 0.58" | bc -l) )); then
    MAX_PCT=$(echo "$MAX_PCT * 1.05" | bc -l)
    PHASE="OFFENSIVE"
  fi

  jq -n --argjson max_pct "$MAX_PCT" \
        --arg phase "$PHASE" \
        --argjson daily_cap "$DAILY_CAP" \
        --argjson weekly_cap "$WEEKLY_CAP" \
        '{max_pct_risk:$max_pct, phase:$phase, daily_cap:$daily_cap, weekly_cap:$weekly_cap, ts:now}' > "$GUARD_FILE"

  log "📏 Phase=$PHASE | MAX_PCT_RISK→$(printf '%.5f' "$MAX_PCT") | WR=$WR trades=$TRADES"
done

