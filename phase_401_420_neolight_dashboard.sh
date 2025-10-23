#!/bin/bash
# ============================================================
# AI Money Web :: Phase 401–420
# NeoLight v2 Dashboard (Neon Cyberpunk UI) – Autopilot
# ============================================================
set -e

echo "🎛  NeoLight v2 :: starting scaffold..."

# 0) Clean port 8000 if anything is stuck
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on :8000 (PID $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# 1) Structure + backups
mkdir -p backups backend templates static logs runtime
[ -f backend/main.py ] && cp backend/main.py backups/main.py.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f static/dashboard.html ] && cp static/dashboard.html backups/dashboard.html.$(date +"%Y%m%d_%H%M%S").bak || true
[ -f templates/index.html ] && cp templates/index.html backups/index.html.$(date +"%Y%m%d_%H%M%S").bak || true

# 2) Backend (FastAPI + WebSocket)
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json, time, random, asyncio, datetime

app = FastAPI(title="AI Money Web :: NeoLight v2")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "NeoLight v2 running"}

@app.get("/api/trades")
def get_trades():
    # last 50 lines from runtime/orders.jsonl if present
    trades = []
    path = "runtime/orders.jsonl"
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                try:
                    trades.append(json.loads(line))
                except:
                    pass
    return trades[-50:]

@app.websocket("/ws")
async def ws_feed(ws: WebSocket):
    await ws.accept()
    # seed price from last trade (if any)
    last_price = 100.0
    try:
        trades = get_trades()
        if trades:
            last_price = float(trades[-1].get("price", last_price))
    except:
        pass

    o = h = l = c = float(last_price)
    base = c

    while True:
        try:
            # mock-tick candle (kept lightweight; you can wire live prices here later)
            delta = random.uniform(-0.6, 0.6)
            o = c
            c = max(1.0, o + delta)
            h = max(o, c) + abs(random.uniform(0, 0.4))
            l = min(o, c) - abs(random.uniform(0, 0.4))
            volume = random.randint(60, 220)

            # KPIs & gauges
            balance = 10000 + random.uniform(-60, 60)
            profit = random.uniform(-2, 2)
            loss = max(0, random.uniform(-1, 1))
            vol_pct = random.randint(40, 85)
            div_pct = random.randint(10, 60)

            payload = {
                "ts": int(time.time() * 1000),
                "ohlc": {
                    "open": round(o, 2), "high": round(h, 2),
                    "low": round(l, 2),  "close": round(c, 2),
                    "volume": volume
                },
                "kpis": {
                    "balance": balance, "profit": profit,
                    "loss": loss, "volPct": vol_pct, "divPct": div_pct
                },
                "sparks": {
                    "balance": balance + random.uniform(-10, 10),
                    "profit": profit + random.uniform(-0.5, 0.5),
                    "loss": loss + random.uniform(-0.5, 0.5)
                }
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(0.8)
        except Exception:
            break
PYCODE

# 3) Templates (NeoLight v2 HTML)
cat > templates/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>A.I. TRADING DASHBOARD</title>

  <!-- Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@400;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <!-- Styles -->
  <link rel="stylesheet" href="/static/style.css"/>

  <!-- Charts -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <div class="wrap">
    <header class="marquee neon-panel">
      <div class="marquee__inner">
        <span class="title">A.I. TRADING DASHBOARD</span>
        <span class="blip"></span>
      </div>
    </header>

    <main class="grid">
      <!-- Left hero: city background + candles -->
      <section class="panel hero neon-panel">
        <div class="panel__title red">STOCKS</div>
        <canvas id="cityOverlay" class="city"></canvas>
        <div id="candles" class="candles"></div>
      </section>

      <!-- Right sidebar cards -->
      <aside class="sidebar">
        <section class="panel neon-panel">
          <div class="panel__title cyan">NEURAL NET</div>
          <div class="wire-head">
            <div class="mesh"></div>
            <div class="meter"><span id="nnPct">67%</span></div>
          </div>
        </section>
        <section class="panel neon-panel">
          <div class="panel__title cyan">RISK MODEL</div>
          <div class="wire-head small">
            <div class="mesh"></div>
            <div class="bars">
              <div class="bar"></div><div class="bar"></div><div class="bar"></div>
            </div>
          </div>
        </section>
      </aside>

      <!-- KPI row -->
      <section class="panel neon-panel kpi">
        <div class="panel__title cyan">BALANCE</div>
        <div class="kpi__val"><span id="k_balance">$10,000</span></div>
        <canvas id="spark_balance" class="spark"></canvas>
      </section>

      <section class="panel neon-panel kpi">
        <div class="panel__title amber">PROFIT</div>
        <div class="kpi__val"><span id="k_profit">+0.00%</span></div>
        <canvas id="spark_profit" class="spark"></canvas>
      </section>

      <section class="panel neon-panel kpi">
        <div class="panel__title red">LOSS</div>
        <div class="kpi__val"><span id="k_loss">0.00%</span></div>
        <canvas id="spark_loss" class="spark"></canvas>
      </section>

      <!-- Market Trends + Donuts -->
      <section class="panel neon-panel cube">
        <div class="panel__title red">MARKET TRENDS</div>
        <canvas id="cubeGrid"></canvas>
      </section>

      <section class="panel neon-panel donuts">
        <div class="panel__title red">METRICS</div>
        <canvas id="donut_vol"></canvas>
        <canvas id="donut_div"></canvas>
      </section>

      <!-- Bottom consoles -->
      <section class="panel neon-panel console">
        <div class="panel__title amber">&lt;DATA&gt;</div>
        <pre id="logA" class="console__body"></pre>
      </section>

      <section class="panel neon-panel console">
        <div class="panel__title amber">&lt;DATA&gt;</div>
        <pre id="logB" class="console__body"></pre>
      </section>
    </main>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
HTML

# 4) Neon CSS
cat > static/style.css <<'CSS'
:root{
  --bg:#0a0b0f; --cyan:#00f5ff; --red:#ff2d2d; --amber:#ffb000; --lime:#00ff88; --mag:#b100ff; --panel:#10131a;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; background:radial-gradient(1000px 800px at 50% -20%, #111 0%, var(--bg) 60%, #000 100%);
  color:#cde; font-family:"Share Tech Mono", ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing:0.3px;
}
.neon-panel{
  position:relative; background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00));
  border:1.5px solid var(--cyan); border-radius:14px; padding:12px;
  box-shadow:0 0 12px rgba(0,245,255,.35), inset 0 0 18px rgba(0,245,255,.08);
}
.neon-panel::after{content:""; position:absolute; inset:0; border-radius:14px; pointer-events:none; box-shadow:0 0 24px rgba(0,245,255,.15);}
.wrap{max-width:1200px; margin:24px auto; padding:0 14px}
.marquee{margin-bottom:16px}
.marquee__inner{display:flex; align-items:center; justify-content:space-between}
.title{font-family:"Press Start 2P", monospace; color:var(--red); font-size:20px; letter-spacing:1.5px; text-shadow:0 0 8px rgba(255,45,45,.6);}
.blip{width:10px; height:10px; background:var(--red); border-radius:50%; box-shadow:0 0 14px rgba(255,45,45,.8);}
.grid{
  display:grid; gap:14px;
  grid-template-columns: 2fr 1fr;
  grid-template-areas:
    "hero sidebar"
    "k1   sidebar"
    "k2   cube"
    "k3   donuts"
    "c1   c2";
}
.hero{grid-area:hero; min-height:380px; overflow:hidden}
.sidebar{grid-area:sidebar; display:grid; gap:14px}
.kpi:nth-of-type(1){grid-area:k1}
.kpi:nth-of-type(2){grid-area:k2}
.kpi:nth-of-type(3){grid-area:k3}
.cube{grid-area:cube}
.donuts{grid-area:donuts}
.console:nth-of-type(1){grid-area:c1}
.console:nth-of-type(2){grid-area:c2}
.panel{background:var(--panel)}
.panel__title{font-family:Orbitron, sans-serif; margin-bottom:8px; font-size:13px; letter-spacing:1.2px}
.cyan{color:var(--cyan)} .red{color:var(--red)} .amber{color:var(--amber)}
.city{position:absolute; inset:0; opacity:0.3; filter:contrast(120%) saturate(120%)}
.candles{position:absolute; inset:40px 16px 16px 16px}
.kpi{display:flex; flex-direction:column; gap:8px}
.kpi__val{font-size:18px}
.spark{height:60px}
.cube canvas{width:100%; height:220px}
.donuts{display:grid; grid-template-columns:1fr 1fr; align-items:center; gap:8px}
.donuts canvas{height:140px}
.console__body{height:160px; overflow:auto; background:#06080c; color:#9ee; border:1px dashed rgba(0,245,255,.3); padding:10px; font-size:12px;}
.wire-head{height:180px; position:relative; display:flex; align-items:center; justify-content:center}
.wire-head.small{height:140px}
.mesh{
  width:140px;height:140px;border:1.5px solid var(--cyan); border-radius:50%;
  box-shadow:0 0 12px rgba(0,245,255,.3), inset 0 0 12px rgba(0,245,255,.15);
  background:
    radial-gradient(transparent 58%, rgba(0,245,255,.15) 59% 61%, transparent 62%),
    repeating-linear-gradient(0deg, rgba(0,245,255,.2) 0 1px, transparent 1px 10px),
    repeating-linear-gradient(90deg, rgba(0,245,255,.2) 0 1px, transparent 1px 10px);
}
.meter{position:absolute; bottom:8px; right:12px; font-weight:700; color:var(--cyan)}
.bars{display:flex; gap:6px; position:absolute; right:10px; bottom:10px}
.bar{width:6px; height:40px; background:var(--red); box-shadow:0 0 8px rgba(255,45,45,.6)}
.bar:nth-child(2){height:28px; background:var(--amber); box-shadow:0 0 8px rgba(255,176,0,.6)}
.bar:nth-child(3){height:50px; background:var(--cyan); box-shadow:0 0 8px rgba(0,245,255,.6)}
CSS

# 5) Neon JS (charts, donuts, websocket, city overlay)
cat > static/app.js <<'JSCODE'
// Cityscape pixel overlay
const cityCanvas = document.getElementById('cityOverlay');
const ctx = cityCanvas.getContext('2d');
function resizeCity(){ cityCanvas.width = cityCanvas.clientWidth; cityCanvas.height = cityCanvas.clientHeight; }
addEventListener('resize', resizeCity); resizeCity();
function drawCity(){
  const w = cityCanvas.width, h = cityCanvas.height;
  ctx.clearRect(0,0,w,h);
  for(let i=0;i<200;i++){
    ctx.fillStyle = ['#00f5ff','#ff2d2d','#ffb000','#00ff88','#b100ff'][i%5];
    ctx.fillRect(Math.random()*w, Math.random()*h*0.5, 2, 2);
  }
  let x=0;
  while(x<w){
    const bw=20+Math.random()*40, bh=h*0.2+Math.random()*h*0.6;
    ctx.fillStyle='rgba(255,255,255,0.02)'; ctx.fillRect(x,h-bh,bw,bh);
    ctx.strokeStyle='#0ff'; ctx.shadowColor='#0ff'; ctx.shadowBlur=6; ctx.strokeRect(x+0.5,h-bh+0.5,bw-1,bh-1); ctx.shadowBlur=0;
    for(let y=h-bh+6;y<h-6;y+=8){
      if(Math.random()<0.3) continue;
      ctx.fillStyle=['#ffb000','#ff2d2d','#00f5ff'][Math.floor(Math.random()*3)];
      ctx.fillRect(x+4+Math.random()*(bw-8), y, 3, 2);
    }
    x += bw + 6;
  }
}
drawCity();

// Lightweight-charts: candlesticks
const chartContainer = document.getElementById('candles');
const candleChart = LightweightCharts.createChart(chartContainer, {
  layout:{ background:{ type:'solid', color:'transparent'}, textColor:'#9ee' },
  rightPriceScale:{ borderVisible:false }, timeScale:{ borderVisible:false },
  grid:{ vertLines:{ color:'rgba(0,0,0,0)'}, horzLines:{ color:'rgba(0,0,0,0)'} },
  crosshair:{ mode: 0 }
});
const candleSeries = candleChart.addCandlestickSeries({
  upColor:'#00ff88', downColor:'#ff2d2d', borderUpColor:'#00ff88', borderDownColor:'#ff2d2d', wickUpColor:'#00ff88', wickDownColor:'#ff2d2d'
});

// Chart.js helpers
function sparkline(ctx){
  return new Chart(ctx, {
    type:'line',
    data:{ labels:Array(20).fill(''), datasets:[{ data:Array(20).fill(0), tension:0.3, borderWidth:1.8, fill:false }]},
    options:{ plugins:{legend:{display:false}}, scales:{x:{display:false}, y:{display:false}}, elements:{point:{radius:0}} }
  });
}
const sBal = sparkline(document.getElementById('spark_balance').getContext('2d')); sBal.data.datasets[0].borderColor='#00f5ff';
const sPro = sparkline(document.getElementById('spark_profit').getContext('2d'));  sPro.data.datasets[0].borderColor='#ffb000';
const sLos = sparkline(document.getElementById('spark_loss').getContext('2d'));    sLos.data.datasets[0].borderColor='#ff2d2d';

function donut(el){
  return new Chart(el.getContext('2d'), {
    type:'doughnut',
    data:{ labels:['Value','Rest'], datasets:[{ data:[50,50], backgroundColor:['#00f5ff','#062126'], borderWidth:1 }] },
    options:{ plugins:{legend:{display:false}}, cutout:'70%', circumference:360, rotation:-90, elements:{arc:{borderWidth:1}} }
  });
}
const dVol = donut(document.getElementById('donut_vol'));
const dDiv = donut(document.getElementById('donut_div'));

// 3D-ish cube grid
const cube = document.getElementById('cubeGrid'); const cctx = cube.getContext('2d');
function drawCubeGrid(){
  cube.width = cube.clientWidth; cube.height = cube.clientHeight;
  const w=cube.width, h=cube.height;
  cctx.clearRect(0,0,w,h); cctx.strokeStyle='#ffb000'; cctx.shadowColor='#ffb000'; cctx.shadowBlur=6;
  for(let i=0;i<20;i++){ cctx.beginPath(); cctx.moveTo(0, h*0.4+i*10); cctx.lineTo(w, h*0.4+i*8); cctx.stroke(); }
  for(let i=0;i<20;i++){ cctx.beginPath(); cctx.moveTo(i*20, h*0.4); cctx.lineTo(i*18, h); cctx.stroke(); }
  for(let i=0;i<8;i++){ const baseX=60+i*80; const barH=40+Math.random()*120; cctx.fillStyle='#ffb000'; cctx.fillRect(baseX, h-10-barH, 24, barH); }
  cctx.shadowBlur=0;
}
drawCubeGrid(); addEventListener('resize', drawCubeGrid);

// KPI elements
const elBal=document.getElementById('k_balance'); const elPro=document.getElementById('k_profit'); const elLos=document.getElementById('k_loss'); const nnPct=document.getElementById('nnPct');
const logA=document.getElementById('logA'); const logB=document.getElementById('logB');

// WS feed
const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');
let timeBase = Math.floor(Date.now()/1000);
ws.onmessage=(ev)=>{
  const d = JSON.parse(ev.data);
  candleSeries.update({ time: Math.floor(d.ts/1000) - timeBase, open:d.ohlc.open, high:d.ohlc.high, low:d.ohlc.low, close:d.ohlc.close });

  elBal.textContent = `$${d.kpis.balance.toFixed(2)}`;
  elPro.textContent = `${d.kpis.profit>=0?'+':''}${d.kpis.profit.toFixed(2)}%`;
  elLos.textContent = `${d.kpis.loss.toFixed(2)}%`;
  nnPct.textContent = `${Math.max(0, Math.min(99, d.kpis.volPct))}%`;

  function pushSpark(chart,val){ const arr=chart.data.datasets[0].data; arr.shift(); arr.push(val); chart.update('none'); }
  pushSpark(sBal, d.sparks.balance); pushSpark(sPro, d.sparks.profit); pushSpark(sLos, d.sparks.loss);

  dVol.data.datasets[0].data=[d.kpis.volPct, 100-d.kpis.volPct];
  dDiv.data.datasets[0].data=[d.kpis.divPct, 100-d.kpis.divPct];
  dVol.update('none'); dDiv.update('none');

  const lineA = `[${new Date(d.ts).toLocaleTimeString()}] OHLC: ${JSON.stringify(d.ohlc)}`;
  const lineB = `α=${(Math.random()*1.2).toFixed(2)} β=${(Math.random()*1.2).toFixed(2)} pnl=${(d.kpis.profit*100).toFixed(1)}`;
  logA.textContent = (logA.textContent.split('\\n').slice(-50).join('\\n') + '\\n' + lineA).trim();
  logB.textContent = (logB.textContent.split('\\n').slice(-50).join('\\n') + '\\n' + lineB).trim();
};
JSCODE

# 6) Deps (ensure installed) – safe install inside venv
source venv/bin/activate || true
pip install fastapi "uvicorn[standard]" jinja2 python-dotenv >/dev/null

# 7) Start server
echo "🚀 Starting NeoLight v2 backend..."
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ NeoLight v2 live:"
echo "   Dashboard → http://127.0.0.1:8000/dashboard"
echo "   Health    → http://127.0.0.1:8000/api/health"

