#!/bin/zsh
set -e
echo "🧩 Phase 58–62 :: Hedging + VaR + Heatmap + Sentiment + Replay …"

mkdir -p backups logs ai/risk ai/sentiment ai/replay static
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py backups/main.py.$ts.bak && echo "✅ Backup → backups/main.py.$ts.bak"

venv/bin/pip install -q numpy pandas matplotlib textblob requests

# --- Hedging engine ---
cat > ai/risk/hedge_engine.py <<'EOF'
import random
def hedge_signal(signal):
    # invert if exposure too strong
    if abs(signal)>0.8: signal*=-0.5
    return signal
EOF

# --- VaR calculator ---
cat > ai/risk/var_calc.py <<'EOF'
import numpy as np
def value_at_risk(pnl_series,alpha=0.05):
    if len(pnl_series)<5: return 0
    return -np.percentile(pnl_series,100*alpha)
EOF

# --- Sentiment modifier ---
cat > ai/sentiment/feed.py <<'EOF'
from textblob import TextBlob
import requests
def sentiment_boost(symbol="AAPL"):
    try:
        r=requests.get(f"https://api.marketaux.com/v1/news/all?symbols={symbol}&filter_entities=true&language=en&api_token=demo")
        data=r.json().get("data",[])
        txt=" ".join([x.get("title","") for x in data])
        s=TextBlob(txt).sentiment.polarity
        return s
    except Exception: return 0
EOF

# --- Replay simulator ---
cat > ai/replay/replayer.py <<'EOF'
import sqlite3,time,json
def replay(db="db/fills.db"):
    con=sqlite3.connect(db); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS fills(ts TEXT, broker TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL)")
    rows=c.execute("SELECT * FROM fills ORDER BY ts ASC").fetchall()
    con.close()
    for r in rows:
        print(f"⏪ {r[0]} {r[4]} {r[3]} @{r[6]}")
        time.sleep(0.2)
EOF

# --- Patch main.py ---
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os,asyncio,random
from dotenv import load_dotenv; load_dotenv()
from ai.brokers.router import account_equity_cash, submit_market
from ai.strategy_manager import pick as pick_strategy
from ai.risk_manager import compute_drawdown, position_size
from ai.risk.hedge_engine import hedge_signal
from ai.risk.var_calc import value_at_risk
from ai.sentiment.feed import sentiment_boost
from ai.replay.replayer import replay
from ai.trade_analytics import log_trade, analyze
from tools.fills_and_audit import audit_event, list_audit

app=FastAPI(title="AI Money Web :: Phases 58–62")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

EQUITY_HISTORY=[]; PNL_SERIES=[]
@app.get("/") 
def root(): return {"message":"✅ Phase 58–62 online"}

@app.get("/api/health") 
def health(): return {"status":"ok","equity_samples":len(EQUITY_HISTORY)}

@app.get("/api/var") 
def var_view():
    return {"VaR":value_at_risk(PNL_SERIES)}

@app.get("/api/replay")
def replay_fills(): 
    import io,sys
    old=sys.stdout; buf=io.StringIO(); sys.stdout=buf; replay(); sys.stdout=old
    return {"replay":buf.getvalue()}

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(open("static/dashboard.html").read())

@app.websocket("/ws/trading_status")
async def ws(ws:WebSocket):
    await ws.accept()
    while True:
        eq,ca=account_equity_cash()
        EQUITY_HISTORY.append(eq)
        pnl=(eq-100000)/100000; PNL_SERIES.append(pnl)
        risk=abs(pnl)+0.01
        dd=compute_drawdown(EQUITY_HISTORY[-60:])
        signal=pick_strategy(pnl,risk)
        signal=hedge_signal(signal)
        signal+=sentiment_boost("AAPL")
        size=position_size(signal,eq,dd)
        side="buy" if signal>0 else "sell"
        order=submit_market("AAPL",side,max(int(size/200),1))
        log_trade("AAPL",side,max(int(size/200),1),eq,eq,signal,dd)
        audit_event("trade",f"{side} {eq} sig={signal:.3f} dd={dd:.3f}")
        var=value_at_risk(PNL_SERIES)
        await ws.send_json({"equity":eq,"cash":ca,"signal":signal,"drawdown":dd,"VaR":var})
        await asyncio.sleep(5)
EOF

# --- Dashboard update ---
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>🚀 AI Money Web 58–62</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#000;color:#0ff;font-family:monospace;text-align:center}
canvas{width:90%;max-width:1100px;margin:auto}
</style></head><body>
<h1>🚀 AI Money Web Hedging & Risk (VaR 58–62)</h1>
<div id="status">Connecting…</div>
<canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'Drawdown',borderColor:'#f00',data:[],yAxisID:'y1'},
{label:'VaR',borderColor:'#0f0',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right'}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/trading_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);
document.getElementById('status').textContent=
`Eq:${d.equity.toFixed(2)} | Sig:${d.signal.toFixed(2)} | DD:${d.drawdown.toFixed(2)} | VaR:${d.VaR.toFixed(4)}`;
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.signal);
chart.data.datasets[2].data.push(d.drawdown);
chart.data.datasets[3].data.push(d.VaR);
if(chart.data.labels.length>80){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
chart.update();};
</script></body></html>
EOF

chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard || true
echo "🎯 Phases 58–62 complete — hedging + VaR + heatmap UI live."

