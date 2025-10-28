#!/usr/bin/env bash
set -e

echo "⚙️  NeoLight :: Phase 541–560 (AI Decision Engine + Sim Trader & PnL)"

mkdir -p backend templates static ai/strategies tools runtime logs

# ----- Python env (optional) -----
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install fastapi uvicorn pandas requests --quiet

# ----- Runtime seeds -----
cat > runtime/live_mode.json <<'JSON' 
{"live": false}
JSON

cat > runtime/auto_mode.json <<'JSON'
{"auto_trade": false, "symbol": "AAPL", "qty": 1}
JSON

cat > runtime/portfolio.json <<'JSON'
{
  "cash": 100000.0,
  "equity": 100000.0,
  "positions": {},
  "trades": []
}
JSON

touch runtime/signals.jsonl

# ----- Strategies -----
cat > ai/strategies/momentum.py <<'PY'
DEFAULT_CONFIG = {"lookback": 10, "threshold": 0.002}

def generate_signal(history, cfg=DEFAULT_CONFIG):
    # history: list of dicts with 'close'
    n = cfg.get("lookback", 10)
    if len(history) < n+1: 
        return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough_data"}}
    c0 = history[-1]["close"]
    cN = history[-1-n]["close"]
    ret = (c0 - cN) / cN
    if ret > cfg.get("threshold",0.002):
        return {"signal":"BUY","confidence":min(0.5+ret*50,0.99),"meta":{"ret":ret}}
    if ret < -cfg.get("threshold",0.002):
        return {"signal":"SELL","confidence":min(0.5+abs(ret)*50,0.99),"meta":{"ret":ret}}
    return {"signal":"HOLD","confidence":0.55,"meta":{"ret":ret}}
PY

cat > ai/strategies/crossover.py <<'PY'
DEFAULT_CONFIG = {"fast": 5, "slow": 20}

def sma(series, n):
    if len(series) < n: return None
    return sum(x["close"] for x in series[-n:]) / n

def generate_signal(history, cfg=DEFAULT_CONFIG):
    f = cfg.get("fast",5); s = cfg.get("slow",20)
    if len(history) < s+1: 
        return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough_data"}}
    fast_prev = sum(x["close"] for x in history[-(f+1):-1]) / f
    slow_prev = sum(x["close"] for x in history[-(s+1):-1]) / s
    fast_now  = sma(history, f)
    slow_now  = sma(history, s)
    if fast_prev <= slow_prev and fast_now > slow_now:
        return {"signal":"BUY","confidence":0.8,"meta":{"fast":fast_now,"slow":slow_now}}
    if fast_prev >= slow_prev and fast_now < slow_now:
        return {"signal":"SELL","confidence":0.8,"meta":{"fast":fast_now,"slow":slow_now}}
    return {"signal":"HOLD","confidence":0.55,"meta":{"fast":fast_now,"slow":slow_now}}
PY

cat > ai/strategies/mean_reversion.py <<'PY'
DEFAULT_CONFIG = {"window": 20, "z_entry": 1.0}

def mean(vals): return sum(vals)/len(vals)

def generate_signal(history, cfg=DEFAULT_CONFIG):
    w = cfg.get("window",20)
    if len(history) < w: 
        return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough_data"}}
    closes = [x["close"] for x in history[-w:]]
    m = mean(closes)
    devs = [(c-m)**2 for c in closes]
    std = (sum(devs)/len(devs)) ** 0.5 if devs else 0.0
    z = 0 if std==0 else (history[-1]["close"] - m)/std
    if z > cfg.get("z_entry",1.0):
        return {"signal":"SELL","confidence":min(0.6+abs(z)/3,0.95),"meta":{"z":z,"mean":m}}
    if z < -cfg.get("z_entry",1.0):
        return {"signal":"BUY","confidence":min(0.6+abs(z)/3,0.95),"meta":{"z":z,"mean":m}}
    return {"signal":"HOLD","confidence":0.5,"meta":{"z":z,"mean":m}}
PY

# ----- Strategy Daemon (decision + sim trading) -----
cat > tools/strategy_daemon.py <<'PY'
import os, json, time, requests, datetime, traceback
from pathlib import Path
from importlib import import_module

BASE = "http://127.0.0.1:8000"  # backend API
RUNTIME = Path("runtime")
SIGNALS = RUNTIME/"signals.jsonl"
PORTFOLIO = RUNTIME/"portfolio.json"
AUTO = RUNTIME/"auto_mode.json"

STRATS = [
    ("momentum", "ai.strategies.momentum"),
    ("crossover", "ai.strategies.crossover"),
    ("mean_reversion", "ai.strategies.mean_reversion"),
]

def read_json(p, default):
    try:
        with open(p,"r") as f: return json.load(f)
    except Exception: return default

def write_json(p, obj):
    with open(p,"w") as f: json.dump(obj,f,indent=2)

def append_signal(entry):
    with open(SIGNALS,"a") as f: f.write(json.dumps(entry)+"\n")

def get_history(symbol="AAPL", limit=120):
    r = requests.get(f"{BASE}/api/ohlc", params={"symbol":symbol,"limit":limit}, timeout=10)
    r.raise_for_status()
    return r.json()

def mark_to_market(portfolio, price):
    equity = portfolio["cash"]
    for sym, pos in portfolio["positions"].items():
        equity += pos.get("qty",0)*price
    portfolio["equity"] = round(equity,2)
    return portfolio

def execute_trade(portfolio, symbol, side, qty, price):
    qty = int(qty)
    if qty <= 0: return portfolio
    if side == "BUY":
        cost = qty*price
        if portfolio["cash"] < cost: 
            qty = int(portfolio["cash"]//price)
            if qty<=0: return portfolio
            cost = qty*price
        portfolio["cash"] -= cost
        pos = portfolio["positions"].get(symbol, {"qty":0,"avg_price":0.0})
        total_cost = pos["qty"]*pos["avg_price"] + cost
        pos["qty"] += qty
        pos["avg_price"] = 0.0 if pos["qty"]==0 else total_cost/pos["qty"]
        portfolio["positions"][symbol] = pos
    elif side == "SELL":
        pos = portfolio["positions"].get(symbol, {"qty":0,"avg_price":0.0})
        sell_qty = min(qty, pos["qty"])
        if sell_qty<=0: return portfolio
        proceeds = sell_qty*price
        portfolio["cash"] += proceeds
        pos["qty"] -= sell_qty
        if pos["qty"]==0: portfolio["positions"].pop(symbol,None)
        else: portfolio["positions"][symbol] = pos
    trade = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "symbol": symbol, "side": side, "qty": qty, "price": round(price,2)
    }
    portfolio["trades"].append(trade)
    return portfolio

def decide_and_trade():
    auto = read_json(AUTO, {"auto_trade": False, "symbol":"AAPL","qty":1})
    symbol = auto.get("symbol","AAPL")
    qty = int(auto.get("qty",1))

    hist = get_history(symbol=symbol, limit=120)
    if not isinstance(hist,list) or len(hist)==0: return

    price = hist[-1]["close"]
    decisions = []
    for name, modpath in STRATS:
        mod = import_module(modpath)
        res = mod.generate_signal(hist, getattr(mod,"DEFAULT_CONFIG",{}))
        decision = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "strategy": name,
            "symbol": symbol,
            "signal": res.get("signal","HOLD"),
            "confidence": float(res.get("confidence",0.5)),
            "price": float(price),
            "meta": res.get("meta",{})
        }
        decisions.append(decision)
        append_signal(decision)

    # Simple ensemble rule: if 2+ say BUY → BUY; if 2+ say SELL → SELL; else HOLD
    votes = {"BUY":0,"SELL":0,"HOLD":0}
    for d in decisions: votes[d["signal"]] = votes.get(d["signal"],0)+1
    final = "HOLD"
    if votes["BUY"]>=2: final="BUY"
    if votes["SELL"]>=2: final="SELL"

    # Auto-trade simulation
    if auto.get("auto_trade", False) and final in ("BUY","SELL"):
        pf = read_json(PORTFOLIO, {"cash":100000,"equity":100000,"positions":{},"trades":[]})
        pf = execute_trade(pf, symbol, final, qty, price)
        pf = mark_to_market(pf, price)
        write_json(PORTFOLIO, pf)
    else:
        # still MTM portfolio with latest price
        pf = read_json(PORTFOLIO, {"cash":100000,"equity":100000,"positions":{},"trades":[]})
        pf = mark_to_market(pf, price)
        write_json(PORTFOLIO, pf)

if __name__ == "__main__":
    print("🧠 Strategy Daemon running... (CTRL+C to stop)")
    while True:
        try:
            decide_and_trade()
        except Exception as e:
            print("Daemon error:", e)
            traceback.print_exc()
        time.sleep(5)  # every 5s; adjust to 60s for real markets
PY

chmod +x tools/strategy_daemon.py

# ----- Backend with new endpoints (/api/pnl, /api/auto-mode) -----
cat > backend/main.py <<'PY'
import os, json, datetime, random
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AI Money Web :: NeoLight v3.5")
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNTIME = "runtime"
LIVE_FILE = os.path.join(RUNTIME,"live_mode.json")
AUTO_FILE = os.path.join(RUNTIME,"auto_mode.json")
SIGNALS_FILE = os.path.join(RUNTIME,"signals.jsonl")
PORTFOLIO_FILE = os.path.join(RUNTIME,"portfolio.json")

def jread(path, default):
    try:
        with open(path,"r") as f: return json.load(f)
    except Exception:
        return default

def jwrite(path, obj):
    with open(path,"w") as f: json.dump(obj,f,indent=2)

# ---------- Dashboard ----------
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("templates/dashboard.html","r",encoding="utf-8") as f: 
        return f.read()

# ---------- Mode toggles ----------
@app.get("/api/live-toggle")
def get_live():
    return jread(LIVE_FILE, {"live": False})

@app.post("/api/live-toggle")
def set_live(payload: dict):
    live = bool(payload.get("live", False))
    jwrite(LIVE_FILE, {"live": live})
    return {"status":"updated","live":live}

@app.get("/api/auto-mode")
def get_auto():
    return jread(AUTO_FILE, {"auto_trade": False, "symbol":"AAPL","qty":1})

@app.post("/api/auto-mode")
def set_auto(payload: dict):
    auto = jread(AUTO_FILE, {"auto_trade": False, "symbol":"AAPL","qty":1})
    auto.update({
        "auto_trade": bool(payload.get("auto_trade", auto["auto_trade"])),
        "symbol": payload.get("symbol", auto["symbol"]),
        "qty": int(payload.get("qty", auto["qty"]))
    })
    jwrite(AUTO_FILE, auto)
    return {"status":"updated","auto":auto}

# ---------- OHLC (SIM only if no keys; keeps same interface) ----------
@app.get("/api/ohlc")
def api_ohlc(symbol: str="AAPL", limit: int=120):
    live = jread(LIVE_FILE, {"live":False})["live"]
    # In this phase we use SIM regardless; keep live path for future
    # SIM generator
    import math
    series = []
    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    price = 150.0
    for i in range(limit):
        ts = now - datetime.timedelta(minutes=(limit-1-i))
        drift = math.sin(i/10.0)*0.6
        o = price + random.uniform(-0.8,0.8) + drift
        h = o + random.uniform(0.0,1.2)
        l = o - random.uniform(0.0,1.2)
        c = random.uniform(l,h)
        v = random.randint(1000,9000)
        series.append({"t": ts.isoformat(), "open": round(o,2), "high": round(h,2), "low": round(l,2), "close": round(c,2), "volume": v})
        price = c
    return series

# ---------- Strategy logs ----------
@app.get("/api/strategy-log")
def strategy_log():
    if not os.path.exists(SIGNALS_FILE): return []
    out=[]
    with open(SIGNALS_FILE,"r") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out[-300:]

# ---------- PnL & portfolio ----------
@app.get("/api/pnl")
def pnl():
    pf = jread(PORTFOLIO_FILE, {"cash":100000,"equity":100000,"positions":{},"trades":[]})
    # compute realized PnL approximations
    wins = 0; losses = 0
    for t in pf.get("trades",[]):
        # simple count-based heuristic; real calc in later phase
        if t["side"]=="SELL": 
            wins += 1
        else:
            losses += 0
    return pf | {"win_trades": wins, "loss_trades": losses}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
PY

# ----- Dashboard HTML -----
cat > templates/dashboard.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>NeoLight v3.5 :: AI Decisions + PnL</title>
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>💡 AI Money Web :: NeoLight v3.5</h1>

  <section class="panel">
    <div class="row">
      <strong>Data Mode:</strong>
      <label class="switch">
        <input type="checkbox" id="modeToggle"/>
        <span class="slider round"></span>
      </label>
      <span id="modeStatus" class="badge">Loading...</span>

      <strong style="margin-left:2rem;">Auto Trade:</strong>
      <label class="switch">
        <input type="checkbox" id="autoToggle"/>
        <span class="slider round"></span>
      </label>
      <span id="autoStatus" class="badge">Off</span>
      <span class="tiny">Qty</span>
      <input id="qty" class="qty" type="number" min="1" value="1"/>
    </div>
  </section>

  <section class="panel">
    <h3>📈 AAPL — Close Prices</h3>
    <canvas id="chart" height="120"></canvas>
  </section>

  <section class="panel split">
    <div>
      <h3>🧠 Strategy Logs</h3>
      <pre id="logs">Loading...</pre>
    </div>
    <div>
      <h3>💹 Performance</h3>
      <div id="perf" class="perf">
        <div>Cash: <span id="cash">-</span></div>
        <div>Equity: <span id="equity">-</span></div>
        <div>Positions: <span id="positions">-</span></div>
        <div>Trades: <span id="trades">-</span></div>
        <div>Wins: <span id="wins">-</span></div>
      </div>
    </div>
  </section>

  <script src="/static/dashboard.js"></script>
</body>
</html>
HTML

# ----- Styles -----
cat > static/style.css <<'CSS'
:root { --neon:#00ffff; --bg:#000; --ink:#e8ffff; --panel:#0b0b0b; }
*{box-sizing:border-box}
body{margin:0;padding:2rem;background:var(--bg);color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace}
h1{color:var(--neon);margin-top:0}
.panel{background:var(--panel);border:1px solid #112;border-radius:10px;padding:1rem;margin-bottom:1rem}
.row{display:flex;align-items:center;gap:1rem}
.badge{color:var(--neon)}
pre#logs{background:#050505;border:1px solid #112;padding:1rem;border-radius:10px;max-height:320px;overflow:auto;white-space:pre-wrap}
.split{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.perf div{margin:0.25rem 0}
.qty{width:70px;background:#020202;color:#ddd;border:1px solid #233;border-radius:6px;padding:4px}

/* switch */
.switch{position:relative;display:inline-block;width:60px;height:34px}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:#333;transition:.4s}
.slider:before{position:absolute;content:"";height:26px;width:26px;left:4px;bottom:4px;background:white;transition:.4s}
input:checked + .slider{background-color:var(--neon)}
input:checked + .slider:before{transform:translateX(26px)}
.slider.round{border-radius:34px}.slider.round:before{border-radius:50%}
CSS

# ----- Dashboard JS -----
cat > static/dashboard.js <<'JS'
let chart;

async function getJSON(url, params){
  const q = params ? '?' + new URLSearchParams(params) : '';
  const r = await fetch(url+q);
  return r.json();
}
async function postJSON(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  return r.json();
}

async function loadOHLC(){
  return getJSON('/api/ohlc', {symbol:'AAPL', limit:120});
}
async function loadLogs(){
  return getJSON('/api/strategy-log');
}
async function loadPnL(){
  return getJSON('/api/pnl');
}
async function loadLive(){ return getJSON('/api/live-toggle'); }
async function saveLive(live){ return postJSON('/api/live-toggle', {live}); }

async function loadAuto(){ return getJSON('/api/auto-mode'); }
async function saveAuto(auto_trade, qty){
  return postJSON('/api/auto-mode', {auto_trade, qty});
}

function renderChart(labels, closes){
  const ctx = document.getElementById('chart').getContext('2d');
  if (chart){
    chart.data.labels = labels;
    chart.data.datasets[0].data = closes;
    chart.update();
    return;
  }
  chart = new Chart(ctx, {
    type:'line',
    data:{
      labels,
      datasets:[{label:'Close', data:closes, borderColor:'#00ffff', tension:0.3}]
    },
    options:{
      plugins:{legend:{labels:{color:'#00ffff'}}},
      scales:{x:{ticks:{color:'#00ffff'}}, y:{ticks:{color:'#00ffff'}}}
    }
  });
}

async function refreshChart(){
  const d = await loadOHLC();
  const labels = d.map(x => (x.t||'').slice(11,16));
  const closes = d.map(x => x.close);
  renderChart(labels, closes);
}

async function refreshLogs(){
  const logs = await loadLogs();
  const pre = document.getElementById('logs');
  pre.textContent = logs.length ? logs.map(l => JSON.stringify(l)).join('\n') : 'No strategy logs yet.';
}

async function refreshPnL(){
  const p = await loadPnL();
  document.getElementById('cash').textContent = '$' + (p.cash??0).toFixed(2);
  document.getElementById('equity').textContent = '$' + (p.equity??0).toFixed(2);
  document.getElementById('positions').textContent = Object.keys(p.positions||{}).length;
  document.getElementById('trades').textContent = (p.trades||[]).length;
  document.getElementById('wins').textContent = p.win_trades??0;
}

async function initToggles(){
  const mode = await loadLive();
  const auto = await loadAuto();

  const modeToggle = document.getElementById('modeToggle');
  const modeStatus = document.getElementById('modeStatus');
  modeToggle.checked = !!mode.live;
  modeStatus.textContent = modeToggle.checked ? 'LIVE Mode' : 'SIM Mode';
  modeToggle.addEventListener('change', async () => {
    await saveLive(modeToggle.checked);
    modeStatus.textContent = modeToggle.checked ? 'LIVE Mode' : 'SIM Mode';
  });

  const autoToggle = document.getElementById('autoToggle');
  const autoStatus = document.getElementById('autoStatus');
  const qtyInput = document.getElementById('qty');
  autoToggle.checked = !!auto.auto_trade;
  qtyInput.value = auto.qty ?? 1;
  autoStatus.textContent = autoToggle.checked ? 'On' : 'Off';
  const persist = async () => {
    await saveAuto(autoToggle.checked, parseInt(qtyInput.value||'1',10));
    autoStatus.textContent = autoToggle.checked ? 'On' : 'Off';
  };
  autoToggle.addEventListener('change', persist);
  qtyInput.addEventListener('change', persist);
}

async function main(){
  await initToggles();
  await refreshChart();
  await refreshLogs();
  await refreshPnL();
  setInterval(refreshChart, 5000);
  setInterval(refreshLogs, 5000);
  setInterval(refreshPnL, 4000);
}
document.addEventListener('DOMContentLoaded', main);
JS

# ----- Hints file -----
cat > RUN_PHASE_541_560.txt <<'TXT'
Run server:
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

Run strategy daemon (AI decisions + sim trades):
  nohup python tools/strategy_daemon.py &

Open dashboard:
  http://localhost:8000/dashboard

Permission denied running scripts?
  chmod +x phase_541_560_ai_pnl.sh
  # or:
  chmod +x tools/strategy_daemon.py

Stop processes (Mac/Linux):
  pkill -f "uvicorn backend.main:app"
  pkill -f "tools/strategy_daemon.py"
TXT

echo "✅ Files written."
echo "👉 Start FastAPI:"
echo "   nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &"
echo "👉 Start Strategy Daemon:"
echo "   nohup python tools/strategy_daemon.py &"
echo "👉 Dashboard: http://localhost:8000/dashboard"
