#!/bin/zsh
set -e

echo "🚀 Phase 171–190 :: Autopilot (Paper Trading Toggle + Supervisor + WS) ..."

timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools runtime
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup -> backups/main.py.$timestamp.bak" || true

echo "🧩 Installing deps..."
pip install -q "uvicorn[standard]" fastapi python-dotenv requests websockets wsproto alpaca-trade-api

# .env template (only created if missing)
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# ---- Alpaca Paper Trading (.env) ----
PAPER_TRADE=0
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_API_KEY_ID=YOUR_KEY_HERE
ALPACA_API_SECRET=YOUR_SECRET_HERE
# Optional throttle/risk
MAX_NOTIONAL_PER_TRADE=1000
MAX_OPEN_POSITIONS=2
RISK_CAP=0.03
EOF
  echo "✍️  Created .env template (edit later to enable paper trading)."
else
  echo "ℹ️  .env already exists — keeping your keys."
fi

# ------------------- main.py -------------------
cat > main.py << 'EOF'
import os, json, time, asyncio, datetime
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
RUNTIME = BASE_DIR / "runtime"
STATUS_FILE = RUNTIME / "alpaca_status.json"

load_dotenv()
app = FastAPI(title="AI Money Web :: Phase 171–190")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def read_status():
    try:
        if STATUS_FILE.exists():
            return json.loads(STATUS_FILE.read_text())
    except Exception as e:
        return {"status":"error","error":str(e)}
    return {"status":"booting","source":"unknown"}

def write_status(obj: dict):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(obj, indent=2))

@app.get("/")
def root():
    s = read_status()
    return {"message":"✅ Phase 171–190 online", "mode": s.get("source","mock"), "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/dashboard")
def dashboard():
    return FileResponse(str(BASE_DIR / "static" / "dashboard.html"))

@app.get("/api/alpaca_status")
def alpaca_status():
    return JSONResponse(read_status())

@app.post("/api/toggle_mode")
def toggle_mode():
    # Safely flip PAPER_TRADE in .env
    env_path = BASE_DIR / ".env"
    text = env_path.read_text()
    if "PAPER_TRADE=1" in text:
        text = text.replace("PAPER_TRADE=1","PAPER_TRADE=0")
        mode = "mock"
    else:
        text = text.replace("PAPER_TRADE=0","PAPER_TRADE=1")
        mode = "paper"
    env_path.write_text(text)
    # write a hint in runtime for supervisor
    (RUNTIME / "toggle.flag").write_text(str(time.time()))
    return {"ok":True, "mode":mode}

@app.websocket("/ws/alpaca_status")
async def ws_alpaca_status(websocket: WebSocket):
    await websocket.accept()
    print("📡 WS client connected.")
    last = ""
    try:
        while True:
            s = read_status()
            cur = json.dumps(s)
            if cur != last:
                await websocket.send_text(cur)
                last = cur
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        print("🔌 WS client disconnected.")
EOF

# ------------------- static/dashboard.html -------------------
cat > static/dashboard.html << 'EOF'
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>AI Money Web :: 171–190</title>
  <style>
    body{background:#0b0c10;color:#eafdfc;font-family:system-ui,Arial;margin:0;padding:24px;text-align:center}
    .badge{display:inline-block;padding:6px 12px;border-radius:8px;margin:8px 0}
    .ok{background:#133;box-shadow:0 0 12px #0ff;color:#0ff}
    .err{background:#311;box-shadow:0 0 12px #f66;color:#f66}
    .btn{margin:10px;padding:8px 14px;border:1px solid #0ff;border-radius:8px;color:#0ff;background:transparent;cursor:pointer}
    #panel{width:820px;max-width:95vw;margin:24px auto;padding:16px;border-radius:16px;background:#111;border:1px solid #0ff;box-shadow:0 0 24px #0ff3}
    pre{white-space:pre-wrap;text-align:left;background:#091015;padding:12px;border-radius:10px;overflow:auto}
  </style>
</head>
<body>
  <h1>🚀 AI Money Web Autopilot Dashboard (Phase 171–190)</h1>
  <div id="conn" class="badge err">❌ Disconnected</div>
  <div id="mode" class="badge ok">Mode: loading...</div>
  <div id="panel">
    <button class="btn" onclick="toggleMode()">Toggle Mode (mock ↔ paper)</button>
    <h3>Live Status</h3>
    <pre id="out">waiting...</pre>
  </div>

<script>
const out = document.getElementById('out');
const modeEl = document.getElementById('mode');
const conn = document.getElementById('conn');

async function fetchStatus(){
  const r = await fetch('/api/alpaca_status');
  const j = await r.json();
  out.textContent = JSON.stringify(j,null,2);
  modeEl.textContent = "Mode: " + (j.source || "unknown");
}
async function toggleMode(){
  await fetch('/api/toggle_mode',{method:'POST'});
  setTimeout(fetchStatus, 800);
}

let ws;
function connectWS(){
  ws = new WebSocket('ws://127.0.0.1:8000/ws/alpaca_status');
  ws.onopen = () => { conn.textContent="🟢 Connected"; conn.className="badge ok"; };
  ws.onclose = () => { conn.textContent="❌ Disconnected"; conn.className="badge err"; setTimeout(connectWS, 1500); };
  ws.onmessage = (e) => {
    try{
      const j = JSON.parse(e.data);
      out.textContent = JSON.stringify(j,null,2);
      modeEl.textContent = "Mode: " + (j.source || "unknown");
    }catch(err){}
  };
}
connectWS();
fetchStatus();
</script>
</body>
</html>
EOF

# ------------------- tools/trader_supervisor.py -------------------
cat > tools/trader_supervisor.py << 'EOF'
import os, time, json, random, math
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
STATUS_FILE = RUNTIME / "alpaca_status.json"

load_dotenv(BASE / ".env")
PAPER = os.getenv("PAPER_TRADE","0") == "1"
ALPACA_BASE = os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets")
KEY = os.getenv("ALPACA_API_KEY_ID","")
SECRET = os.getenv("ALPACA_API_SECRET","")

def write(s):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(s, indent=2))

def mock_loop():
    equity = 100000.0
    cash   = 25000.0
    t0 = time.time()
    while True:
        # small random walk
        equity += random.uniform(-20, 30)
        s = {
            "status":"connected","equity":round(equity,2),"cash":round(cash,2),
            "buying_power": 50000, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source":"mock"
        }
        write(s)
        time.sleep(2)

def alpaca_loop():
    try:
        from alpaca_trade_api.rest import REST
        api = REST(KEY, SECRET, base_url=ALPACA_BASE)
    except Exception as e:
        write({"status":"error","error":f"alpaca import/connect failed: {e}","source":"paper"})
        time.sleep(3)
        return

    while True:
        try:
            acct = api.get_account()
            s = {
                "status":"connected",
                "equity": float(getattr(acct,"equity",0)),
                "cash": float(getattr(acct,"cash",0)),
                "buying_power": float(getattr(acct,"buying_power",0)),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source":"paper"
            }
            write(s)
        except Exception as e:
            write({"status":"error","error":str(e),"source":"paper"})
        time.sleep(3)

def main():
    # honor toggle flag; reload .env if user flips mode
    last_flag = None
    while True:
        flag_file = RUNTIME / "toggle.flag"
        now_flag = flag_file.read_text().strip() if flag_file.exists() else None

        if now_flag != last_flag:
            load_dotenv(BASE / ".env", override=True)
        last_flag = now_flag

        PAPER = os.getenv("PAPER_TRADE","0") == "1"
        if PAPER and os.getenv("ALPACA_API_KEY_ID") and os.getenv("ALPACA_API_SECRET"):
            write({"status":"connecting","source":"paper"})
            alpaca_loop()   # returns only on error
        else:
            write({"status":"connecting","source":"mock"})
            mock_loop()     # never returns

if __name__ == "__main__":
    main()
EOF

echo "🔪 Restarting backend..."
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &

echo "🤖 Starting trader supervisor..."
nohup venv/bin/python3 tools/trader_supervisor.py > logs/trader.log 2>&1 &

sleep 5
if curl -s http://127.0.0.1:8000/ | grep -q "Phase 171–190"; then
  echo "✅ Backend healthy — opening dashboard..."
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend not responding. Check logs/backend.log"
fi

echo "🎯 Phase 171–190 complete."
echo "📄 Logs -> logs/backend.log | logs/trader.log"

