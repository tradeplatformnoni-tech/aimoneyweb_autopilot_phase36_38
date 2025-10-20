#!/bin/zsh
set -e
echo "🧩 Phase 39 + 40 :: Multi-Agent Fusion & Risk Manager Setup..."
mkdir -p backups logs static ai models tools
timestamp=$(date +"%Y%m%d_%H%M%S")

# 1️⃣ Backup existing main.py
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup saved"

# 2️⃣ Install dependencies
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api sqlite-utils numpy pandas joblib

# 3️⃣ Create AI Agents
cat > ai/agent_alpha.py <<'EOF'
import numpy as np, random
def predict_signal(pnl,risk):
    return np.tanh(pnl*10 - risk*5 + random.uniform(-0.1,0.1))
EOF

cat > ai/agent_beta.py <<'EOF'
import numpy as np, random
def predict_signal(pnl,risk):
    return np.sin(pnl*15)+random.uniform(-0.05,0.05)
EOF

cat > ai/agent_gamma.py <<'EOF'
import numpy as np, random
def predict_signal(pnl,risk):
    return (pnl/(risk+1e-6))*np.exp(-abs(pnl)*5)+random.uniform(-0.1,0.1)
EOF

# 4️⃣ Fusion Engine & Risk Manager
cat > ai/fusion_engine.py <<'EOF'
import numpy as np
from ai import agent_alpha, agent_beta, agent_gamma
def fuse_signals(pnl,risk,equity,drawdown):
    a=agent_alpha.predict_signal(pnl,risk)
    b=agent_beta.predict_signal(pnl,risk)
    c=agent_gamma.predict_signal(pnl,risk)
    weights=[0.5,0.3,0.2]
    raw=np.dot([a,b,c],weights)
    risk_adj=max(0.1,1-drawdown/10)
    return float(raw*risk_adj)
EOF

cat > ai/risk_manager.py <<'EOF'
import numpy as np
def compute_drawdown(equity_series):
    if len(equity_series)<2:return 0
    peak=max(equity_series)
    trough=equity_series[-1]
    dd=(peak-trough)/peak*100
    return dd
def position_size(signal,equity,drawdown):
    base=equity*0.01
    adj=(1-abs(signal))*max(0.2,1-drawdown/20)
    return max(base*adj,100)
EOF

# 5️⃣ main.py (integrating fusion & risk logic)
cat > main.py <<'EOF'
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import asyncio,random,os,requests
from ai.ai_brain import ensure_db,log_trade,learn
from ai.fusion_engine import fuse_signals
from ai.risk_manager import compute_drawdown,position_size

load_dotenv();ensure_db()
app=FastAPI(title="AI Money Web Fusion Engine")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
EQUITY_HISTORY=[]

@app.get("/")
def root():return{"message":"✅ AI Money Web Fusion & Risk Manager Online"}

@app.get("/api/fusion_status")
def fusion_status():
    global EQUITY_HISTORY
    equity=100000+random.uniform(-500,500)
    cash=25000+random.uniform(-100,100)
    pnl=(equity-100000)/100000
    risk=abs(pnl)+0.01
    EQUITY_HISTORY.append(equity)
    drawdown=compute_drawdown(EQUITY_HISTORY[-50:])
    fused=fuse_signals(pnl,risk,equity,drawdown)
    size=position_size(fused,equity,drawdown)
    log_trade(equity,pnl,risk)
    adaptive=learn()
    return{
      "status":"connected",
      "equity":equity,
      "cash":cash,
      "drawdown":drawdown,
      "adaptive_score":adaptive,
      "fused_signal":fused,
      "position_size":size}

@app.websocket("/ws/fusion_status")
async def ws_fusion(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(fusion_status())
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        print("🔌 Client disconnected")

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"):
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h2>Dashboard missing — re-run setup</h2>")
EOF

# 6️⃣ Dashboard HTML
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>🚀 AI Money Web Fusion + Risk Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:black;color:#0ff;font-family:monospace;text-align:center;}canvas{width:90%;max-width:800px;margin:auto;}</style>
</head><body>
<h1>🚀 AI Money Web Fusion & Risk Manager (Phases 39-40)</h1>
<div id="status">Connecting…</div>
<canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Fused Signal',borderColor:'#ff0',data:[]},
{label:'Drawdown (%)',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{x:{ticks:{color:'#0ff'}},y:{ticks:{color:'#0ff'}},y1:{position:'right',ticks:{color:'#f00'}}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/fusion_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);
document.getElementById('status').textContent=`✅ ${d.status} | Eq:${d.equity.toFixed(2)} | Drawdown:${d.drawdown.toFixed(2)}% | Signal:${d.fused_signal.toFixed(4)} | Size:${d.position_size.toFixed(2)}`;
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.fused_signal);
chart.data.datasets[2].data.push(d.drawdown);
if(chart.data.labels.length>30){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
chart.update();};
</script></body></html>
EOF

# 7️⃣ Launch Backend
chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard
echo "🎯 Phases 39 + 40 complete — Multi-Agent Fusion and Risk Manager active."

