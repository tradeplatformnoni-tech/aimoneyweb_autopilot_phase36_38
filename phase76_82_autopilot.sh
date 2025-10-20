#!/bin/zsh
set -e
echo "🧠 Phase 76–82 :: Cloud-Swarm Evolution + Consensus + Dashboard …"

mkdir -p backups logs ai/swarm static
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py backups/main.py.$ts.bak && echo "✅ Backup → backups/main.py.$ts.bak"

venv/bin/pip install -q torch boto3 numpy requests fastapi uvicorn

# --- Swarm coordinator ---
cat > ai/swarm/coord.py <<'EOF'
import json,random,requests,os,time
PEERS=["http://127.0.0.1:8000","http://127.0.0.1:8001"]
def broadcast_signal(sig):
    results=[]
    for peer in PEERS:
        try:
            r=requests.post(f"{peer}/api/swarm",json={"signal":sig},timeout=2)
            results.append(r.json().get("ack","ok"))
        except Exception as e:
            results.append(str(e))
    return results
EOF

# --- Evolution engine ---
cat > ai/swarm/evolve.py <<'EOF'
import random,torch,os
MODEL="models/deep_rl_model.pt"
def mutate_weights(path=MODEL,scale=0.05):
    if not os.path.exists(path): return False
    w=torch.load(path,map_location="cpu")
    for k in w: w[k]+=torch.randn_like(w[k])*scale
    new_path=path.replace(".pt","_mut.pt"); torch.save(w,new_path)
    return new_path
EOF

# --- Consensus voting ---
cat > ai/swarm/vote.py <<'EOF'
import numpy as np
def consensus(votes):
    arr=np.sign(votes)
    return float(np.sign(np.sum(arr)))
EOF

# --- Heartbeat monitor ---
cat > ai/swarm/heartbeat.py <<'EOF'
import time,requests
def ping(peer="http://127.0.0.1:8000"):
    try:
        r=requests.get(peer+"/api/health",timeout=2)
        return r.status_code==200
    except Exception: return False
EOF

# --- main.py patch ---
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio, random, os
from dotenv import load_dotenv; load_dotenv()
from ai.swarm.coord import broadcast_signal
from ai.swarm.evolve import mutate_weights
from ai.swarm.vote import consensus
from ai.swarm.heartbeat import ping
from ai.risk.var_calc import value_at_risk
from ai.sentiment.feed import sentiment_boost
from ai.brokers.router import account_equity_cash, submit_market

app=FastAPI(title="AI Money Web Swarm (76–82)")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

EQUITY=[]

@app.get("/")
def root(): return {"message":"✅ Swarm node active"}

@app.get("/api/health")
def health(): return {"alive":True}

@app.post("/api/swarm")
async def swarm_post(req:Request):
    data=await req.json()
    sig=data.get("signal",0)
    return {"ack":"ok","mirror":sig}

@app.websocket("/ws/swarm")
async def ws(ws:WebSocket):
    await ws.accept()
    while True:
        eq,ca=account_equity_cash()
        EQUITY.append(eq)
        pnl=(eq-100000)/100000
        var=value_at_risk([pnl])
        sent=sentiment_boost("AAPL")
        votes=[random.uniform(-1,1) for _ in range(3)]
        sig=consensus(votes)+sent
        if abs(sig)>1: sig*=0.5
        submit_market("AAPL","buy" if sig>0 else "sell",1)
        broadcast_signal(sig)
        mutate_weights()
        await ws.send_json({"eq":eq,"signal":sig,"var":var,"votes":votes})
        await asyncio.sleep(5)

@app.get("/dashboard",response_class=HTMLResponse)
def dash(): return HTMLResponse(open("static/dashboard.html").read())
EOF

# --- Dashboard ---
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>🚀 AI Money Web Swarm (76–82)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#000;color:#0ff;font-family:monospace;text-align:center}
canvas{width:90%;max-width:1100px}
</style></head><body>
<h1>🚀 AI Money Web Cloud-Swarm (76–82)</h1>
<div id="status">Connecting...</div><canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'VaR',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right'}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/swarm');
ws.onmessage=(e)=>{
  const d=JSON.parse(e.data);
  document.getElementById('status').textContent=
  `Eq:${d.eq.toFixed(2)} | Sig:${d.signal.toFixed(2)} | VaR:${d.var.toFixed(3)} | Votes:${d.votes}`;
  chart.data.labels.push(new Date().toLocaleTimeString());
  chart.data.datasets[0].data.push(d.eq);
  chart.data.datasets[1].data.push(d.signal);
  chart.data.datasets[2].data.push(d.var);
  if(chart.data.labels.length>100){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
  chart.update();
};
</script></body></html>
EOF

chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard || true
echo "🎯 Phase 76–82 complete — Swarm evolution + consensus live."

