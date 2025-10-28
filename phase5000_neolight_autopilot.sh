#!/usr/bin/env bash
# ===========================================================
# 🧠 NeoLight Autopilot (Phase 5000–6000)
# One-command: repair, rebuild, relaunch, and self-heal.
# Works in zsh or bash. Requires Docker Desktop running.
# ===========================================================

set -euo pipefail

echo ""
echo "🧠 Launching NeoLight Autopilot — Phase 5000–6000"
echo "=========================================================="

# ---------- helpers ----------
say(){ printf "%b\n" "$*"; }
have(){ command -v "$1" >/dev/null 2>&1; }

ensure_dir(){ mkdir -p "$1"; }
ensure_file(){
  local f="$1" ; local body="${2:-}"
  if [ ! -f "$f" ]; then printf "%s" "$body" > "$f"; fi
}
ensure_exec(){ chmod +x "$1" 2>/dev/null || true; }

# ---------- preflight ----------
if ! have docker; then
  say "⚠️  Docker CLI not found. Install Docker Desktop first."; exit 1
fi
if ! docker info >/dev/null 2>&1; then
  say "⚠️  Docker is not running. Please start Docker Desktop and re-run."; exit 1
fi

# ---------- structure ----------
say "📁 Ensuring project structure..."
ensure_dir ai
ensure_dir agents
ensure_dir dashboard
ensure_dir logs
ensure_dir runtime
ensure_dir config
ensure_dir k8s

ensure_file runtime/portfolio.json '{}'
ensure_file runtime/goal_config.json '{}'
ensure_file logs/system_health.log ""

# ---------- critical files (create if missing) ----------
say "🧩 Ensuring dashboard files..."
ensure_file dashboard/__init__.py ""
ensure_file dashboard/jinja_sanitizer.py \
'import html
def sanitize_template(x):
    return x if not isinstance(x, str) else html.escape(x)
'
# Minimal port helper (only used when running locally)
ensure_file dashboard/flask_port_handler.py \
'import socket, os
def get_available_port(default=5050):
    p = os.environ.get("PORT")
    if p:
        try: return int(p)
        except: pass
    s = socket.socket()
    try:
        s.bind(("", default)); s.close(); return default
    except:
        s.close()
    s = socket.socket(); s.bind(("",0)); port=s.getsockname()[1]; s.close(); return port
'

# Robust Flask app (safe even if your fuller version already exists)
if [ ! -f dashboard/flask_app.py ]; then
cat > dashboard/flask_app.py <<'PY'
# 🧠 NeoLight Dashboard (Phase 5000 minimal-safe)
from flask import Flask, jsonify, render_template_string
import json, pathlib, os, time, requests

app = Flask(__name__)

def load_json_safe(p):
    pth = pathlib.Path(p)
    if not pth.exists(): return {}
    try: return json.loads(pth.read_text())
    except Exception as e: return {"error": str(e)}

@app.route("/health")
def health(): return jsonify({"status":"ok","ts":time.time()})

def prices():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids":"bitcoin,ethereum,gold","vs_currencies":"usd"}, timeout=6)
        d = r.json()
        return {"BTC": d.get("bitcoin",{}).get("usd"),
                "ETH": d.get("ethereum",{}).get("usd"),
                "GOLD": d.get("gold",{}).get("usd"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def index():
    html = """
    <html><head><meta http-equiv="refresh" content="15">
    <title>NeoLight Wealth Mesh Dashboard</title>
    <style>
    body{background:#0a0f14;color:#e8e8e8;font-family:monospace}
    h1{color:#00ff9d} h2{color:#00ffff}
    .card{margin:12px 0;padding:10px;border:1px solid #222;border-radius:8px}
    pre{white-space:pre-wrap;word-break:break-word;color:#b2f7ff}
    </style></head><body>
    <h1>🧠 NeoLight Wealth Mesh Dashboard</h1>
    <div class="card"><h2>🪙 Live BTC/ETH/GOLD</h2><pre>{{ prices }}</pre></div>
    <div class="card"><h2>💰 Portfolio</h2><pre>{{ portfolio }}</pre></div>
    <div class="card"><h2>📊 Telemetry</h2><pre>{{ telemetry }}</pre></div>
    <div class="card"><h2>🛡️ Risk Policy</h2><pre>{{ risk }}</pre></div>
    <footer><small>Auto-refresh 15s • {{ now }}</small></footer>
    </body></html>
    """
    return render_template_string(html,
        prices=json.dumps(prices(), indent=2),
        portfolio=json.dumps(load_json_safe("runtime/portfolio.json"), indent=2),
        telemetry=json.dumps(load_json_safe("logs/telemetry_push.json"), indent=2),
        risk=json.dumps(load_json_safe("config/risk_policy.json"), indent=2),
        now=time.strftime("%Y-%m-%d %H:%M:%S")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT","5050") or 5050)
    print(f"🌍 Dashboard live on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port)
PY
fi

say "🧠 Ensuring agent core..."
if [ ! -f ai/agent_core.py ]; then
cat > ai/agent_core.py <<'PY'
# 🧠 NeoLight Agent Core — persistent heartbeat
import time, datetime, sys
print("🧠 NeoLight Agent Core initializing..."); sys.stdout.flush()
try:
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] ✅ Core AI Engine heartbeat — system stable."); sys.stdout.flush()
        time.sleep(20)
except KeyboardInterrupt:
    print("🧠 Agent Core shutting down gracefully."); sys.stdout.flush()
PY
fi

# ---------- Dockerfiles (dashboard, observer, autopatch, agent_core) ----------
say "🐳 Ensuring Dockerfiles..."
cat > dashboard/Dockerfile <<'DOCK'
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask gunicorn requests plotly pandas numpy pyyaml
ENV PYTHONPATH=/app
EXPOSE 5050
CMD ["gunicorn","-w","2","-b","0.0.0.0:5050","flask_app:app"]
DOCK

cat > observer.Dockerfile <<'DOCK'
FROM python:3.12-slim
WORKDIR /app
COPY ai/observer/autoheal_observer.py /app/autoheal_observer.py
RUN pip install --no-cache-dir requests docker
CMD ["python","autoheal_observer.py"]
DOCK

# Ensure observer script exists
ensure_dir ai/observer
if [ ! -f ai/observer/autoheal_observer.py ]; then
cat > ai/observer/autoheal_observer.py <<'PY'
import os, time, json, subprocess, requests, datetime
LOG_PATH = "logs/autopilot_observer.jsonl"
PUSH_URL = "https://api.pushover.net/1/messages.json"
PUSH_USER = os.getenv("PUSHOVER_USER"); PUSH_TOKEN = os.getenv("PUSHOVER_TOKEN")
def push(msg):
    if not (PUSH_USER and PUSH_TOKEN): return
    requests.post(PUSH_URL, data={"token":PUSH_TOKEN,"user":PUSH_USER,"title":"NeoLight Observer","message":msg})
def loop():
    print("🛡️ Observer active — monitoring containers...")
    while True:
        now = datetime.datetime.now().isoformat()
        out = subprocess.getoutput("docker ps --format '{{.Names}} {{.Status}}'")
        status = {ln.split()[0]:" ".join(ln.split()[1:]) for ln in out.splitlines() if ln.strip()}
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH,"a") as f: f.write(json.dumps({"timestamp":now,"status":status})+"\n")
        for name, st in status.items():
            if "Exited" in st or "Restarting" in st:
                push(f"{name} => {st}")
                subprocess.run(["docker","restart",name])
        time.sleep(60)
if __name__=="__main__": loop()
PY
fi

# Autopatch: simple placeholder uses observer base (safe default)
cat > autopatch_controller.py <<'DOCK'
FROM python:3.12-slim
WORKDIR /app
COPY ai/observer/autoheal_observer.py /app/autoheal_observer.py
RUN pip install --no-cache-dir requests docker pyyaml kubernetes
CMD ["python","autoheal_observer.py"]
DOCK

# Agent core Dockerfile (builds from local source)
ensure_dir agents/core
cat > agents/Dockerfile <<'DOCK'
FROM python:3.12-slim
WORKDIR /app
COPY ai/agent_core.py /app/agent_core.py
RUN pip install --no-cache-dir requests
CMD ["python","agent_core.py"]
DOCK

# ---------- docker-compose ----------
say "🧾 Ensuring docker-compose.yml..."
cat > docker-compose.yml <<'YAML'
services:
  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    container_name: neolight_dashboard
    ports: ["5050:5050"]
    restart: always
    healthcheck:
      test: ["CMD-SHELL","curl -sf http://127.0.0.1:5050/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./runtime:/app/runtime
      - ./logs:/app/logs
      - ./config:/app/config

  autopatch:
    build:
      context: .
      dockerfile: autopatch_controller.py
    container_name: neolight_autopatch
    restart: always
    environment:
      - PUSHOVER_TOKEN=${PUSHOVER_TOKEN}
      - PUSHOVER_USER=${PUSHOVER_USER}
    volumes:
      - ./logs:/app/logs
      - ./runtime:/app/runtime

  observer:
    build:
      context: .
      dockerfile: observer.Dockerfile
    container_name: neolight_observer
    restart: always
    environment:
      - PUSHOVER_TOKEN=${PUSHOVER_TOKEN}
      - PUSHOVER_USER=${PUSHOVER_USER}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./logs:/app/logs

  agent_core:
    image: neolight/agent-core:latest
    build:
      context: .
      dockerfile: agents/Dockerfile
    container_name: aimoneyweb_autopilot_phase36_38-agent_core-1
    restart: always

networks:
  default:
    name: neolight_mesh
YAML

# ---------- permissions ----------
say "🔧 Fixing permissions..."
ensure_exec *.sh
chmod -R 755 dashboard agents ai || true

# ---------- rebuild & launch ----------
say "🏗️ Rebuilding containers..."
docker compose down --remove-orphans >/dev/null 2>&1 || true
docker compose build --no-cache

say "🚀 Starting stack..."
docker compose up -d

# ---------- watchdog (NeoLight-Fix) ----------
say "🩺 Launching NeoLight-Fix watchdog..."
cat > neo_lightfix_watchdog.sh <<'SH'
#!/usr/bin/env bash
while true; do
  docker ps --format '{{.Names}} {{.Status}}' | while read -r name status_rest; do
    # If not "Up", attempt restart
    if echo "$status_rest" | grep -vq "^Up"; then
      echo "⚠️  $name unhealthy: $status_rest -> restarting"
      docker restart "$name" >/dev/null 2>&1
    fi
  done
  sleep 20
done
SH
ensure_exec neo_lightfix_watchdog.sh
# run in background if not already
pgrep -f neo_lightfix_watchdog.sh >/dev/null 2>&1 || nohup ./neo_lightfix_watchdog.sh >/dev/null 2>&1 &

# ---------- summary ----------
echo ""
say "✅ NeoLight Autopilot complete."
say "🌐 Dashboard: http://127.0.0.1:5050"
say "🪪 Tip: add PUSHOVER_TOKEN and PUSHOVER_USER in .env to receive alerts."
say "🧰 Logs: docker compose logs -f"
say "=========================================================="

