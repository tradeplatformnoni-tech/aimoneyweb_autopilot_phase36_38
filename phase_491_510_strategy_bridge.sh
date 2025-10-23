#!/bin/bash
# ============================================================
# AI Money Web :: Phase 491–510 — Strategy Param Bridge + Daemon Wire
# - Keeps NeoLight v3.2 visual style (city bg fixed)
# - Dashboard strategy panel loads defaults, saves JSON, applies to daemon
# - Simple file-based signaling for hot reload
# ============================================================
set -e

echo "🧠 Phase 491–510 :: Strategy Bridge + Daemon Wire"

# 0) clean port
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing PID $pid on :8000"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1) structure + backups
mkdir -p backend templates static runtime logs backups ai/strategies tools
[ -f backend/main.py ] && cp backend/main.py backups/main.py.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f templates/index.html ] && cp templates/index.html backups/index.html.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/style.css ] && cp static/style.css backups/style.css.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/app.js ] && cp static/app.js backups/app.js.$(date +"%Y%m%d_%H%M%S").bak || true

# 2) strategies (defaults + simple signal logic)
cat > ai/strategies/momentum.py <<'PY'
DEFAULT_CONFIG = {"window": 5, "symbol": "AAPL", "threshold": 0.01}

def name(): return "momentum"

def generate_signal(history=None, cfg=None):
    # very simple momentum: if last close > prev close by threshold -> buy, else sell
    cfg = (cfg or DEFAULT_CONFIG).copy()
    thr = float(cfg.get("threshold", 0.01))
    close = history[-1]["close"] if history else 100.0
    prev  = history[-2]["close"] if history and len(history)>1 else close * (1 - thr/2)
    if (close - prev)/max(prev,1e-9) > thr: 
        return {"action":"buy","confidence":0.7,"reason":"mom_up"}
    return {"action":"sell","confidence":0.6,"reason":"mom_down"}
PY

cat > ai/strategies/crossover.py <<'PY'
DEFAULT_CONFIG = {"fast": 5, "slow": 10, "symbol": "AAPL"}

def name(): return "crossover"

def generate_signal(history=None, cfg=None):
    cfg = (cfg or DEFAULT_CONFIG).copy()
    f, s = int(cfg.get("fast",5)), int(cfg.get("slow",10))
    arr = [h["close"] for h in (history or [])][-max(f,s):]
    if len(arr) < max(f,s): return {"action":"hold","confidence":0.0,"reason":"insufficient"}
    def sma(n): 
        a = arr[-n:]
        return sum(a)/len(a) if a else 0
    if sma(f) > sma(s): return {"action":"buy","confidence":0.65,"reason":"golden_cross"}
    return {"action":"sell","confidence":0.65,"reason":"death_cross"}
PY

cat > ai/strategies/mean_reversion.py <<'PY'
DEFAULT_CONFIG = {"lookback": 14, "band": 2.0, "symbol": "AAPL"}

def name(): return "mean_reversion"

def generate_signal(history=None, cfg=None):
    cfg = (cfg or DEFAULT_CONFIG).copy()
    n = int(cfg.get("lookback",14))
    arr = [h["close"] for h in (history or [])][-n:]
    if len(arr) < n: return {"action":"hold","confidence":0.0,"reason":"insufficient"}
    mean = sum(arr)/n
    last = arr[-1]
    band = float(cfg.get("band",2.0)) * (max(arr)-min(arr)+1e-9)/n
    if last < mean - band: return {"action":"buy","confidence":0.6,"reason":"below_band"}
    if last > mean + band: return {"action":"sell","confidence":0.6,"reason":"above_band"}
    return {"action":"hold","confidence":0.3,"reason":"inside_band"}
PY

# 3) backend main.py (v3.2 look + strategy endpoints)
cat > backend/main.py <<'PY'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, json, time, asyncio, random, datetime, uuid, importlib, traceback

app = FastAPI(title="AI Money Web :: NeoLight v3.2 + Strategy Bridge")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------- models ----------
class PaperTradeRequest(BaseModel):
    symbol: str
    price: float
    action: str
    qty: float = 1.0

class StrategyConfig(BaseModel):
    name: str
    params: dict = {}

# ---------- views ----------
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ---------- strategies ----------
@app.get("/api/strategies")
def list_strategies():
    os.makedirs("ai/strategies", exist_ok=True)
    names = [f[:-3] for f in os.listdir("ai/strategies") if f.endswith(".py")]
    if not names:
        names = ["momentum","crossover","mean_reversion"]
    return {"strategies": names}

@app.get("/api/strategy_default")
def strategy_default(name: str):
    try:
        mod = importlib.import_module(f"ai.strategies.{name}")
        defaults = getattr(mod, "DEFAULT_CONFIG", {})
        return {"name": name, "params": defaults}
    except Exception:
        raise HTTPException(status_code=404, detail="strategy not found")

@app.get("/api/strategy_config")
def strategy_config_get():
    p = "runtime/strategy_config.json"
    if os.path.exists(p):
        return json.load(open(p))
    # fallback default
    return {"name":"momentum","params":{"window":5,"threshold":0.01,"symbol":"AAPL"}}

@app.post("/api/strategy_config")
def strategy_config_set(cfg: StrategyConfig):
    os.makedirs("runtime", exist_ok=True)
    with open("runtime/strategy_config.json","w") as f:
        json.dump(cfg.model_dump(), f, indent=2)
    # also append a command for daemon
    with open("runtime/commands.jsonl","a") as f:
        f.write(json.dumps({"ts":time.time(),"cmd":"reload_config"})+"\n")
    return {"status":"ok","saved":cfg.model_dump()}

@app.post("/api/strategy/apply")
def strategy_apply():
    os.makedirs("runtime", exist_ok=True)
    with open("runtime/commands.jsonl","a") as f:
        f.write(json.dumps({"ts":time.time(),"cmd":"apply"})+"\n")
    return {"status":"ok","applied":True}

# ---------- trading ----------
@app.post("/api/paper_trade")
def paper_trade(req: PaperTradeRequest):
    os.makedirs("runtime", exist_ok=True)
    t = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": req.symbol, "price": req.price,
        "action": req.action, "qty": req.qty
    }
    with open("runtime/orders.jsonl","a") as f:
        f.write(json.dumps(t)+"\n")
    return {"status":"executed","trade":t}

# ---------- performance (simple rolling calc) ----------
@app.get("/api/performance")
def performance():
    p = "runtime/orders.jsonl"
    if not os.path.exists(p): return {"pnl":0,"win_rate":0,"sharpe":0}
    prices, actions = [], []
    with open(p) as f:
        for ln in f:
            try:
                t = json.loads(ln)
                prices.append(float(t["price"])); actions.append(t["action"])
            except: pass
    if len(prices)<2: return {"pnl":0,"win_rate":0,"sharpe":0}
    diffs = [p2-p1 for p1,p2 in zip(prices,prices[1:])]
    pnl = sum(d if actions[i]=="buy" else -d for i,d in enumerate(diffs))
    gains = [max(0,d) for d in diffs]; losses = [abs(d) for d in diffs if d<0]
    win_rate = len(gains)/(len(gains)+len(losses)) if (gains or losses) else 0
    import statistics, math
    rets = [(p2/p1-1) for p1,p2 in zip(prices,prices[1:]) if p1>0]
    sharpe = statistics.mean(rets)/statistics.stdev(rets)*math.sqrt(252) if len(rets)>1 and statistics.stdev(rets)>0 else 0
    return {"pnl":round(pnl,2),"win_rate":round(win_rate,3),"sharpe":round(sharpe,2)}

# ---------- websocket (synthetic candles + kpis) ----------
@app.websocket("/ws")
async def ws_feed(ws: WebSocket):
    await ws.accept()
    base = 200.0
    while True:
        o = base + random.uniform(-1,1)
        h = o + random.uniform(0,2)
        l = o - random.uniform(0,2)
        c = l + random.uniform(0, max(0.1, h-l))
        payload = {
            "ts": int(time.time()*1000),
            "ohlc": {"open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)},
            "kpis": {
                "balance": 10000 + random.uniform(-120,120),
                "profit": random.uniform(-2,2),
                "loss": random.uniform(-1,1)
            }
        }
        await ws.send_json(payload)
        await asyncio.sleep(1)
PY

# 4) template (strategy panel wired; v3.2 layout; fixed bg on body)
cat > templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>NeoLight v3.2 — Strategy Bridge</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <header class="top neon">
    <div class="brand">🧠 AI Money Web :: NeoLight v3.2</div>
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
      <section id="live" class="panel neon">
        <h2>Live Candles</h2>
        <div id="candles"></div>
      </section>

      <section id="kpi" class="grid3">
        <div class="panel neon"><h3>Balance</h3><div class="big" id="k_balance">$10,000</div></div>
        <div class="panel neon"><h3>Profit</h3><div class="big" id="k_profit">+0.00%</div></div>
        <div class="panel neon"><h3>Loss</h3><div class="big" id="k_loss">0.00%</div></div>
      </section>

      <section id="perf" class="panel neon">
        <h2>AI Money Web :: Performance</h2>
        <div class="perf">
          <div>PnL: <span id="pnl">$0.00</span></div>
          <div>Win Rate: <span id="win">0.0%</span></div>
          <div>Sharpe: <span id="sharpe">0.00</span></div>
        </div>
      </section>

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

      <section id="strategy" class="panel neon">
        <h2>Strategy Config (Live)</h2>
        <div class="row">
          <label>Strategy
            <select id="s_name"></select>
          </label>
          <button id="btnLoadDefault">Load Defaults</button>
          <button id="btnSaveApply">Save & Apply</button>
        </div>
        <label>Params (JSON)
          <textarea id="s_params" rows="10">{}</textarea>
        </label>
        <pre id="stratOut" class="console"></pre>
      </section>

      <section id="system" class="grid2">
        <div class="panel neon">
          <h2>System</h2>
          <pre id="sys" class="console"></pre>
        </div>
        <div class="panel neon">
          <h2>Notes</h2>
          <pre class="console">Config saved to runtime/strategy_config.json
Daemon listens to runtime/commands.jsonl → {"cmd":"reload_config"}</pre>
        </div>
      </section>
    </main>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
HTML

# 5) CSS (v3.2 look; fixed full-page city bg)
cat > static/style.css <<'CSS'
:root{
  --bg:#07090e; --panel:#0f131b; --cyan:#00f5ff; --red:#ff2d2d; --amber:#ffb000; --ink:#cfe9ff;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; color:var(--ink);
  font-family:"Share Tech Mono", ui-monospace, Menlo, monospace;
  background:var(--bg);
}
body::before{
  content:""; position:fixed; inset:0; z-index:-1;
  background:url('/static/city_bg.gif') center/cover no-repeat;
  opacity:0.25; filter:contrast(1.05) brightness(0.9);
}
a{color:var(--cyan); text-decoration:none}
.neon{border:1.5px solid var(--cyan); border-radius:14px; box-shadow:0 0 12px rgba(0,245,255,.35), inset 0 0 18px rgba(0,245,255,.08); background:linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0))}
.top{position:sticky;top:0;z-index:50;display:flex;gap:18px;align-items:center;justify-content:space-between;margin:10px;padding:10px 16px}
.brand{font-family:"Press Start 2P", monospace;color:var(--red);font-size:18px;letter-spacing:1.6px;text-shadow:0 0 10px rgba(255,45,45,.65)}
.anchors a{margin:0 8px}
.layout{display:grid;grid-template-columns:230px 1fr;gap:12px;padding:10px}
.sidenav{position:sticky; top:68px; height:calc(100vh - 86px); overflow:auto; padding:10px; display:flex; flex-direction:column; gap:10px}
.content{min-height:100vh; display:flex; flex-direction:column; gap:14px}
.panel{padding:12px; background:var(--panel)}
.grid3{display:grid; grid-template-columns:repeat(3,1fr); gap:14px}
.grid2{display:grid; grid-template-columns:1fr 1fr; gap:14px}
.big{font-size:22px}
.console{background:#061018; border:1px dashed rgba(0,245,255,.35); padding:8px; height:200px; overflow:auto; font-size:12px}
.form{display:grid; gap:10px; grid-template-columns:repeat(4,1fr); align-items:end}
.form textarea{grid-column:1/-1}
.form button{grid-column:1/-1; padding:8px 10px; background:var(--cyan); color:#001419; border:none; border-radius:8px; font-weight:700; cursor:pointer}
h2,h3{margin:6px 0 12px 0}
#candles{height:400px}
CSS

# 6) JS (wire defaults, save/apply, live charts)
cat > static/app.js <<'JSCODE'
const $  = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const fmt = n => (Math.abs(n)>=1? n.toFixed(2): n.toFixed(4));
async function jget(u){ const r=await fetch(u); return r.json(); }
async function jpost(u,b){ const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})}); return r.json(); }

// ---- lightweight-charts
const chart = LightweightCharts.createChart($('#candles'),{
  layout:{background:{type:'solid',color:'transparent'},textColor:'#b5eaff'},
  grid:{vertLines:{visible:false},horzLines:{visible:false}},
  rightPriceScale:{borderVisible:false}, timeScale:{borderVisible:false}
});
const series = chart.addCandlestickSeries({ upColor:'#00ff88', downColor:'#ff2d2d', borderUpColor:'#00ff88', borderDownColor:'#ff2d2d', wickUpColor:'#00ff88', wickDownColor:'#ff2d2d'});

const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onmessage = ev => {
  const d = JSON.parse(ev.data);
  series.update({ time:Math.floor(d.ts/1000), ...d.ohlc });
  $('#k_balance').textContent = `$${fmt(d.kpis.balance)}`;
  $('#k_profit').textContent = `${d.kpis.profit>=0?'+':''}${fmt(d.kpis.profit)}%`;
  $('#k_loss').textContent = `${fmt(d.kpis.loss)}%`;
};

// ---- performance
async function refreshPerf(){
  const p = await jget('/api/performance');
  $('#pnl').textContent = `$${fmt(p.pnl)}`;
  $('#win').textContent = `${(p.win_rate*100).toFixed(1)}%`;
  $('#sharpe').textContent = `${fmt(p.sharpe)}`;
}
setInterval(refreshPerf, 4000); refreshPerf();

// ---- trade
$('#tradeForm').addEventListener('submit', async e=>{
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

// ---- strategy: list + load defaults + load saved + save/apply
async function loadStrategyList(){
  const data = await jget('/api/strategies');
  const sel = $('#s_name'); sel.innerHTML='';
  (data.strategies||[]).forEach(n=>{
    const o = document.createElement('option'); o.value = o.textContent = n; sel.appendChild(o);
  });
}
async function loadSaved(){
  const cfg = await jget('/api/strategy_config');
  $('#s_name').value = cfg.name || 'momentum';
  $('#s_params').value = JSON.stringify(cfg.params || {}, null, 2);
  $('#stratOut').textContent = 'loaded saved config';
}
async function loadDefaults(){
  const name = $('#s_name').value;
  const d = await jget('/api/strategy_default?name='+encodeURIComponent(name));
  $('#s_params').value = JSON.stringify(d.params || {}, null, 2);
  $('#stratOut').textContent = 'loaded defaults for '+name;
}
async function saveApply(){
  let params={}; try{ params=JSON.parse($('#s_params').value||'{}'); }catch(e){ $('#stratOut').textContent='⚠️ JSON error: '+e.message; return; }
  const name = $('#s_name').value;
  const save = await jpost('/api/strategy_config', {name, params});
  const apply = await jpost('/api/strategy/apply', {});
  $('#stratOut').textContent = JSON.stringify({save, apply}, null, 2);
}
$('#btnLoadDefault').addEventListener('click', loadDefaults);
$('#btnSaveApply').addEventListener('click', saveApply);
$('#s_name').addEventListener('change', loadDefaults);

(async ()=>{ await loadStrategyList(); await loadSaved(); })();
JSCODE

# 7) Strategy Daemon (hot-reload on commands + simple signal -> order demo)
cat > tools/strategy_daemon.py <<'PY'
import os, json, time, importlib, random, datetime

CFG_PATH = "runtime/strategy_config.json"
CMD_PATH = "runtime/commands.jsonl"
ORDERS   = "runtime/orders.jsonl"
HIST     = []  # in-memory OHLC history for strategy inputs

def load_cfg():
    if not os.path.exists(CFG_PATH):
        return {"name":"momentum","params":{"window":5,"threshold":0.01,"symbol":"AAPL"}}
    with open(CFG_PATH) as f: return json.load(f)

def next_bar(prev=200.0):
    o = prev + random.uniform(-1, 1)
    h = o + random.uniform(0, 2)
    l = o - random.uniform(0, 2)
    c = l + random.uniform(0, max(0.1, h-l))
    return {"time":int(time.time()), "open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)}

def maybe_apply_command(last_pos):
    if not os.path.exists(CMD_PATH): return last_pos
    # read last command
    with open(CMD_PATH) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines: return last_pos
    try:
        cmd = json.loads(lines[-1])
        if cmd.get("cmd") in ("reload_config","apply"):
            print("[daemon] applying new config…")
            return None  # force reload
    except: pass
    return last_pos

def write_order(symbol, price, action, qty=1.0):
    os.makedirs("runtime", exist_ok=True)
    t = {"id": str(int(time.time()*1000))[-8:], "timestamp": datetime.datetime.utcnow().isoformat(),
         "symbol": symbol, "price": price, "action": action, "qty": qty}
    with open(ORDERS,"a") as f: f.write(json.dumps(t)+"\n")
    print("[daemon] order:", t)

def main():
    print("[daemon] strategy daemon online")
    cfg = load_cfg(); last_loaded = time.time(); module=None
    try:
        module = importlib.import_module(f"ai.strategies.{cfg['name']}")
    except Exception as e:
        print("[daemon] strategy load error:", e)

    last_close = 200.0
    position = None  # "long" or "short"
    while True:
        position = maybe_apply_command(position)
        if position is None:
            # reload
            cfg = load_cfg()
            try:
                module = importlib.import_module(f"ai.strategies.{cfg['name']}")
                importlib.reload(module)
                print("[daemon] loaded", cfg["name"], "params:", cfg.get("params"))
            except Exception as e:
                print("[daemon] reload error:", e)
            position = "flat"

        bar = next_bar(last_close); last_close = bar["close"]
        HIST.append(bar); HIST[:] = HIST[-200:]

        try:
            sig = getattr(module, "generate_signal")(HIST, cfg.get("params"))
        except Exception as e:
            print("[daemon] signal error:", e); sig={"action":"hold","confidence":0,"reason":"error"}

        # extremely basic execution demo: place a 1-qty order on buy/sell
        if sig["action"] in ("buy","sell"):
            write_order(cfg["params"].get("symbol","AAPL"), last_close, sig["action"], 1.0)

        time.sleep(1.0)

if __name__ == "__main__":
    main()
PY

# 8) assets (ensure backgrounds exist)
cp /mnt/data/94ad2ced2bb9305b9e43c4e777b.gif static/city_bg.gif 2>/dev/null || true
cp /mnt/data/0226f526bbb43af1397cddb2ca6babf0.jpg static/cyber_side.jpg 2>/dev/null || true

# 9) deps + start
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" python-dotenv >/dev/null

echo "🚀 Starting backend…"
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "✅ Dashboard → http://127.0.0.1:8000/dashboard"
echo "🤖 Run the daemon in another shell:  python tools/strategy_daemon.py"

