# =========================================
# PHASE 37 :: ALPACA PAPER + PRO DASHBOARD
# Safe Quick-Fix Autopilot (zsh-friendly)
# =========================================
set -e

echo "🧠 Phase 37 :: Starting…"

# 0) Sanity: ensure we are in project root
[ -d venv ] || { echo "❌ venv not found. Create it: python3 -m venv venv && source venv/bin/activate"; exit 1; }

# 1) Make dirs + backup
mkdir -p backups logs static tools test static/css
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py "backups/main.py.$ts.bak" && echo "✅ Backed up main.py -> backups/main.py.$ts.bak"

# 2) Universal corrector (if present)
if [ -f tools/auto_syntax_corrector.py ]; then
  echo "🩹 Running universal corrector…"
  venv/bin/python3 tools/auto_syntax_corrector.py || true
else
  echo "ℹ️ Skipping corrector (tools/auto_syntax_corrector.py not found)."
fi

# 3) Deps (pin stable libs; all inside venv)
echo "📦 Installing deps in venv…"
venv/bin/pip install --upgrade pip >/dev/null
venv/bin/pip install fastapi uvicorn 'alpaca-trade-api' 'python-dotenv' requests >/dev/null

# 4) .env template (only create if missing)
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# === Alpaca Paper API ===
ALPACA_API_KEY_ID=YOUR_PAPER_KEY_ID
ALPACA_API_SECRET_KEY=YOUR_PAPER_SECRET
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Optional: 0/1 to toggle tiny random paper orders in future phases
PAPER_TRADING_ENABLE=0
EOF
  echo "✍️  Created .env (fill with your Alpaca Paper keys)."
fi

# 5) Dashboard HTML (dark theme + KPIs + status badge + live chart)
mkdir -p static
cat > static/dashboard.html << 'EOF'
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>AI Money Web • Pro Dashboard</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
  <style>
    :root { --bg:#0b1220; --card:#131c2e; --text:#e2e8f0; --accent:#22d3ee; --ok:#22c55e; --bad:#ef4444; }
    body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,Segoe UI,Inter,sans-serif}
    header{padding:18px 20px;border-bottom:1px solid #1f2a44}
    h1{margin:0;color:var(--accent);text-shadow:0 0 10px #0891b2}
    .wrap{padding:20px;display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
    .card{background:var(--card);border-radius:12px;padding:16px;box-shadow:0 0 16px #0ea5e980}
    .kpi{font-size:14px;opacity:.9}
    .kpi b{font-size:22px}
    .row{display:flex;align-items:center;gap:8px}
    .dot{width:12px;height:12px;border-radius:50%}
    .ok{background:var(--ok);box-shadow:0 0 8px var(--ok)}
    .bad{background:var(--bad);box-shadow:0 0 8px var(--bad)}
    canvas{max-width:100%;height:320px}
    .muted{opacity:.75}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    @media (max-width:700px){.grid2{grid-template-columns:1fr}}
    code{background:#0f172a;padding:2px 6px;border-radius:6px}
  </style>
</head>
<body>
  <header class="row" style="justify-content:space-between">
    <h1>🚀 AI Money Web — Pro Dashboard</h1>
    <div class="row"><span id="dot" class="dot bad"></span><span id="state">Disconnected</span></div>
  </header>

  <section class="wrap">
    <div class="card grid2">
      <div class="kpi">Equity<br><b id="equity">—</b></div>
      <div class="kpi">Cash<br><b id="cash">—</b></div>
      <div class="kpi">Buying Power<br><b id="bp">—</b></div>
      <div class="kpi">PnL (session)<br><b id="pnl" class="muted">—</b></div>
    </div>

    <div class="card">
      <div class="row" style="justify-content:space-between"><b>📈 Equity Curve</b><span class="muted" id="ts">—</span></div>
      <canvas id="equityChart"></canvas>
    </div>

    <div class="card muted">
      Alpaca status endpoint: <code>/api/alpaca_status</code><br/>
      WebSocket stream: <code>/ws/alpaca_status</code>
    </div>
  </section>

  <script>
    // Chart setup
    const ctx=document.getElementById('equityChart');
    const data={labels:[],datasets:[{label:'Equity',data:[],borderColor:'#22d3ee',tension:.3}]};
    const chart=new Chart(ctx,{type:'line',data,options:{animation:false,scales:{x:{ticks:{color:'#94a3b8'}},y:{ticks:{color:'#94a3b8'}}}}});

    const dot=document.getElementById('dot'), state=document.getElementById('state');
    const eq=document.getElementById('equity'), cash=document.getElementById('cash'), bp=document.getElementById('bp');
    const pnl=document.getElementById('pnl'), tsEl=document.getElementById('ts');

    let startEquity=null;
    function fmt(n){return (n==null||isNaN(n))?'—':Number(n).toLocaleString(undefined,{maximumFractionDigits:2});}
    function updateKPI(j){
      if(j.status==='connected'){dot.className='dot ok'; state.textContent='Connected to Alpaca Paper ✅';}
      else if(j.status==='error'){dot.className='dot bad'; state.textContent='Error (see logs) ❌';}
      else {dot.className='dot bad'; state.textContent=j.status||'Disconnected';}
      eq.textContent=fmt(j.equity); cash.textContent=fmt(j.cash); bp.textContent=fmt(j.buying_power);
      if(startEquity===null && j.equity!=null){startEquity=Number(j.equity);}
      if(startEquity!=null && j.equity!=null){const d=Number(j.equity)-startEquity; pnl.textContent=(d>=0?'+':'')+fmt(d);}
      tsEl.textContent = j.timestamp || new Date().toLocaleTimeString();
    }
    function pushPoint(j){
      if(!j.equity) return;
      const label=(j.timestamp? new Date(j.timestamp):new Date()).toLocaleTimeString();
      data.labels.push(label); data.datasets[0].data.push(j.equity);
      if(data.labels.length>120){data.labels.shift(); data.datasets[0].data.shift();}
      chart.update();
    }

    // Prime KPIs with REST then switch to WS
    fetch('/api/alpaca_status').then(r=>r.json()).then(j=>{ updateKPI(j); pushPoint(j); }).catch(()=>{});
    const ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws/alpaca_status');
    ws.onmessage=(ev)=>{ try{const j=JSON.parse(ev.data); updateKPI(j); pushPoint(j);}catch(e){} };
    ws.onclose=()=>{ dot.className='dot bad'; state.textContent='Disconnected'; };
  </script>
</body>
</html>
EOF

# 6) main.py (FastAPI + Alpaca Paper integration + WS stream + fallback)
cat > main.py << 'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio, os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

API_KEY   = os.getenv("ALPACA_API_KEY_ID")
API_SEC   = os.getenv("ALPACA_API_SECRET_KEY")
BASE_URL  = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Lazy import so the app can still boot without the package in dev
ALPACA_OK = False
try:
    from alpaca_trade_api.rest import REST
    alpaca = REST(API_KEY, API_SEC, base_url=BASE_URL) if API_KEY and API_SEC else None
    ALPACA_OK = alpaca is not None
except Exception:
    alpaca = None

app = FastAPI(title="AI Money Web • Phase 37")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def utcnow():
    return datetime.now(timezone.utc).isoformat()

@app.get("/")
def root():
    return {"message": "✅ AI Money Web Backend is alive"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    if not os.path.exists("static/dashboard.html"):
        return HTMLResponse("<h1>Dashboard missing. Re-run Phase 36.1.</h1>", status_code=500)
    with open("static/dashboard.html") as f:
        return f.read()

@app.get("/api/alpaca_status")
def api_alpaca_status():
    try:
        if ALPACA_OK:
            acct = alpaca.get_account()
            return {
                "status": "connected",
                "equity": float(acct.equity),
                "cash": float(acct.cash),
                "buying_power": float(acct.buying_power),
                "timestamp": utcnow(),
                "source": "alpaca"
            }
        # Fallback mock if keys missing
        return {"status":"disconnected","equity":100000.0,"cash":25000.0,"buying_power":50000.0,"timestamp":utcnow(),"source":"mock"}
    except Exception as e:
        return JSONResponse({"status":"error","message":str(e),"timestamp":utcnow()}, status_code=200)

@app.websocket("/ws/alpaca_status")
async def ws_alpaca_status(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            try:
                if ALPACA_OK:
                    acct = alpaca.get_account()
                    payload = {
                        "status": "connected",
                        "equity": float(acct.equity),
                        "cash": float(acct.cash),
                        "buying_power": float(acct.buying_power),
                        "timestamp": utcnow(),
                        "source": "alpaca"
                    }
                else:
                    payload = {"status":"disconnected","equity":100000.0,"cash":25000.0,"buying_power":50000.0,"timestamp":utcnow(),"source":"mock"}
                await ws.send_json(payload)
            except Exception as e:
                await ws.send_json({"status":"error","message":str(e),"timestamp":utcnow()})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
EOF

# 7) Autopilot watcher (keeps backend healthy; restarts on failure)
cat > tools/autopilot_watcher.py << 'EOF'
import os, time, subprocess, requests, signal, sys

PORT = os.getenv("PORT","8000")
BASE = f"http://127.0.0.1:{PORT}"
LOG = "logs/autopilot_watcher.log"

def free_port():
    os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")

def start_backend():
    with open("logs/backend.log","a") as f:
        return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT], stdout=f, stderr=f)

def healthy():
    try:
        r = requests.get(BASE+"/", timeout=2)
        r2 = requests.get(BASE+"/api/alpaca_status", timeout=2)
        return r.status_code==200 and r2.status_code==200
    except Exception:
        return False

def main():
    os.makedirs("logs", exist_ok=True)
    proc = start_backend()
    while True:
        if proc.poll() is not None or not healthy():
            free_port()
            proc.terminate() if proc.poll() is None else None
            time.sleep(1)
            proc = start_backend()
        time.sleep(7)

if __name__=="__main__":
    main()
EOF

# 8) Launch everything
echo "🔪 Freeing :8000…"; kill -9 $(lsof -t -i:8000) 2>/dev/null || true
echo "🚀 Starting backend…"; nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
echo "🛡️  Starting autopilot watcher…"; nohup venv/bin/python3 tools/autopilot_watcher.py > logs/watcher.log 2>&1 &
sleep 5

# 9) Health check + open dashboard
if curl -s http://127.0.0.1:8000/ | grep -q "AI Money Web"; then
  echo "✅ Backend alive. Opening dashboard…"
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend not responding. See logs/backend.log"
  head -n 40 logs/backend.log || true
fi

echo "🎯 Phase 37 complete."

