#!/bin/zsh
set -e
echo "🧠 Phase 38 :: Adaptive Learning Autopilot Setup..."
mkdir -p backups logs static tools ai
timestamp=$(date +"%Y%m%d_%H%M%S")

# 1️⃣ Backup
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup saved" || echo "⚠️ No main.py yet"

# 2️⃣ Install packages
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api sqlite-utils numpy

# 3️⃣ RL Brain
cat > ai/ai_brain.py <<'EOF'
import sqlite3, numpy as np, os, time
DB="learning_data.db"
os.makedirs("ai",exist_ok=True)
def ensure_db():
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS trades(ts TEXT, equity REAL, pnl REAL, risk REAL)")
    con.commit();con.close()
def log_trade(equity,pnl,risk):
    con=sqlite3.connect(DB);cur=con.cursor()
    cur.execute("INSERT INTO trades VALUES(datetime('now'),?,?,?)",(equity,pnl,risk))
    con.commit();con.close()
def learn():
    con=sqlite3.connect(DB);cur=con.cursor()
    cur.execute("SELECT pnl,risk FROM trades ORDER BY ts DESC LIMIT 50")
    rows=cur.fetchall();con.close()
    if not rows:return 0
    pnl=np.array([r[0] for r in rows]);risk=np.array([r[1] for r in rows])+1e-9
    score=float(np.mean(pnl/risk))
    open("ai/policy.txt","w").write(str(score))
    return score
if __name__=="__main__":
    ensure_db()
    while True:
        s=learn()
        print(f"🧩 Learned adaptive score: {s:.4f}")
        time.sleep(10)
EOF

# 4️⃣ Update main.py
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import asyncio, os, requests, sqlite3, random
from ai.ai_brain import ensure_db, log_trade, learn

load_dotenv();ensure_db()
app=FastAPI(title="AI Money Web Autopilot")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/")
def root():return{"message":"✅ AI Money Web Backend with RL Adaptive Learning"}

@app.get("/api/alpaca_status")
def alpaca_status():
    key=os.getenv("APCA_API_KEY_ID","mock");secret=os.getenv("APCA_API_SECRET_KEY","mock")
    base=os.getenv("APCA_API_BASE_URL","https://paper-api.alpaca.markets")
    try:
        if key=="mock":
            equity=100000+random.uniform(-500,500);cash=25000+random.uniform(-100,100)
            pnl=(equity-100000)/100000;log_trade(equity,pnl,abs(pnl)+0.01)
            return{"status":"mock","equity":equity,"cash":cash,"adaptive_score":learn()}
        r=requests.get(f"{base}/v2/account",headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret})
        data=r.json();equity=float(data.get("equity",0));cash=float(data.get("cash",0))
        pnl=(equity-100000)/100000;log_trade(equity,pnl,abs(pnl)+0.01)
        data["adaptive_score"]=learn();return data
    except Exception as e:return{"status":"error","detail":str(e)}

@app.websocket("/ws/alpaca_status")
async def ws_alpaca(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(alpaca_status());await asyncio.sleep(3)
    except WebSocketDisconnect:print("🔌 Client disconnected")

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"):
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h2>Missing dashboard.html</h2>")
EOF

# 5️⃣ Dashboard HTML
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>🚀 AI Money Web Adaptive Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:black;color:#0ff;font-family:monospace;text-align:center;}canvas{width:90%;max-width:800px;margin:auto;}</style>
</head><body>
<h1>🚀 AI Money Web Dashboard (Phase 38 Adaptive)</h1>
<div id="status">Connecting…</div><canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Adaptive Score',borderColor:'#0f0',data:[],yAxisID:'y1'}]},
options:{scales:{x:{ticks:{color:'#0ff'}},y:{type:'linear',position:'left',ticks:{color:'#0ff'}},y1:{type:'linear',position:'right',ticks:{color:'#0f0'}}}}});
const statusDiv=document.getElementById('status');
const ws=new WebSocket('ws://127.0.0.1:8000/ws/alpaca_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);statusDiv.textContent="✅ "+d.status+" | Eq:"+d.equity.toFixed(2)+" | Score:"+d.adaptive_score.toFixed(4);
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.adaptive_score);
if(chart.data.labels.length>30){chart.data.labels.shift();chart.data.datasets[0].data.shift();chart.data.datasets[1].data.shift();}
chart.update();};
</script></body></html>
EOF

# 6️⃣ Relaunch backend
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard
echo "🎯 Phase 38 Adaptive Learning Autopilot complete."

