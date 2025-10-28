#!/usr/bin/env bash
# ==========================================================
# NeoLight :: Phase 681–700+  — Cloud AI Agent + AutoFix
# Local runner + Docker + PM2 + K8s/Fly.io templates
# ==========================================================
set -e

echo "🌩️  NeoLight :: Cloud AI Agent (Phase 681–700+)"

# ---------- Prep ----------
mkdir -p backend tools templates static runtime logs k8s
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install --quiet fastapi uvicorn requests pandas numpy psutil python-multipart

# Always ensure PYTHONPATH works
echo 'export PYTHONPATH=$(pwd)' > .venv/bin/activate_pathfix
chmod +x .venv/bin/activate_pathfix
source .venv/bin/activate_pathfix

# ---------- Runtime seeds ----------
[ -f runtime/notify_config.json ] || echo '{"discord_webhook": null, "telegram_token": null, "telegram_chat": null}' > runtime/notify_config.json
[ -f runtime/agent_state.json ]   || echo '{"last_ts": null}' > runtime/agent_state.json
touch runtime/agent_log.jsonl runtime/signals.jsonl

# ---------- Backend notify helper (idempotent) ----------
cat > backend/notify.py <<'PY'
import json, os, requests
CONFIG_FILE = "runtime/notify_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: return json.load(f)
    return {"discord_webhook": None, "telegram_token": None, "telegram_chat": None}

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2)

def send_discord(msg, url):
    if not url: return {"status":"no webhook"}
    try:
        r = requests.post(url, json={"content": msg}, timeout=8)
        return {"status":"ok","code":r.status_code}
    except Exception as e:
        return {"status":"error","error":str(e)}

def send_telegram(msg, token, chat):
    if not token or not chat: return {"status":"no token/chat"}
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, data={"chat_id": chat, "text": msg}, timeout=8)
        return {"status":"ok","code":r.status_code}
    except Exception as e:
        return {"status":"error","error":str(e)}

def notify_all(message):
    cfg = load_config()
    return {
        "discord":  send_discord(message, cfg.get("discord_webhook")),
        "telegram": send_telegram(message, cfg.get("telegram_token"), cfg.get("telegram_chat"))
    }
PY

# ---------- AI Agent (supervisor/orchestrator) ----------
cat > tools/agent_loop.py <<'PY'
import os, json, time, datetime, requests, psutil, subprocess, traceback
from pathlib import Path

BASE = "http://127.0.0.1:8000"
RUNTIME = Path("runtime")
SIGNALS = RUNTIME/"signals.jsonl"
AGENT_STATE = RUNTIME/"agent_state.json"
AGENT_LOG = RUNTIME/"agent_log.jsonl"
NOTIFY_CFG = RUNTIME/"notify_config.json"

def jread(p, d): 
    try: return json.load(open(p,"r"))
    except: return d
def jwrite(p, o): json.dump(o, open(p,"w"), indent=2)
def append_log(entry): open(AGENT_LOG,"a").write(json.dumps(entry)+"\n")

def health_ok():
    try:
        r = requests.get(BASE+"/api/health", timeout=5)
        return r.ok
    except Exception:
        return False

def notify(message):
    try:
        # Use backend notify endpoint if available
        r = requests.post(BASE+"/api/notify/test", json={"message": message}, timeout=8)
        if r.ok: return True
    except Exception: pass
    # Offline fallback: print to stdout
    print("[ALERT]", message)
    append_log({"ts":datetime.datetime.utcnow().isoformat(),"type":"notify_fallback","message":message})
    return False

def ensure_services():
    # Ensure FastAPI exists
    backend_up = any("uvicorn" in p.name() for p in psutil.process_iter(attrs=["name"]))
    if not backend_up:
        notify("⚠️ Backend down. Attempting AutoFix…")
        try:
            subprocess.call(["neolight-fix"])
        except Exception:
            # fallback local bring-up
            subprocess.Popen(["nohup","uvicorn","backend.main:app","--host","0.0.0.0","--port","8000","--reload"])
        time.sleep(3)
    # Ensure strategy daemon exists
    daemon_up = any("strategy_daemon.py" in " ".join(p.cmdline()) for p in psutil.process_iter(attrs=["cmdline"]))
    if not daemon_up:
        notify("⚠️ Strategy daemon down. Restarting…")
        subprocess.Popen(["nohup","python","tools/strategy_daemon.py"])

def read_new_signals():
    state = jread(AGENT_STATE, {"last_ts": None})
    last_ts = state.get("last_ts")
    new = []
    if not SIGNALS.exists(): 
        return new
    with open(SIGNALS,"r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if (last_ts is None) or (ts and ts > last_ts):
                    new.append(obj)
            except: pass
    if new:
        state["last_ts"] = new[-1].get("timestamp")
        jwrite(AGENT_STATE, state)
    return new

def summarize(signals):
    # Simple per-interval ensemble summary
    votes = {"BUY":0,"SELL":0,"HOLD":0}
    for s in signals: votes[s.get("signal","HOLD")] = votes.get(s.get("signal","HOLD"),0)+1
    if votes["BUY"]>=2: final="BUY"
    elif votes["SELL"]>=2: final="SELL"
    else: final="HOLD"
    return final, votes

def main_loop():
    print("🌩️  Cloud AI Agent running…")
    while True:
        try:
            ensure_services()
            ok = health_ok()
            if not ok: 
                notify("❌ Backend health failed after AutoFix attempt.")
                time.sleep(5); 
                continue

            news = read_new_signals()
            if news:
                final, votes = summarize(news)
                price = news[-1].get("price")
                msg = f"🧠 NeoLight signal update: {final} @ {price} | votes={votes}"
                notify(msg)
                append_log({"ts":datetime.datetime.utcnow().isoformat(),"type":"signal_summary","final":final,"votes":votes,"price":price})
        except Exception as e:
            append_log({"ts":datetime.datetime.utcnow().isoformat(),"type":"agent_error","err":str(e)})
            traceback.print_exc()
        time.sleep(10)

if __name__=="__main__":
    main_loop()
PY
chmod +x tools/agent_loop.py

# ---------- Helper scripts ----------
cat > restart_all.sh <<'SH'
#!/usr/bin/env bash
set -e
echo "♻️  Restarting NeoLight backend + daemon + agent"
pkill -f "uvicorn backend.main:app" || true
pkill -f "tools/strategy_daemon.py" || true
pkill -f "tools/agent_loop.py" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/strategy_daemon.py  >> logs/daemon.log  2>&1 &
nohup python tools/agent_loop.py       >> logs/agent.log   2>&1 &
sleep 2
echo "✅ Done. Health:"; curl -s http://127.0.0.1:8000/api/health || true; echo
SH
chmod +x restart_all.sh

# ---------- Requirements (for Docker) ----------
cat > requirements.txt <<'REQ'
fastapi
uvicorn
requests
pandas
numpy
psutil
python-multipart
REQ

# ---------- Dockerfile (app + agent in one container, using PM2 runtime) ----------
cat > Dockerfile <<'DOCK'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pm2 psutil
COPY . .
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# PM2 will run both backend and agent
CMD ["pm2-runtime", "ecosystem.config.cjs"]
DOCK

# ---------- PM2 ecosystem (runs backend + agent) ----------
cat > ecosystem.config.cjs <<'PM2'
module.exports = {
  apps: [
    {
      name: "neolight-backend",
      script: "uvicorn",
      args: "backend.main:app --host 0.0.0.0 --port 8000",
      autorestart: true,
      max_restarts: 50
    },
    {
      name: "neolight-agent",
      script: "python",
      args: "tools/agent_loop.py",
      autorestart: true,
      max_restarts: 50
    }
  ]
}
PM2

# ---------- docker-compose (local) ----------
cat > docker-compose.yml <<'YML'
version: "3.8"
services:
  neolight:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./:/app
    restart: unless-stopped
YML

# ---------- K8s template (single pod, dev) ----------
cat > k8s/neolight-deploy.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neolight
spec:
  replicas: 1
  selector:
    matchLabels: { app: neolight }
  template:
    metadata:
      labels: { app: neolight }
    spec:
      containers:
        - name: neolight
          image: neolight:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
          env:
            - name: PYTHONPATH
              value: /app
          command: ["pm2-runtime","ecosystem.config.cjs"]
---
apiVersion: v1
kind: Service
metadata:
  name: neolight-svc
spec:
  selector: { app: neolight }
  ports:
    - port: 80
      targetPort: 8000
      protocol: TCP
      name: http
  type: ClusterIP
YAML

# ---------- Fly.io sample (manual deploy later) ----------
cat > fly.toml <<'FLY'
app = "neolight-app"
primary_region = "ord"
[build]
  dockerfile = "Dockerfile"
[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
FLY

# ---------- Make sure perms are right on all scripts ----------
find . -type f -name "*.sh" -exec chmod +x {} \;

# ---------- Bring everything up locally ----------
echo "🚀 Starting backend + daemon + agent"
pkill -f "uvicorn backend.main:app" || true
pkill -f "tools/strategy_daemon.py" || true
pkill -f "tools/agent_loop.py" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/strategy_daemon.py  >> logs/daemon.log  2>&1 &
nohup python tools/agent_loop.py       >> logs/agent.log   2>&1 &

# ---------- Final output ----------
sleep 2
echo "✅ Phase 681–700+ complete."
echo "   Health: $(curl -s http://127.0.0.1:8000/api/health || echo 'unavailable')"
echo "👉 Dashboard: http://localhost:8000/dashboard"
echo "👉 Agent log: tail -f logs/agent.log"
echo "👉 Docker (optional): docker compose up --build"
echo "👉 K8s (optional): kubectl apply -f k8s/neolight-deploy.yaml"

