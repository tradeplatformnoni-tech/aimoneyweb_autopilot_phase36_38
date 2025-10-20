#!/bin/zsh
set -e
echo "🤖 Phase 69–75 :: Multi-Agent, Risk Sentinel, Arbitration, Cloud Sync …"

mkdir -p backups logs ai/agents ai/sync ai/recovery static
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py backups/main.py.$ts.bak && echo "✅ Backup -> backups/main.py.$ts.bak"

venv/bin/pip install -q boto3 torch numpy pandas matplotlib joblib requests

# --- Multi-Agent Coordinator ---
cat > ai/agents/coordinator.py <<'EOF'
import random, numpy as np
def agent_votes(pnl,dd,var,sentiment):
    strat_vote = np.sign(pnl - dd)
    risk_vote  = -1 if var>0.02 else 1
    sent_vote  = 1 if sentiment>0 else -1
    votes = [strat_vote, risk_vote, sent_vote]
    decision = np.sign(sum(votes))
    return float(decision), votes
EOF

# --- Risk Sentinel ---
cat > ai/agents/sentinel.py <<'EOF'
import random, time
def guard(signal, var, dd):
    if abs(signal)>1.2 or var>0.03 or dd>0.05:
        print("⚠️ Sentinel blocked over-risky signal.")
        return 0.0
    return signal
EOF

# --- Trade Arbitration ---
cat > ai/agents/arbitrator.py <<'EOF'
def arbitrate(votes, fallback=0):
    if sum(votes)>1: return 1
    elif sum(votes)<-1: return -1
    else: return fallback
EOF

# --- Cloud Sync ---
cat > ai/sync/cloudsync.py <<'EOF'
import boto3, os, json, time
from dotenv import load_dotenv; load_dotenv()
BUCKET=os.getenv("AWS_BUCKET","aimoneyweb-sync")
REGION=os.getenv("AWS_REGION","us-east-1")

def push_state(state:dict):
    try:
        s3=boto3.client("s3",region_name=REGION)
        key=f"state_{time.strftime('%Y%m%d_%H%M%S')}.json"
        s3.put_object(Body=json.dumps(state),Bucket=BUCKET,Key=key)
        print(f"☁️ Cloud sync → s3://{BUCKET}/{key}")
    except Exception as e: print("⚠️ Cloud sync failed:",e)
EOF

# --- Recovery Watchdog ---
cat > ai/recovery/watchdog.py <<'EOF'
import subprocess,time,os
def ensure_process(cmd:str, name="subsystem"):
    while True:
        proc=subprocess.Popen(cmd,shell=True)
        proc.wait()
        print(f"🔁 {name} crashed — restarting in 5s")
        time.sleep(5)
EOF

# --- PnL Forecast ---
cat > ai/agents/forecast.py <<'EOF'
import numpy as np
def forecast_pnl(equity_series):
    if len(equity_series)<5: return 0
    x=np.arange(len(equity_series)); y=np.array(equity_series)
    slope=np.polyfit(x,y,1)[0]
    return float(slope/1000)
EOF

# --- main.py patch ---
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os,asyncio,random
from dotenv import load_dotenv; load_dotenv()
from ai.brokers.router import account_equity_cash, submit_market
from ai.strategy_manager import pick as pick_strategy
from ai.risk.var_calc import value_at_risk
from ai.sentiment.feed import sentiment_boost
from ai.agents.coordinator import agent_votes
from ai.agents.sentinel import guard
from ai.agents.arbitrator import arbitrate
from ai.agents.forecast import forecast_pnl
from ai.sync.cloudsync import push_state

app=FastAPI(title="AI Money Web Autonomy (Phases 69–75)")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

EQUITY_HISTORY=[]

@app.get("/")
def root(): return {"message":"✅ AI Autonomy Engine Online (69–75)"}

@app.get("/api/status")
def status():
    return {"samples":len(EQUITY_HISTORY)}

@app.websocket("/ws/autopilot")
async def ws(ws:WebSocket):
    await ws.accept()
    while True:
        eq,ca=account_equity_cash()
        EQUITY_HISTORY.append(eq)
        pnl=(eq-100000)/100000
        dd=abs(pnl)*random.uniform(0.5,1.2)
        var=value_at_risk([pnl])
        sent=sentiment_boost("AAPL")

        decision,votes=agent_votes(pnl,dd,var,sent)
        arb=arbitrate(votes, fallback=random.choice([-1,1]))
        total_signal=guard(decision+arb, var, dd)
        forecast=forecast_pnl(EQUITY_HISTORY[-60:])
        side="buy" if total_signal>0 else "sell"
        submit_market("AAPL", side, 1)
        push_state({"eq":eq,"var":var,"sent":sent,"signal":total_signal,"forecast":forecast})
        await ws.send_json({
            "eq":eq,"signal":total_signal,"var":var,"dd":dd,
            "sent":sent,"forecast":forecast,"votes":votes
        })
        await asyncio.sleep(5)

@app.get("/dashboard",response_class=HTMLResponse)
def dash():
    return HTMLResponse(open("static/dashboard.html").read())
EOF

# --- Dashboard ---
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>🚀 AI Money Web Autonomy (69–75)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#000;color:#0ff;font-family:monospace;text-align:center}
canvas{width:90%;max-width:1100px}
</style></head><body>
<h1>🚀 AI Money Web Autonomy Dashboard (69–75)</h1>
<div id="status">Connecting...</div><canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'Forecast',borderColor:'#0f0',data:[]},
{label:'VaR',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right'}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/autopilot');
ws.onmessage=(e)=>{
  const d=JSON.parse(e.data);
  document.getElementById('status').textContent=
  `Eq:${d.eq.toFixed(2)} | Sig:${d.signal.toFixed(2)} | VaR:${d.var.toFixed(3)} | Fcast:${d.forecast.toFixed(4)} | Votes:${d.votes}`;
  chart.data.labels.push(new Date().toLocaleTimeString());
  chart.data.datasets[0].data.push(d.eq);
  chart.data.datasets[1].data.push(d.signal);
  chart.data.datasets[2].data.push(d.forecast);
  chart.data.datasets[3].data.push(d.var);
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
echo "🎯 Phases 69–75 complete — multi-agent fusion & risk sentinel live."

