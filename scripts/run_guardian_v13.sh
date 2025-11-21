#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${ROOT:-$HOME/neolight}"
VENV="${VENV:-$ROOT/venv}"
LOGS="${LOGS:-$ROOT/logs}"
mkdir -p "$LOGS"

PY="$VENV/bin/python"
UVICORN="$VENV/bin/uvicorn"

heal_ports() {
  for P in 8090 8091 8092 8093 8094 8095 8096 8097 8098 8099 8100 8105; do
    lsof -i :$P -t | xargs -r kill -9 || true
  done
}

ensure_running() {
  local name=$1 cmd=$2 log=$3
  echo "🧠 Ensuring $name"
  nohup bash -lc "
    source '$VENV/bin/activate'
    export PYTHONPATH='$ROOT'
    cd '$ROOT'
    while true; do
      echo '[Guardian v13] Starting $name @' \$(date -Is) >> '$log'
      $cmd >> '$log' 2>&1 &
      pid=\$!
      sleep 2
      if ! kill -0 \$pid 2>/dev/null; then
        echo '[Guardian v13] $name crashed. Retrying...' >> '$log'
        sleep 2
      else
        wait \$pid
      fi
    done
  " >/dev/null 2>&1 &
}

heal_ports

ensure_running "intelligence_orchestrator" "$PY $ROOT/agents/intelligence_orchestrator.py" "$LOGS/intelligence_orchestrator_v13.log"
ensure_running "smart_trader" "$PY $ROOT/trader/smart_trader.py" "$LOGS/smart_trader_v13.log"
ensure_running "weights_bridge" "$PY $ROOT/agents/weights_bridge.py" "$LOGS/weights_bridge_v13.log"
ensure_running "dashboard_v3" "$UVICORN dashboard.status_endpoint:app --host 0.0.0.0 --port 8100" "$LOGS/dashboard_v3_v13.log"

echo "✅ Guardian v13 launcher started. Logs in $LOGS/"
