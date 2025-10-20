#!/bin/zsh
set -e
echo "🧠 Phase 41–45 :: Full Production Autopilot Setup…"
mkdir -p backups logs static ai tools cloud models
timestamp=$(date +"%Y%m%d_%H%M%S")

# 1️⃣ Backup
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup saved"

# 2️⃣ Install dependencies
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api boto3 supabase pandas numpy joblib python-telegram-bot supervisor docker

# 3️⃣ Create Cloud & Notifier helpers
cat > tools/cloud_sync.py <<'EOF'
import os,boto3,sqlite3,time
def upload_logs(bucket):
    s3=boto3.client("s3")
    for f in os.listdir("logs"):
        path=os.path.join("logs",f)
        s3.upload_file(path,bucket,f)
        print("☁️ Uploaded:",f)
def backup_db(bucket):
    if os.path.exists("learning_data.db"):
        s3=boto3.client("s3")
        s3.upload_file("learning_data.db",bucket,f"db_{int(time.time())}.sqlite")
        print("☁️ DB synced")
EOF

cat > tools/telegram_notifier.py <<'EOF'
import os,requests
BOT=os.getenv("TELEGRAM_BOT_TOKEN");CHAT=os.getenv("TELEGRAM_CHAT_ID")
def send(msg):
    if not BOT or not CHAT:return
    requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                  data={"chat_id":CHAT,"text":msg})
EOF

# 4️⃣ Broker Mode switcher
cat > ai/broker_toggle.py <<'EOF'
import os,alpaca_trade_api as tradeapi
from dotenv import load_dotenv
load_dotenv()
def get_api():
    key=os.getenv("ALPACA_API_KEY");secret=os.getenv("ALPACA_SECRET_KEY")
    paper=os.getenv("ALPACA_MODE","paper")
    base="https://paper-api.alpaca.markets" if paper=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(key,secret,base)
def get_account():
    api=get_api()
    a=api.get_account()
    return {"equity":float(a.equity),"cash":float(a.cash),"status":a.status}
EOF

# 5️⃣ Main backend
cat > main.py <<'EOF'
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio,os,random
from ai.broker_toggle import get_account
from ai.risk_manager import compute_drawdown,position_size
from ai.fusion_engine import fuse_signals
from tools.cloud_sync import upload_logs
from tools.telegram_notifier import send

app=FastAPI(title="AI Money Web v2 Production")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,
                   allow_methods=["*"],allow_headers=["*"])
EQUITY_HISTORY=[]

@app.get("/")
def root():return{"message":"✅ AI Money Web v2 Production Online"}

@app.get("/api/trading_status")
def trading_status():
    try:
        acct=get_account()
        eq,ca=acct["equity"],acct["cash"]
        pnl=(eq-100000)/100000;risk=abs(pnl)+0.01
        EQUITY_HISTORY.append(eq)
        draw=compute_drawdown(EQUITY_HISTORY[-50:])
        sig=fuse_signals(pnl,risk,eq,draw)
        pos=position_size(sig,eq,draw)
        send(f"📊 Equity:{eq:.2f} Signal:{sig:.3f} Pos:{pos:.2f}")
        return{"status":"live","equity":eq,"cash":ca,"signal":sig,"drawdown":draw,"size":pos}
    except Exception as e:return{"status":"error","detail":str(e)}

@app.get("/sync")
def sync():
    try:upload_logs(os.getenv("S3_BUCKET","aimoneyweb-backups"))
    except Exception as e:return{"detail":str(e)}
    return{"synced":"✅"}

@app.websocket("/ws/trading_status")
async def ws(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(trading_status())
            await asyncio.sleep(5)
    except WebSocketDisconnect:pass

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"):
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h2>Dashboard missing – rerun setup</h2>")
EOF

# 6️⃣ Dashboard HTML
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>🚀 AI Money Web Production (Phases 41–45)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:black;color:#0ff;font-family:monospace;text-align:center;}canvas{width:90%;max-width:900px;margin:auto;}</style>
</head><body>
<h1>🚀 AI Money Web Production Dashboard (Phases 41–45)</h1>
<div id="status">Connecting…</div><canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'Drawdown (%)',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right',ticks:{color:'#f00'}}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/trading_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);
document.getElementById('status').textContent=`✅ ${d.status} | Eq:${d.equity.toFixed(2)} | Sig:${d.signal.toFixed(3)} | DD:${d.drawdown.toFixed(2)} | Pos:${d.size.toFixed(2)}`;
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.signal);
chart.data.datasets[2].data.push(d.drawdown);
if(chart.data.labels.length>40){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
chart.update();};
</script></body></html>
EOF

# 7️⃣ Launch backend + make scripts executable
chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard
echo "🎯 Phases 41–45 complete — Full Production Autopilot online."

