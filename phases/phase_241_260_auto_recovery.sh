#!/usr/bin/env bash
set -Eeuo pipefail

LABEL="phase_241_260_auto_recovery"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${ROOT}/state/performance_metrics.csv"
LOG_DIR="${ROOT}/logs"; mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/${LABEL}_${STAMP}.log"

GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

# thresholds (tune later / can come from runtime JSON)
MAX_DRAWDOWN="8.0"   # %
MIN_WINRATE="0.40"
MIN_SHARPE="-0.10"   # if negative for long, consider intervene
COOLDOWN_SEC=600

log "🩺 Auto-Recovery supervisor active"

get_latest(){
  tail -n 1 "$STATE" 2>/dev/null || echo ""
}

while true; do
  sleep 300
  row="$(get_latest)"
  [ -z "$row" ] && { log "No metrics yet"; continue; }
  IFS=, read -r ts equity pnl dd sharpe sortino wr t7 <<< "$row"

  # Compare thresholds
  bad_dd=$(awk "BEGIN{print ($dd > $MAX_DRAWDOWN)?1:0}")
  bad_wr=$(awk "BEGIN{print ($wr < $MIN_WINRATE)?1:0}")
  bad_sh=$(awk "BEGIN{print ($sharpe < $MIN_SHARPE)?1:0}")

  if [ "$bad_dd" -eq 1 ] || [ "$bad_wr" -eq 1 ] || [ "$bad_sh" -eq 1 ]; then
    log "🔴 Degradation detected (dd=${dd}% wr=${wr} sharpe=${sharpe}) → Intervention"
    # Restart SmartTrader gently (paper/live based on your config)
    pkill -f "trader/smart_trader.py" || true
    sleep 3
    nohup python3 "${ROOT}/trader/smart_trader.py" > "${LOG_DIR}/trader_bridge.log" 2>&1 &
    log "🔁 SmartTrader restarted. Cooling ${COOLDOWN_SEC}s"
    sleep "$COOLDOWN_SEC"
  else
    log "🟢 Performance ok (dd=${dd}% wr=${wr} sharpe=${sharpe})"
  fi
done

