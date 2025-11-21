#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
RUNTIME_DIR="${ROOT_DIR}/runtime"; mkdir -p "$RUNTIME_DIR"
STATE="${RUNTIME_DIR}/atlas_learning.json"
DD_FILE="${RUNTIME_DIR}/drawdown_state.json"
LOG_FILE="${LOG_DIR}/drawdown_guard.log"

log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE"; }

# seed
[[ -f "$DD_FILE" ]] || echo '{"equity_start":0,"equity_now":0,"daily_dd":0,"weekly_dd":0,"halt":false}' > "$DD_FILE"

log "🧯 Drawdown Guard online"

# NOTE: Replace with real equity source if available.
get_equity(){ jq -r '.equity // 90000.0' "$STATE" 2>/dev/null || echo 90000.0; }

DAY_START_TS=$(date +%s)
WEEK_START_TS=$DAY_START_TS

while true; do
  sleep 15
  [[ -f "$STATE" ]] || { log "Waiting for state..."; continue; }
  EQ=$(get_equity)
  NOW=$(date +%s)

  # Reset daily/weekly anchors
  if (( NOW - DAY_START_TS > 86400 )); then DAY_START_TS=$NOW; DAY_EQ=$EQ; fi
  if (( NOW - WEEK_START_TS > 604800 )); then WEEK_START_TS=$NOW; WEEK_EQ=$EQ; fi

  DAY_EQ=${DAY_EQ:-$EQ}
  WEEK_EQ=${WEEK_EQ:-$EQ}

  DD_DAY=$(python3 - <<PY
eq=$EQ; start=$DAY_EQ
print(0 if start==0 else max(0,(start-eq)/start))
PY
)
  DD_WEEK=$(python3 - <<PY
eq=$EQ; start=$WEEK_EQ
print(0 if start==0 else max(0,(start-eq)/start))
PY
)

  HALT=false
  (( $(echo "$DD_DAY >= 0.020" | bc -l) )) && HALT=true
  (( $(echo "$DD_WEEK >= 0.050" | bc -l) )) && HALT=true

  jq -n --argjson equity_now "$EQ" \
        --argjson daily_dd "$DD_DAY" \
        --argjson weekly_dd "$DD_WEEK" \
        --argjson halt "$HALT" \
        --arg day_anchor "${DAY_EQ:-$EQ}" \
        --arg week_anchor "${WEEK_EQ:-$EQ}" \
        '{equity_now:$equity_now, daily_dd:$daily_dd, weekly_dd:$weekly_dd, halt:$halt, day_anchor:$day_anchor, week_anchor:$week_anchor, ts:now}' \
        > "$DD_FILE"

  if [[ "$HALT" == "true" ]]; then
    log "⛔ HALT — DD day=$(printf '%.2f' "$(echo "$DD_DAY*100" | bc -l)")%% week=$(printf '%.2f' "$(echo "$DD_WEEK*100" | bc -l)")%%"
  else
    log "🟢 Safe — DD day=$(printf '%.2f' "$(echo "$DD_DAY*100" | bc -l)")%% week=$(printf '%.2f' "$(echo "$DD_WEEK*100" | bc -l)")%%"
  fi
done

