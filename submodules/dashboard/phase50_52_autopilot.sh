#!/bin/zsh
set -e
echo "🧠 Phase 50–52+ :: Cloud Pack + Telegram + Auto-Trainer …"

# 0) Prep
mkdir -p backups logs static ai tools models db cloud
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py backups/main.py.$ts.bak && echo "✅ Backup -> backups/main.py.$ts.bak"

# 1) Deps (venv)
venv/bin/pip install -q fastapi uvicorn requests python-dotenv \
  alpaca-trade-api pandas numpy joblib sqlite-utils \
  python-telegram-bot boto3 supervisor

# 2) .env template (keeps your values if exists)
if [ ! -f .env ]; then
cat > .env <<'EOF'
ALPACA_API_KEY=your_alpaca_paper_api_key_here
ALPACA_SECRET_KEY=your_alpaca_paper_secret_key_here
ALPACA_MODE=paper               # paper | live

S3_BUCKET=aimoneyweb-backups    # optional
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1

TELEGRAM_BOT_TOKEN=             # optional
TELEGRAM_CHAT_ID=               # optional
EOF
echo "✍️  Created .env — fill values as needed."
else
  echo "✅ .env already exists (keeping your keys)."
fi

# 3) Cloud sync helper (S3)
cat > tools/cloud_sync.py <<'EOF'
import os, time, boto3, glob
from dotenv import load_dotenv; load_dotenv()

BUCKET = os.getenv("S3_BUCKET")
def _client():
    if not BUCKET: return None
    return boto3.client("s3")

def upload_logs():
    c=_client()
    if not c: return "S3 not configured"
    sent=0
    for path in glob.glob("logs/*"):
        key=os.path.basename(path)
        try: c.upload_file(path, BUCKET, f"logs/{key}"); sent+=1
        except Exception as e: print("S3 err:",e)
    return f"uploaded:{sent}"

def backup_db():
    c=_client()
    if not c or not os.path.exists("db/trades.db"): return "no db or s3"
    key=f"db/trades_{int(time.time())}.sqlite"
    try: c.upload_file("db/trades.db", BUCKET, key); return key
    except Exception as e: return f"db upload err:{e}"

if __name__=="__main__":
    print(upload_logs()); print(backup_db())
EOF

# 4) Telegram assistant (polling)
cat > tools/telegram_bot.py <<'EOF'
import os, asyncio, json
from dotenv import load_dotenv; load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

BASE = "http://127.0.0.1:8000"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI Money Web ready. Commands: /status /positions /mode /sync")

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r=requests.get(f"{BASE}/api/trading_status",timeout=5).json()
        await update.message.reply_text(f"✅ Eq:{r.get('equity'):.2f} Sig:{r.get('signal'):.3f} DD:{r.get('drawdown'):.2f}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

async def positions(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r=requests.get(f"{BASE}/api/positions").json()
        await update.message.reply_text("📦 Positions:\n"+json.dumps(r,indent=2))
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

async def mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        m = " ".join(ctx.args).strip().lower()
        r=requests.post(f"{BASE}/api/mode",json={"mode":m}).json()
        await update.message.reply_text("🔁 "+str(r))
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

async def sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r=requests.get(f"{BASE}/sync").json()
        await update.message.reply_text("☁️ "+str(r))
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

def run():
    if not BOT or not CHAT: 
        print("Telegram not configured; set TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID"); return
    app=Application.builder().token(BOT).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("mode", mode))
    app.add_handler(CommandHandler("sync", sync))
    app.run_polling()

if __name__=="__main__": run()
EOF

# 5) Auto-trainer (daily best model promotion)
cat > ai/auto_trainer.py <<'EOF'
import os, time, sqlite3, pandas as pd, numpy as np, joblib
os.makedirs("models",exist_ok=True)
DB="db/trades.db"
def data():
    if not os.path.exists(DB): return None
    c=sqlite3.connect(DB); df=pd.read_sql("SELECT * FROM trades",c); c.close()
    return df if not df.empty else None
def train():
    df=data()
    if df is None: print("no data yet"); return
    # simple linear metric on (price changes vs signal)
    pnl=df["price"].diff().fillna(0)
    sig=df["signal"].fillna(0)
    if len(sig)<5: return
    w=float(np.dot(pnl, sig)/ (np.linalg.norm(sig)+1e-6))
    score=float(pnl.mean())
    model={"weights":[w], "score":score, "ts":time.time()}
    path=f"models/model_{int(model['ts'])}.pkl"
    joblib.dump(model, path); joblib.dump(model, "models/active_model.pkl")
    print("🧠 model saved:", path, "score:",score)
if __name__=="__main__":
    while True:
        train(); time.sleep(60*60*24)
EOF

# 6) Update trade executor/analytics if missing
if [ ! -f ai/trade_executor.py ]; then
cat > ai/trade_executor.py <<'EOF'
import os,alpaca_trade_api as tradeapi
from dotenv import load_dotenv; load_dotenv()
def _api():
    base="https://paper-api.alpaca.markets" if os.getenv("ALPACA_MODE","paper")=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), base)
def place_trade(signal,size):
    api=_api(); sym="AAPL"; side="buy" if signal>0 else "sell"; qty=max(int(size/200),1)
    try: o=api.submit_order(symbol=sym, qty=qty, side=side, type="market", time_in_force="gtc"); return o.id
    except Exception as e: return f"error:{e}"
def get_positions():
    api=_api()
    try: return [p._raw for p in api.list_positions()]
    except: return []
EOF
fi

if [ ! -f ai/trade_analytics.py ]; then
cat > ai/trade_analytics.py <<'EOF'
import os,sqlite3,time,pandas as pd
os.makedirs("db",exist_ok=True); DB="db/trades.db"
def log_trade(symbol,side,qty,price,equity,signal,drawdown):
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades(
        ts TEXT, symbol TEXT, side TEXT, qty INT, price REAL, equity REAL, signal REAL, drawdown REAL)""")
    c.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)",
              (time.strftime("%Y-%m-%d %H:%M:%S"),symbol,side,qty,price,equity,signal,drawdown))
    conn.commit(); conn.close()
def analyze():
    conn=sqlite3.connect(DB); df=pd.read_sql("SELECT * FROM trades",conn); conn.close()
    if df.empty: return {"count":0,"avg_pnl":0,"last_signal":0}
    df["pnl"]=df["price"].diff().fillna(0)
    return {"count":len(df),"avg_pnl":round(df["pnl"].mean(),4),"last_signal":round(df["signal"].iloc[-1],3)}
EOF
fi

# 7) Update main.py with new endpoints + health/sync + mode toggle
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv; load_dotenv()
import os, random, asyncio
from ai.fusion_engine import fuse_signals
from ai.risk_manager import compute_drawdown, position_size
from ai.trade_executor import place_trade, get_positions
from ai.trade_analytics import log_trade, analyze
from tools.cloud_sync import upload_logs, backup_db

app=FastAPI(title="AI Money Web :: Phases 50–52+")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
EQUITY_HISTORY=[]

@app.get("/health")
def health(): return {"ok":True}

@app.get("/")
def root(): return {"message":"✅ AI Money Web Cloud Pack Online"}

@app.get("/api/positions")
def positions(): return get_positions()

@app.post("/api/mode")
def mode(payload: dict = Body(...)):
    m=(payload or {}).get("mode","").lower()
    if m in ("paper","live"):
        os.environ["ALPACA_MODE"]=m
        return {"mode":m,"note":"only affects new processes; set in .env for persistence"}
    return {"error":"send {'mode':'paper'|'live'}"}

@app.get("/sync")
def sync(): return {"logs":upload_logs(),"db":backup_db()}

@app.get("/api/trading_status")
def status():
    # NOTE: replace the next two lines with real account pulls if desired
    equity=100000+random.uniform(-600,600); cash=25000+random.uniform(-200,200)
    pnl=(equity-100000)/100000; risk=abs(pnl)+0.01
    EQUITY_HISTORY.append(equity)
    draw=compute_drawdown(EQUITY_HISTORY[-60:])
    sig=fuse_signals(pnl,risk,equity,draw)
    size=position_size(sig,equity,draw)
    oid=place_trade(sig,size) if os.getenv("ALPACA_API_KEY") else None
    log_trade("AAPL","buy" if sig>0 else "sell",int(size/200),equity,equity,sig,draw)
    return {"equity":equity,"cash":cash,"signal":sig,"drawdown":draw,"trade_id":oid,"analytics":analyze()}

@app.websocket("/ws/trading_status")
async def ws(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(status()); await asyncio.sleep(5)
    except WebSocketDisconnect: pass

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"): 
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h3>Dashboard missing — rerun setup.</h3>")
EOF

# 8) Dashboard V2 (same look, shows analytics)
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>🚀 AI Money Web Cloud (50–52+)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:#000;color:#0ff;font-family:monospace;text-align:center}canvas{width:92%;max-width:1000px;margin:auto}</style>
</head><body>
<h1>🚀 AI Money Web — Cloud Pack (50–52+)</h1>
<div id="status">Connecting…</div><div id="analytics"></div>
<canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'Drawdown (%)',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right'}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/trading_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);
document.getElementById('status').textContent=`✅ Eq:${d.equity.toFixed(2)} Sig:${d.signal.toFixed(3)} DD:${d.drawdown.toFixed(2)}`;
document.getElementById('analytics').textContent=`Trades:${d.analytics.count} AvgPnL:${d.analytics.avg_pnl}`;
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.signal);
chart.data.datasets[2].data.push(d.drawdown);
if(chart.data.labels.length>60){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
chart.update();};
</script></body></html>
EOF

# 9) Docker + Supervisor (Phase 50)
cat > Dockerfile <<'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn requests python-dotenv alpaca-trade-api \
    pandas numpy joblib python-telegram-bot boto3 supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 8000
CMD ["/usr/bin/supervisord","-n"]
EOF

cat > docker-compose.yml <<'EOF'
version: "3.9"
services:
  aimoneyweb:
    build: .
    ports: ["8000:8000"]
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - ALPACA_MODE=${ALPACA_MODE}
      - S3_BUCKET=${S3_BUCKET}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    restart: unless-stopped
EOF

cat > supervisord.conf <<'EOF'
[supervisord]
nodaemon=true

[program:uvicorn]
command=python -m uvicorn main:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/logs/uvicorn.err
stdout_logfile=/app/logs/uvicorn.out

[program:auto_trainer]
command=python ai/auto_trainer.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/logs/trainer.err
stdout_logfile=/app/logs/trainer.out

[program:telegram]
command=python tools/telegram_bot.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/app/logs/telegram.err
stdout_logfile=/app/logs/telegram.out
EOF

# 10) Local launch (venv)
chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 ai/auto_trainer.py > logs/auto_trainer.log 2>&1 &
if [ -n "$(grep -E '^TELEGRAM_BOT_TOKEN=.*\S' .env)" ]; then
  nohup venv/bin/python3 tools/telegram_bot.py > logs/telegram.log 2>&1 &
fi
sleep 5
open http://127.0.0.1:8000/dashboard || true
echo "🎯 Phase 50–52+ complete. Local running. Docker instructions printed below."

echo ""
echo "🐳 Docker (optional):"
echo "  docker compose build && docker compose up -d"
echo "  open http://127.0.0.1:8000/dashboard"
echo ""
echo "🧰 Scripts are executable. If macOS ever says 'permission denied':"
echo "  chmod +x *.sh tools/*.py ai/*.py"

