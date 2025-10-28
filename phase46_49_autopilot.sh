#!/bin/zsh
set -e
echo "🚀 Phase 46–49 :: AI Paper Trading & Live Mode Setup..."
mkdir -p backups logs ai static tools db
timestamp=$(date +"%Y%m%d_%H%M%S")

# 1️⃣ Backup
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup saved"

# 2️⃣ Dependencies
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api sqlite-utils pandas numpy joblib

# 3️⃣ Create .env (add your keys here)
cat > .env <<'EOF'
ALPACA_API_KEY=your_alpaca_paper_api_key_here
ALPACA_SECRET_KEY=your_alpaca_paper_secret_key_here
ALPACA_MODE=paper
S3_BUCKET=aimoneyweb-backups
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF
echo "✅ .env created — edit it to add your real Alpaca Paper API keys."

# 4️⃣ Trade Executor
cat > ai/trade_executor.py <<'EOF'
import os, time, alpaca_trade_api as tradeapi
from dotenv import load_dotenv
load_dotenv()

def get_api():
    key=os.getenv("ALPACA_API_KEY")
    secret=os.getenv("ALPACA_SECRET_KEY")
    mode=os.getenv("ALPACA_MODE","paper")
    base="https://paper-api.alpaca.markets" if mode=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(key,secret,base)

def place_trade(signal,size):
    api=get_api()
    side="buy" if signal>0 else "sell"
    symbol="AAPL"
    qty=max(int(size/200),1)
    try:
        order=api.submit_order(symbol=symbol,qty=qty,side=side,type="market",time_in_force="gtc")
        print(f"📈 Order Placed: {side.upper()} {qty} {symbol}")
        return order.id
    except Exception as e:
        print("⚠️ Trade failed:",e)
        return None

def get_positions():
    api=get_api()
    try:return [p._raw for p in api.list_positions()]
    except: return []
EOF

# 5️⃣ Trade Analytics
cat > ai/trade_analytics.py <<'EOF'
import sqlite3,time,os,pandas as pd
DB="db/trades.db"
os.makedirs("db",exist_ok=True)

def log_trade(symbol,side,qty,price,equity,signal,drawdown):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades(
        ts TEXT, symbol TEXT, side TEXT, qty INT, price REAL, equity REAL,
        signal REAL, drawdown REAL)""")
    c.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)",
              (time.strftime("%Y-%m-%d %H:%M:%S"),symbol,side,qty,price,equity,signal,drawdown))
    conn.commit();conn.close()

def analyze():
    conn=sqlite3.connect(DB)
    df=pd.read_sql("SELECT * FROM trades",conn)
    conn.close()
    if len(df)==0:return {"count":0,"avg_pnl":0}
    df["pnl"]=df["price"].diff().fillna(0)
    return {
        "count":len(df),
        "avg_pnl":round(df["pnl"].mean(),2),
        "last_signal":round(df["signal"].iloc[-1],3)
    }
EOF

# 6️⃣ Main backend (adds live trading + analytics)
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio, random, os
from ai.fusion_engine import fuse_signals
from ai.risk_manager import compute_drawdown, position_size
from ai.trade_executor import place_trade, get_positions
from ai.trade_analytics import log_trade, analyze
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="AI Money Web :: Phases 46–49")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
EQUITY_HISTORY=[]

@app.get("/")
def root(): return {"message":"✅ AI Money Web Paper Trading Mode Active"}

@app.get("/api/trading_status")
def status():
    equity=100000+random.uniform(-500,500)
    cash=25000+random.uniform(-200,200)
    pnl=(equity-100000)/100000
    risk=abs(pnl)+0.01
    EQUITY_HISTORY.append(equity)
    draw=compute_drawdown(EQUITY_HISTORY[-50:])
    sig=fuse_signals(pnl,risk,equity,draw)
    size=position_size(sig,equity,draw)
    oid=place_trade(sig,size)
    log_trade("AAPL","buy" if sig>0 else "sell",int(size/200),equity,equity,sig,draw)
    return {"equity":equity,"cash":cash,"signal":sig,"drawdown":draw,"trade_id":oid,"positions":get_positions(),"analytics":analyze()}

@app.websocket("/ws/trading_status")
async def ws(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(status())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("🔌 Client disconnected")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"):
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h3>Dashboard missing — rerun setup.</h3>")
EOF

# 7️⃣ Dashboard HTML (adds analytics + positions view)
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>🚀 AI Money Web (Phases 46–49)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:black;color:#0ff;font-family:monospace;text-align:center;}canvas{width:90%;max-width:900px;margin:auto;}</style>
</head><body>
<h1>🚀 AI Money Web — Live Paper Trading Dashboard</h1>
<div id="status">Connecting…</div>
<div id="analytics"></div>
<canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'Drawdown (%)',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right',ticks:{color:'#f00'}}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/trading_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);
document.getElementById('status').textContent=`✅ Eq:${d.equity.toFixed(2)} | Sig:${d.signal.toFixed(3)} | DD:${d.drawdown.toFixed(2)} | Pos:${d.positions.length}`;
document.getElementById('analytics').textContent=`Trades:${d.analytics.count} | AvgPnL:${d.analytics.avg_pnl}`;
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.signal);
chart.data.datasets[2].data.push(d.drawdown);
if(chart.data.labels.length>40){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
chart.update();};
</script></body></html>
EOF

# 8️⃣ Make scripts executable
chmod +x *.sh ai/*.py tools/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard
echo "🎯 Phases 46–49 complete — Paper Trading + Analytics + Live Mode Ready."

