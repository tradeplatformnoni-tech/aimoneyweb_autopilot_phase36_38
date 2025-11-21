#!/usr/bin/env bash
# =============================================================
# ⚙️ NeoLight Guardian v23 — Autonomous Final Quantum Build
# =============================================================
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${ROOT:-$HOME/neolight}"
VENV="${VENV:-$ROOT/venv}"
LOGS="${LOGS:-$ROOT/logs}"
RUNTIME="${RUNTIME:-$ROOT/runtime}"
LOCK="$RUNTIME/.guardian.lock"
mkdir -p "$LOGS" "$RUNTIME"
export PATH="$VENV/bin:$PATH"
export PYTHONPATH="$ROOT"
cd "$ROOT" || exit 1

PY="$VENV/bin/python"
UVICORN="$VENV/bin/uvicorn"

# ---- UI Helpers ----
color(){ printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
note(){  color "36" "🧠 $*"; }
ok(){    color "32" "✅ $*"; }
warn(){  color "33" "⚠️  $*"; }
err(){   color "31" "🛑 $*"; }

# ---- Clean Lock ----
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

# ---- Prepare Environment ----
note "Preparing environment..."
mkdir -p "$LOGS"
for log in intelligence_orchestrator smart_trader weights_bridge dashboard_v3 guardian; do
  : > "$LOGS/$log.log"
done

note "Healing Python environment..."
"$VENV/bin/pip" install --upgrade pip wheel setuptools >/dev/null 2>&1 || true
"$VENV/bin/pip" install -q fastapi uvicorn psutil starlette python-dateutil anyio click >/dev/null 2>&1 || true

# ---- Validate Python Health ----
note "Validating Python modules..."
"$PY" - <<'PY' || {
  import importlib, sys
  for mod in ['fastapi','uvicorn','psutil','starlette','anyio']:
      try: importlib.import_module(mod)
      except Exception as e: sys.exit(f"Missing or broken: {mod} ({e})")
  print("✅ Core Python modules OK")
PY
}

# ---- Rebuild Status Endpoint ----
mkdir -p "$ROOT/dashboard"
cat > "$ROOT/dashboard/status_endpoint.py" <<'PY'
from fastapi import FastAPI
import psutil, os, time, datetime, json, glob

app = FastAPI(title="NeoLight Guardian v23", version="23")

def safe_json(obj):
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception as e:
        return {"error": str(e)}

@app.get("/status")
def status():
    try:
        logs = {os.path.basename(f): time.ctime(os.path.getmtime(f)) for f in glob.glob(os.path.expanduser("~/neolight/logs/*.log"))}
        processes = [p.info for p in psutil.process_iter(attrs=["pid","name","cpu_percent","memory_percent"]) if any(k in " ".join(p.info.get("name","")) for k in ["uvicorn","intelligence_orchestrator","smart_trader","weights_bridge"])]
        system = {
            "cpu": psutil.cpu_percent(interval=0.3),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
            "uptime": time.ctime(),
        }
        return safe_json({"system": system, "guardian": {"logs": logs, "agents": processes}})
    except Exception as e:
        return {"error": f"Guardian status failed: {e}"}
PY

# ---- Heal Ports ----
note "Healing ports..."
for P in {8090..8110}; do
  lsof -i :$P -t | xargs -r kill -9 || true
done

# ---- Smart Runner ----
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

# ---- Launch Agents ----
ensure_running "intelligence_orchestrator" "$PY ./agents/intelligence_orchestrator.py" "$LOGS/intelligence_orchestrator.log"
ensure_running "smart_trader" "$PY ./trader/smart_trader.py" "$LOGS/smart_trader.log"
ensure_running "weights_bridge" "$PY ./agents/weights_bridge.py" "$LOGS/weights_bridge.log"

# ---- Dashboard / Status API ----
port=8100
for i in {0..10}; do
  ensure_running "dashboard_v3" "$UVICORN dashboard.status_endpoint:app --host 0.0.0.0 --port $port" "$LOGS/dashboard_v3.log"
  sleep 5
  if lsof -i :$port >/dev/null 2>&1; then
    ok "Guardian v23 active — status live at http://localhost:$port/status"
    break
  else
    warn "Port $port failed — switching..."
    port=$((port+1))
  fi
done

# ---- Continuous Self-Healing Loop ----
while true; do
  note "Assessing system health..."
  df -h > "$LOGS/system_health.log" 2>&1
  ps -eo pid,comm,%cpu,%mem | sort -k3 -r | head -n 15 >> "$LOGS/system_health.log"
  sleep 300
done
