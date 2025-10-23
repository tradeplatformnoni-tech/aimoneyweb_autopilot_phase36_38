#!/usr/bin/env bash
# === phase_581_600_autofix_launcher.sh ===
set -e
echo "🧠 NeoLight :: Phase 581–600 :: AutoFix + Resilience Patch"

mkdir -p backend templates static runtime ai/strategies tools logs

# --- Fix Environment ---
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install fastapi uvicorn requests pandas --quiet

# --- Ensure proper PYTHONPATH export on activation ---
echo 'export PYTHONPATH=$(pwd)' > .venv/bin/activate_pathfix
chmod +x .venv/bin/activate_pathfix
source .venv/bin/activate_pathfix

# --- Rebuild backend/main.py (safe baseline) ---
cat > backend/main.py <<'PY'
import os, json, datetime, math, random
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AI Money Web :: NeoLight v3.6 AutoFix")
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNTIME = "runtime"
os.makedirs(RUNTIME, exist_ok=True)
LIVE_FILE = os.path.join(RUNTIME,"live_mode.json")
PORTFOLIO_FILE = os.path.join(RUNTIME,"portfolio.json")

def jread(path, default): 
    try: return json.load(open(path))
    except Exception: return default
def jwrite(path, obj): 
    json.dump(obj, open(path,"w"), indent=2)

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return open("templates/dashboard.html").read()

@app.get("/api/health")
def health():
    return {"status":"ok","timestamp":datetime.datetime.utcnow().isoformat()}

@app.get("/api/ohlc")
def ohlc(symbol: str="AAPL", limit: int=120):
    data=[]; now=datetime.datetime.utcnow()
    price=150
    for i in range(limit):
        ts=now-datetime.timedelta(minutes=limit-i)
        drift=math.sin(i/10)*0.8
        o=price+random.uniform(-0.8,0.8)+drift
        h=o+random.uniform(0,1.2); l=o-random.uniform(0,1.2)
        c=random.uniform(l,h)
        data.append({"t":ts.isoformat(),"open":o,"high":h,"low":l,"close":c})
        price=c
    return data
PY

# --- Dashboard Template ---
cat > templates/dashboard.html <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>NeoLight v3.6 AutoFix</title>
<link rel="stylesheet" href="/static/style.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>💡 AI Money Web :: AutoFix Health</h1>
  <p>Status: <span id="health">Checking...</span></p>
  <canvas id="chart" height="120"></canvas>
  <script src="/static/dashboard.js"></script>
</body>
</html>
HTML

# --- Simple style ---
cat > static/style.css <<'CSS'
body{background:#000;color:#0ff;font-family:monospace;padding:2rem}
h1{color:#0ff}
CSS

# --- JS to ping health + draw OHLC ---
cat > static/dashboard.js <<'JS'
async function getJSON(u){return (await fetch(u)).json();}
async function health(){
  const h=document.getElementById('health');
  try{const r=await getJSON('/api/health');h.textContent='✅ '+r.status;}
  catch(e){h.textContent='❌ Offline';}
}
async function chart(){
  const data=await getJSON('/api/ohlc');
  const ctx=document.getElementById('chart').getContext('2d');
  new Chart(ctx,{type:'line',data:{
    labels:data.map(d=>d.t.slice(11,16)),
    datasets:[{label:'Close',data:data.map(d=>d.close),borderColor:'#0ff'}]
  }});
}
health();chart();
JS

# --- Health check helper script ---
cat > tools/health_check.sh <<'BASH'
#!/usr/bin/env bash
if ! curl -s http://127.0.0.1:8000/api/health >/dev/null; then
  echo "🛠 Restarting FastAPI..."
  pkill -f "uvicorn backend.main:app" || true
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
else
  echo "✅ FastAPI healthy"
fi
BASH
chmod +x tools/health_check.sh

# --- Run server fresh ---
pkill -f "uvicorn backend.main:app" || true
echo "🚀 Launching FastAPI..."
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

echo "✅ Done. Test:  curl http://127.0.0.1:8000/api/health"
echo "Then open 👉  http://localhost:8000/dashboard"
echo "If you ever see 'permission denied':  chmod +x phase_581_600_autofix_launcher.sh"

