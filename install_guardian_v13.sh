#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${ROOT:-$HOME/neolight}"
VENV="${VENV:-$ROOT/venv}"
LOGS="${LOGS:-$ROOT/logs}"
mkdir -p "$LOGS"

echo "✅ Installing Guardian v13 repair system..."
if [ ! -x "$VENV/bin/python" ]; then
  /usr/bin/env python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip wheel setuptools
"$VENV/bin/pip" install psutil uvicorn fastapi plotly pandas yfinance gTTS Pillow playsound3 || true

cat > "$ROOT/neo_light_fix.sh" <<'BASH'
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
    while true; do
      echo '[Guardian] Starting $name' >> '$log'
      $cmd >> '$log' 2>&1 &
      pid=\$!
      sleep 2
      if ! kill -0 \$pid 2>/dev/null; then
        echo '[Guardian] $name crashed. Retrying...' >> '$log'
        sleep 2
      else
        wait \$pid
      fi
    done
  " >/dev/null 2>&1 &
}

heal_ports

ensure_running "intelligence_orchestrator" "$PY intelligence_orchestrator.py" "$LOGS/intelligence_orchestrator.log"
ensure_running "smart_trader" "$PY smart_trader.py" "$LOGS/smart_trader.log"
ensure_running "weights_bridge" "$PY weights_bridge.py" "$LOGS/weights_bridge.log"
ensure_running "dashboard_v3" "$UVICORN dashboard_v3:app --host 0.0.0.0 --port 8100" "$LOGS/dashboard_v3.log"

echo "✅ Guardian v13 started. Logs in $LOGS/"
BASH

chmod +x "$ROOT/neo_light_fix.sh"
echo "✅ Guardian v13 installed successfully!"
