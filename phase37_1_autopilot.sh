#!/bin/zsh
set -e

echo "🧠 Phase 37.1 :: Self-Healing Autopilot Starting…"
mkdir -p backups logs static tools
timestamp=$(date +"%Y%m%d_%H%M%S")

[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup saved" || echo "⚠️ No main.py to backup"
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api

cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import asyncio, os, requests

load_dotenv()
app = FastAPI(title="AI Money Web")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"message": "✅ AI Money Web Backend is alive"}

@app.get("/api/alpaca_status")
def alpaca_status():
    key = os.getenv("APCA_API_KEY_ID", "mock")
    secret = os.getenv("APCA_API_SECRET_KEY", "mock")
    base = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
    try:
        if key == "mock":
            return {"status": "mock", "equity": 100000, "cash": 25000}
        r = requests.get(f"{base}/v2/account", headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
        return r.json()
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.websocket("/ws/alpaca_status")
async def websocket_alpaca_status(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(alpaca_status())
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        print("🔌 Client disconnected from /ws/alpaca_status")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    path = "static/dashboard.html"
    if os.path.exists(path):
        with open(path) as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Dashboard file missing. Run Phase 36.1 setup.</h1>")
EOF

mkdir -p static
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><title>🚀 AI Money Web Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:black;color:#0ff;font-family:monospace;text-align:center;}canvas{width:90%;max-width:800px;margin:auto;}</style>
</head><body>
<h1>🚀 AI Money Web Dashboard</h1>
<div id="status">Connecting…</div><canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[{label:'Equity ($)',borderColor:'#0ff',data:[]}]},options:{scales:{x:{ticks:{color:'#0ff'}},y:{ticks:{color:'#0ff'}}}}});
const statusDiv=document.getElementById('status');
const ws=new WebSocket('ws://127.0.0.1:8000/ws/alpaca_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);statusDiv.textContent="✅ "+d.status+" | Equity: "+d.equity.toFixed(2);
  chart.data.labels.push(new Date().toLocaleTimeString());
  chart.data.datasets[0].data.push(d.equity);
  if(chart.data.labels.length>20){chart.data.labels.shift();chart.data.datasets[0].data.shift();}
  chart.update();};
</script></body></html>
EOF

mkdir -p tools
cat > tools/autopilot_watcher.py <<'EOF'
import os, time, subprocess, requests
PORT = "8000"
BASE = f"http://127.0.0.1:{PORT}"

def start():
    with open("logs/backend.log","a") as f:
        return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],stdout=f,stderr=f)

def healthy():
    try:
        requests.get(BASE+"/",timeout=2); requests.get(BASE+"/api/alpaca_status",timeout=2)
        return True
    except:
        return False

def main():
    os.makedirs("logs",exist_ok=True)
    p=start()
    while True:
        if p.poll() is not None or not healthy():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            p=start()
        time.sleep(7)

if __name__=="__main__":
    main()
EOF

kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 tools/autopilot_watcher.py > logs/watcher.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard
echo "✅ Self-Healing Autopilot Phase 37.1 complete!"

