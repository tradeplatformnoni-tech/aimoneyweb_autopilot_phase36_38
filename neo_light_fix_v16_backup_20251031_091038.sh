#!/usr/bin/env bash
# ============================================================
# 🌍 NeoLight Guardian v16.0 — Fully Autonomous + Live Health API
# ============================================================
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${ROOT:-$HOME/neolight}"
VENV="${VENV:-$ROOT/venv}"
LOGS="${LOGS:-$ROOT/logs}"
RUNTIME="${RUNTIME:-$ROOT/runtime}"
LOCK="$RUNTIME/.guardian.lock"

mkdir -p "$LOGS" "$RUNTIME"
export PATH="$VENV/bin:$PATH"
export PYTHONPATH="${PYTHONPATH:-$ROOT}"
cd "$ROOT" || exit 1

PY="$VENV/bin/python"
UVICORN="$VENV/bin/uvicorn"

# --- Utility Display ---
color(){ printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
note(){  color "36" "🧠 $*"; }
ok(){    color "32" "✅ $*"; }
warn(){  color "33" "⚠️  $*"; }
err(){   color "31" "🛑 $*"; }

# --- Health Endpoint: /status ---
mkdir -p "$ROOT/dashboard"
cat > "$ROOT/dashboard/status_endpoint.py" <<'PY'
from fastapi import FastAPI
import psutil, os, time, datetime, json, glob

app = FastAPI(title="NeoLight Health API", version="16.0")

def last_log_updates(log_dir):
    result = {}
    for path in glob.glob(os.path.join(log_dir, "*.log")):
        name = os.path.basename(path)
        try:
            result[name] = time.ctime(os.path.getmtime(path))
        except Exception:
            result[name] = "unavailable"
    return result

@app.get("/status")
def status():
    return {
        "system": {
            "uptime": datetime.datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=0.3),
            "mem_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent
        },
        "guardian": {
            "pid": os.getpid(),
            "logs": last_log_updates(os.path.expanduser("~/neolight/logs")),
            "agents": [p.info for p in psutil.process_iter(attrs=["pid","name","cmdline"]) if any(k in " ".join(p.info["cmdline"]) for k in ["intelligence_orchestrator","smart_trader","weights_bridge","uvicorn"])]
        }
    }
PY

# --- Guardian Core ---
if [[ "${1:-}" == "--force" ]]; then
  warn "Force mode — unlocking Guardian..."
  rm -f "$LOCK"
fi
if [[ -f "$LOCK" ]]; then
  warn "Guardian already running ($LOCK). Exiting."
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"; warn "Guardian stopped gracefully."' EXIT

note "Preparing environment..."
mkdir -p "$LOGS"
for log in intelligence_orchestrator smart_trader weights_bridge dashboard_v3 guardian; do
  : > "$LOGS/$log.log"
done

note "Healing Python environment..."
"$VENV/bin/pip" install --upgrade pip wheel setuptools python-dateutil fastapi psutil >/dev/null 2>&1 || true

note "Healing ports..."
pkill -f "uvicorn.*8100" >/dev/null 2>&1 || true
for P in 8090 8091 8092 8093 8094 8095 8096 8097 8098 8099 8100 8105; do
  lsof -i :$P -t | xargs -r kill -9 || true
done

# --- Smart Runner ---
ensure_running() {
  local name="$1" cmd="$2" log="$3"
  note "Ensuring $name"
  nohup bash -lc "
    source '$VENV/bin/activate'
    export PYTHONPATH='$ROOT'
    cd '$ROOT'
    backoff=2
    while true; do
      echo '[Guardian] Starting $name @' \$(date '+%Y-%m-%dT%H:%M:%S') >> '$log'
      $cmd >> '$log' 2>&1 &
      pid=\$!
      sleep 3
      if ! kill -0 \$pid 2>/dev/null; then
        echo '[Guardian] $name crashed. Backoff '\$backoff's' >> '$log'
        sleep \$backoff
        backoff=\$((backoff*2)); [ \$backoff -gt 60 ] && backoff=60
      else
        wait \$pid
        backoff=2
      fi
    done
  " >/dev/null 2>&1 &
}

# --- Launch agents ---
ensure_running "intelligence_orchestrator" "$PY ./agents/intelligence_orchestrator.py" "$LOGS/intelligence_orchestrator.log"
ensure_running "smart_trader" "$PY ./trader/smart_trader.py" "$LOGS/smart_trader.log"
ensure_running "weights_bridge" "$PY ./agents/weights_bridge.py" "$LOGS/weights_bridge.log"

# --- Dashboard with Status API ---
while lsof -i :8100 >/dev/null 2>&1; do
  warn "Port 8100 busy, waiting 5s..."
  sleep 5
done
ensure_running "dashboard_v3" "$UVICORN dashboard.status_endpoint:app --host 0.0.0.0 --port 8100" "$LOGS/dashboard_v3.log"

ok "Guardian v16.0 active — monitoring + health API live at http://localhost:8100/status"

# --- Main loop (continuous maintenance) ---
while true; do
  note "Assessing system health..."
  df -h > "$LOGS/system_health.log" 2>&1
  ps -eo pid,comm,%cpu,%mem | sort -k3 -r | head -n 15 >> "$LOGS/system_health.log"
  sleep 300
done
