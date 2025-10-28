#!/bin/bash
echo "🚀 Phase 2401–3000: NeoLight Unified Core Console + Self-Healing Framework"
echo "--------------------------------------------------------------------------"

# 1️⃣ Ensure directories exist
mkdir -p ai api/core ui/static ui/templates tools logs config

# 2️⃣ Create the Core Console Dashboard (FastAPI Template)
cat > api/core/routes.py <<'EOF'
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import json, os

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    status = {
        "agents": [],
        "optimizer": {},
        "brain": {},
        "market": {},
    }
    if os.path.exists("config/agents.json"):
        status["agents"] = json.load(open("config/agents.json"))
    if os.path.exists("config/optimizer.json"):
        status["optimizer"] = json.load(open("config/optimizer.json"))
    if os.path.exists("config/brain.json"):
        status["brain"] = json.load(open("config/brain.json"))
    if os.path.exists("config/marketplace.json"):
        status["market"] = json.load(open("config/marketplace.json"))

    html = f"""
    <html>
      <head><title>NeoLight Core Console</title></head>
      <body style='font-family: Arial;'>
        <h1>🧠 NeoLight Core Console</h1>
        <h3>System Overview</h3>
        <pre>{json.dumps(status, indent=2)}</pre>
        <h3>Quick Actions</h3>
        <ul>
          <li><a href="/api/brain/download">Download Brain JSON</a></li>
          <li><a href="/api/nlp/query">NLP Query</a></li>
          <li><a href="/api/marketplace/list">Marketplace List</a></li>
          <li><a href="/api/collab/record">Collaboration Log</a></li>
        </ul>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
EOF
echo "🧩 Core Console route added (api/core/routes.py)."

# 3️⃣ AI Orchestration Daemon
cat > tools/orchestrator.py <<'EOF'
"""
tools/orchestrator.py
Coordinates all active agents, checks health, and triggers repairs.
"""
import subprocess, time, os, json

AGENTS = json.load(open("config/agents.json")) if os.path.exists("config/agents.json") else []
LOG = "logs/orchestrator.log"

def check_services():
    services = ["uvicorn", "strategy_daemon", "telemetry_daemon"]
    running = []
    for s in services:
        if os.system(f"pgrep -f {s} > /dev/null") == 0:
            running.append(s)
    return running

def auto_fix():
    if not os.path.exists("./neolight-fix"):
        return
    os.system("./neolight-fix")

if __name__ == "__main__":
    while True:
        running = check_services()
        msg = f"[Orchestrator] Running: {running}"
        print(msg)
        open(LOG, "a").write(msg + "\n")
        if len(running) < 3:
            print("⚠️ Missing service detected, running AutoFix...")
            auto_fix()
        time.sleep(300)
EOF
echo "🧠 Orchestrator daemon ready."

# 4️⃣ Core Auto-Recovery (AI Self-Heal)
cat > tools/self_heal.py <<'EOF'
"""
tools/self_heal.py
Watches logs for anomalies and triggers corrective scripts.
"""
import time, os

LOG = "logs/backend.log"

def detect_issue():
    if not os.path.exists(LOG):
        return False
    with open(LOG) as f:
        lines = f.readlines()[-10:]
    return any("Traceback" in l or "ERROR" in l for l in lines)

if __name__ == "__main__":
    while True:
        if detect_issue():
            print("⚠️ Issue detected! Running AutoFix...")
            os.system("./neolight-fix")
        time.sleep(120)
EOF
echo "🧬 Self-Heal module ready."

# 5️⃣ Hook Core Console routes into backend
MAIN="backend/main.py"
if ! grep -q "api.core" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.core import routes as core_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(core_routes.router)' "$MAIN"
  echo "🔗 Core Console route registered in backend."
fi

# 6️⃣ Restart FastAPI
pkill -f uvicorn 2>/dev/null
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted and Core Console active."

# 7️⃣ Launch background monitors
nohup python3 tools/orchestrator.py > logs/orchestrator.log 2>&1 &
nohup python3 tools/self_heal.py > logs/selfheal.log 2>&1 &
echo "🧩 Orchestrator + Self-Heal monitors running."

# 8️⃣ Optional alert
[ -f tools/alert_notify.py ] && python3 tools/alert_notify.py "🧠 Phase 2401–3000 active | Core Console + Self-Heal running"

echo "✅ Autopilot complete for Phase 2401–3000."

