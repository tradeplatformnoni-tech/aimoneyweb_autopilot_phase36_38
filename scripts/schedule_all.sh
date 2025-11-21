#!/usr/bin/env bash
set -euo pipefail
ROOT="${HOME}/neolight"
PY="${ROOT}/venv/bin/python3"
LOG="${ROOT}/logs/schedule_stdout.log"
STATE_DIR="${ROOT}/runtime/scheduler"

mkdir -p "${ROOT}/logs"
mkdir -p "${STATE_DIR}"

run_daily_task() {
  local task_name="$1"
  shift
  local stamp="${STATE_DIR}/${task_name}_$(date '+%F').stamp"
  if [[ ! -f "$stamp" ]]; then
    local command_desc="$1"; shift
    local now="$(date '+%F %T')"
    echo "[$now] ▶️ Running scheduled task: ${command_desc}" >> "$LOG" 2>&1
    # shellcheck disable=SC2068
    "$@" >> "$LOG" 2>&1 && touch "$stamp"
  fi
}

run_weekly_task() {
  local task_name="$1"
  shift
  local stamp="${STATE_DIR}/${task_name}_$(date '+%G-%V').stamp"
  if [[ ! -f "$stamp" ]]; then
    local command_desc="$1"; shift
    local now="$(date '+%F %T')"
    echo "[$now] 🔁 Weekly scheduled task: ${command_desc}" >> "$LOG" 2>&1
    # shellcheck disable=SC2068
    "$@" >> "$LOG" 2>&1 && touch "$stamp"
  fi
}

while true; do
  NOW="$(date '+%F %T')"
  echo "[$NOW] 🔁 Intelligence tick…" >> "$LOG" 2>&1
  nohup "$PY" "$ROOT/agents/intelligence_orchestrator.py" >> "${ROOT}/logs/intel_orchestrator.log" 2>&1 || true
  # optional knowledge integrator; harmless if missing
  if [[ -f "${ROOT}/agents/knowledge_integrator.py" ]]; then
    nohup "$PY" "$ROOT/agents/knowledge_integrator.py" >> "${ROOT}/logs/knowledge_integrator.log" 2>&1 || true
  fi

  run_daily_task "strategy_performance_daily" \
    "strategy performance report" \
    "$PY" "$ROOT/analytics/strategy_performance.py" --daily

  run_daily_task "sports_model_nba" \
    "sports model report NBA" \
    "$PY" "$ROOT/analytics/sports_model_report.py" --sport nba

  run_daily_task "sports_model_soccer" \
    "sports model report Soccer" \
    "$PY" "$ROOT/analytics/sports_model_report.py" --sport soccer

  run_weekly_task "ai_rebalance_review" \
    "AI cohort weekly rebalance snapshot" \
    "$PY" "$ROOT/analytics/weekly_ai_rebalance.py"

  run_weekly_task "commodity_tail_risk" \
    "Commodity hedge tail-risk monitor" \
    "$PY" "$ROOT/analytics/weekly_ai_rebalance.py" --macro-only

  sleep 14400  # 4 hours
done
