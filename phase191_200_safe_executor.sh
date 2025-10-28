#!/bin/zsh
set -e

echo "🚀 Phase 191–200 :: Safe Order Executor + /api/signal + Dashboard Trade Widget"

timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools ai runtime
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup -> backups/main.py.$timestamp.bak" || true

echo "🧩 Installing deps..."
pip install -q "uvicorn[standard]" fastapi python-dotenv requests websockets wsproto alpaca-trade-api pandas

# 1) Ensure .env keys and risk settings exist (add if missing)
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# ---- Alpaca Paper Trading (.env) ----
PAPER_TRADE=0
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_API_KEY_ID=YOUR_KEY_HERE
ALPACA_API_SECRET=YOUR_SECRET_HERE

# ---- Risk + Limits ----
SYMBOL_WHITELIST=AAPL,MSFT,GOOGL,NVDA,SPY,QQQ
MAX_NOTIONAL_PER_TRADE=1000
MAX_OPEN_POSITIONS=3
RISK_CAP=0.03
VAR_LOOKBACK_DAYS=10
EOF
  echo "✍️  Created .env template — edit later to enable paper trading."
else
  echo "ℹ️  .env exists — ensuring risk keys..."
  grep -q '^SYMBOL_WHITELIST=' .env || echo 'SYMBOL_WHITELIST=AAPL,MSFT,GOOGL,NVDA,SPY,QQQ' >> .env
  grep -q '^MAX_NOTIONAL_PER_TRADE=' .env || echo 'MAX_NOTIONAL_PER_TRADE=1000' >> .env
  grep -q '^MAX_OPEN_POSITIONS=' .env || echo 'MAX_OPEN_POSITIONS=3' >> .env
  grep -q '^RISK_CAP=' .env || echo 'RISK_CAP=0.03' >> .env
  grep -q '^VAR_LOOKBACK_DAYS=' .env || echo 'VAR_LOOKBACK_DAYS=10' >> .env
fi

# 2) main.py (API: /, /dashboard, /api/alpaca_status, /api/toggle_mode, /api/signal, WS)
cat > main.py << 'EOF'
import os, json, time, asyncio, datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

BASE_DIR = Path(__file__).parent
RUNTIME = BASE_DIR / "runtime"
STATUS_FILE = RUNTIME / "alpaca_status.json"
SIGNALS_FILE = RUNTIME / "signals.jsonl"
ORDERS_FILE = RUNTIME / "orders.jsonl"

load_dotenv()
app = FastAPI(title="AI Money Web :: Phase 191–200 (Safe Executor)")

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

def write_signal(sig: dict):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS_FILE, "a") as f:
        f.write(json.dumps(sig) + "\n")

def read_orders(limit: int = 50):
    out = []
    if ORDERS_FILE.exists():
        with open(ORDERS_FILE) as f:
            for line in f:
                try: out.append(json.loads(line))
                except: pass
    return out[-limit:]

@app.get("/")
def root():
    s = read_status()
    return {"message":"✅ Phase 191–200 online", "mode": s.get("source","mock"), "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/dashboard")
def dashboard():
    return FileResponse(str(BASE_DIR / "static" / "dashboard.html"))

@app.get("/api/alpaca_status")
def alpaca_status():
    return JSONResponse(read_status())

@app.post("/api/toggle_mode")
def toggle_mode():
    env_path = BASE_DIR / ".env"
    text = env_path.read_text()
    if "PAPER_TRADE=1" in text:
        text = text.replace("PAPER_TRADE=1","PAPER_TRADE=0")
        mode = "mock"
    else:
        text = text.replace("PAPER_TRADE=0","PAPER_TRADE=1")
        mode = "paper"
    env_path.write_text(text)
    (RUNTIME / "toggle.flag").write_text(str(time.time()))
    return {"ok":True, "mode":mode}

@app.get("/api/orders")
def orders():
    return {"orders": read_orders(100)}

@app.post("/api/signal")
def signal(
    symbol: str = Body(..., embed=True),
    side: str = Body(..., embed=True),            # "buy" or "sell"
    notional: Optional[float] = Body(None, embed=True),
    qty: Optional[int] = Body(None, embed=True),
    tag: Optional[str] = Body(None, embed=True)
):
    sig = {
        "ts": time.time(),
        "symbol": symbol.upper(),
        "side": side.lower(),
        "notional": notional,
        "qty": qty,
        "tag": tag or "api",
        "source": "api"
    }
    write_signal(sig)
    return {"queued": True, "signal": sig}

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

# 3) Dashboard with Trade Widget
cat > static/dashboard.html << 'EOF'
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>AI Money Web :: 191–200</title>
  <style>
    body{background:#0b0c10;color:#eafdfc;font-family:system-ui,Arial;margin:0;padding:24px;text-align:center}
    .badge{display:inline-block;padding:6px 12px;border-radius:8px;margin:8px 0}
    .ok{background:#133;box-shadow:0 0 12px #0ff;color:#0ff}
    .err{background:#311;box-shadow:0 0 12px #f66;color:#f66}
    .btn{margin:10px;padding:8px 14px;border:1px solid #0ff;border-radius:8px;color:#0ff;background:transparent;cursor:pointer}
    #panel{width:900px;max-width:95vw;margin:24px auto;padding:16px;border-radius:16px;background:#111;border:1px solid #0ff;box-shadow:0 0 24px #0ff3;text-align:left}
    pre{white-space:pre-wrap;background:#091015;padding:12px;border-radius:10px;overflow:auto}
    input,select{background:#0a1118;border:1px solid #0ff;color:#bdf; padding:6px 10px;border-radius:8px}
    label{display:block;margin-top:8px}
    .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  </style>
</head>
<body>
  <h1>🚀 AI Money Web Autopilot (Phase 191–200)</h1>
  <div id="conn" class="badge err">❌ Disconnected</div>
  <div id="mode" class="badge ok">Mode: loading...</div>

  <div id="panel">
    <div class="row">
      <button class="btn" onclick="toggleMode()">Toggle Mode (mock ↔ paper)</button>
      <button class="btn" onclick="refresh()">Refresh Status</button>
    </div>

    <h3>Live Status</h3>
    <pre id="out">waiting...</pre>

    <h3>Send Test Order</h3>
    <div class="row">
      <label>Symbol <input id="sym" value="AAPL"/></label>
      <label>Side
        <select id="side">
          <option>buy</option>
          <option>sell</option>
        </select>
      </label>
      <label>Notional ($) <input id="notional" type="number" value="200"/></label>
      <button class="btn" onclick="sendOrder()">Send</button>
      <span id="resp" class="badge ok" style="display:none;"></span>
    </div>

    <h3>Recent Orders</h3>
    <pre id="orders">loading...</pre>
  </div>

<script>
const out = document.getElementById('out');
const ordersBox = document.getElementById('orders');
const modeEl = document.getElementById('mode');
const conn = document.getElementById('conn');
const resp = document.getElementById('resp');

async function refresh(){
  const r = await fetch('/api/alpaca_status'); const j = await r.json();
  out.textContent = JSON.stringify(j,null,2);
  modeEl.textContent = "Mode: " + (j.source || "unknown");
  const o = await (await fetch('/api/orders')).json();
  ordersBox.textContent = JSON.stringify(o,null,2);
}
async function toggleMode(){ await fetch('/api/toggle_mode',{method:'POST'}); setTimeout(refresh, 800); }
async function sendOrder(){
  const sym=document.getElementById('sym').value.trim();
  const side=document.getElementById('side').value;
  const notional=parseFloat(document.getElementById('notional').value||'0');
  const res = await fetch('/api/signal',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol:sym, side, notional})});
  const j = await res.json();
  resp.style.display='inline-block'; resp.textContent='Queued: '+JSON.stringify(j);
  setTimeout(refresh, 1000);
}
let ws;
function connectWS(){
  ws = new WebSocket('ws://127.0.0.1:8000/ws/alpaca_status');
  ws.onopen = () => { conn.textContent="🟢 Connected"; conn.className="badge ok"; };
  ws.onclose = () => { conn.textContent="❌ Disconnected"; conn.className="badge err"; setTimeout(connectWS, 1500); };
  ws.onmessage = (e) => {
    try{ const j = JSON.parse(e.data); out.textContent = JSON.stringify(j,null,2); modeEl.textContent = "Mode: " + (j.source || "unknown"); }catch(err){}
  };
}
connectWS(); refresh();
</script>
</body>
</html>
EOF

# 4) Risk and executor
cat > ai/risk.py << 'EOF'
import os, json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
ORDERS = RUNTIME / "orders.jsonl"

def load_env():
    return {
        "SYMBOL_WHITELIST": set(os.getenv("SYMBOL_WHITELIST","AAPL,MSFT,GOOGL,SPY").split(",")),
        "MAX_NOTIONAL_PER_TRADE": float(os.getenv("MAX_NOTIONAL_PER_TRADE","1000")),
        "MAX_OPEN_POSITIONS": int(os.getenv("MAX_OPEN_POSITIONS","3")),
        "RISK_CAP": float(os.getenv("RISK_CAP","0.03")),
        "VAR_LOOKBACK_DAYS": int(os.getenv("VAR_LOOKBACK_DAYS","10")),
    }

def approve(symbol:str, side:str, notional:float, open_positions:int) -> (bool,str):
    env = load_env()
    if symbol.upper() not in env["SYMBOL_WHITELIST"]:
        return False, f"symbol {symbol} not in whitelist"
    if notional <= 0:
        return False, "notional must be > 0"
    if notional > env["MAX_NOTIONAL_PER_TRADE"]:
        return False, f"notional exceeds MAX_NOTIONAL_PER_TRADE={env['MAX_NOTIONAL_PER_TRADE']}"
    if open_positions >= env["MAX_OPEN_POSITIONS"] and side.lower()=="buy":
        return False, f"open positions >= MAX_OPEN_POSITIONS={env['MAX_OPEN_POSITIONS']}"
    # Simple VaR guard: if recent drawdowns in orders exceed RISK_CAP, block buys
    try:
        if ORDERS.exists():
            rows = [json.loads(l) for l in ORDERS.read_text().strip().splitlines() if l.strip()]
            df = pd.DataFrame(rows)
            df = df.tail(env["VAR_LOOKBACK_DAYS"])
            if "pnl" in df.columns and len(df) >= 3:
                dd = df["pnl"].sum()
                if dd < 0 and abs(dd)/max(1.0, df.get("equity_before", pd.Series([1])).iloc[-1]) > env["RISK_CAP"]:
                    if side.lower()=="buy":
                        return False, f"blocked by VaR guard (dd={dd:.2f})"
    except Exception:
        pass
    return True, "ok"
EOF

cat > tools/order_executor.py << 'EOF'
import os, time, json, math
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict
from ai.risk import approve

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
SIGNALS = RUNTIME / "signals.jsonl"
ORDERS = RUNTIME / "orders.jsonl"
STATUS = RUNTIME / "alpaca_status.json"

load_dotenv(BASE / ".env")
PAPER = os.getenv("PAPER_TRADE","0") == "1"
ALPACA_BASE = os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets")
KEY = os.getenv("ALPACA_API_KEY_ID","")
SECRET = os.getenv("ALPACA_API_SECRET","")

def read_status()->Dict:
    try:
        if STATUS.exists():
            return json.loads(STATUS.read_text())
    except Exception: pass
    return {"equity":0,"cash":0,"status":"unknown","source":"mock"}

def append_order(obj:dict):
    with open(ORDERS, "a") as f:
        f.write(json.dumps(obj) + "\n")

def open_positions_count(api=None) -> int:
    if api is None: return 0
    try:
        pos = api.list_positions()
        return len(pos)
    except Exception:
        return 0

def get_last_price(api, symbol:str)->float:
    try:
        # Alpaca data v2 could be used; keep minimal for simplicity:
        quote = api.get_latest_trade(symbol)
        return float(getattr(quote, "price", 0) or getattr(quote, "p", 0) or 0)
    except Exception:
        return 0.0

def execute_mock(sig:dict):
    now = datetime.utcnow().isoformat()
    st = read_status()
    notional = sig.get("notional") or 0
    pnl = round((0.002 * (1 if sig["side"]=="buy" else -1)) * max(1, notional), 2)
    rec = {
        "ts": now, "symbol": sig["symbol"], "side": sig["side"],
        "mode": "mock", "status": "filled", "notional": notional,
        "qty": sig.get("qty"), "pnl": pnl, "equity_before": st.get("equity")
    }
    append_order(rec)

def execute_paper(sig:dict):
    from alpaca_trade_api.rest import REST, TimeInForce, OrderSide, AssetClass
    api = REST(KEY, SECRET, base_url=ALPACA_BASE)
    st = read_status()
    open_pos = open_positions_count(api)

    notional = float(sig.get("notional") or 0.0)
    symbol = sig["symbol"].upper()
    side = sig["side"].lower()

    ok, why = approve(symbol, side, notional, open_pos)
    if not ok:
        append_order({"ts":datetime.utcnow().isoformat(),"symbol":symbol,"side":side,"mode":"paper","status":"rejected","reason":why})
        return

    # compute qty if notional given (prefer notional orders for simplicity)
    qty = sig.get("qty")
    if notional and not qty:
        last = get_last_price(api, symbol) or 0
        if last > 0:
            qty = max(1, int(notional // last))
        else:
            qty = max(1, int(notional // 100))  # conservative fallback

    params = dict(symbol=symbol, side=side, type="market", time_in_force="day")
    if notional and hasattr(api, "submit_order"):
        params["notional"] = float(notional)
    else:
        params["qty"] = int(qty or 1)

    try:
        o = api.submit_order(**params)
        rec = {
            "ts": datetime.utcnow().isoformat(),
            "symbol": symbol, "side": side,
            "mode":"paper","status":"submitted",
            "id": getattr(o, "id", None), "notional": notional, "qty": params.get("qty"),
            "equity_before": st.get("equity")
        }
    except Exception as e:
        rec = {"ts": datetime.utcnow().isoformat(), "symbol":symbol, "side":side, "mode":"paper","status":"error","error":str(e)}
    append_order(rec)

def consume():
    """tail-like consumer that processes new signals and truncates the file to prevent growth."""
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if not SIGNALS.exists():
        SIGNALS.write_text("")

    while True:
        lines = []
        with open(SIGNALS) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                lines.append(line)

        if lines:
            # process then truncate
            SIGNALS.write_text("")
            for ln in lines:
                try:
                    sig = json.loads(ln)
                    if PAPER and KEY and SECRET:
                        execute_paper(sig)
                    else:
                        execute_mock(sig)
                except Exception as e:
                    append_order({"ts": datetime.utcnow().isoformat(), "mode":"executor", "status":"error", "error": str(e)})
        time.sleep(1.5)

if __name__ == "__main__":
    consume()
EOF

# 5) Restart backend, launch supervisor + executor
echo "🔪 Restarting backend..."
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &

echo "🤖 Starting telemetry supervisor (mock/paper based on .env)..."
# reuse existing supervisor if present, else create minimal fallback
if [ ! -f tools/trader_supervisor.py ]; then
cat > tools/trader_supervisor.py << 'EOF'
import os, time, json, random
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

def write(s): RUNTIME.mkdir(parents=True, exist_ok=True); STATUS_FILE.write_text(json.dumps(s, indent=2))

def mock_loop():
    equity=100000.0; cash=25000.0
    while True:
        equity += random.uniform(-15, 22)
        write({"status":"connected","equity":round(equity,2),"cash":round(cash,2),"buying_power":50000,"timestamp":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),"source":"mock"})
        time.sleep(2)

def alpaca_loop():
    from alpaca_trade_api.rest import REST
    api = REST(KEY, SECRET, base_url=ALPACA_BASE)
    while True:
        try:
            acct = api.get_account()
            write({"status":"connected","equity":float(getattr(acct,"equity",0)),"cash":float(getattr(acct,"cash",0)),"buying_power":float(getattr(acct,"buying_power",0)),"timestamp":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),"source":"paper"})
        except Exception as e:
            write({"status":"error","error":str(e),"source":"paper"})
        time.sleep(3)

def main():
    while True:
        PAPER = os.getenv("PAPER_TRADE","0") == "1"
        if PAPER and KEY and SECRET: alpaca_loop()
        else: mock_loop()

if __name__=="__main__": main()
EOF
fi

nohup venv/bin/python3 tools/trader_supervisor.py > logs/trader.log 2>&1 &

echo "🛠  Starting order executor..."
nohup venv/bin/python3 tools/order_executor.py > logs/executor.log 2>&1 &

sleep 5
if curl -s http://127.0.0.1:8000/ | grep -q "Phase 191–200"; then
  echo "✅ Backend healthy — opening dashboard..."
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend not responding. Check logs/backend.log"
  head -n 60 logs/backend.log || true
fi

echo "🎯 Phase 191–200 ready."
echo "📄 Logs -> logs/backend.log | logs/trader.log | logs/executor.log"

