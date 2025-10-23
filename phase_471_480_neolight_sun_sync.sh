#!/bin/bash
# ============================================================
# AI Money Web :: Phase 471–480 — NeoLight v3.2 Sun-Synced Theme
# - Uses .env LAT, LON (and optional TZ) to compute sunrise/sunset
# - Dims left-nav wallpaper during day, brightens at night
# - Keeps Live, KPIs, Quick Trade, Strategy controls
# ============================================================
set -e

echo "🌅 NeoLight v3.2 — Sun-Synced Theme…"

# 0) kill any server on :8000
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing PID $pid on :8000"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1) folders + backups
mkdir -p backend templates static runtime logs backups ai/strategies
[ -f backend/main.py ] && cp backend/main.py "backups/main.py.$(date +"%Y%m%d_%H%M%S").bak" || true
[ -f templates/index.html ] && cp templates/index.html "backups/index.html.$(date +"%Y%m%d_%H%M%S").bak" || true
[ -f static/style.css ] && cp static/style.css "backups/style.css.$(date +"%Y%m%d_%H%M%S").bak" || true
[ -f static/app.js ] && cp static/app.js "backups/app.js.$(date +"%Y%m%d_%H%M%S").bak" || true

# 2) backend
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, json, time, asyncio, random, datetime, uuid

# Astral for sunrise/sunset
try:
    from astral import LocationInfo
    from astral.sun import sun
except Exception as e:
    LocationInfo = None
    sun = None

app = FastAPI(title="AI Money Web :: NeoLight v3.2")
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

@app.get("/api/time")
def api_time():
    now = datetime.datetime.now()
    return {"server_iso": now.isoformat(), "hour": now.hour, "minute": now.minute}

@app.get("/api/sun")
def api_sun():
    """Return sunrise/sunset times for today using .env LAT, LON (and optional TZ)."""
    lat = os.getenv("LAT")
    lon = os.getenv("LON")
    tz = os.getenv("TZ", "UTC")
    if not (lat and lon):
        # Fallback fixed times (day 8–18)
        today = datetime.date.today()
        sunrise = datetime.datetime.combine(today, datetime.time(8,0)).isoformat()
        sunset  = datetime.datetime.combine(today, datetime.time(18,0)).isoformat()
        return {"ok": False, "reason": "LAT/LON not set in .env", "sunrise": sunrise, "sunset": sunset, "tz": tz}
    try:
        if LocationInfo is None or sun is None:
            raise RuntimeError("astral not available")
        loc = LocationInfo(latitude=float(lat), longitude=float(lon), timezone=tz)
        s = sun(loc.observer, date=datetime.date.today(), tzinfo=datetime.timezone.utc)
        # send UTC ISO strings; browser will convert to local
        return {"ok": True, "sunrise_utc": s["sunrise"].isoformat(), "sunset_utc": s["sunset"].isoformat(), "tz": tz}
    except Exception as e:
        today = datetime.date.today()
        sunrise = datetime.datetime.combine(today, datetime.time(8,0)).isoformat()
        sunset  = datetime.datetime.combine(today, datetime.time(18,0)).isoformat()
        return {"ok": False, "reason": str(e), "sunrise": sunrise, "sunset": sunset, "tz": tz}

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

# 3) template
cat > templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>NeoLight v3.2 — Sun Sync</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css"/>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <header class="top neon">
    <div class="brand">🧠 AI Money Web :: NeoLight v3.2</div>
    <div class="actions">
      <label class="toggle">Theme:
        <select id="themeSelect">
          <option value="auto">Auto (Sunrise/Sunset)</option>
          <option value="dawn">Dawn</option>
          <option value="day">Day</option>
          <option value="dusk">Dusk</option>
          <option value="night">Night</option>
        </select>
      </label>
    </div>
  </header>

  <div class="layout">
    <aside class="sidenav dimmable" style="background-image:url('/static/cyber_side.jpg')">
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

# 4) css
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
.sidenav{position:sticky;top:64px;height:calc(100vh - 74px);overflow:auto;background-size:cover;background-position:center;border-radius:12px;padding:16px;transition:filter .6s ease, opacity .6s ease}
.sidenav.dimmable.day{filter:grayscale(25%) brightness(.75);opacity:.8}
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

# 5) js (sun-sync logic + all actions)
cat > static/app.js <<'JSCODE'
const $ = s=>document.querySelector(s);
const root = document.documentElement;
const themeSelect = $("#themeSelect");
const side = document.querySelector(".sidenav.dimmable");

// ---- Theme helpers ----
function setTheme(t){ root.setAttribute("data-theme", t); side.classList.toggle("day", t==="day"); }

// Compute theme from sunrise/sunset (Date objects in local time)
function themeFromSun(now, sunrise, sunset){
  // windows: night -> dawn (sunrise-90m..sunrise+60m) -> day -> dusk (sunset-90m..sunset+60m) -> night
  const ms = 60*1000;
  const dawnStart = new Date(sunrise.getTime() - 90*ms);
  const dawnEnd   = new Date(sunrise.getTime() + 60*ms);
  const duskStart = new Date(sunset.getTime() - 90*ms);
  const duskEnd   = new Date(sunset.getTime() + 60*ms);

  if (now >= dawnStart && now <= dawnEnd) return "dawn";
  if (now > dawnEnd && now < duskStart)   return "day";
  if (now >= duskStart && now <= duskEnd) return "dusk";
  return "night";
}

let sunTimes = null;
async function fetchSun(){
  try{
    const r = await fetch("/api/sun"); const j = await r.json();
    // Convert ISO (UTC) to local Date
    if (j.sunrise_utc && j.sunset_utc){
      sunTimes = {
        sunrise: new Date(j.sunrise_utc),
        sunset: new Date(j.sunset_utc)
      };
    }else if (j.sunrise && j.sunset){
      sunTimes = { sunrise:new Date(j.sunrise), sunset:new Date(j.sunset) };
    }
  }catch(e){ console.warn("sun err", e); }
}

function autoThemeTick(){
  if (themeSelect.value!=="auto" || !sunTimes) return;
  const now = new Date();
  setTheme(themeFromSun(now, sunTimes.sunrise, sunTimes.sunset));
}

// ---- Candles ----
const chart = LightweightCharts.createChart(document.getElementById("candles"), {
  layout:{ background:{ type:"solid", color:"transparent"}, textColor:"#bde" },
  grid:{ vertLines:{ visible:false }, horzLines:{ visible:false } },
  rightPriceScale:{ borderVisible:false }, timeScale:{ borderVisible:false }
});
const series = chart.addCandlestickSeries({
  upColor:"#00ff88", downColor:"#ff2d2d", borderUpColor:"#00ff88", borderDownColor:"#ff2d2d", wickUpColor:"#00ff88", wickDownColor:"#ff2d2d"
});
const ws = new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
ws.onmessage = ev=>{
  const d = JSON.parse(ev.data);
  series.update({ time:Math.floor(d.ts/1000), ...d.ohlc });
  $("#bal").textContent = "$"+d.kpis.balance.toFixed(2);
  $("#pro").textContent = (d.kpis.profit>=0?"+":"")+d.kpis.profit.toFixed(2)+"%";
  $("#los").textContent = d.kpis.loss.toFixed(2)+"%";
};

// ---- Trade ----
$("#tradeForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const body = {
    symbol: $("#sym").value.trim(),
    price: parseFloat($("#price").value),
    action: $("#act").value,
    qty: parseFloat($("#qty").value)
  };
  const r = await fetch("/api/paper_trade",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  $("#out").textContent = JSON.stringify(await r.json(), null, 2);
});

// ---- Strategies ----
async function loadStrategies(){
  const r = await fetch("/api/strategies"); const j = await r.json();
  const sel = $("#strategySelect"); sel.innerHTML="";
  (j.strategies||[]).forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; sel.appendChild(o); });
}
$("#runStrategy").addEventListener("click", async ()=>{
  const name = $("#strategySelect").value;
  const r = await fetch("/api/strategy/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
  $("#stratOut").textContent = JSON.stringify(await r.json(), null, 2);
});
loadStrategies();

// ---- Theme wiring ----
themeSelect.addEventListener("change", ()=>{
  const v = themeSelect.value;
  if (v==="auto"){ autoThemeTick(); return; }
  setTheme(v);
});

// Initial pulls
(async ()=>{
  await fetchSun();
  autoThemeTick();
  setInterval(fetchSun, 30*60*1000);  // refresh sun calc every 30 min
  setInterval(autoThemeTick, 60*1000); // update theme every minute
})();
JSCODE

# 6) assets — reuse your GIF/wallpaper if present
cp /mnt/data/94ad2ced2bb9305b9e43c4e777b.gif static/city_bg.gif 2>/dev/null || true
cp /mnt/data/0226f526bbb43af1397cddb2ca6babf0.jpg static/cyber_side.jpg 2>/dev/null || true

# 7) start server (install astral)
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" python-dotenv astral >/dev/null

echo "🚀 Starting NeoLight v3.2 …"
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "✅ Dashboard → http://127.0.0.1:8000/dashboard"
echo "💡 TIP: add to .env -> LAT=40.7128  LON=-74.0060  TZ=America/New_York"

