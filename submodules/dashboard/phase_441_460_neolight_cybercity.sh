#!/bin/bash
# =============================================================
# AI Money Web :: Phase 441–460 — NeoLight v3 CyberCity Mode
# =============================================================
set -e

echo "🌆 Launching NeoLight v3 CyberCity setup..."

# 0️⃣ Kill anything on :8000
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing PID $pid on :8000"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1️⃣ Ensure folders
mkdir -p backend templates static runtime logs ai/strategies backups
[ -f backend/main.py ] && cp backend/main.py backups/main.py.$(date +"%Y%m%d_%H%M%S").bak || true

# 2️⃣ Backend main.py
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, json, time, asyncio, random, datetime, uuid

app = FastAPI(title="AI Money Web :: NeoLight v3")
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

@app.websocket("/ws")
async def feed(ws: WebSocket):
    await ws.accept()
    base = 200.0
    while True:
        o = base + random.uniform(-1, 1)
        h = o + random.uniform(0, 2)
        l = o - random.uniform(0, 2)
        c = l + random.uniform(0, h - l)
        data = {
            "ts": int(time.time()*1000),
            "ohlc": {"open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)},
            "kpis":{
                "balance":10000+random.uniform(-100,100),
                "profit":random.uniform(-2,2),
                "loss":random.uniform(-1,1)
            }
        }
        await ws.send_json(data)
        await asyncio.sleep(1)

@app.post("/api/paper_trade")
def trade(req: PaperTradeRequest):
    os.makedirs("runtime", exist_ok=True)
    t = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": req.symbol,
        "price": req.price,
        "action": req.action,
        "qty": req.qty
    }
    with open("runtime/orders.jsonl", "a") as f:
        f.write(json.dumps(t) + "\n")
    return {"status":"executed","trade":t}

@app.get("/api/strategies")
def list_strategies():
    os.makedirs("ai/strategies", exist_ok=True)
    files = [f.replace(".py","") for f in os.listdir("ai/strategies") if f.endswith(".py")]
    return {"strategies": files}

@app.post("/api/strategy/run")
def run_strategy(body: dict):
    name = body.get("name")
    os.makedirs("runtime", exist_ok=True)
    with open("runtime/last_strategy.txt","w") as f:
        f.write(name)
    return {"status":"running","strategy":name}
PYCODE

# 3️⃣ HTML template
cat > templates/index.html <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>NeoLight v3 CyberCity</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <header class="top neon">
    <h1>🧠 AI Money Web :: NeoLight v3</h1>
  </header>

  <div class="layout">
    <aside class="sidenav" style="background-image:url('/static/cyber_side.jpg')">
      <nav>
        <a href="#live">📈 Live</a>
        <a href="#kpi">🧪 KPIs</a>
        <a href="#perf">📊 Performance</a>
        <a href="#trade">💸 Trade</a>
        <a href="#strategy">🧠 Strategy</a>
        <a href="#system">⚙️ System</a>
      </nav>
    </aside>

    <main class="content">
      <section id="live" class="panel neon city-bg">
        <h2>STOCKS & CRYPTO</h2>
        <div id="candles"></div>
      </section>

      <section id="kpi" class="grid3">
        <div class="panel neon"><h3>BALANCE</h3><div id="bal">$10,000</div></div>
        <div class="panel neon"><h3>PROFIT</h3><div id="pro">+0.00%</div></div>
        <div class="panel neon"><h3>LOSS</h3><div id="los">0.00%</div></div>
      </section>

      <section id="trade" class="panel neon">
        <h2>Quick Trade</h2>
        <form id="tradeForm">
          <input id="sym" value="BTC/USD" />
          <input id="price" type="number" step="0.01" value="63000" />
          <select id="act"><option>buy</option><option>sell</option></select>
          <input id="qty" type="number" value="0.01" step="0.01" />
          <button>Execute</button>
        </form>
        <pre id="out"></pre>
      </section>

      <section id="strategy" class="panel neon">
        <h2>AI Strategies</h2>
        <select id="strategySelect"></select>
        <button id="runStrategy">Run Selected</button>
        <pre id="stratOut"></pre>
      </section>

      <section id="system" class="panel neon">
        <h2>System Log</h2>
        <pre id="log"></pre>
      </section>
    </main>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
HTML

# 4️⃣ CSS with neon + animated GIF
cat > static/style.css <<'CSS'
:root {
  --bg: #05070c;
  --cyan: #00f5ff;
  --red: #ff2d2d;
  --amber: #ffb000;
  --ink: #d7ecff;
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; font-family: "Share Tech Mono", monospace; background: var(--bg); color: var(--ink); overflow-x: hidden; }
a { color: var(--cyan); text-decoration: none; }

.top { position: sticky; top: 0; padding: 12px; background: rgba(0,0,0,0.8); border-bottom: 2px solid var(--cyan); text-align: center; font-family: "Press Start 2P", monospace; color: var(--red); text-shadow: 0 0 10px var(--red); z-index: 1000; }

.layout { display: grid; grid-template-columns: 250px 1fr; min-height: 100vh; }

.sidenav { background-size: cover; background-position: center; display: flex; flex-direction: column; justify-content: center; padding: 20px; position: sticky; top: 0; height: 100vh; }
.sidenav a { display: block; margin: 12px 0; font-family: "Orbitron"; font-size: 18px; text-shadow: 0 0 10px var(--cyan); }

.content { padding: 16px; display: flex; flex-direction: column; gap: 20px; }
.panel { padding: 16px; border: 1.5px solid var(--cyan); border-radius: 12px; background: rgba(0,0,0,0.55); box-shadow: 0 0 20px rgba(0,245,255,0.3); }

.city-bg { background: url('/static/city_bg.gif') no-repeat center center / cover; min-height: 400px; position: relative; }
.city-bg h2 { text-shadow: 0 0 10px var(--amber); }

.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
#candles { height: 400px; }
form { display: flex; gap: 8px; flex-wrap: wrap; }
button { background: var(--cyan); color: #000; border: none; padding: 8px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; }
pre { background: rgba(0,0,0,0.4); padding: 10px; border-radius: 8px; overflow: auto; }
CSS

# 5️⃣ JS
cat > static/app.js <<'JSCODE'
const chartContainer = document.getElementById("candles");
const chart = LightweightCharts.createChart(chartContainer, {
  layout:{background:{type:"solid",color:"transparent"},textColor:"#bdf"},
  grid:{vertLines:{visible:false},horzLines:{visible:false}},
  rightPriceScale:{borderVisible:false},
  timeScale:{borderVisible:false},
});
const candleSeries = chart.addCandlestickSeries({
  upColor:"#00ff88",downColor:"#ff2d2d",borderUpColor:"#00ff88",borderDownColor:"#ff2d2d"
});

const ws = new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');
ws.onmessage = ev => {
  const d = JSON.parse(ev.data);
  candleSeries.update({time:Math.floor(d.ts/1000),open:d.ohlc.open,high:d.ohlc.high,low:d.ohlc.low,close:d.ohlc.close});
  document.getElementById("bal").textContent = "$"+d.kpis.balance.toFixed(2);
  document.getElementById("pro").textContent = (d.kpis.profit>=0?"+":"")+d.kpis.profit.toFixed(2)+"%";
  document.getElementById("los").textContent = d.kpis.loss.toFixed(2)+"%";
};

document.getElementById("tradeForm").addEventListener("submit", async e=>{
  e.preventDefault();
  const res = await fetch("/api/paper_trade",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      symbol:document.getElementById("sym").value,
      price:parseFloat(document.getElementById("price").value),
      action:document.getElementById("act").value,
      qty:parseFloat(document.getElementById("qty").value)
    })
  });
  const j = await res.json();
  document.getElementById("out").textContent = JSON.stringify(j,null,2);
});

async function loadStrategies(){
  const r = await fetch("/api/strategies");
  const s = await r.json();
  const sel = document.getElementById("strategySelect");
  sel.innerHTML = "";
  s.strategies.forEach(st=>{
    const opt = document.createElement("option");
    opt.value = st; opt.textContent = st;
    sel.appendChild(opt);
  });
}
loadStrategies();

document.getElementById("runStrategy").addEventListener("click", async ()=>{
  const name = document.getElementById("strategySelect").value;
  const r = await fetch("/api/strategy/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
  const j = await r.json();
  document.getElementById("stratOut").textContent = JSON.stringify(j,null,2);
});
JSCODE

# 6️⃣ Copy assets (GIF + sidewall)
cp /mnt/data/94ad2ced2bb9305b9bc8b9e43c4e777b.gif static/city_bg.gif || true
cp /mnt/data/0226f526bbb43af1397cddb2ca6babf0.jpg static/cyber_side.jpg || true

# 7️⃣ Start
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" python-dotenv >/dev/null

echo "🚀 Starting NeoLight v3 CyberCity..."
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "✅ Dashboard → http://127.0.0.1:8000/dashboard"

