#!/bin/bash
# ============================================================
# AI Money Web :: Phase 461–470 — NeoLight v3.1 Day/Night Mode
# - Dynamic theme by local time (dawn/day/dusk/night)
# - City lights fade + manual theme toggle
# - Keeps live WS candles, KPIs, Trade, Strategy list
# ============================================================
set -e

echo "🌗 NeoLight v3.1 — Day/Night Mode…"

# 0) Clean port
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing PID $pid on :8000"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1) Ensure structure + backups
mkdir -p backend templates static runtime logs backups ai/strategies
[ -f backend/main.py ] && cp backend/main.py backups/main.py.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f templates/index.html ] && cp templates/index.html backups/index.html.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/style.css ] && cp static/style.css backups/style.css.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/app.js ] && cp static/app.js backups/app.js.$(date +"%Y%m%d_%H%M%S").bak || true

# 2) Backend (keeps previous features; adds /api/time for server time if you want it)
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, json, time, asyncio, random, datetime, uuid

app = FastAPI(title="AI Money Web :: NeoLight v3.1")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class PaperTradeRequest(BaseModel):
    symbol: str
    price: float
    action: str
    qty: float = 1

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dash(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/time")
def api_time():
    # Server-side time (browser will mostly use local time)
    now = datetime.datetime.now()
    return {"server_iso": now.isoformat(), "hour": now.hour, "minute": now.minute}

@app.get("/api/strategies")
def list_strategies():
    os.makedirs("ai/strategies", exist_ok=True)
    files = [f[:-3] for f in os.listdir("ai/strategies") if f.endswith(".py")]
    return {"strategies": files}

@app.post("/api/strategy/run")
def run_strategy(body: dict):
    name = (body or {}).get("name", "momentum")
    os.makedirs("runtime", exist_ok=True)
    with open("runtime/last_strategy.txt","w") as f:
        f.write(name)
    return {"status":"running","strategy":name}

@app.post("/api/paper_trade")
def trade(req: PaperTradeRequest):
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

@app.websocket("/ws")
async def ws_feed(ws: WebSocket):
    await ws.accept()
    base = 200.0
    while True:
        o = base + random.uniform(-1, 1)
        h = o + random.uniform(0, 2)
        l = o - random.uniform(0, 2)
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
PYCODE

# 3) Template (adds Theme Toggle)
cat > templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>NeoLight v3.1 — Dynamic Day/Night</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <header class="top neon">
    <div class="brand">🧠 AI Money Web :: NeoLight v3.1</div>
    <div class="actions">
      <label class="toggle">Theme:
        <select id="themeSelect">
          <option value="auto">Auto (Local Time)</option>
          <option value="dawn">Dawn</option>
          <option value="day">Day</option>
          <option value="dusk">Dusk</option>
          <option value="night">Night</option>
        </select>
      </label>
    </div>
  </header>

  <div class="layout">
    <aside class="sidenav" style="background-image:url('/static/cyber_side.jpg')">
      <nav>
        <a href="#live">📈 Live</a>
        <a href="#kpi">🧪 KPIs</a>
        <a href="#trade">💸 Trade</a>
        <a href="#strategy">🧠 Strategy</a>
        <a href="#system">⚙️ System</a>
      </nav>
    </aside>

    <main class="content">
      <section id="live" class="panel neon cityStage">
        <div class="cityBackdrop"></div>
        <h2>Live Candles</h2>
        <div id="candles"></div>
      </section>

      <section id="kpi" class="grid3">
        <div class="panel neon"><h3>Balance</h3><div class="big" id="bal">$10,000</div></div>
        <div class="panel neon"><h3>Profit</h3><div class="big" id="pro">+0.00%</div></div>
        <div class="panel neon"><h3>Loss</h3><div class="big" id="los">0.00%</div></div>
      </section>

      <section id="trade" class="panel neon">
        <h2>Quick Trade</h2>
        <form id="tradeForm" class="form">
          <label>Symbol <input id="sym" value="BTC/USD"/></label>
          <label>Price <input id="price" type="number" step="0.01" value="63000"/></label>
          <label>Action 
            <select id="act"><option>buy</option><option>sell</option></select>
          </label>
          <label>Qty <input id="qty" type="number" step="0.01" value="0.01"/></label>
          <button>Execute</button>
        </form>
        <pre id="out" class="console"></pre>
      </section>

      <section id="strategy" class="panel neon">
        <h2>Strategies</h2>
        <div class="row">
          <select id="strategySelect"></select>
          <button id="runStrategy">Run Selected</button>
        </div>
        <pre id="stratOut" class="console"></pre>
      </section>

      <section id="system" class="panel neon">
        <h2>System</h2>
        <pre id="sys" class="console"></pre>
      </section>
    </main>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
HTML

# 4) CSS (themes + animations + scrolling)
cat > static/style.css <<'CSS'
:root{
  --ink:#d7ecff; --cyan:#00f5ff; --red:#ff2d2d; --amber:#ffb000;
  --bg:#05070c; --panel:rgba(0,0,0,.55); --glow:rgba(0,245,255,.3);
  --city-brightness:1; --city-opacity:.9;
}
/* Theme palettes */
:root[data-theme="dawn"] { --bg:#0b0f1a; --city-brightness:1.1; --city-opacity:.85; }
:root[data-theme="day"]  { --bg:#0d1320; --city-brightness:1.0; --city-opacity:.75; }
:root[data-theme="dusk"] { --bg:#080b14; --city-brightness:1.2; --city-opacity:.92; }
:root[data-theme="night"]{ --bg:#04060a; --city-brightness:1.35; --city-opacity:1; }

*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Share Tech Mono", monospace;overflow-x:hidden}
a{color:var(--cyan);text-decoration:none}

.neon{border:1.5px solid var(--cyan);border-radius:12px;box-shadow:0 0 18px var(--glow), inset 0 0 12px rgba(0,245,255,.07)}
.top{position:sticky;top:0;z-index:1000;margin:10px;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,.7)}
.brand{font-family:"Press Start 2P";color:var(--red);text-shadow:0 0 10px rgba(255,45,45,.7)}
.toggle select{margin-left:6px}

.layout{display:grid;grid-template-columns:260px 1fr;gap:12px;padding:10px}
.sidenav{position:sticky;top:64px;height:calc(100vh - 74px);overflow:auto;background-size:cover;background-position:center;border-radius:12px;padding:16px}
.sidenav nav a{display:block;margin:10px 0;font-family:Orbitron, sans-serif;font-size:18px;text-shadow:0 0 10px var(--cyan)}
.content{display:flex;flex-direction:column;gap:14px}

.panel{background:var(--panel);padding:14px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.big{font-size:22px}

.cityStage{position:relative;min-height:420px;overflow:hidden}
.cityBackdrop{
  position:absolute;inset:0;background:url('/static/city_bg.gif') center/cover no-repeat;
  filter:brightness(var(--city-brightness)); opacity:var(--city-opacity);
  animation:pulse 16s ease-in-out infinite;
}
@keyframes pulse{0%{filter:brightness(calc(var(--city-brightness) * .95))}50%{filter:brightness(calc(var(--city-brightness) * 1.05))}100%{filter:brightness(calc(var(--city-brightness) * .95))}}
#candles{position:relative;height:400px}

.form{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;align-items:end}
.form button{grid-column:1/-1;background:var(--cyan);color:#012;padding:8px 10px;border:none;border-radius:8px;font-weight:700;cursor:pointer}
.row{display:flex;gap:10px;align-items:center}
.console{background:#061118;border:1px dashed rgba(0,245,255,.35);padding:8px;border-radius:8px;overflow:auto;max-height:220px}
CSS

# 5) JS (theme engine + city fade + existing features)
cat > static/app.js <<'JSCODE'
const $ = s=>document.querySelector(s);

// ---- Theme Engine ----
const root = document.documentElement;
const themeSelect = $("#themeSelect");

function themeFromHour(h){
  // Dawn 5-8, Day 9-16, Dusk 17-19, Night 20-4
  if (h>=5 && h<=8) return "dawn";
  if (h>=9 && h<=16) return "day";
  if (h>=17 && h<=19) return "dusk";
  return "night";
}

function applyTheme(t){
  root.setAttribute("data-theme", t);
}

function autoThemeTick(){
  if (themeSelect.value !== "auto") return;
  const h = new Date().getHours();
  applyTheme(themeFromHour(h));
}
themeSelect.addEventListener("change", ()=>{
  const v = themeSelect.value;
  if (v === "auto") autoThemeTick(); else applyTheme(v);
});
autoThemeTick(); setInterval(autoThemeTick, 60*1000);

// ---- Candles (Lightweight Charts) ----
const chart = LightweightCharts.createChart(document.getElementById("candles"), {
  layout:{ background:{ type:"solid", color:"transparent"}, textColor:"#bde" },
  grid:{ vertLines:{ visible:false }, horzLines:{ visible:false } },
  rightPriceScale:{ borderVisible:false }, timeScale:{ borderVisible:false }
});
const series = chart.addCandlestickSeries({
  upColor:"#00ff88", downColor:"#ff2d2d", borderUpColor:"#00ff88", borderDownColor:"#ff2d2d", wickUpColor:"#00ff88", wickDownColor:"#ff2d2d"
});

// ---- WebSocket live feed & KPI updates ----
const ws = new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
ws.onmessage = ev=>{
  const d = JSON.parse(ev.data);
  series.update({ time:Math.floor(d.ts/1000), ...d.ohlc });
  $("#bal").textContent = "$"+d.kpis.balance.toFixed(2);
  $("#pro").textContent = (d.kpis.profit>=0?"+":"")+d.kpis.profit.toFixed(2)+"%";
  $("#los").textContent = d.kpis.loss.toFixed(2)+"%";
};

// ---- Quick Trade ----
$("#tradeForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const body = {
    symbol: $("#sym").value.trim(),
    price: parseFloat($("#price").value),
    action: $("#act").value,
    qty: parseFloat($("#qty").value)
  };
  const r = await fetch("/api/paper_trade",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const j = await r.json();
  $("#out").textContent = JSON.stringify(j,null,2);
});

// ---- Strategy list + run ----
async function loadStrategies(){
  const r = await fetch("/api/strategies"); const j = await r.json();
  const sel = $("#strategySelect"); sel.innerHTML = "";
  (j.strategies||[]).forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; sel.appendChild(o); });
}
$("#runStrategy").addEventListener("click", async ()=>{
  const name = $("#strategySelect").value;
  const r = await fetch("/api/strategy/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
  const j = await r.json();
  $("#stratOut").textContent = JSON.stringify(j,null,2);
});
loadStrategies();

// ---- System info (sample from /api/time) ----
async function sysTick(){
  const r = await fetch("/api/time"); const j = await r.json();
  $("#sys").textContent = JSON.stringify(j,null,2);
}
sysTick(); setInterval(sysTick, 5000);
JSCODE

# 6) Assets (re-use if already present)
# If you used earlier phases, these should exist; ignore errors if not.
cp /mnt/data/94ad2ced2bb9305b9bc8b9e43c4e777b.gif static/city_bg.gif 2>/dev/null || true
cp /mnt/data/0226f526bbb43af1397cddb2ca6babf0.jpg static/cyber_side.jpg 2>/dev/null || true

# 7) Start server
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" python-dotenv >/dev/null

echo "🚀 Starting NeoLight v3.1…"
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "✅ Dashboard → http://127.0.0.1:8000/dashboard"

