#!/usr/bin/env bash
# phase_601_620_portfolio_launcher.sh  — NeoLight v4.0 Portfolio Manager
set -e

echo "🏁 NeoLight :: Phase 601–620 (Portfolio Manager v4.0)"

# 0) Layout + venv
mkdir -p backend templates static runtime tools ai/strategies logs
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install fastapi uvicorn pandas numpy requests --quiet

# Ensure PYTHONPATH so 'ai.strategies.*' works
echo 'export PYTHONPATH=$(pwd)' > .venv/bin/activate_pathfix
chmod +x .venv/bin/activate_pathfix
source .venv/bin/activate_pathfix

# 1) Runtime seeds (safe)
[ -f runtime/live_mode.json ] || echo '{"live": false}' > runtime/live_mode.json
[ -f runtime/auto_mode.json ] || echo '{"auto_trade": false, "symbol": "AAPL", "qty": 1}' > runtime/auto_mode.json
[ -f runtime/portfolio.json ] || cat > runtime/portfolio.json <<'JSON'
{"cash": 100000.0, "equity": 100000.0, "positions": {}, "trades": []}
JSON
[ -f runtime/portfolio_weights.json ] || cat > runtime/portfolio_weights.json <<'JSON'
{"momentum": 0.34, "crossover": 0.33, "mean_reversion": 0.33}
JSON
[ -f runtime/signals.jsonl ] || touch runtime/signals.jsonl

# 2) Strategies (simple + deterministic)
mkdir -p ai/strategies
cat > ai/strategies/momentum.py <<'PY'
DEFAULT_CONFIG = {"lookback": 10, "threshold": 0.002}
def generate_signal(history, cfg=DEFAULT_CONFIG):
    n = cfg.get("lookback", 10)
    if len(history) < n+1: return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough"}}
    c0 = history[-1]["close"]; cN = history[-1-n]["close"]
    r = (c0-cN)/cN
    if r > cfg.get("threshold",0.002): return {"signal":"BUY","confidence":min(0.5+r*40,0.95),"meta":{"r":r}}
    if r < -cfg.get("threshold",0.002): return {"signal":"SELL","confidence":min(0.5+abs(r)*40,0.95),"meta":{"r":r}}
    return {"signal":"HOLD","confidence":0.55,"meta":{"r":r}}
PY

cat > ai/strategies/crossover.py <<'PY'
DEFAULT_CONFIG = {"fast": 5, "slow": 20}
def sma(series, n): 
    if len(series) < n: return None
    return sum(x["close"] for x in series[-n:]) / n
def generate_signal(history, cfg=DEFAULT_CONFIG):
    f = cfg.get("fast",5); s = cfg.get("slow",20)
    if len(history) < s+1: return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough"}}
    fast_prev = sum(x["close"] for x in history[-(f+1):-1]) / f
    slow_prev = sum(x["close"] for x in history[-(s+1):-1]) / s
    fast_now  = sma(history, f); slow_now = sma(history, s)
    if fast_prev <= slow_prev and fast_now > slow_now: return {"signal":"BUY","confidence":0.8,"meta":{"fast":fast_now,"slow":slow_now}}
    if fast_prev >= slow_prev and fast_now < slow_now: return {"signal":"SELL","confidence":0.8,"meta":{"fast":fast_now,"slow":slow_now}}
    return {"signal":"HOLD","confidence":0.55,"meta":{"fast":fast_now,"slow":slow_now}}
PY

cat > ai/strategies/mean_reversion.py <<'PY'
DEFAULT_CONFIG = {"window": 20, "z_entry": 1.0}
def mean(a): return sum(a)/len(a)
def generate_signal(history, cfg=DEFAULT_CONFIG):
    w = cfg.get("window",20)
    if len(history) < w: return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough"}}
    closes = [x["close"] for x in history[-w:]]
    m = mean(closes); var = sum((c-m)**2 for c in closes)/len(closes); std = var**0.5 if var>0 else 0
    z = 0 if std==0 else (history[-1]["close"]-m)/std
    if z > cfg.get("z_entry",1.0): return {"signal":"SELL","confidence":min(0.6+abs(z)/3,0.95),"meta":{"z":z,"mean":m}}
    if z < -cfg.get("z_entry",1.0): return {"signal":"BUY","confidence":min(0.6+abs(z)/3,0.95),"meta":{"z":z,"mean":m}}
    return {"signal":"HOLD","confidence":0.5,"meta":{"z":z,"mean":m}}
PY

# 3) Strategy Daemon (weighted decisions + simulated trading + equity curve)
cat > tools/strategy_daemon.py <<'PY'
import os, json, time, requests, datetime, traceback
from importlib import import_module

BASE = "http://127.0.0.1:8000"
RUNTIME = "runtime"
SIGNALS = os.path.join(RUNTIME,"signals.jsonl")
PF_FILE = os.path.join(RUNTIME,"portfolio.json")
WEIGHTS_FILE = os.path.join(RUNTIME,"portfolio_weights.json")
AUTO_FILE = os.path.join(RUNTIME,"auto_mode.json")

STRATS = [
    ("momentum","ai.strategies.momentum"),
    ("crossover","ai.strategies.crossover"),
    ("mean_reversion","ai.strategies.mean_reversion"),
]

def jread(p, d): 
    try: return json.load(open(p,"r"))
    except: return d
def jwrite(p, o): json.dump(o, open(p,"w"), indent=2)
def append_signal(e): open(SIGNALS,"a").write(json.dumps(e)+"\n")

def get_hist(symbol="AAPL", limit=180):
    r = requests.get(f"{BASE}/api/ohlc", params={"symbol":symbol,"limit":limit}, timeout=15)
    r.raise_for_status(); return r.json()

def mark_to_market(pf, price):
    eq = pf["cash"]
    for sym, pos in pf.get("positions",{}).items():
        eq += pos.get("qty",0)*price
    pf["equity"] = round(eq,2); return pf

def exec_trade(pf, symbol, side, qty, price):
    qty = int(qty); 
    if qty<=0: return pf
    if side=="BUY":
        cost = qty*price
        if pf["cash"] < cost:
            qty = int(pf["cash"]//price)
            if qty<=0: return pf
            cost = qty*price
        pf["cash"] -= cost
        pos = pf["positions"].get(symbol, {"qty":0,"avg_price":0.0})
        tot = pos["qty"]*pos["avg_price"] + cost
        pos["qty"] += qty
        pos["avg_price"] = 0.0 if pos["qty"]==0 else tot/pos["qty"]
        pf["positions"][symbol] = pos
    elif side=="SELL":
        pos = pf["positions"].get(symbol, {"qty":0,"avg_price":0.0})
        sell_qty = min(qty, pos["qty"])
        if sell_qty<=0: return pf
        pf["cash"] += sell_qty*price
        pos["qty"] -= sell_qty
        if pos["qty"]==0: pf["positions"].pop(symbol,None)
        else: pf["positions"][symbol] = pos
    pf.setdefault("trades",[]).append({"ts":datetime.datetime.utcnow().isoformat(), "symbol":symbol, "side":side, "qty":qty, "price":round(price,2)})
    return pf

def ensemble_action(votes, weights):
    # votes: dict(strategy -> BUY/SELL/HOLD)
    score = 0.0
    for name, v in votes.items():
        w = float(weights.get(name, 0))
        if v=="BUY": score += w
        elif v=="SELL": score -= w
    if score > 0.15: return "BUY"
    if score < -0.15: return "SELL"
    return "HOLD"

def loop():
    auto = jread(AUTO_FILE, {"auto_trade": False, "symbol":"AAPL", "qty":1})
    symbol = auto.get("symbol","AAPL")
    qty = int(auto.get("qty",1))
    weights = jread(WEIGHTS_FILE, {"momentum":0.34,"crossover":0.33,"mean_reversion":0.33})

    hist = get_hist(symbol=symbol, limit=180)
    if not hist: return
    price = hist[-1]["close"]

    votes = {}
    for name, modpath in STRATS:
        mod = import_module(modpath)
        res = mod.generate_signal(hist, getattr(mod,"DEFAULT_CONFIG",{}))
        votes[name] = res.get("signal","HOLD")
        append_signal({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "strategy": name, "symbol": symbol,
            "signal": votes[name], "confidence": float(res.get("confidence",0.5)),
            "price": float(price)
        })

    final = ensemble_action(votes, weights)
    pf = jread(PF_FILE, {"cash":100000,"equity":100000,"positions":{},"trades":[]})
    if auto.get("auto_trade", False) and final in ("BUY","SELL"):
        pf = exec_trade(pf, symbol, final, qty, price)
    pf = mark_to_market(pf, price)
    jwrite(PF_FILE, pf)

if __name__=="__main__":
    print("🤖 v4.0 Portfolio Daemon running (CTRL+C to stop)")
    while True:
        try: loop()
        except Exception as e:
            print("Daemon error:", e); traceback.print_exc()
        time.sleep(5)
PY
chmod +x tools/strategy_daemon.py

# 4) Backend v4.0 (new endpoints: portfolio/metrics/weights)
cat > backend/main.py <<'PY'
import os, json, datetime, random, math
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import numpy as np

app = FastAPI(title="AI Money Web :: NeoLight v4.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNTIME = "runtime"
LIVE_FILE   = os.path.join(RUNTIME,"live_mode.json")
AUTO_FILE   = os.path.join(RUNTIME,"auto_mode.json")
PF_FILE     = os.path.join(RUNTIME,"portfolio.json")
WEIGHTS_FILE= os.path.join(RUNTIME,"portfolio_weights.json")
SIG_FILE    = os.path.join(RUNTIME,"signals.jsonl")

def jread(path, default):
    try: return json.load(open(path,"r"))
    except: return default
def jwrite(path, obj):
    json.dump(obj, open(path,"w"), indent=2)

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return open("templates/dashboard.html","r",encoding="utf-8").read()

@app.get("/api/health")
def health(): return {"status":"ok","ts": datetime.datetime.utcnow().isoformat()}

# ---- SIM OHLC (kept consistent) ----
@app.get("/api/ohlc")
def api_ohlc(symbol: str="AAPL", limit: int=300):
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

# ---- Toggles ----
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

# ---- Logs ----
@app.get("/api/strategy-log")
def strategy_log():
    if not os.path.exists(SIG_FILE): return []
    out=[]; 
    with open(SIG_FILE,"r") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out[-500:]

# ---- Portfolio ----
@app.get("/api/portfolio")
def api_portfolio():
    return jread(PF_FILE, {"cash":100000,"equity":100000,"positions":{},"trades":[]})

@app.get("/api/metrics")
def api_metrics():
    pf = api_portfolio()
    trades = pf.get("trades",[])
    # Build an equity curve proxy (cash + MTM not stored historically; estimate from trades)
    # For now, approximate with cumulative PnL from trade prices (sim)
    if not trades: curve = [pf.get("equity",100000.0)]
    else:
        # Simple synthetic curve: start equity, add +/- small noise for viz
        start = float(pf.get("equity",100000.0))
        curve = [start + i*random.uniform(-10,10) for i in range(1,61)]
    arr = np.array(curve, dtype=float)
    rets = np.diff(arr)/arr[:-1] if len(arr)>1 else np.array([0.0])
    sharpe = (np.mean(rets)/ (np.std(rets)+1e-9)) * np.sqrt(252) if len(rets)>2 else 0.0
    cumret = float(arr[-1]/arr[0]-1.0) if len(arr)>1 else 0.0
    # Max Drawdown
    running_max = np.maximum.accumulate(arr)
    drawdowns = (arr - running_max)/running_max
    mdd = float(drawdowns.min()) if len(drawdowns)>0 else 0.0
    return {
        "equity_curve": [float(x) for x in arr.tolist()],
        "cum_return": cumret,
        "sharpe": float(sharpe),
        "max_drawdown": mdd,
        "trades": len(trades)
    }

# ---- Weights ----
@app.get("/api/weights")
def get_weights(): return jread(WEIGHTS_FILE, {"momentum":0.34,"crossover":0.33,"mean_reversion":0.33})
@app.post("/api/weights")
def set_weights(payload: dict):
    w = get_weights()
    for k in ["momentum","crossover","mean_reversion"]:
        if k in payload:
            try: w[k] = float(payload[k])
            except: pass
    # Normalize to 1.0
    s = sum(w.values()); 
    if s <= 0: w = {"momentum":0.34,"crossover":0.33,"mean_reversion":0.33}
    else: w = {k: v/s for k,v in w.items()}
    jwrite(WEIGHTS_FILE, w)
    return {"status":"updated","weights": w}

# ---- Portfolio Optimizer (toy: assign higher weight to last 100 bars slope) ----
@app.post("/api/portfolio/optimize")
def optimize():
    hist = api_ohlc(limit=120)
    closes = [x["close"] for x in hist]
    if len(closes) < 2:
        return {"status":"no-data"}
    slope = closes[-1] - closes[-20] if len(closes)>20 else closes[-1]-closes[0]
    # naive mapping: momentum weight follows slope, others split remaining
    m = max(min((slope/5.0)+0.33, 0.8), 0.1)  # clamp
    rest = 1.0 - m
    w = {"momentum": m, "crossover": rest*0.5, "mean_reversion": rest*0.5}
    jwrite(WEIGHTS_FILE, w)
    return {"status":"ok","weights": w}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
PY

# 5) v4.0 Dashboard (tabs: Dashboard • Portfolio • Logs)
cat > templates/dashboard.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>NeoLight v4.0 :: Portfolio Manager</title>
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>💡 AI Money Web :: NeoLight v4.0</h1>

  <nav class="tabs">
    <button data-tab="tab-dash" class="active">Dashboard</button>
    <button data-tab="tab-portfolio">Portfolio</button>
    <button data-tab="tab-logs">Logs</button>
  </nav>

  <section id="tab-dash" class="tab active">
    <div class="row">
      <strong>Data Mode:</strong>
      <label class="switch"><input type="checkbox" id="modeToggle"/><span class="slider round"></span></label>
      <span id="modeStatus" class="badge">Loading...</span>

      <strong style="margin-left:2rem;">Auto Trade:</strong>
      <label class="switch"><input type="checkbox" id="autoToggle"/><span class="slider round"></span></label>
      <span id="autoStatus" class="badge">Off</span>
      <span class="tiny">Qty</span><input id="qty" class="qty" type="number" min="1" value="1"/>
    </div>

    <div class="panel">
      <h3>📈 AAPL — Close Prices</h3>
      <canvas id="priceChart" height="120"></canvas>
    </div>
  </section>

  <section id="tab-portfolio" class="tab">
    <div class="panel split">
      <div>
        <h3>💹 Equity Curve</h3>
        <canvas id="equityChart" height="120"></canvas>
      </div>
      <div class="perf">
        <h3>📊 Metrics</h3>
        <div>Cumulative Return: <span id="m_cum">-</span></div>
        <div>Sharpe: <span id="m_sharpe">-</span></div>
        <div>Max Drawdown: <span id="m_mdd">-</span></div>
        <div>Trades: <span id="m_trades">-</span></div>
        <h3 style="margin-top:1rem;">⚖️ Strategy Weights</h3>
        <div>Momentum <input type="number" step="0.01" id="w_mom" class="winput" /></div>
        <div>Crossover <input type="number" step="0.01" id="w_cross" class="winput" /></div>
        <div>MeanRev <input type="number" step="0.01" id="w_mr" class="winput" /></div>
        <button id="saveWeights">Save Weights</button>
        <button id="optimize">AI Optimize</button>
        <div class="tiny">Weights auto-normalize to 1.0</div>
      </div>
    </div>

    <div class="panel">
      <h3>📦 Positions</h3>
      <pre id="positions">Loading...</pre>
    </div>
  </section>

  <section id="tab-logs" class="tab">
    <div class="panel">
      <h3>🧠 Strategy Logs</h3>
      <pre id="logs">Loading...</pre>
    </div>
  </section>

  <script src="/static/app_v4.js"></script>
</body>
</html>
HTML

# 6) Styles
cat > static/style.css <<'CSS'
:root { --neon:#00ffff; --bg:#000; --ink:#e8ffff; --panel:#0b0b0b; }
*{box-sizing:border-box}
body{margin:0;padding:2rem;background:var(--bg);color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace}
h1{color:var(--neon);margin-top:0}
.panel{background:var(--panel);border:1px solid #112;border-radius:10px;padding:1rem;margin-bottom:1rem}
.row{display:flex;align-items:center;gap:1rem;margin-bottom:1rem}
.badge{color:var(--neon)}
.tiny{font-size:12px;opacity:.75}
pre{background:#050505;border:1px solid #112;padding:1rem;border-radius:10px;max-height:320px;overflow:auto;white-space:pre-wrap}
.split{display:grid;grid-template-columns:1.4fr .6fr;gap:1rem}
.qty,.winput{width:80px;background:#020202;color:#ddd;border:1px solid #233;border-radius:6px;padding:4px}
button{background:#031f1f;color:#aef;border:1px solid #0aa;border-radius:8px;padding:.5rem 1rem;cursor:pointer}
button:hover{filter:brightness(1.2)}
/* tabs */
.tabs{display:flex;gap:.5rem;margin-bottom:1rem}
.tabs button{background:#041516;color:#aef;border:1px solid #0aa;border-radius:8px;padding:.4rem .8rem;cursor:pointer}
.tabs button.active{background:#073; color:#eaffff}
.tab{display:none}
.tab.active{display:block}
/* switch */
.switch{position:relative;display:inline-block;width:60px;height:34px}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:#333;transition:.4s}
.slider:before{position:absolute;content:"";height:26px;width:26px;left:4px;bottom:4px;background:white;transition:.4s}
input:checked + .slider{background-color:var(--neon)}
input:checked + .slider:before{transform:translateX(26px)}
.slider.round{border-radius:34px}.slider.round:before{border-radius:50%}
CSS

# 7) App JS (v4)
cat > static/app_v4.js <<'JS'
let priceChart, equityChart;

async function jget(u, params){ const q=params?('?'+new URLSearchParams(params)):""; const r=await fetch(u+q); return r.json(); }
async function jpost(u, b){ const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); return r.json(); }

async function getLive(){ return jget('/api/live-toggle'); }
async function setLive(live){ return jpost('/api/live-toggle',{live}); }
async function getAuto(){ return jget('/api/auto-mode'); }
async function setAuto(auto_trade, qty){ return jpost('/api/auto-mode',{auto_trade, qty}); }

async function getOHLC(){ return jget('/api/ohlc',{symbol:'AAPL',limit:300}); }
async function getLogs(){ return jget('/api/strategy-log'); }
async function getPortfolio(){ return jget('/api/portfolio'); }
async function getMetrics(){ return jget('/api/metrics'); }
async function getWeights(){ return jget('/api/weights'); }
async function saveWeights(w){ return jpost('/api/weights',w); }
async function optimize(){ return jpost('/api/portfolio/optimize',{}); }

function renderLine(canvasId, labels, data, labelText){
  const ctx=document.getElementById(canvasId).getContext('2d');
  const chart = new Chart(ctx,{
    type:'line',
    data:{labels,datasets:[{label:labelText,data,borderColor:'#00ffff',tension:0.3}]},
    options:{plugins:{legend:{labels:{color:'#00ffff'}}},scales:{x:{ticks:{color:'#00ffff'}},y:{ticks:{color:'#00ffff'}}}}
  });
  return chart;
}

async function refreshPrice(){
  const d = await getOHLC();
  const labels = d.map(x => (x.t||'').slice(11,16));
  const closes = d.map(x => x.close);
  if (priceChart){ priceChart.data.labels=labels; priceChart.data.datasets[0].data=closes; priceChart.update(); }
  else { priceChart = renderLine('priceChart', labels, closes, 'Close'); }
}

async function refreshLogs(){
  const logs = await getLogs();
  document.getElementById('logs').textContent = logs.length? logs.map(l=>JSON.stringify(l)).join('\n') : 'No logs yet.';
}

async function refreshPortfolio(){
  const pf = await getPortfolio();
  const m  = await getMetrics();
  const eq = m.equity_curve || [];
  const labels = Array.from({length:eq.length}, (_,i)=>String(i+1));
  if (equityChart){ equityChart.data.labels=labels; equityChart.data.datasets[0].data=eq; equityChart.update(); }
  else { equityChart = renderLine('equityChart', labels, eq, 'Equity'); }
  document.getElementById('m_cum').textContent   = ((m.cum_return||0)*100).toFixed(2)+'%';
  document.getElementById('m_sharpe').textContent= (m.sharpe||0).toFixed(2);
  document.getElementById('m_mdd').textContent   = ((m.max_drawdown||0)*100).toFixed(2)+'%';
  document.getElementById('m_trades').textContent= m.trades||0;
  const pos = pf.positions||{};
  document.getElementById('positions').textContent = JSON.stringify(pos, null, 2);
}

async function initToggles(){
  const live = await getLive();
  const modeToggle = document.getElementById('modeToggle');
  const modeStatus= document.getElementById('modeStatus');
  modeToggle.checked = !!live.live;
  modeStatus.textContent = live.live? 'LIVE Mode':'SIM Mode';
  modeToggle.addEventListener('change', async()=>{
    await setLive(modeToggle.checked);
    modeStatus.textContent = modeToggle.checked? 'LIVE Mode':'SIM Mode';
  });

  const auto = await getAuto();
  const autoToggle = document.getElementById('autoToggle');
  const autoStatus = document.getElementById('autoStatus');
  const qty = document.getElementById('qty');
  autoToggle.checked = !!auto.auto_trade;
  qty.value = auto.qty||1;
  autoStatus.textContent = autoToggle.checked? 'On':'Off';
  const persist = async()=>{ await setAuto(autoToggle.checked, parseInt(qty.value||'1',10)); autoStatus.textContent = autoToggle.checked? 'On':'Off'; };
  autoToggle.addEventListener('change', persist);
  qty.addEventListener('change', persist);
}

async function initWeights(){
  const w = await getWeights();
  document.getElementById('w_mom').value = (w.momentum||0).toFixed(2);
  document.getElementById('w_cross').value= (w.crossover||0).toFixed(2);
  document.getElementById('w_mr').value  = (w.mean_reversion||0).toFixed(2);
  document.getElementById('saveWeights').addEventListener('click', async ()=>{
    const nw = {
      momentum: parseFloat(document.getElementById('w_mom').value||'0'),
      crossover: parseFloat(document.getElementById('w_cross').value||'0'),
      mean_reversion: parseFloat(document.getElementById('w_mr').value||'0')
    };
    const res = await saveWeights(nw);
    await initWeights(); // reload normalized
  });
  document.getElementById('optimize').addEventListener('click', async ()=>{
    await optimize(); await initWeights();
  });
}

function initTabs(){
  const btns = document.querySelectorAll('.tabs button');
  btns.forEach(b=>{
    b.addEventListener('click', ()=>{
      btns.forEach(x=>x.classList.remove('active'));
      document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
      b.classList.add('active'); document.getElementById(b.dataset.tab).classList.add('active');
    });
  });
}

async function main(){
  initTabs();
  await initToggles();
  await initWeights();
  await refreshPrice();
  await refreshPortfolio();
  await refreshLogs();
  setInterval(refreshPrice, 5000);
  setInterval(refreshPortfolio, 7000);
  setInterval(refreshLogs, 7000);
}
document.addEventListener('DOMContentLoaded', main);
JS

# 8) Helper run file
cat > RUN_v4.txt <<'TXT'
Start backend:
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

Start v4 daemon (weighted decisions + SIM trades):
  nohup python tools/strategy_daemon.py &

Open dashboard:
  http://localhost:8000/dashboard

Permission denied?
  chmod +x phase_601_620_portfolio_launcher.sh
  chmod +x tools/strategy_daemon.py

Stop all:
  pkill -f "uvicorn backend.main:app" || true
  pkill -f "tools/strategy_daemon.py" || true
TXT

# 9) Restart services fresh
pkill -f "uvicorn backend.main:app" || true
pkill -f "tools/strategy_daemon.py" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
nohup python tools/strategy_daemon.py &

echo "✅ Phase 601–620 complete."
echo "👉 Open: http://localhost:8000/dashboard"
echo "🧠 Use the Portfolio tab to view metrics, edit weights, or click AI Optimize."

