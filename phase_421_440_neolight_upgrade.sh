#!/bin/bash
# ============================================================
# AI Money Web :: Phase 421–440 — NeoLight v2.5 Full Dashboard
# ============================================================
set -e

echo "🟣 NeoLight v2.5 :: scaffolding…"

# 0) Clean port
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing PID $pid on :8000"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1) Structure + backups
mkdir -p backend templates static runtime logs backups
[ -f backend/main.py ] && cp backend/main.py backups/main.py.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f templates/index.html ] && cp templates/index.html backups/index.html.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/style.css ] && cp static/style.css backups/style.css.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/app.js ] && cp static/app.js backups/app.js.$(date +"%Y%m%d_%H%M%S").bak || true

# 2) Backend
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, json, time, random, asyncio, datetime, math, statistics, uuid

app = FastAPI(title="AI Money Web :: NeoLight v2.5")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------- Models --------
class PaperTradeRequest(BaseModel):
    symbol: str
    price: float
    action: str
    qty: float = 1

class StrategyConfig(BaseModel):
    name: str
    params: dict = {}

# -------- Views --------
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -------- Health/Env/System --------
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "NeoLight v2.5 running"}

@app.get("/api/env_check")
def env_check():
    keys = [
        "ALPACA_MODE","PAPER_TRADE","ALPACA_BASE_URL",
        "ALPACA_API_KEY_ID","ALPACA_API_SECRET","SYMBOL_WHITELIST"
    ]
    return {k: os.getenv(k, "❌ Not Set") for k in keys}

@app.get("/api/restarts")
def restarts():
    out = []
    p = "logs/restart_log.txt"
    if os.path.exists(p):
        with open(p) as f:
            out = [ln.strip() for ln in f if ln.strip()]
    return {"restarts": out[-50:]}

# -------- Strategy Config (runtime) --------
@app.get("/api/strategy_config")
def strategy_config_get():
    os.makedirs("runtime", exist_ok=True)
    p = "runtime/strategy_config.json"
    if os.path.exists(p):
        return json.load(open(p))
    return {"name":"momentum","params":{"window":5}}

@app.post("/api/strategy_config")
def strategy_config_set(cfg: StrategyConfig):
    os.makedirs("runtime", exist_ok=True)
    with open("runtime/strategy_config.json","w") as f:
        json.dump(cfg.model_dump(), f, indent=2)
    return {"status":"ok","saved":cfg.model_dump()}

# -------- Trades & Paper Execution --------
@app.get("/api/trades")
def get_trades():
    trades = []
    p = "runtime/orders.jsonl"
    if os.path.exists(p):
        with open(p) as f:
            for ln in f:
                try: trades.append(json.loads(ln))
                except: pass
    return trades[-200:]

@app.post("/api/paper_trade")
def paper_trade(req: PaperTradeRequest):
    os.makedirs("runtime", exist_ok=True)
    trade = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": req.symbol, "price": req.price,
        "action": req.action, "qty": req.qty
    }
    with open("runtime/orders.jsonl","a") as f:
        f.write(json.dumps(trade)+"\n")

    # Optional: Alpaca bridge if PAPER_TRADE=1 (kept commented for safety)
    # if os.getenv("PAPER_TRADE") == "1":
    #     import requests
    #     headers = {
    #       "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY_ID"),
    #       "APCA-API-SECRET-KEY": os.getenv("ALPACA_API_SECRET"),
    #       "Content-Type": "application/json"
    #     }
    #     url = os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets") + "/v2/orders"
    #     payload = {"symbol": req.symbol, "side": req.action, "type":"market","time_in_force":"gtc"}
    #     if "/" in req.symbol or req.symbol.endswith("USD"):
    #         payload["notional"] = round(req.price * req.qty, 2)
    #     else:
    #         payload["qty"] = req.qty
    #     try: requests.post(url, headers=headers, json=payload, timeout=5)
    #     except Exception as e: trade["alpaca_error"] = str(e)

    return {"status":"executed","trade":trade}

# -------- Performance --------
@app.get("/api/performance")
def performance():
    p = "runtime/orders.jsonl"
    if not os.path.exists(p): return {"pnl":0,"win_rate":0,"sharpe":0}
    prices, actions = [], []
    with open(p) as f:
        for ln in f:
            try:
                t = json.loads(ln.strip())
                prices.append(float(t["price"]))
                actions.append(t["action"])
            except: pass
    if len(prices)<2: return {"pnl":0,"win_rate":0,"sharpe":0}
    pnl = sum([prices[i+1]-prices[i] if actions[i]=="buy" else prices[i]-prices[i+1] for i in range(len(prices)-1)])
    diffs = [p2-p1 for p1,p2 in zip(prices,prices[1:])]
    gains = [max(0,d) for d in diffs]; losses = [abs(d) for d in diffs if d<0]
    win_rate = len(gains)/(len(gains)+len(losses)) if (gains or losses) else 0
    ret = [p2/p1-1 for p1,p2 in zip(prices,prices[1:]) if p1>0]
    sharpe = statistics.mean(ret)/statistics.stdev(ret)*math.sqrt(252) if len(ret)>1 and statistics.stdev(ret)>0 else 0
    return {"pnl":round(pnl,2),"win_rate":round(win_rate,3),"sharpe":round(sharpe,2)}

# -------- WebSocket feed (candles + KPIs) --------
@app.websocket("/ws")
async def ws_feed(ws: WebSocket):
    await ws.accept()
    # Seed from last trade
    base = 200.0
    tr = get_trades()
    if tr: 
        try: base = float(tr[-1].get("price", base))
        except: pass
    o = h = l = c = base
    while True:
        delta = random.uniform(-0.5,0.6)
        o = c; c = max(1.0, o + delta)
        h = max(o,c) + abs(random.uniform(0,0.35))
        l = min(o,c) - abs(random.uniform(0,0.35))
        payload = {
            "ts": int(time.time()*1000),
            "ohlc": {"open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)},
            "kpis": {
                "balance": 10000 + random.uniform(-100,100),
                "profit": random.uniform(-2,2),
                "loss": max(0, random.uniform(-1,1)),
                "volPct": random.randint(45,85),
                "divPct": random.randint(15,65)
            }
        }
        await ws.send_text(json.dumps(payload))
        await asyncio.sleep(0.9)
PYCODE

# 3) Template (Full page, scrollable, sticky header + left nav)
cat > templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>A.I. TRADING DASHBOARD</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@400;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <header class="topbar neon">
    <div class="logo">A.I. TRADING DASHBOARD</div>
    <nav class="anchors">
      <a href="#live">Live</a>
      <a href="#kpi">KPIs</a>
      <a href="#perf">Performance</a>
      <a href="#trade">Trade</a>
      <a href="#strategy">Strategy</a>
      <a href="#system">System</a>
    </nav>
  </header>

  <div class="layout">
    <aside class="sidenav neon">
      <a href="#live">📈 Live</a>
      <a href="#kpi">🧪 KPIs</a>
      <a href="#perf">📊 Performance</a>
      <a href="#trade">💸 Trade</a>
      <a href="#strategy">🧠 Strategy</a>
      <a href="#system">⚙️ System</a>
    </aside>

    <main class="content">
      <!-- LIVE -->
      <section id="live" class="panel neon">
        <h2>STOCKS</h2>
        <canvas id="cityOverlay" class="city"></canvas>
        <div id="candles" class="candles"></div>
      </section>

      <!-- KPIs -->
      <section id="kpi" class="grid3">
        <div class="panel neon">
          <h3>BALANCE</h3>
          <div class="big" id="k_balance">$10,000</div>
          <canvas id="spark_balance" class="spark"></canvas>
        </div>
        <div class="panel neon">
          <h3>PROFIT</h3>
          <div class="big" id="k_profit">+0.00%</div>
          <canvas id="spark_profit" class="spark"></canvas>
        </div>
        <div class="panel neon">
          <h3>LOSS</h3>
          <div class="big" id="k_loss">0.00%</div>
          <canvas id="spark_loss" class="spark"></canvas>
        </div>
      </section>

      <!-- PERFORMANCE -->
      <section id="perf" class="panel neon">
        <h2>AI Money Web :: Performance Dashboard</h2>
        <div class="perf">
          <div>PnL: <span id="pnl">$0.00</span></div>
          <div>Win Rate: <span id="win">0.0%</span></div>
          <div>Sharpe: <span id="sharpe">0.00</span></div>
        </div>
        <table class="tbl">
          <thead><tr><th>Timestamp</th><th>Symbol</th><th>Action</th><th>Price</th><th>Qty</th></tr></thead>
          <tbody id="trades"></tbody>
        </table>
      </section>

      <!-- TRADE -->
      <section id="trade" class="panel neon">
        <h2>Quick Trade</h2>
        <form id="tradeForm" class="form">
          <label>Symbol <input id="t_symbol" value="BTC/USD"/></label>
          <label>Price <input id="t_price" type="number" step="0.01" value="25000"/></label>
          <label>Action 
            <select id="t_action"><option>buy</option><option>sell</option></select>
          </label>
          <label>Qty <input id="t_qty" type="number" step="0.001" value="0.01"/></label>
          <button type="submit">Send Paper Trade</button>
        </form>
        <pre id="tradeOut" class="console"></pre>
      </section>

      <!-- STRATEGY -->
      <section id="strategy" class="panel neon">
        <h2>Strategy Config</h2>
        <form id="stratForm" class="form">
          <label>Name
            <select id="s_name">
              <option value="momentum">momentum</option>
              <option value="crossover">crossover</option>
              <option value="mean_reversion">mean_reversion</option>
            </select>
          </label>
          <label>Params (JSON)
            <textarea id="s_params" rows="6">{ "window": 5 }</textarea>
          </label>
          <button type="submit">Save Config</button>
        </form>
        <pre id="stratOut" class="console"></pre>
      </section>

      <!-- SYSTEM -->
      <section id="system" class="grid2">
        <div class="panel neon">
          <h2>System / Environment</h2>
          <pre id="env" class="console"></pre>
        </div>
        <div class="panel neon">
          <h2>Restart Log</h2>
          <pre id="restarts" class="console"></pre>
        </div>
      </section>
    </main>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
HTML

# 4) CSS — scrollable layout, sticky header, neon
cat > static/style.css <<'CSS'
:root{
  --bg:#07090e; --panel:#0f131b; --cyan:#00f5ff; --red:#ff2d2d; --amber:#ffb000; --ink:#cfe9ff;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:radial-gradient(1200px 900px at 50% -20%, #10131a 0%, var(--bg) 60%, #000 100%); color:var(--ink); font-family:"Share Tech Mono", ui-monospace, Menlo, monospace;}
a{color:var(--cyan); text-decoration:none}
.neon{border:1.5px solid var(--cyan); border-radius:14px; box-shadow:0 0 12px rgba(0,245,255,.35), inset 0 0 18px rgba(0,245,255,.08); background:linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0))}
.topbar{position:sticky;top:0;z-index:50;display:flex;gap:18px;align-items:center;justify-content:space-between;margin:10px;padding:10px 16px}
.logo{font-family:"Press Start 2P", monospace;color:var(--red);font-size:18px;letter-spacing:1.6px;text-shadow:0 0 10px rgba(255,45,45,.65)}
.anchors a{margin:0 8px}
.layout{display:grid;grid-template-columns:230px 1fr;gap:12px;padding:10px}
.sidenav{position:sticky; top:68px; height:calc(100vh - 86px); overflow:auto; padding:10px; display:flex; flex-direction:column; gap:10px}
.content{min-height:100vh; display:flex; flex-direction:column; gap:14px}
.panel{padding:12px; background:var(--panel)}
.grid3{display:grid; grid-template-columns:repeat(3,1fr); gap:14px}
.grid2{display:grid; grid-template-columns:1fr 1fr; gap:14px}
.big{font-size:22px}
.tbl{width:100%; border-collapse:collapse; margin-top:10px}
.tbl th,.tbl td{border:1px solid rgba(0,245,255,.25); padding:6px 8px}
.city{position:absolute; inset:0; opacity:.28}
.candles{position:relative; height:420px}
.spark{height:80px}
.console{background:#061018; border:1px dashed rgba(0,245,255,.35); padding:8px; height:200px; overflow:auto; font-size:12px}
.form{display:grid; gap:10px; grid-template-columns:repeat(4,1fr); align-items:end}
.form textarea{grid-column:1/-1}
.form button{grid-column:1/-1; padding:8px 10px; background:var(--cyan); color:#001419; border:none; border-radius:8px; font-weight:700; cursor:pointer}
h2,h3{margin:6px 0 12px 0}
#live{position:relative; min-height:460px}
CSS

# 5) JS — charts, websockets, actions, performance, env, trades
cat > static/app.js <<'JSCODE'
// ---------- tiny helpers ----------
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const fmt = n => (Math.abs(n)>=1? n.toFixed(2): n.toFixed(4));
async function jget(url){ const r = await fetch(url); return r.json(); }
async function jpost(url, body){ const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); return r.json(); }

// ---------- city overlay ----------
const city = $('#cityOverlay'); const cctx = city.getContext('2d');
function sizeCity(){ city.width = city.clientWidth; city.height = city.clientHeight; } addEventListener('resize', sizeCity); sizeCity();
function drawCity(){
  const w=city.width,h=city.height; cctx.clearRect(0,0,w,h);
  for(let i=0;i<200;i++){ cctx.fillStyle=['#00f5ff','#ff2d2d','#ffb000','#00ff88','#b100ff'][i%5]; cctx.fillRect(Math.random()*w, Math.random()*h*0.5, 2, 2); }
  let x=0; while(x<w){ const bw=20+Math.random()*40, bh=h*0.25+Math.random()*h*0.55;
    cctx.fillStyle='rgba(255,255,255,.02)'; cctx.fillRect(x,h-bh,bw,bh);
    cctx.strokeStyle='#0ff'; cctx.shadowColor='#0ff'; cctx.shadowBlur=6; cctx.strokeRect(x+0.5,h-bh+0.5,bw-1,bh-1); cctx.shadowBlur=0;
    for(let y=h-bh+8;y<h-6;y+=10){ if(Math.random()<0.3) continue; cctx.fillStyle=['#ffb000','#ff2d2d','#00f5ff'][Math.floor(Math.random()*3)]; cctx.fillRect(x+4+Math.random()*(bw-8), y, 3, 2); }
    x += bw + 6;
  }
} drawCity();

// ---------- lightweight-candles ----------
const chart = LightweightCharts.createChart($('#candles'), {
  layout:{ background:{ type:'solid', color:'transparent'}, textColor:'#b5eaff' },
  rightPriceScale:{ borderVisible:false }, timeScale:{ borderVisible:false },
  grid:{ vertLines:{ visible:false}, horzLines:{ visible:false} }, crosshair:{ mode: 0 }
});
const series = chart.addCandlestickSeries({ upColor:'#00ff88', downColor:'#ff2d2d', borderUpColor:'#00ff88', borderDownColor:'#ff2d2d', wickUpColor:'#00ff88', wickDownColor:'#ff2d2d' });

// ---------- sparklines ----------
function spark(el, color){
  const ctx = el.getContext('2d');
  return new Chart(ctx,{ type:'line', data:{ labels:Array(24).fill(''), datasets:[{ data:Array(24).fill(0), tension:.35, borderWidth:1.7, fill:false, borderColor:color}]},
    options:{ plugins:{legend:{display:false}}, elements:{point:{radius:0}}, scales:{x:{display:false},y:{display:false}} } });
}
const sBal = spark($('#spark_balance'), '#00f5ff');
const sPro = spark($('#spark_profit'), '#ffb000');
const sLos = spark($('#spark_loss'), '#ff2d2d');

// ---------- performance + trades table ----------
async function refreshPerf(){
  const p = await jget('/api/performance');
  $('#pnl').textContent = `$${fmt(p.pnl)}`;
  $('#win').textContent = `${(p.win_rate*100).toFixed(1)}%`;
  $('#sharpe').textContent = `${fmt(p.sharpe)}`;

  const trades = await jget('/api/trades');
  const tbody = $('#trades'); tbody.innerHTML='';
  trades.slice().reverse().forEach(t=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${new Date(t.timestamp).toLocaleString()}</td><td>${t.symbol}</td><td>${t.action}</td><td>${t.price}</td><td>${t.qty}</td>`;
    tbody.appendChild(tr);
  });
}

// ---------- env + restarts ----------
async function refreshSystem(){
  const env = await jget('/api/env_check'); $('#env').textContent = JSON.stringify(env, null, 2);
  const rs = await jget('/api/restarts'); $('#restarts').textContent = rs.restarts.join('\n');
}

// ---------- websocket KPIs ----------
const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onmessage = ev=>{
  const d = JSON.parse(ev.data);
  series.update({ time: Math.floor(d.ts/1000), open:d.ohlc.open, high:d.ohlc.high, low:d.ohlc.low, close:d.ohlc.close });

  $('#k_balance').textContent = `$${fmt(d.kpis.balance)}`;
  $('#k_profit').textContent  = `${d.kpis.profit>=0?'+':''}${fmt(d.kpis.profit)}%`;
  $('#k_loss').textContent    = `${fmt(d.kpis.loss)}%`;

  function push(chart, val){ const a=chart.data.datasets[0].data; a.shift(); a.push(val); chart.update('none'); }
  push(sBal, d.kpis.balance); push(sPro, d.kpis.profit); push(sLos, d.kpis.loss);
};

// ---------- trade form ----------
$('#tradeForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const payload = {
    symbol: $('#t_symbol').value.trim(),
    price: parseFloat($('#t_price').value),
    action: $('#t_action').value,
    qty: parseFloat($('#t_qty').value)
  };
  const res = await jpost('/api/paper_trade', payload);
  $('#tradeOut').textContent = JSON.stringify(res, null, 2);
  refreshPerf();
});

// ---------- strategy form ----------
async function loadStrategy(){
  const cfg = await jget('/api/strategy_config');
  $('#s_name').value = cfg.name || 'momentum';
  $('#s_params').value = JSON.stringify(cfg.params || {}, null, 2);
}
$('#stratForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  let params={}; try{ params=JSON.parse($('#s_params').value||'{}'); }catch(e){}
  const res = await jpost('/api/strategy_config', { name: $('#s_name').value, params });
  $('#stratOut').textContent = JSON.stringify(res, null, 2);
});
loadStrategy();

// ---------- intervals ----------
refreshPerf(); refreshSystem();
setInterval(refreshPerf, 4000);
setInterval(refreshSystem, 8000);
JSCODE

# 6) Ensure deps
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" jinja2 python-dotenv >/dev/null

# 7) Start + log restart
python - <<'PY'
import os, datetime
os.makedirs("logs", exist_ok=True)
open("logs/restart_log.txt","a").write(f"Restarted at {datetime.datetime.now().isoformat()}\n")
PY

echo "🚀 Starting backend…"
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "✅ Dashboard → http://127.0.0.1:8000/dashboard"
echo "🩺 Health    → http://127.0.0.1:8000/api/health"

