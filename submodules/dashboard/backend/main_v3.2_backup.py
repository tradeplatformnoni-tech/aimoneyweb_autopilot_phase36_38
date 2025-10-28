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
