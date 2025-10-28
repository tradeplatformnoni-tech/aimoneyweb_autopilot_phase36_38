#!/usr/bin/env bash
# phase_561_580_compare_opt_launcher.sh
set -e

# 1) Write the actual phase script
cat > phase_561_580_compare_opt.sh <<'BASH'
#!/usr/bin/env bash
set -e

echo "🧭 NeoLight :: Phase 561–580 (Strategy Comparison + AI Optimizer)"

mkdir -p backend templates static ai/strategies tools runtime logs

# --- Ensure venv (optional) ---
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install fastapi uvicorn pandas requests --quiet

# --- Runtime seeds ---
[ -f runtime/strategy_overrides.json ] || echo '{}' > runtime/strategy_overrides.json
[ -f runtime/optimizer.json ] || echo '{"status":"idle","last_best":{}}' > runtime/optimizer.json
[ -f runtime/live_mode.json ] || echo '{"live": false}' > runtime/live_mode.json
[ -f runtime/auto_mode.json ] || echo '{"auto_trade": false, "symbol": "AAPL", "qty": 1}' > runtime/auto_mode.json
[ -f runtime/portfolio.json ] || cat > runtime/portfolio.json <<'JSON'
{"cash":100000.0,"equity":100000.0,"positions":{},"trades":[]}
JSON
touch runtime/signals.jsonl

# --- Patch strategy daemon to read overrides (idempotent) ---
cat > tools/strategy_daemon.py <<'PY'
import os, json, time, requests, datetime, traceback
from pathlib import Path
from importlib import import_module

BASE = "http://127.0.0.1:8000"  # backend API
RUNTIME = Path("runtime")
SIGNALS = RUNTIME/"signals.jsonl"
PORTFOLIO = RUNTIME/"portfolio.json"
AUTO = RUNTIME/"auto_mode.json"
OVERRIDES_FILE = RUNTIME/"strategy_overrides.json"

STRATS = [
    ("momentum", "ai.strategies.momentum"),
    ("crossover", "ai.strategies.crossover"),
    ("mean_reversion", "ai.strategies.mean_reversion"),
]

def rjson(p, default): 
    try:
        with open(p,"r") as f: return json.load(f)
    except: return default

def wjson(p, obj):
    with open(p,"w") as f: json.dump(obj,f,indent=2)

def append_signal(entry):
    with open(SIGNALS,"a") as f: f.write(json.dumps(entry)+"\n")

def get_history(symbol="AAPL", limit=180):
    r = requests.get(f"{BASE}/api/ohlc", params={"symbol":symbol,"limit":limit}, timeout=15)
    r.raise_for_status()
    return r.json()

def mark_to_market(portfolio, price):
    equity = portfolio["cash"]
    for sym, pos in portfolio.get("positions",{}).items():
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
    trade = {"ts": datetime.datetime.utcnow().isoformat(),
             "symbol": symbol, "side": side, "qty": qty, "price": round(price,2)}
    portfolio.setdefault("trades", []).append(trade)
    return portfolio

def decide_and_trade():
    auto = rjson(AUTO, {"auto_trade": False, "symbol":"AAPL","qty":1})
    symbol = auto.get("symbol","AAPL")
    qty = int(auto.get("qty",1))

    hist = get_history(symbol=symbol, limit=180)
    if not isinstance(hist,list) or len(hist)==0: return

    price = hist[-1]["close"]
    overrides = rjson(OVERRIDES_FILE, {})

    decisions = []
    for name, modpath in STRATS:
        mod = import_module(modpath)
        base_cfg = getattr(mod,"DEFAULT_CONFIG",{})
        merged = {**base_cfg, **overrides.get(name, {})}
        res = mod.generate_signal(hist, merged)
        decisions.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "strategy": name,
            "symbol": symbol,
            "signal": res.get("signal","HOLD"),
            "confidence": float(res.get("confidence",0.5)),
            "price": float(price),
            "config": merged,
            "meta": res.get("meta",{})
        })

    # append all strategy decisions to log
    for d in decisions: append_signal(d)

    # ensemble vote
    votes = {"BUY":0,"SELL":0,"HOLD":0}
    for d in decisions: votes[d["signal"]] = votes.get(d["signal"],0)+1
    final = "HOLD"
    if votes["BUY"]>=2: final="BUY"
    if votes["SELL"]>=2: final="SELL"

    pf = rjson(PORTFOLIO, {"cash":100000,"equity":100000,"positions":{},"trades":[]})
    if auto.get("auto_trade", False) and final in ("BUY","SELL"):
        pf = execute_trade(pf, symbol, final, qty, price)
    pf = mark_to_market(pf, price)
    wjson(PORTFOLIO, pf)

if __name__ == "__main__":
    print("🧠 Strategy Daemon (overrides-aware) running... (CTRL+C to stop)")
    while True:
        try:
            decide_and_trade()
        except Exception as e:
            print("Daemon error:", e)
            traceback.print_exc()
        time.sleep(5)
PY
chmod +x tools/strategy_daemon.py

# --- Optimizer (simple param sweep) ---
cat > tools/optimizer.py <<'PY'
import os, json, time, itertools, datetime, requests, traceback
from pathlib import Path
from importlib import import_module

BASE = "http://127.0.0.1:8000"
RUNTIME = Path("runtime")
STATUS_FILE = RUNTIME/"optimizer.json"
OVERRIDES_FILE = RUNTIME/"strategy_overrides.json"

STRATEGIES = {
    "momentum": ("ai.strategies.momentum", {"lookback":[8,10,12,14], "threshold":[0.001,0.002,0.003]}),
    "crossover": ("ai.strategies.crossover", {"fast":[4,5,8], "slow":[18,20,30]}),
    "mean_reversion": ("ai.strategies.mean_reversion", {"window":[15,20,25], "z_entry":[0.8,1.0,1.2]})
}

def get_ohlc(symbol="AAPL", limit=360):
    r = requests.get(f"{BASE}/api/ohlc", params={"symbol":symbol,"limit":limit}, timeout=20)
    r.raise_for_status()
    return r.json()

def backtest(strategy_module, params, history):
    # simple: enter full position on BUY, flat on HOLD, short on SELL (simulated)
    pos = 0   # -1 short, 0 flat, 1 long
    pnl = 0.0
    last_px = history[0]["close"]
    for i in range(1, len(history)):
        h = history[:i+1]
        sig = strategy_module.generate_signal(h, params).get("signal","HOLD")
        price = history[i]["close"]
        # PnL update from position
        pnl += pos * (price - last_px)
        # Position update
        if sig == "BUY": pos = 1
        elif sig == "SELL": pos = -1
        else: pass
        last_px = price
    return pnl

def run_optimizer():
    symbol = "AAPL"
    hist = get_ohlc(symbol=symbol, limit=360)
    status = {"status":"running","started":datetime.datetime.utcnow().isoformat(),
              "progress":{}, "best":{}}
    with open(STATUS_FILE,"w") as f: json.dump(status,f,indent=2)

    best_overrides = {}
    for name, (modpath, grid) in STRATEGIES.items():
        try:
            mod = import_module(modpath)
            keys = list(grid.keys())
            best = {"score": float("-inf"), "params": None}
            combos = list(itertools.product(*[grid[k] for k in keys]))
            for idx, combo in enumerate(combos, start=1):
                params = dict(zip(keys, combo))
                score = backtest(mod, params, hist)
                if score > best["score"]:
                    best = {"score": score, "params": params}
                status["progress"][name] = {"tested": idx, "total": len(combos), "best": best}
                with open(STATUS_FILE,"w") as f: json.dump(status,f,indent=2)
            best_overrides[name] = best["params"]
        except Exception as e:
            status["progress"][name] = {"error": str(e)}
            with open(STATUS_FILE,"w") as f: json.dump(status,f,indent=2)

    status["status"] = "complete"
    status["completed"] = datetime.datetime.utcnow().isoformat()
    status["best"] = best_overrides
    with open(STATUS_FILE,"w") as f: json.dump(status,f,indent=2)

    # persist overrides for daemon
    cur = {}
    if OVERRIDES_FILE.exists():
        try: cur = json.load(open(OVERRIDES_FILE,"r"))
        except: cur = {}
    cur.update(best_overrides)
    json.dump(cur, open(OVERRIDES_FILE,"w"), indent=2)

if __name__ == "__main__":
    try:
        run_optimizer()
    except Exception as e:
        st = {"status":"error","error":str(e)}
        json.dump(st, open(STATUS_FILE,"w"), indent=2)
        traceback.print_exc()
PY
chmod +x tools/optimizer.py

# --- Backend: add /api/compare and /api/optimizer endpoints & keep prior routes ---
cat > backend/main.py <<'PY'
import os, json, datetime, random, math, subprocess, sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from importlib import import_module

app = FastAPI(title="AI Money Web :: NeoLight v3.6")
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNTIME = "runtime"
LIVE_FILE = os.path.join(RUNTIME,"live_mode.json")
AUTO_FILE = os.path.join(RUNTIME,"auto_mode.json")
SIGNALS_FILE = os.path.join(RUNTIME,"signals.jsonl")
PORTFOLIO_FILE = os.path.join(RUNTIME,"portfolio.json")
OPT_FILE = os.path.join(RUNTIME,"optimizer.json")

def jread(path, default): 
    try: return json.load(open(path,"r"))
    except: return default
def jwrite(path, obj): 
    json.dump(obj, open(path,"w"), indent=2)

# --------- Dashboard ----------
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return open("templates/dashboard.html","r",encoding="utf-8").read()

# --------- SIM OHLC (we stay SIM-friendly) ----------
@app.get("/api/ohlc")
def api_ohlc(symbol: str="AAPL", limit: int=240):
    series = []
    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    price = 150.0
    for i in range(limit):
        ts = now - datetime.timedelta(minutes=(limit-1-i))
        drift = math.sin(i/12.0)*0.8
        o = price + random.uniform(-0.8,0.8) + drift
        h = o + random.uniform(0.0,1.2)
        l = o - random.uniform(0.0,1.2)
        c = random.uniform(l,h)
        v = random.randint(1000,9000)
        series.append({"t": ts.isoformat(), "open": round(o,2), "high": round(h,2), "low": round(l,2), "close": round(c,2), "volume": v})
        price = c
    return series

# --------- Modes ----------
@app.get("/api/live-toggle")
def get_live(): return jread(LIVE_FILE, {"live": False})
@app.post("/api/live-toggle")
def set_live(payload: dict):
    live = bool(payload.get("live", False))
    jwrite(LIVE_FILE, {"live": live})
    return {"status":"updated","live":live}

@app.get("/api/auto-mode")
def get_auto(): return jread(AUTO_FILE, {"auto_trade": False, "symbol":"AAPL","qty":1})
@app.post("/api/auto-mode")
def set_auto(payload: dict):
    auto = get_auto()
    auto.update({
        "auto_trade": bool(payload.get("auto_trade", auto["auto_trade"])),
        "symbol": payload.get("symbol", auto["symbol"]),
        "qty": int(payload.get("qty", auto["qty"]))
    })
    jwrite(AUTO_FILE, auto)
    return {"status":"updated","auto":auto}

# --------- Logs / PnL ----------
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
    return out[-500:]

@app.get("/api/pnl")
def pnl():
    pf = jread(PORTFOLIO_FILE, {"cash":100000,"equity":100000,"positions":{},"trades":[]})
    wins = sum(1 for t in pf.get("trades",[]) if t.get("side")=="SELL")
    return pf | {"win_trades": wins}

# --------- Strategy Comparison ----------
@app.get("/api/compare")
def api_compare(symbol: str="AAPL", limit: int=300):
    # compute per-strategy cumulative returns by walking OHLC and re-running strategies
    from ai.strategies import momentum, crossover, mean_reversion
    history = api_ohlc(symbol=symbol, limit=limit)
    strategies = {
        "momentum": (momentum, getattr(momentum,"DEFAULT_CONFIG",{})),
        "crossover": (crossover, getattr(crossover,"DEFAULT_CONFIG",{})),
        "mean_reversion": (mean_reversion, getattr(mean_reversion,"DEFAULT_CONFIG",{}))
    }
    results = {}
    for name, (mod, cfg) in strategies.items():
        pnl = 0.0; pos = 0; last = history[0]["close"]
        curve = [0.0]
        for i in range(1, len(history)):
            h = history[:i+1]
            sig = mod.generate_signal(h, cfg).get("signal","HOLD")
            px = history[i]["close"]
            pnl += pos * (px - last)
            if sig == "BUY": pos = 1
            elif sig == "SELL": pos = -1
            last = px
            curve.append(round(pnl,2))
        results[name] = curve
    labels = [h["t"][11:16] for h in history]
    return {"labels": labels, "curves": results}

# --------- Optimizer Control ----------
@app.post("/api/optimizer/start")
def opt_start():
    if jread(OPT_FILE, {"status":"idle"}).get("status") == "running":
        return {"status":"running"}
    # start as detached subprocess
    if sys.platform.startswith("win"):
        subprocess.Popen([sys.executable, "tools/optimizer.py"], creationflags=0x00000008)
    else:
        subprocess.Popen([sys.executable, "tools/optimizer.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"status":"started"}

@app.get("/api/optimizer/status")
def opt_status():
    return jread(OPT_FILE, {"status":"idle"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
PY

# --- Dashboard (adds Compare + Optimizer UI) ---
cat > templates/dashboard.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>NeoLight v3.6 :: Compare + Optimizer</title>
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>💡 AI Money Web :: NeoLight v3.6</h1>

  <section class="panel">
    <div class="row">
      <strong>Data Mode:</strong>
      <label class="switch"><input type="checkbox" id="modeToggle"/><span class="slider round"></span></label>
      <span id="modeStatus" class="badge">Loading...</span>

      <strong style="margin-left:2rem;">Auto Trade:</strong>
      <label class="switch"><input type="checkbox" id="autoToggle"/><span class="slider round"></span></label>
      <span id="autoStatus" class="badge">Off</span>
      <span class="tiny">Qty</span><input id="qty" class="qty" type="number" min="1" value="1"/>
    </div>
  </section>

  <section class="panel">
    <h3>📈 AAPL — Close Prices</h3>
    <canvas id="chart" height="110"></canvas>
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

  <section class="panel">
    <h3>📊 Strategy Comparison</h3>
    <canvas id="compare" height="120"></canvas>
  </section>

  <section class="panel">
    <h3>🧬 AI Optimizer</h3>
    <div class="row">
      <button id="optStart">Start Optimizer</button>
      <span id="optStatus" class="badge">idle</span>
    </div>
    <pre id="optBest">{}</pre>
  </section>

  <script src="/static/dashboard.js"></script>
</body>
</html>
HTML

# --- Styles (append minor extras if not present) ---
cat > static/style.css <<'CSS'
:root { --neon:#00ffff; --bg:#000; --ink:#e8ffff; --panel:#0b0b0b; }
*{box-sizing:border-box}
body{margin:0;padding:2rem;background:var(--bg);color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace}
h1{color:var(--neon);margin-top:0}
.panel{background:var(--panel);border:1px solid #112;border-radius:10px;padding:1rem;margin-bottom:1rem}
.row{display:flex;align-items:center;gap:1rem}
.badge{color:var(--neon)}
pre#logs, pre#optBest{background:#050505;border:1px solid #112;padding:1rem;border-radius:10px;max-height:320px;overflow:auto;white-space:pre-wrap}
.split{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.perf div{margin:0.25rem 0}
.qty{width:70px;background:#020202;color:#ddd;border:1px solid #233;border-radius:6px;padding:4px}
button{background:#031f1f;color:#aef; border:1px solid #0aa; border-radius:8px; padding:.5rem 1rem; cursor:pointer}
button:hover{filter:brightness(1.2)}
.switch{position:relative;display:inline-block;width:60px;height:34px}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:#333;transition:.4s}
.slider:before{position:absolute;content:"";height:26px;width:26px;left:4px;bottom:4px;background:white;transition:.4s}
input:checked + .slider{background-color:var(--neon)}
input:checked + .slider:before{transform:translateX(26px)}
.slider.round{border-radius:34px}.slider.round:before{border-radius:50%}
CSS

# --- Dashboard JS (adds compare chart + optimizer controls) ---
cat > static/dashboard.js <<'JS'
let chart, compareChart;

async function getJSON(url, params){
  const q = params ? '?' + new URLSearchParams(params) : '';
  const r = await fetch(url+q); return r.json();
}
async function postJSON(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); 
  return r.json();
}

async function loadOHLC(){ return getJSON('/api/ohlc', {symbol:'AAPL', limit:240}); }
async function loadLogs(){ return getJSON('/api/strategy-log'); }
async function loadPnL(){ return getJSON('/api/pnl'); }
async function loadLive(){ return getJSON('/api/live-toggle'); }
async function saveLive(live){ return postJSON('/api/live-toggle', {live}); }
async function loadAuto(){ return getJSON('/api/auto-mode'); }
async function saveAuto(auto_trade, qty){ return postJSON('/api/auto-mode', {auto_trade, qty}); }
async function loadCompare(){ return getJSON('/api/compare', {symbol:'AAPL', limit:300}); }
async function optStart(){ return postJSON('/api/optimizer/start', {}); }
async function optStatus(){ return getJSON('/api/optimizer/status'); }

function renderChart(labels, closes){
  const ctx = document.getElementById('chart').getContext('2d');
  if (chart){ chart.data.labels = labels; chart.data.datasets[0].data = closes; chart.update(); return; }
  chart = new Chart(ctx, {
    type:'line',
    data:{ labels, datasets:[{label:'Close', data:closes, borderColor:'#00ffff', tension:0.3}] },
    options:{ plugins:{legend:{labels:{color:'#00ffff'}}}, scales:{x:{ticks:{color:'#00ffff'}}, y:{ticks:{color:'#00ffff'}}}}
  });
}

function renderCompare(labels, curves){
  const ctx = document.getElementById('compare').getContext('2d');
  const ds = Object.entries(curves).map(([name, data]) => ({label:name, data, fill:false, borderWidth:2}));
  if (compareChart){ compareChart.data.labels = labels; compareChart.data.datasets = ds; compareChart.update(); return; }
  compareChart = new Chart(ctx, {
    type:'line',
    data:{ labels, datasets: ds },
    options:{ plugins:{legend:{labels:{color:'#00ffff'}}}, scales:{x:{ticks:{color:'#00ffff'}}, y:{ticks:{color:'#00ffff'}}}}
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
  document.getElementById('logs').textContent = logs.length ? logs.map(l => JSON.stringify(l)).join('\n') : 'No strategy logs yet.';
}

async function refreshPnL(){
  const p = await loadPnL();
  document.getElementById('cash').textContent = '$'+(p.cash??0).toFixed(2);
  document.getElementById('equity').textContent = '$'+(p.equity??0).toFixed(2);
  document.getElementById('positions').textContent = Object.keys(p.positions||{}).length;
  document.getElementById('trades').textContent = (p.trades||[]).length;
  document.getElementById('wins').textContent = p.win_trades??0;
}

async function refreshCompare(){
  const d = await loadCompare();
  renderCompare(d.labels, d.curves);
}

async function refreshOptimizer(){
  const st = await optStatus();
  document.getElementById('optStatus').textContent = st.status || 'idle';
  document.getElementById('optBest').textContent = JSON.stringify(st.best || st.last_best || {}, null, 2);
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
  autoToggle.checked = !!auto.auto_trade; qtyInput.value = auto.qty ?? 1;
  autoStatus.textContent = autoToggle.checked ? 'On' : 'Off';
  const persist = async () => {
    await saveAuto(autoToggle.checked, parseInt(qtyInput.value||'1',10));
    autoStatus.textContent = autoToggle.checked ? 'On' : 'Off';
  };
  autoToggle.addEventListener('change', persist);
  qtyInput.addEventListener('change', persist);

  document.getElementById('optStart').addEventListener('click', async () => {
    await optStart(); setTimeout(refreshOptimizer, 1000);
  });
}

async function main(){
  await initToggles();
  await refreshChart(); await refreshLogs(); await refreshPnL(); await refreshCompare(); await refreshOptimizer();
  setInterval(refreshChart, 5000);
  setInterval(refreshLogs, 5000);
  setInterval(refreshPnL, 4000);
  setInterval(refreshCompare, 9000);
  setInterval(refreshOptimizer, 4000);
}
document.addEventListener('DOMContentLoaded', main);
JS

echo "✅ Phase 561–580 files written."
echo "-----------------------------------------"
echo "1) Restart backend:"
echo "   pkill -f 'uvicorn backend.main:app' || true"
echo "   nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &"
echo "2) Restart daemon (uses overrides):"
echo "   pkill -f 'tools/strategy_daemon.py' || true"
echo "   nohup python tools/strategy_daemon.py &"
echo "3) Open dashboard:"
echo "   http://localhost:8000/dashboard"
echo "4) Start Optimizer from the dashboard (button) or:"
echo "   curl -X POST http://localhost:8000/api/optimizer/start"
BASH

# 2) Make executable + run it
chmod +x phase_561_580_compare_opt.sh
./phase_561_580_compare_opt.sh

