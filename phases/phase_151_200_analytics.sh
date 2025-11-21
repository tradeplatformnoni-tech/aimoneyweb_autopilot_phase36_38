#!/usr/bin/env bash
set -Eeuo pipefail

LABEL="phase_151_200_analytics"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/logs"; mkdir -p "$LOG_DIR"
RUN_DIR="${ROOT}/runtime"; mkdir -p "$RUN_DIR"
STATE_DIR="${ROOT}/state"; mkdir -p "$STATE_DIR"
CSV="${STATE_DIR}/performance_metrics.csv"
HEALTH="${STATE_DIR}/model_health.json"
TRADER_LOG="${ROOT}/logs/trader_bridge.log"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/${LABEL}_${STAMP}.log"

GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

init_csv(){
  if [ ! -f "$CSV" ]; then
    echo "timestamp,equity,pnl_1d,drawdown,sharpe_30d,sortino_30d,win_rate_7d,trades_7d" > "$CSV"
  fi
}

calc_metrics(){
  # Lightweight parse from SmartTrader messages & state
  local equity=0 pnl_1d=0 dd=0 sharpe=0 sortino=0 wr=0 t7=0
  # Equity proxy: last cash + realized pnl in trader/state.json (if present)
  if [ -f "${ROOT}/trader/state.json" ]; then
    equity=$(jq -r '.balances.USD + 0' "${ROOT}/trader/state.json" 2>/dev/null || echo 0)
  fi

  # PnL signals (very simple: count SELL win/loss lines)
  local wins losses
  wins=$(grep -a "🟥 SELL" "$TRADER_LOG" 2>/dev/null | awk '{for(i=1;i<=NF;i++){if($i ~ /pnl=/){split($i,a,"="); if(a[2]>=0) c++}}} END{print 0+c}')
  losses=$(grep -a "🟥 SELL" "$TRADER_LOG" 2>/dev/null | awk '{for(i=1;i<=NF;i++){if($i ~ /pnl=/){split($i,a,"="); if(a[2]<0) c++}}} END{print 0+c}')
  local total=$((wins+losses))
  if [ "$total" -gt 0 ]; then wr=$(awk "BEGIN{print $wins/$total}"); fi
  t7=$total

  # Placeholder daily pnl and risk stats (refine later with actual equity curve)
  pnl_1d="0"
  dd="0.0"
  sharpe="0.0"
  sortino="0.0"

  echo "$equity,$pnl_1d,$dd,$sharpe,$sortino,$wr,$t7"
}

write_health(){
  # Model health: uptime & restarts gleaned from logs (simplified)
  local restarts=0
  restarts=$(grep -a "Guardian restarting" "${LOG_DIR}"/daemon_*.log 2>/dev/null | wc -l | tr -d ' ')
  jq -n --arg ts "$(date -Iseconds)" \
        --arg uptime "$(uptime | sed 's/^ *//')" \
        --argjson restarts "$restarts" \
        '{last_update:$ts, uptime:$uptime, restarts:$restarts}' > "$HEALTH"
}

log "🧮 Analytics engine online"
init_csv

while true; do
  IFS=, read -r equity pnl dd sharpe sortino wr t7 < <(calc_metrics)
  echo "$(date -Iseconds),${equity},${pnl},${dd},${sharpe},${sortino},${wr},${t7}" >> "$CSV"
  write_health
  log "📈 Appended metrics → equity=${equity} win_rate=$(printf '%.2f' "${wr:-0}") trades_7d=${t7:-0}"
  sleep 3600
done

