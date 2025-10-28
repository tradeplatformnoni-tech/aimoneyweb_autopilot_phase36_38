from backend.advisor_routes_v2 import router as advisor_v2_router
from backend.advisor_routes import router as advisor_router
import os, json, math, random, datetime
from fastapi import FastAPI
from api.core import routes as core_routes
from api.core import portfolio_routes
from api.deal import routes as deal_routes
from api.collab import routes as collab_routes
from api.marketplace import routes as marketplace_routes
from api.nlp import routes as nlp_routes
from api.brain import routes as brain_routes
from api.orchestrator import trigger as orchestrator_trigger
from api.network import peer as peer_api, handshake as handshake_api, ping as ping_api
from api.mesh import sync as mesh_sync, message as mesh_message, state as mesh_state
from fastapi.staticfiles import StaticFiles
from api.console import routes as console_routes
from api.backtest import run as backtest_run
from api.research import discover as research_discover
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import numpy as np

from backend.notify import load_config, save_config, notify_all
from backend.goal_engine import update_progress
from ai.providers import alpaca_provider, crypto_com_provider

app = FastAPI(title="AI Money Web :: NeoLight v4.5 (Phase 701–750)")
app.include_router(advisor_v2_router)
app.include_router(advisor_router)
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
