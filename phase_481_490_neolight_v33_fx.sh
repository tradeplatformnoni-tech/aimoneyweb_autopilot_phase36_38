#!/bin/bash
# ============================================================
# AI Money Web :: Phase 481–490 — NeoLight v3.3 FX Pack
# - Animated gradient borders
# - Trade sound cue (WebAudio)
# - Strategy-specific colorways
# - Wallpaper fix for left nav + city gif
# ============================================================
set -e

echo "🎛  NeoLight v3.3 — FX Pack…"

# 0) Clean port
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing PID $pid on :8000"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1) Folders + backups
mkdir -p backend templates static runtime logs backups ai/strategies
[ -f backend/main.py ] && cp backend/main.py "backups/main.py.$(date +"%Y%m%d_%H%M%S").bak" || true
[ -f templates/index.html ] && cp templates/index.html "backups/index.html.$(date +"%Y%m%d_%H%M%S").bak" || true
[ -f static/style.css ] && cp static/style.css "backups/style.css.$(date +"%Y%m%d_%H%M%S").bak" || true
[ -f static/app.js ] && cp static/app.js "backups/app.js.$(date +"%Y%m%d_%H%M%S").bak" || true

# 2) Backend (keeps v3.2 endpoints)
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, json, time, asyncio, random, datetime, uuid

app = FastAPI(title="AI Money Web :: NeoLight v3.3")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class PaperTradeRequest(BaseModel):
    symbol: str
    price: float
    action: str
    qty: float = 1.0

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dash(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/strategies")
def list_strategies():
    os.makedirs("ai/strategies", exist_ok=True)
    # ensure some defaults exist for the selector if folder empty
    defaults = ["momentum", "crossover", "mean_reversion"]
    files = [f[:-3] for f in os.listdir("ai/strategies") if f.endswith(".py")]
    return {"strategies": files or defaults}

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

# 3) Template (adds strategy color hint + audio-ready)
cat > templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>NeoLight v3.3 — FX Pack</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <header class="top neon fx-border">
    <div class="brand">🧠 AI Money Web :: NeoLight v3.3</div>
    <div class="actions">
      <span class="tag" id="strategyTag">strategy: momentum</span>
    </div>
  </header>

  <div class="layout">
    <aside class="sidenav dimmable" id="leftNav">
      <nav>
        <a href="#live">📈 Live</a>
        <a href="#kpi">🧪 KPIs</a>
        <a href="#trade">💸 Trade</a>
        <a href="#strategy">🧠 Strategy</a>
        <a href="#system">⚙️ System</a>
      </nav>
    </aside>

    <main class="content">
      <section id="live" class="panel neon fx-border cityStage">
        <div class="cityBackdrop"></div>
        <h2>Live Candles</h2>
        <div id="candles"></div>
      </section>

      <section id="kpi" class="grid3">
        <div class="panel neon fx-border"><h3>Balance</h3><div class="big" id="bal">$10,000</div></div>
        <div class="panel neon fx-border"><h3>Profit</h3><div class="big" id="pro">+0.00%</div></div>
        <div class="panel neon fx-border"><h3>Loss</h3><div class="big" id="los">0.00%</div></div>
      </section>

      <section id="trade" class="panel neon fx-border">
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

      <section id="strategy" class="panel neon fx-border">
        <h2>Strategies</h2>
        <div class="row">
          <select id="strategySelect"></select>
          <button id="runStrategy">Run Selected</button>
        </div>
        <pre id="stratOut" class="console"></pre>
      </section>

      <section id="system" class="panel neon fx-border">
        <h2>System</h2>
        <pre id="sys" class="console"></pre>
      </section>
    </main>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
HTML

# 4) CSS (animated gradient borders + wallpaper fix)
cat > static/style.css <<'CSS'
:root{
  --ink:#d7ecff; --cyan:#00f5ff; --red:#ff2d2d; --amber:#ffb000;
  --bg:#05070c; --panel:rgba(0,0,0,.55);
  --hue:180; /* will shift per strategy */
  --city-brightness:1.2; --city-opacity:.9;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Share Tech Mono", monospace;overflow-x:hidden}
a{color:var(--cyan);text-decoration:none}

.top{position:sticky;top:0;z-index:1000;margin:10px;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,.7)}
.brand{font-family:"Press Start 2P";color:var(--red);text-shadow:0 0 10px rgba(255,45,45,.7)}
.tag{font-family:Orbitron, sans-serif;color:#9ef}

.layout{display:grid;grid-template-columns:260px 1fr;gap:12px;padding:10px}
.sidenav{
  position:sticky; top:64px; height:calc(100vh - 74px); overflow:auto; border-radius:12px; padding:16px;
  background-image:url('/static/cyber_side.jpg'); background-size:cover; background-position:center;
  filter:brightness(.85) saturate(1.05);
}
.sidenav nav a{display:block;margin:10px 0;font-family:Orbitron, sans-serif;font-size:18px;text-shadow:0 0 10px var(--cyan)}
.content{display:flex;flex-direction:column;gap:14px}

/* Panels */
.panel{background:var(--panel);padding:14px;border-radius:12px;border:1.5px solid rgba(0,245,255,.4)}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.big{font-size:22px}

/* City stage */
.cityStage{position:relative;min-height:420px;overflow:hidden}
.cityBackdrop{
  position:absolute;inset:0;background:url('/static/city_bg.gif') center/cover no-repeat;
  filter:brightness(var(--city-brightness)); opacity:var(--city-opacity); animation:pulse 16s ease-in-out infinite;
}
@keyframes pulse{0%{filter:brightness(1)}50%{filter:brightness(1.1)}100%{filter:brightness(1)}}
#candles{position:relative;height:400px}

/* Animated gradient border (FX) */
.fx-border{
  position:relative;
}
.fx-border::before{
  content:""; position:absolute; inset:-2px; border-radius:14px; z-index:-1;
  background: conic-gradient(from 0deg, 
    hsl(var(--hue) 100% 60%), 
    hsl(calc(var(--hue)+60) 100% 55%), 
    hsl(calc(var(--hue)+120) 100% 60%), 
    hsl(calc(var(--hue)+180) 100% 55%), 
    hsl(calc(var(--hue)+240) 100% 60%), 
    hsl(calc(var(--hue)+300) 100% 55%), 
    hsl(var(--hue) 100% 60%)
  );
  filter: blur(6px) saturate(1.2); opacity:.55;
  animation:borderSpin 18s linear infinite;
}
@keyframes borderSpin{to{transform:rotate(360deg)}}

/* Forms / console */
.form{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;align-items:end}
.form button{grid-column:1/-1;background:var(--cyan);color:#012;padding:8px 10px;border:none;border-radius:8px;font-weight:700;cursor:pointer}
.row{display:flex;gap:10px;align-items:center}
.console{background:#061118;border:1px dashed rgba(0,245,255,.35);padding:8px;border-radius:8px;overflow:auto;max-height:220px}

/* Strategy colorways (changes hue) */
:root[data-strategy="momentum"]{ --hue:180 }
:root[data-strategy="crossover"]{ --hue:300 }
:root[data-strategy="mean_reversion"]{ --hue:45 }
CSS

# 5) JS (WebAudio sound, strategy colorway, wallpaper guarantee)
cat > static/app.js <<'JSCODE'
const $ = s=>document.querySelector(s);
const root = document.documentElement;
const tag = $("#strategyTag");

/* --- Guarantee wallpaper is visible (in case CSS failed earlier) --- */
(function ensureWallpaper(){
  const nav = document.getElementById("leftNav");
  const img = "url('/static/cyber_side.jpg')";
  const applied = getComputedStyle(nav).backgroundImage;
  if (!applied || applied === "none") {
    nav.style.backgroundImage = img;
    nav.style.backgroundSize = "cover";
    nav.style.backgroundPosition = "center";
  }
})();

/* --- Lightweight Charts --- */
const chart = LightweightCharts.createChart(document.getElementById("candles"), {
  layout:{ background:{ type:"solid", color:"transparent"}, textColor:"#bde" },
  grid:{ vertLines:{ visible:false }, horzLines:{ visible:false } },
  rightPriceScale:{ borderVisible:false }, timeScale:{ borderVisible:false }
});
const series = chart.addCandlestickSeries({
  upColor:"#00ff88", downColor:"#ff2d2d", borderUpColor:"#00ff88", borderDownColor:"#ff2d2d", wickUpColor:"#00ff88", wickDownColor:"#ff2d2d"
});

/* --- WebSocket feed --- */
const ws = new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
ws.onmessage = ev=>{
  const d = JSON.parse(ev.data);
  series.update({ time:Math.floor(d.ts/1000), ...d.ohlc });
  $("#bal").textContent = "$"+d.kpis.balance.toFixed(2);
  $("#pro").textContent = (d.kpis.profit>=0?"+":"")+d.kpis.profit.toFixed(2)+"%";
  $("#los").textContent = d.kpis.loss.toFixed(2)+"%";
};

/* --- Trade sound cue (WebAudio beep chord) --- */
let audioCtx;
function playTradeSound(success=true){
  try{
    audioCtx = audioCtx || new (window.AudioContext||window.webkitAudioContext)();
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type = "sawtooth";
    o.frequency.value = success ? 880 : 220;
    g.gain.value = 0.02;
    o.connect(g); g.connect(audioCtx.destination);
    o.start();
    setTimeout(()=>o.stop(), 140);
  }catch(e){ /* ignore */ }
}

/* --- Quick Trade --- */
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
  if (j && j.status === "executed") playTradeSound(true); else playTradeSound(false);
});

/* --- Strategies: list + run + colorway --- */
async function loadStrategies(){
  const r = await fetch("/api/strategies"); const j = await r.json();
  const sel = $("#strategySelect"); sel.innerHTML="";
  (j.strategies||[]).forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; sel.appendChild(o); });
}
$("#runStrategy").addEventListener("click", async ()=>{
  const name = $("#strategySelect").value || "momentum";
  const r = await fetch("/api/strategy/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
  const j = await r.json();
  $("#stratOut").textContent = JSON.stringify(j,null,2);
  tag.textContent = "strategy: " + name;
  root.setAttribute("data-strategy", name);   // updates --hue → animated borders change color family
});
loadStrategies();

/* --- System tick (basic time) --- */
async function sysTick(){
  const t = new Date();
  $("#sys").textContent = JSON.stringify({local:t.toLocaleString()}, null, 2);
}
setInterval(sysTick, 3000); sysTick();
JSCODE

# 6) Assets — ensure backgrounds exist (copy from uploads)
cp /mnt/data/94ad2ced2bb9305b9e43c4e777b.gif static/city_bg.gif 2>/dev/null || true
cp /mnt/data/0226f526bbb43af1397cddb2ca6babf0.jpg static/cyber_side.jpg 2>/dev/null || true

# 7) Start
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" python-dotenv >/dev/null

echo "🚀 Starting NeoLight v3.3…"
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "✅ Dashboard → http://127.0.0.1:8000/dashboard"

