# 🧠 Phase 91–100 :: Global Autopilot Fusion
echo "🚀 Starting Phase 91–100 Autopilot Fusion Setup..."

# 1️⃣  Backup + prepare
timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools ai
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ main.py backed up → backups/main.py.$timestamp.bak"

# 2️⃣  Ensure dependencies
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api schedule

# 3️⃣  Rebuild main.py
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import asyncio, os, json, datetime, random

app = FastAPI(title="AI Money Web Global Autopilot Fusion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "✅ Global Autopilot Fusion active",
        "phase": "91–100",
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return FileResponse("static/dashboard.html")

@app.websocket("/ws/fusion")
async def fusion_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            payload = {
                "status": "ok",
                "equity": round(100000 + random.uniform(-500, 500), 2),
                "pnl": round(random.uniform(-200, 200), 2),
                "signal": random.choice(["BUY", "SELL", "HOLD"]),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            await ws.send_json(payload)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        print("🔌 WebSocket client disconnected")
EOF

# 4️⃣  Create dashboard HTML
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Money Web Fusion Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
 body {background:#0e1117;color:#fff;font-family:Arial;text-align:center;}
 canvas {max-width:600px;margin-top:20px;}
</style>
</head>
<body>
<h1>🌎 AI Money Web Fusion Dashboard</h1>
<p>Status: <span id="status">Connecting...</span></p>
<p>Signal: <span id="signal">—</span></p>
<canvas id="equityChart"></canvas>
<script>
const ws=new WebSocket("ws://127.0.0.1:8000/ws/fusion");
const ctx=document.getElementById("equityChart").getContext("2d");
let data={labels:[],datasets:[{label:"Equity",data:[],borderColor:"lime",fill:false}]};
const chart=new Chart(ctx,{type:"line",data});
ws.onmessage=e=>{
 const j=JSON.parse(e.data);
 document.getElementById("status").innerText=j.status;
 document.getElementById("signal").innerText=j.signal;
 data.labels.push(j.timestamp.split("T")[1].split(".")[0]);
 data.datasets[0].data.push(j.equity);
 if(data.labels.length>30){data.labels.shift();data.datasets[0].data.shift();}
 chart.update();
};
</script>
</body>
</html>
EOF

# 5️⃣  Create self-healing watcher
cat > tools/fusion_watcher.py <<'EOF'
import subprocess, time, requests, os

PORT="8000"
BASE=f"http://127.0.0.1:{PORT}"
def start():
    return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],
                             stdout=open("logs/backend.log","a"),stderr=subprocess.STDOUT)

def healthy():
    try:
        r=requests.get(BASE,timeout=2)
        return r.status_code==200
    except Exception: return False

def loop():
    p=start()
    while True:
        if p.poll() is not None or not healthy():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            p=start()
        time.sleep(7)

if __name__=="__main__":
    loop()
EOF

# 6️⃣  Launch everything
echo "🔪 Freeing port :8000..."; kill -9 $(lsof -t -i:8000) 2>/dev/null || true
echo "🚀 Starting backend and watcher..."
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 tools/fusion_watcher.py > logs/watcher.log 2>&1 &

sleep 5
if curl -s http://127.0.0.1:8000/ | grep -q "Global"; then
  echo "✅ Backend alive. Opening dashboard..."
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend did not respond. Check logs/backend.log."
fi

echo "🎯 Phase 91–100 Fusion setup complete."
echo "💾 Logs → ./logs/backend.log and ./logs/watcher.log"
echo "💡 If you see 'permission denied' later: chmod +x *.sh tools/*.py ai/*.py"

