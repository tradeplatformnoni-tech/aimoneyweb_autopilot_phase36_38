#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_BIN="${ROOT}/venv/bin/python3"
LOG_DIR="${ROOT}/logs"
LOG_FILE="${LOG_DIR}/schedule_fast_refresh.log"

mkdir -p "${LOG_DIR}"

log() {
  local now
  now="$(date '+%F %T')"
  echo "[$now] $*" >> "${LOG_FILE}"
}

run_cmd() {
  local desc="$1"
  shift
  log "▶️ ${desc}"
  # shellcheck disable=SC2068
  "$@" >> "${LOG_FILE}" 2>&1 && log "✅ ${desc} complete" || log "❌ ${desc} failed"
}

FAST_INTERVAL_SECONDS="${FAST_INTERVAL_SECONDS:-1800}"  # default 30 minutes

log "🚀 Fast refresh scheduler starting (interval=${FAST_INTERVAL_SECONDS}s)"

while true; do
  run_cmd "Strategy performance snapshot" \
    "${PY_BIN}" "${ROOT}/analytics/strategy_performance.py" --once

  for sport in nba soccer; do
    run_cmd "Sports model report (${sport})" \
      "${PY_BIN}" "${ROOT}/analytics/sports_model_report.py" --sport "${sport}"
  done

  sleep "${FAST_INTERVAL_SECONDS}"
done
