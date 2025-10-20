#!/bin/zsh
set -e
echo "🧠 Phase 38.1 :: AI Trainer Daemon Setup..."
mkdir -p backups logs static tools ai models
timestamp=$(date +"%Y%m%d_%H%M%S")

# 1️⃣ Backup
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup saved"

# 2️⃣ Install/update deps
venv/bin/pip install -q fastapi uvicorn requests python-dotenv alpaca-trade-api sqlite-utils numpy pandas joblib

# 3️⃣ Create AI Trainer Daemon
cat > ai/ai_trainer_daemon.py <<'EOF'
import sqlite3, time, os, numpy as np, pandas as pd, joblib
DB="learning_data.db"
MODEL_DIR="models"
os.makedirs(MODEL_DIR,exist_ok=True)

def fetch_data():
    if not os.path.exists(DB): return pd.DataFrame()
    con=sqlite3.connect(DB)
    df=pd.read_sql("SELECT * FROM trades",con)
    con.close()
    return df

def train_model():
    df=fetch_data()
    if df.empty: 
        print("⚠️ No data yet for training."); return
    X=df[['pnl','risk']].values
    y=(df['pnl']/ (df['risk']+1e-6)).values
    weights=np.polyfit(X[:,0],y,1)
    score=np.mean(y)
    model_file=f"{MODEL_DIR}/model_{time.strftime('%Y%m%d_%H%M%S')}.pkl"
    joblib.dump({'weights':weights,'score':score},model_file)
    print(f"🧠 Trained model saved: {model_file} | score={score:.4f}")
    best_model=find_best_model()
    joblib.dump(best_model,f"{MODEL_DIR}/active_model.pkl")
    print("✅ Best model reloaded for live use.")

def find_best_model():
    models=[f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')]
    if not models: return None
    best=None;best_score=-1e9
    for m in models:
        data=joblib.load(os.path.join(MODEL_DIR,m))
        s=data.get('score',0)
        if s>best_score:best=data;best_score=s
    return best

def loop():
    while True:
        print("🔁 Trainer Daemon tick — checking for new data...")
        train_model()
        time.sleep(3600*24)  # once a day

if __name__=="__main__":
    loop()
EOF

# 4️⃣ Update main.py with model loading
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import asyncio, os, requests, random, joblib
from ai.ai_brain import ensure_db, log_trade, learn

load_dotenv(); ensure_db()
app=FastAPI(title="AI Money Web Trainer Daemon")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

MODEL_PATH="models/active_model.pkl"
ACTIVE_MODEL=joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else {"weights":[0,1],"score":0}

@app.get("/")
def root():
    return {"message":"✅ AI Money Web Trainer Daemon Live","model_score":ACTIVE_MODEL.get("score",0)}

@app.get("/api/alpaca_status")
def alpaca_status():
    try:
        equity=100000+random.uniform(-500,500)
        cash=25000+random.uniform(-200,200)
        pnl=(equity-100000)/100000
        risk=abs(pnl)+0.01
        log_trade(equity,pnl,risk)
        score=learn()
        adjusted=score*ACTIVE_MODEL.get('weights',[0,1])[1]
        return {"status":"mock","equity":equity,"cash":cash,"adaptive_score":score,"adjusted_signal":adjusted}
    except Exception as e:
        return {"status":"error","detail":str(e)}

@app.websocket("/ws/alpaca_status")
async def ws_alpaca(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(alpaca_status())
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        print("🔌 Client disconnected")

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"):
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h2>Dashboard missing. Re-run setup.</h2>")
EOF

# 5️⃣ Dashboard HTML (same as before)
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>🚀 AI Money Web Trainer Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:black;color:#0ff;font-family:monospace;text-align:center;}canvas{width:90%;max-width:800px;margin:auto;}</style>
</head><body>
<h1>🚀 AI Money Web Trainer Daemon (Phase 38.1)</h1>
<div id="status">Connecting…</div>
<canvas id="chart"></canvas>
<script>
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Adaptive Score',borderColor:'#0f0',data:[]},
{label:'Adjusted Signal',borderColor:'#ff0',data:[]}]}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/alpaca_status');
ws.onmessage=(e)=>{const d=JSON.parse(e.data);
document.getElementById('status').textContent=`✅ ${d.status} | Eq: ${d.equity.toFixed(2)} | Score: ${d.adaptive_score.toFixed(4)} | Signal: ${d.adjusted_signal.toFixed(4)}`;
chart.data.labels.push(new Date().toLocaleTimeString());
chart.data.datasets[0].data.push(d.equity);
chart.data.datasets[1].data.push(d.adaptive_score);
chart.data.datasets[2].data.push(d.adjusted_signal);
if(chart.data.labels.length>30){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
chart.update();};
</script></body></html>
EOF

# 6️⃣ Launch everything
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 ai/ai_trainer_daemon.py > logs/trainer.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard
echo "🎯 Phase 38.1 Trainer Daemon active — AI now learns daily!"

