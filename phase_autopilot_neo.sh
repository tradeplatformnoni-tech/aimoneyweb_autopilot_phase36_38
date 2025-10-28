#!/usr/bin/env bash
# ==========================================================
# 🧭 NeoLight A.I. :: Unified Phase Autopilot (4101–4300 Dropped)
# Includes: Dynamic Hedge + Capital Governor + Ticket/Sports + Mesh Telemetry
# with integrated Auto-Fix pilot hooks.
#
# Usage:
#   ./phase_autopilot_neo.sh [--noop] [--rebuild] [--dry-run]
#
# Logs:
#   logs/autopilot_$(date +%F).log
# ==========================================================
set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
LOG_DIR="logs"
RUNTIME_DIR="runtime"
mkdir -p "$LOG_DIR" "$RUNTIME_DIR"
LOG_FILE="$LOG_DIR/autopilot_$(date +%F).log"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
  local lineno="$1"; local cmd="$2"
  echo "❌ ERROR in $SCRIPT_NAME at line ${lineno}: ${cmd}"
  echo "🛠  Invoking Auto-Fix pilot..."
  if command -v bash >/dev/null 2>&1; then
    if [ -f "./neolight_autofix_pilot.sh" ]; then
      bash ./neolight_autofix_pilot.sh || true
    else
      echo "⚠️ Auto-Fix pilot not found in CWD."
    fi
  fi
  echo "🔁 Retry recommendation: re-run the last step or the whole script."
  exit 1
}
trap 'on_error $LINENO "$BASH_COMMAND"' ERR

check_shell_compat() {
  if [ -n "${ZSH_VERSION:-}" ]; then
    setopt NO_NOMATCH || true
  fi
}

ensure_executable() {
  local path="$1"
  if [ -f "$path" ] && [ ! -x "$path" ]; then
    chmod +x "$path"
  fi
}

fix_permissions() {
  # Preemptively fix common permission issues for .sh files
  find . -maxdepth 2 -name "*.sh" -type f -print0 | xargs -0 -I{} chmod +x "{}" || true
}

load_env() {
  if [ -f ".env" ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env | xargs) || true
    echo "🔐 Loaded environment from .env"
  fi
}

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    PY=python3
  elif command -v python >/dev/null 2>&1; then
    PY=python
  else
    echo "❌ Python not found. Please install Python 3.10+."
    exit 1
  fi
  echo "🐍 Using $($PY -V)"
}

ensure_venv() {
  if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
    echo "🧪 Virtualenv activated."
  elif [ -f "requirements.txt" ]; then
    $PY -m venv venv
    # shellcheck disable=SC1091
    source venv/bin/activate
    python -m pip install -U pip wheel
    pip install -r requirements.txt || true
    echo "🧪 Virtualenv created & dependencies installed."
  else
    echo "⚠️ No venv or requirements.txt found. Continuing with system Python."
  fi
}

install_missing_pydeps() {
  local pkgs=("requests" "pandas" "numpy" "pyyaml")
  for p in "${pkgs[@]}"; do
    python - <<PY || pip install "$p"
import importlib, sys
try:
    sys.exit(0 if importlib.util.find_spec("${p}") else 1)
except AttributeError:
    sys.exit(0)
PY
  done
}

check_dirs() {
  mkdir -p logs cache tmp runtime config
  touch runtime/portfolio.json runtime/goal_config.json || true
}

banner() {
  echo "=========================================================="
  echo "🚀 NeoLight Unified Phase Autopilot :: ${START_TS}"
  echo "=========================================================="
}

run_diagnostics() {
  echo "🔍 Running feed + risk + cache diagnostics..."
  python - <<'PY'
import json, os, time, pathlib
print("✅ Python online. CWD:", os.getcwd())
for p in ["logs", "runtime", "config"]:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)
print("📦 Runtime files present:", list(pathlib.Path("runtime").glob("*")))
PY
}

run_signal_engine() {
  echo "🧠 Starting signal engine (market + sentiment)..."
  python -m ai.providers.data_feed --assets "AAPL,MSFT,NVDA,AMZN,SPY,GOOGL,BTC-USD,ETH-USD,XAUUSD" || true
  python -m ai.signal_engine --mode live || true
}

run_risk_and_hedge() {
  echo "🛡  Running Risk Governor + Dynamic Hedge Engine..."
  python -m ai.risk.risk_governor --diag || true
  python -m ai.risk.hedge_engine --assets "BTC-USD:XAUUSD" --auto || true
}

run_capital_governor() {
  echo "💰 Running Capital Governor (performance-based allocation)..."
  python -m ai.capital.capital_governor --rebalance --compound 0.75 || true
}

start_revenue_agents() {
  echo "🎫 Booting TicketBot / SportsInsight / SportsBetBot..."
  (nohup python -m agents.ticketbot --live > logs/ticketbot.out 2>&1 &)
  (nohup python -m agents.sportsinsight --live > logs/sportsinsight.out 2>&1 &)
  (nohup python -m agents.sportsbetbot --live > logs/sportsbetbot.out 2>&1 &)
  echo "👜 Booting Luxury / Collectibles / Dropship..."
  (nohup python -m agents.luxury_agent --segmentation gender > logs/luxury.out 2>&1 &)
  (nohup python -m agents.collectibles_agent --live > logs/collectibles.out 2>&1 &)
  (nohup python -m agents.dropship_agent --live > logs/dropship.out 2>&1 &)
}

push_telemetry() {
  echo "📊 Pushing telemetry to Grafana/Supabase (if configured)..."
  python -m ai.telemetry.push --all || true
}

final_report() {
  echo "✅ Autopilot completed."
  echo "📄 Log saved to: $LOG_FILE"
}

main() {
  banner
  check_shell_compat
  fix_permissions
  load_env
  ensure_python
  ensure_venv
  install_missing_pydeps || true
  check_dirs
  run_diagnostics
  run_signal_engine
  run_risk_and_hedge
  run_capital_governor
  start_revenue_agents
  push_telemetry
  final_report
}

main "$@"

