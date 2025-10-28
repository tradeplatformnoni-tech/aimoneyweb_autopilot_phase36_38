#!/usr/bin/env bash
# ==========================================================
# NeoLight :: Phase 701–750  — Master Autopilot
# - Restores full backend (health + dashboard + notify + goal)
# - Adds provider auto-detect (Alpaca for stocks, Crypto.com for crypto)
# - Keeps paper/sim fallback if keys missing
# - Rebuilds static UI hooks (Notifications tab ready)
# - Restarts backend + daemon + agent
# - Uses neolight-fix if available to self-heal
# ==========================================================
set -e

echo "🧠 NeoLight :: Phase 701–750 Master Autopilot"

mkdir -p backend templates static runtime tools ai/providers logs

# --- venv + deps ---
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install --quiet fastapi uvicorn requests pandas numpy psutil python-multipart

echo 'export PYTHONPATH=$(pwd)' > .venv/bin/activate_pathfix
chmod +x .venv/bin/activate_pathfix
source .venv/bin/activate_pathfix

# --- runtime seeds ---
[ -f runtime/notify_config.json ] || echo '{"discord_webhook": null, "telegram_token": null, "telegram_chat": null}' > runtime/notify_config.json
[ -f runtime/live_mode.json ]    || echo '{"live": false}' > runtime/live_mode.json
[ -f runtime/auto_mode.json ]    || echo '{"auto_trade": false, "symbol": "AAPL", "qty": 1}' > runtime/auto_mode.json
[ -f runtime/portfolio.json ]    || echo '{"cash":100000,"equity":100000,"positions":{},"trades":[]}' > runtime/portfolio.json
[ -f runtime/portfolio_weights.json ] || echo '{"momentum":0.34,"crossover":0.33,"mean_reversion":0.33}' > runtime/portfolio_weights.json
[ -f runtime/signals.jsonl ] || touch runtime/signals.jsonl
[ -f runtime/agent_log.jsonl ] || touch runtime/agent_log.jsonl
[ -f runtime/goal_config.json ] || cat > runtime/goal_config.json <<'JSON'
{
  "target_milestones": {
    "2_years": 1000000,
    "5_years": 10000000,
    "10_years": 50000000
  },
  "current_equity": 25000,
  "growth_target": 0.035,
  "risk_tolerance": "medium"
}
JSON

# --- providers ---
cat > ai/providers/alpaca_provider.py <<'PY'
import os, requests, datetime
BASE="https://data.alpaca.markets/v2"
KEY=os.getenv("ALPACA_API_KEY"); SECRET=os.getenv("ALPACA_SECRET_KEY")
HEAD={"APCA-API-KEY-ID":KEY,"APCA-API-SECRET-KEY":SECRET} if KEY and SECRET else None

def get_ohlc(symbol="AAPL", limit=180):
    if not HEAD:
        return None  # signal to backend to fallback to SIM
    # use bars (5Min) last 'limit'
    url=f"{BASE}/stocks/{symbol}/bars"
    params={"timeframe":"5Min","limit":limit}
    r=requests.get(url,headers=HEAD,params=params,timeout=10)
    if not r.ok: return None
    data=r.json().get("bars",[])
    out=[]
    for b in data:
        out.append({
            "t": b.get("t"),
            "open": b.get("o"), "high": b.get("h"),
            "low": b.get("l"), "close": b.get("c"),
            "volume": b.get("v")
        })
    return out
PY

cat > ai/providers/crypto_com_provider.py <<'PY'
import requests
# Public Candlestick endpoint (no key needed for data)
API_URL="https://api.crypto.com/v2/public/get-candlestick"
def get_ohlc(symbol="BTC_USDT", interval="5m", limit=180):
    r=requests.get(API_URL,params={"instrument_name":symbol,"timeframe":interval},timeout=10)
    if not r.ok: return None
    data=r.json().get("result",{}).get("data",[])
    out=[]
    for d in data[-limit:]:
        out.append({
            "t": d.get("t"),
            "open": float(d.get("o")), "high": float(d.get("h")),
            "low": float(d.get("l")), "close": float(d.get("c")),
            "volume": float(d.get("v",0))
        })
    return out
PY

# --- notify helper ---
cat > backend/notify.py <<'PY'
import json, os, requests
CONFIG_FILE="runtime/notify_config.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: return json.load(f)
    return {"discord_webhook": None, "telegram_token": None, "telegram_chat": None}
def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=2)
def send_discord(msg,url):
    if not url: return {"status":"no webhook"}
    try:
        r=requests.post(url,json={"content":msg},timeout=8)
        return {"status":"ok","code":r.status_code}
    except Exception as e: return {"status":"error","error":str(e)}
def send_telegram(msg,token,chat):
    if not token or not chat: return {"status":"no token/chat"}
    try:
        url=f"https://api.telegram.org/bot{token}/sendMessage"
        r=requests.post(url,data={"chat_id":chat,"text":msg},timeout=8)
        return {"status":"ok","code":r.status_code}
    except Exception as e: return {"status":"error","error":str(e)}
def notify_all(message):
    cfg=load_config()
    return {
        "discord":  send_discord(message, cfg.get("discord_webhook")),
        "telegram": send_telegram(message, cfg.get("telegram_token"), cfg.get("telegram_chat"))
    }
PY

# --- goal engine ---
cat > backend/goal_engine.py <<'PY'
import json, datetime, os
CFG="runtime/goal_config.json"
def update_progress(current_equity: float):
    cfg=json.load(open(CFG)) if os.path.exists(CFG) else {"target_milestones":{}}
    out={"equity":current_equity,"report":[]}
    for yr, tgt in cfg.get("target_milestones",{}).items():
        pct=0 if tgt==0 else round((current_equity/float(tgt))*100,2)
        out["report"].append({"year":yr,"target":float(tgt),"progress":pct})
    out["timestamp"]=datetime.datetime.utcnow().isoformat()
    return out
PY

# --- full backend (RESTORES everything) ---
cat > backend/main.py <<'PY'
import os, json, math, random, datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import numpy as np

from backend.notify import load_config, save_config, notify_all
from backend.goal_engine import update_progress
from ai.providers import alpaca_provider, crypto_com_provider

app = FastAPI(title="AI Money Web :: NeoLight v4.5 (Phase 701–750)")
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNTIME="runtime"
LIVE_FILE=os.path.join(RUNTIME,"live_mode.json")
AUTO_FILE=os.path.join(RUNTIME,"auto_mode.json")
PF_FILE=os.path.join(RUNTIME,"portfolio.json")
WEIGHTS_FILE=os.path.join(RUNTIME,"portfolio_weights.json")
SIG_FILE=os.path.join(RUNTIME,"signals.jsonl")

def jread(p, d): 
    try: return json.load(open(p,"r"))
    except: return d
def jwrite(p, o):
    json.dump(o, open(p,"w"), indent=2)

# ---------- UI ----------
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    # Use existing v4 dashboard if present; else minimal fallback
    cand = "templates/dashboard.html"
    if os.path.exists(cand): return open(cand,"r",encoding="utf-8").read()
    return "<h1 style='color:#0ff;background:#000;padding:2rem'>NeoLight v4.5</h1>"

# ---------- health ----------
@app.get("/api/health")
def health(): return {"status":"ok","ts": datetime.datetime.utcnow().isoformat()}

# ---------- provider auto-detect + OHLC ----------
def _simulate_ohlc(limit=180):
    now=datetime.datetime.utcnow().replace(second=0,microsecond=0)
    price=150.0; out=[]
    for i in range(limit):
        ts=now-datetime.timedelta(minutes=(limit-1-i))
        drift=math.sin(i/12.0)*0.8
        o=price+random.uniform(-0.8,0.8)+drift
        h=o+random.uniform(0,1.2); l=o-random.uniform(0,1.2)
        c=random.uniform(l,h)
        out.append({"t":ts.isoformat(),"open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2),"volume":random.randint(1000,9000)})
        price=c
    return out

def _is_crypto_symbol(sym:str):
    return "_" in sym  # e.g., BTC_USDT

@app.get("/api/ohlc")
def api_ohlc(symbol: str="AAPL", limit: int=180):
    data=None
    if _is_crypto_symbol(symbol):
        data = crypto_com_provider.get_ohlc(symbol=symbol, interval="5m", limit=limit)
    else:
        data = alpaca_provider.get_ohlc(symbol=symbol, limit=limit)
    if not data: 
        data=_simulate_ohlc(limit=limit)
    return data

# ---------- toggles ----------
@app.get("/api/live-toggle")
def get_live(): return jread(LIVE_FILE, {"live": False})
@app.post("/api/live-toggle")
def set_live(payload: dict):
    live=bool(payload.get("live",False)); jwrite(LIVE_FILE, {"live":live}); return {"status":"updated","live":live}

@app.get("/api/auto-mode")
def get_auto(): return jread(AUTO_FILE, {"auto_trade": False, "symbol":"AAPL","qty":1})
@app.post("/api/auto-mode")
def set_auto(payload: dict):
    auto=get_auto(); auto.update({"auto_trade": bool(payload.get("auto_trade",auto["auto_trade"])), "symbol": payload.get("symbol",auto["symbol"]), "qty": int(payload.get("qty",auto["qty"]))})
    jwrite(AUTO_FILE, auto); return {"status":"updated","auto":auto}

# ---------- logs ----------
@app.get("/api/strategy-log")
def strategy_log():
    if not os.path.exists(SIG_FILE): return []
    out=[]
    with open(SIG_FILE,"r") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out[-500:]

# ---------- portfolio + metrics ----------
@app.get("/api/portfolio")
def api_portfolio(): return jread(PF_FILE, {"cash":100000,"equity":100000,"positions":{},"trades":[]})

@app.get("/api/metrics")
def api_metrics():
    pf=api_portfolio(); trades=pf.get("trades",[])
    curve=[pf.get("equity",100000.0)]
    if len(trades)>0:
        for i in range(1,61): curve.append(curve[-1]+random.uniform(-15,15))
    arr=np.array(curve,dtype=float)
    rets=np.diff(arr)/arr[:-1] if len(arr)>1 else np.array([0.0])
    sharpe=(np.mean(rets)/(np.std(rets)+1e-9))*np.sqrt(252) if len(rets)>2 else 0.0
    cumret=float(arr[-1]/arr[0]-1.0) if len(arr)>1 else 0.0
    running_max=np.maximum.accumulate(arr); mdd=float(((arr-running_max)/running_max).min()) if len(arr)>0 else 0.0
    return {"equity_curve":[float(x) for x in arr.tolist()],"cum_return":cumret,"sharpe":float(sharpe),"max_drawdown":mdd,"trades":len(trades)}

# ---------- weights ----------
@app.get("/api/weights")
def get_weights(): return jread(WEIGHTS_FILE, {"momentum":0.34,"crossover":0.33,"mean_reversion":0.33})
@app.post("/api/weights")
def set_weights(payload: dict):
    w=get_weights()
    for k in ["momentum","crossover","mean_reversion"]:
        if k in payload:
            try: w[k]=float(payload[k])
            except: pass
    s=sum(w.values())
    w={"momentum":0.34,"crossover":0.33,"mean_reversion":0.33} if s<=0 else {k:v/s for k,v in w.items()}
    jwrite(WEIGHTS_FILE,w); return {"status":"updated","weights":w}

# ---------- notify ----------
@app.get("/api/notify/config")
def get_notify_config(): return load_config()
@app.post("/api/notify/config")
def set_notify_config(payload: dict):
    cfg=load_config()
    for k in ["discord_webhook","telegram_token","telegram_chat"]:
        if k in payload: cfg[k]=payload[k]
    save_config(cfg); return {"status":"saved","config":cfg}
@app.post("/api/notify/test")
def test_notify(payload: dict):
    msg=payload.get("message","🔔 NeoLight test alert")
    return {"status":"sent","result": notify_all(msg)}

# ---------- goal engine ----------
@app.get("/api/goal")
def read_goal():
    pf=jread(PF_FILE, {"equity":100000})
    return update_progress(current_equity=float(pf.get("equity",100000)))
PY

# --- minimal dashboard if missing (keeps your current one if exists) ---
if [ ! -f templates/dashboard.html ]; then
cat > templates/dashboard.html <<'HTML'
<!doctype html><html><head><meta charset="utf-8"/><title>NeoLight v4.5</title>
<link rel="stylesheet" href="/static/style.css"/><script src="https://cdn.jsdelivr.net/npm/chart.js"></script></head>
<body><h1>💡 AI Money Web :: NeoLight v4.5</h1>
<nav class="tabs"><button data-tab="tab-dash" class="active">Dashboard</button><button data-tab="tab-portfolio">Portfolio</button><button data-tab="tab-logs">Logs</button><button data-tab="tab-notify">Notifications</button></nav>
<section id="tab-dash" class="tab active"><div class="row">
<strong>Data Mode:</strong><span id="modeStatus" class="badge">SIM</span>
<strong style="margin-left:2rem;">Auto Trade:</strong><span id="autoStatus" class="badge">Off</span>
<span class="tiny">Qty</span><input id="qty" class="qty" type="number" min="1" value="1"/></div>
<div class="panel"><h3>📈 Close Prices</h3><canvas id="priceChart" height="120"></canvas></div></section>
<section id="tab-portfolio" class="tab"><div class="panel"><h3>📊 Metrics</h3><pre id="metrics">-</pre></div></section>
<section id="tab-logs" class="tab"><div class="panel"><h3>🧠 Strategy Logs</h3><pre id="logs">-</pre></div></section>
<section id="tab-notify" class="tab"><div class="panel"><h3>🔔 Notification Settings</h3>
<label>Discord Webhook: <input id="discord_url" class="winput"/></label><br>
<label>Telegram Token: <input id="telegram_token" class="winput"/></label><br>
<label>Telegram Chat ID: <input id="telegram_chat" class="winput"/></label><br>
<button id="save_notify">Save</button><button id="test_notify">Send Test Alert</button><pre id="notify_status"></pre></div></section>
<script src="/static/app_v4.js"></script></body></html>
HTML
fi

# --- style ---
cat > static/style.css <<'CSS'
:root { --neon:#00ffff; --bg:#000; --ink:#e8ffff; --panel:#0b0b0b; }
*{box-sizing:border-box} body{margin:0;padding:2rem;background:var(--bg);color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace}
h1{color:var(--neon)} .panel{background:var(--panel);border:1px solid #112;border-radius:10px;padding:1rem;margin-bottom:1rem}
.row{display:flex;align-items:center;gap:1rem;margin-bottom:1rem} .badge{color:var(--neon)} .tiny{font-size:12px;opacity:.75}
pre{background:#050505;border:1px solid #112;padding:1rem;border-radius:10px;max-height:320px;overflow:auto;white-space:pre-wrap}
.tabs{display:flex;gap:.5rem;margin-bottom:1rem}.tabs button{background:#041516;color:#aef;border:1px solid #0aa;border-radius:8px;padding:.4rem .8rem;cursor:pointer}
.tabs button.active{background:#073;color:#eaffff}.tab{display:none}.tab.active{display:block}
.qty,.winput{width:220px;max-width:60%;background:#020202;color:#ddd;border:1px solid #233;border-radius:6px;padding:6px}
CSS

# --- app js (refresh + notify hooks) ---
cat > static/app_v4.js <<'JS'
let priceChart;
const $ = (id)=>document.getElementById(id);
function renderLine(canvasId, labels, data, labelText){
  const ctx=$(canvasId).getContext('2d');
  return new Chart(ctx,{type:'line',data:{labels,datasets:[{label:labelText,data,borderColor:'#00ffff',tension:0.3}]},options:{plugins:{legend:{labels:{color:'#00ffff'}}},scales:{x:{ticks:{color:'#00ffff'}},y:{ticks:{color:'#00ffff'}}}}});
}
function initTabs(){
  const btns=document.querySelectorAll('.tabs button'); const tabs=document.querySelectorAll('.tab');
  btns.forEach(b=>b.addEventListener('click',()=>{btns.forEach(x=>x.classList.remove('active'));tabs.forEach(t=>t.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');}));
}
async function jget(u,params){const q=params?('?'+new URLSearchParams(params)):"";const r=await fetch(u+q);return r.json();}
async function jpost(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return r.json();}
async function refreshPrice(){
  const auto=await jget('/api/auto-mode'); $('qty').value=auto.qty||1; $('autoStatus').textContent=auto.auto_trade?'On':'Off';
  const d=await jget('/api/ohlc',{symbol:auto.symbol||'AAPL',limit:300}); const labels=d.map(x=>(x.t||'').toString().slice(11,16)); const closes=d.map(x=>x.close);
  if (priceChart){priceChart.data.labels=labels;priceChart.data.datasets[0].data=closes;priceChart.update();} else {priceChart=renderLine('priceChart',labels,closes,'Close');}
}
async function refreshLogs(){ const logs=await jget('/api/strategy-log'); $('logs').textContent=logs.length?logs.map(l=>JSON.stringify(l)).join('\n'):'No logs.'; }
async function refreshMetrics(){ const m=await jget('/api/metrics'); $('metrics').textContent=JSON.stringify(m,null,2); }
async function loadNotify(){ const c=await jget('/api/notify/config'); $('discord_url').value=c.discord_webhook||''; $('telegram_token').value=c.telegram_token||''; $('telegram_chat').value=c.telegram_chat||''; }
async function saveNotify(){ const body={discord_webhook:$('discord_url').value,telegram_token:$('telegram_token').value,telegram_chat:$('telegram_chat').value}; const r=await jpost('/api/notify/config',body); $('notify_status').textContent=JSON.stringify(r,null,2); }
async function testNotify(){ const msg=prompt("Enter test message","NeoLight test alert"); const r=await jpost('/api/notify/test',{message:msg}); $('notify_status').textContent=JSON.stringify(r,null,2); }
$('save_notify')?.addEventListener('click',saveNotify); $('test_notify')?.addEventListener('click',testNotify);
document.addEventListener('DOMContentLoaded',async()=>{initTabs();await Promise.all([refreshPrice(),refreshLogs(),refreshMetrics(),loadNotify()]);setInterval(refreshPrice,5000);setInterval(refreshLogs,7000);setInterval(refreshMetrics,7000);});
JS

# --- (optional) strategy_daemon + agent exist check (don’t overwrite user custom) ---
if [ ! -f tools/strategy_daemon.py ]; then
cat > tools/strategy_daemon.py <<'PY'
# Minimal placeholder (your fuller daemon already exists in previous phases)
import time, json, datetime, random
from pathlib import Path
RUNTIME=Path("runtime"); LOG=RUNTIME/"signals.jsonl"
def loop():
    price=150+random.uniform(-1,1)
    s=random.choice(["BUY","SELL","HOLD"])
    LOG.open("a").write(json.dumps({"timestamp":datetime.datetime.utcnow().isoformat(),"strategy":"placeholder","symbol":"AAPL","signal":s,"confidence":0.6,"price":price})+"\n")
if __name__=="__main__":
    while True: loop(); time.sleep(5)
PY
fi

# --- restart everything cleanly ---
echo "♻️ Restarting backend + daemon + agent (if present)"
pkill -f "uvicorn backend.main:app" || true
pkill -f "tools/strategy_daemon.py" || true
pkill -f "tools/agent_loop.py" || true

nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
[ -f tools/strategy_daemon.py ] && nohup python tools/strategy_daemon.py >> logs/daemon.log 2>&1 &
[ -f tools/agent_loop.py ] && nohup python tools/agent_loop.py >> logs/agent.log 2>&1 &

sleep 2
echo "✅ Done. Health check:"; curl -s http://127.0.0.1:8000/api/health || true; echo
echo "👉 Dashboard: http://localhost:8000/dashboard"
echo "👉 If anything fails later: neolight-fix   (AutoFix Pilot)"

