#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s lastpipe

LABEL="phase_151_300_master"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/logs"; mkdir -p "$LOG_DIR"
RUN_DIR="${ROOT}/runtime"; mkdir -p "$RUN_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/${LABEL}_${STAMP}.log"

GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
ok(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "${GREEN}$*${RESET}" | tee -a "$LOG"; }
warn(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "${YELLOW}$*${RESET}" | tee -a "$LOG"; }
err(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "${RED}$*${RESET}" | tee -a "$LOG"; }

need(){ command -v "$1" >/dev/null 2>&1 || { err "Missing dependency: $1"; exit 1; }; }

ok "🚀 Phase 151–300 Master starting"
need python3; need curl; need jq
if ! command -v flock >/dev/null 2>&1; then
  warn "flock not found (recommended). Proceeding without it (single-run assumed)."
fi

# Prefer your dedicated venv if present
if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate" || warn "Could not activate $ROOT/.venv"
elif [ -f "$HOME/.neolight_env/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.neolight_env/.venv/bin/activate" || warn "Could not activate ~/.neolight_env/.venv"
else
  warn "No venv found — relying on system Python"
fi

# One instance guard
LOCKF="${RUN_DIR}/${LABEL}.lock"
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCKF"
  if ! flock -n 9; then
    warn "Another ${LABEL} is running. Exiting."
    exit 0
  fi
fi

# Health check for dashboard
HEALTH_URL="http://127.0.0.1:5050/healthz"
code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo 000)
if [ "$code" != "200" ]; then
  warn "Dashboard not healthy ($code). Attempting to start it."
  pkill -f "uvicorn app:app" || true
  # Run in background
  (cd "${ROOT}/dashboard" && nohup uvicorn app:app --host 0.0.0.0 --port 5050 --reload > "${LOG_DIR}/dashboard_${STAMP}.log" 2>&1 &)
  sleep 3
  code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo 000)
  [ "$code" = "200" ] && ok "🟢 Dashboard healthy (200)" || err "🔴 Dashboard still unhealthy ($code)"
else
  ok "🟢 Dashboard healthy (200)"
fi

# Start subphases (idempotent / restartable)
# 151–200 Analytics
nohup bash "${ROOT}/phases/phase_151_200_analytics.sh" >> "${LOG_DIR}/phase_151_200_analytics.log" 2>&1 &

# 201–240 Metrics Exporter (Prometheus text endpoint + model health)
if ! pgrep -f "python3 ${ROOT}/phases/phase_201_240_metrics_exporter.py" >/dev/null 2>&1; then
  nohup python3 "${ROOT}/phases/phase_201_240_metrics_exporter.py" >> "${LOG_DIR}/metrics_exporter.log" 2>&1 &
fi

# 241–260 Auto-Recovery Supervisor
nohup bash "${ROOT}/phases/phase_241_260_auto_recovery.sh" >> "${LOG_DIR}/phase_241_260_auto_recovery.log" 2>&1 &

# 261–280 Wealth Forecaster (hourly)
if ! pgrep -f "python3 ${ROOT}/phases/phase_261_280_wealth_forecaster.py" >/dev/null 2>&1; then
  nohup python3 "${ROOT}/phases/phase_261_280_wealth_forecaster.py" >> "${LOG_DIR}/wealth_forecaster.log" 2>&1 &
fi

# 281–300 Ops Hardening (tidy logs, prune, validate env)
nohup bash "${ROOT}/phases/phase_281_300_ops_hardening.sh" >> "${LOG_DIR}/phase_281_300_ops_hardening.log" 2>&1 &

ok "✅ Phase 151–300 services launched"

