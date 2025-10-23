#!/bin/bash
echo "🚀 Phase 1801–1900 : Inter-Agent Protocol + Telemetry + AI Firewall"
echo "-----------------------------------------------------------------"

# 1️⃣ Directories
mkdir -p api/mesh ai tools logs/performance config

# 2️⃣ Inter-Agent Protocol
cat > api/mesh/routes.py <<'EOF'
from fastapi import APIRouter, Request
import json, os, time

router = APIRouter()
MAILBOX = "logs/mesh_inbox.json"

def _load():
    return json.load(open(MAILBOX)) if os.path.exists(MAILBOX) else []

def _save(data):
    json.dump(data, open(MAILBOX,"w"), indent=2)

@router.post("/api/mesh/send")
async def send_message(req: Request):
    msg = await req.json()
    data = _load()
    msg["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    data.append(msg)
    _save(data)
    return {"status":"sent","count":len(data)}

@router.get("/api/mesh/inbox")
def inbox():
    return _load()
EOF
echo "🧩 Inter-Agent API created (api/mesh/routes.py)."

# 3️⃣ Telemetry Daemon
cat > tools/telemetry_daemon.py <<'EOF'
import os, psutil, time, json, datetime
LOG = "logs/performance/telemetry.csv"
os.makedirs(os.path.dirname(LOG), exist_ok=True)

header = "timestamp,cpu_percent,mem_percent\n"
if not os.path.exists(LOG):
    open(LOG,"w").write(header)

while True:
    cpu, mem = psutil.cpu_percent(), psutil.virtual_memory().percent
    line = f"{datetime.datetime.now()},{cpu},{mem}\n"
    open(LOG,"a").write(line)
    time.sleep(60)
EOF
echo "📊 Telemetry Daemon added (tools/telemetry_daemon.py)."

# 4️⃣ AI Firewall
cat > ai/firewall.py <<'EOF'
import json, os
RULES = {"max_drawdown":0.3, "min_sharpe":1.0}
LOG = "logs/firewall_log.json"

def validate(strategy):
    ok = strategy.get("drawdown",0)<=RULES["max_drawdown"] \
         and strategy.get("sharpe",0)>=RULES["min_sharpe"]
    rec = {"strategy":strategy,"valid":ok}
    data=[]
    if os.path.exists(LOG): data=json.load(open(LOG))
    data.append(rec)
    json.dump(data, open(LOG,"w"), indent=2)
    return ok
EOF
echo "🛡️ AI Firewall module ready (ai/firewall.py)."

# 5️⃣ Hook routes into backend
MAIN="backend/main.py"
if ! grep -q "api.mesh" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.mesh import routes as mesh_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(mesh_routes.router)' "$MAIN"
  echo "🔗 Inter-Agent route wired into backend."
fi

# 6️⃣ Restart FastAPI
pkill -f uvicorn 2>/dev/null
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted."

# 7️⃣ Start Telemetry in background
nohup python3 tools/telemetry_daemon.py > logs/telemetry.log 2>&1 &
echo "📡 Telemetry Daemon running → logs/telemetry.log"

# 8️⃣ Mobile alert (optional)
[ -f tools/alert_notify.py ] && python3 tools/alert_notify.py "🧠 Phase 1801–1900 complete | Mesh+Telemetry+Firewall active"

echo "✅ Autopilot successfully installed for Phase 1801–1900."

