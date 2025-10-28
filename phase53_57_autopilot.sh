#!/bin/zsh
set -e
echo "🧩 Phase 53–57 :: Multi-Broker + Webhooks + Strategy A/B + Audit …"

mkdir -p backups logs static ai tools ai/brokers db models
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py backups/main.py.$ts.bak && echo "✅ Backup -> backups/main.py.$ts.bak"

# Deps
venv/bin/pip install -q fastapi uvicorn requests python-dotenv \
  alpaca-trade-api ccxt pandas numpy joblib sqlite-utils

# ---------- Brokers ----------
cat > ai/brokers/router.py <<'EOF'
import os, time, random
from dotenv import load_dotenv; load_dotenv()
BROKER=os.getenv("BROKER","ALPACA").upper()
ALPACA_MODE=os.getenv("ALPACA_MODE","paper")
# Lazy imports to keep env light
def _alpaca_api():
    import alpaca_trade_api as tradeapi, os
    base = "https://paper-api.alpaca.markets" if ALPACA_MODE=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), base)
def _binance():
    import ccxt, os
    key=os.getenv("BINANCE_API_KEY"); sec=os.getenv("BINANCE_SECRET_KEY")
    ex=ccxt.binance({'apiKey':key,'secret':sec,'enableRateLimit':True})
    return ex

def account_equity_cash():
    try:
        if BROKER=="ALPACA":
            api=_alpaca_api(); a=api.get_account()
            return float(a.equity), float(a.cash)
        elif BROKER=="BINANCE":
            ex=_binance(); bal=ex.fetch_balance()
            eq = bal.get('total',{}).get('USDT', 100000.0)
            ca = bal.get('free',{}).get('USDT', 25000.0)
            return float(eq), float(ca)
        else: # MOCK
            return 100000.0+random.uniform(-400,400), 25000.0+random.uniform(-200,200)
    except Exception:
        return 100000.0+random.uniform(-400,400), 25000.0+random.uniform(-200,200)

def submit_market(symbol, side, qty):
    try:
        if BROKER=="ALPACA":
            api=_alpaca_api()
            o=api.submit_order(symbol=symbol,qty=int(qty),side=side,type="market",time_in_force="gtc")
            return {"id":o.id,"broker":"ALPACA"}
        elif BROKER=="BINANCE":
            ex=_binance()
            # market orders require lot sizes; treat qty as notional in USDT for simple demo
            o=ex.create_order(symbol=f"{symbol}/USDT", type="market", side=side, amount=max(float(qty)/200.0,0.001))
            return {"id":o.get('id','binance'),"broker":"BINANCE"}
        else:
            return {"id":f"mock-{int(time.time())}","broker":"MOCK"}
    except Exception as e:
        return {"error":str(e),"broker":BROKER}
EOF

# ---------- Strategy Manager ----------
cat > ai/strategy_manager.py <<'EOF'
import os, random, joblib
STRATEGY=os.getenv("STRATEGY","A").upper()
def score_A(pnl, risk): return (pnl/(risk+1e-6))
def score_B(pnl, risk): return (pnl*2 - risk)
def score_C(pnl, risk): return (pnl*1.5)/(risk+0.5)
def pick(pnl, risk):
    s = os.getenv("STRATEGY","A").upper()
    if s=="B": base=score_B(pnl,risk)
    elif s=="C": base=score_C(pnl,risk)
    else: base=score_A(pnl,risk)
    # If a learned model exists, nudge:
    try:
        m=joblib.load("models/active_model.pkl"); w=m.get('weights',[1])[0]
        base = base * (1 + 0.1*float(w))
    except Exception: pass
    return float(base)
EOF

# ---------- Webhook fills + Audit ----------
cat > tools/fills_and_audit.py <<'EOF'
import os, sqlite3, time
os.makedirs("db",exist_ok=True)
FILLS="db/fills.db"; AUDIT="db/audit.db"

def log_fill(data:dict):
    con=sqlite3.connect(FILLS); c=con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS fills(
        ts TEXT, broker TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL)""")
    c.execute("INSERT INTO fills VALUES (?,?,?,?,?,?,?)",(
        time.strftime("%Y-%m-%d %H:%M:%S"),
        data.get("broker","?"), data.get("order_id","?"), data.get("symbol","?"),
        data.get("side","?"), float(data.get("qty",0)), float(data.get("price",0))
    ))
    con.commit(); con.close()

def list_fills(limit=50):
    con=sqlite3.connect(FILLS); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS fills(ts TEXT, broker TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL)")
    rows=c.execute("SELECT * FROM fills ORDER BY ts DESC LIMIT ?",(limit,)).fetchall()
    con.close()
    return [{"ts":r[0],"broker":r[1],"order_id":r[2],"symbol":r[3],"side":r[4],"qty":r[5],"price":r[6]} for r in rows]

def audit_event(kind:str, detail:str):
    con=sqlite3.connect(AUDIT); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS audit(ts TEXT, kind TEXT, detail TEXT)")
    c.execute("INSERT INTO audit VALUES (?,?,?)",(time.strftime("%Y-%m-%d %H:%M:%S"), kind, detail))
    con.commit(); con.close()

def list_audit(limit=100):
    con=sqlite3.connect(AUDIT); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS audit(ts TEXT, kind TEXT, detail TEXT)")
    rows=c.execute("SELECT * FROM audit ORDER BY ts DESC LIMIT ?",(limit,)).fetchall()
    con.close()
    return [{"ts":r[0],"kind":r[1],"detail":r[2]} for r in rows]
EOF

# ---------- Update main.py ----------
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv; load_dotenv()
import os, random, asyncio, json
from ai.brokers.router import account_equity_cash, submit_market
from ai.risk_manager import compute_drawdown, position_size
from ai.fusion_engine import fuse_signals
from ai.strategy_manager import pick as pick_strategy
from ai.trade_analytics import log_trade, analyze
from tools.fills_and_audit import log_fill, list_fills, audit_event, list_audit

app=FastAPI(title="AI Money Web :: Phases 53–57")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

EQUITY_HISTORY=[]
BROKER=os.getenv("BROKER","ALPACA").upper()
STRATEGY=os.getenv("STRATEGY","A").upper()

@app.get("/")
def root(): 
    return {"message":"✅ AI Money Web up", "broker":BROKER, "strategy":STRATEGY}

@app.get("/api/info")
def info():
    return {"broker":BROKER, "strategy":STRATEGY}

@app.post("/api/strategy")
def set_strategy(payload:dict=Body(...)):
    global STRATEGY; s=(payload or {}).get("strategy","A").upper()
    if s not in ("A","B","C"): return {"error":"use A|B|C"}
    STRATEGY=s; os.environ["STRATEGY"]=s
    audit_event("strategy", f"set {s}")
    return {"ok":True,"strategy":s}

@app.get("/api/trading_status")
def trading_status():
    eq, ca = account_equity_cash()
    pnl=(eq-100000)/100000; risk=abs(pnl)+0.01
    EQUITY_HISTORY.append(eq); dd=compute_drawdown(EQUITY_HISTORY[-60:])
    fused = fuse_signals(pnl,risk,eq,dd)
    # Strategy A/B/C rescoring
    scored = pick_strategy(pnl,risk)
    signal = 0.7*fused + 0.3*scored
    size = position_size(signal, eq, dd)
    side = "buy" if signal>0 else "sell"
    res = submit_market("AAPL", side, max(int(size/200),1))
    log_trade("AAPL", side, max(int(size/200),1), eq, eq, signal, dd)
    audit_event("trade", json.dumps({"side":side,"size":size,"signal":signal,"broker":res.get('broker')}))
    return {"broker":BROKER,"strategy":STRATEGY,"equity":eq,"cash":ca,"drawdown":dd,"signal":signal,"size":size,"order":res,"analytics":analyze()}

@app.post("/webhook/fill")
def webhook_fill(payload:dict=Body(...)):
    # expected payload: {order_id,symbol,side,qty,price,broker}
    log_fill(payload or {}); audit_event("fill", json.dumps(payload or {}))
    return {"ok":True}

@app.get("/api/fills")
def fills(): return list_fills()

@app.get("/api/audit")
def audit(): return list_audit()

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    if os.path.exists("static/dashboard.html"): 
        return HTMLResponse(open("static/dashboard.html").read())
    return HTMLResponse("<h3>dashboard missing</h3>")

@app.websocket("/ws/trading_status")
async def ws(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(trading_status()); await asyncio.sleep(5)
    except WebSocketDisconnect: pass
EOF

# ---------- Dashboard V3 ----------
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>🚀 AI Money Web (53–57)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
 body{background:#000;color:#0ff;font-family:monospace;text-align:center}
 .pill{display:inline-block;padding:.25rem .5rem;border:1px solid #0ff;border-radius:9999px;margin:.2rem}
 canvas{width:92%;max-width:1100px;margin:auto}
</style>
</head><body>
<h1>🚀 AI Money Web — Multi-Broker + Strategy A/B + Webhooks</h1>
<div id="tags"></div>
<div id="status">Connecting…</div>
<div id="fills"></div>
<canvas id="chart"></canvas>
<script>
const tags=document.getElementById('tags');
const statusDiv=document.getElementById('status');
const fillsDiv=document.getElementById('fills');
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity ($)',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'Drawdown (%)',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right'}}}});

fetch('/api/info').then(r=>r.json()).then(d=>{
  tags.innerHTML = `<span class="pill">Broker: ${d.broker}</span><span class="pill">Strategy: ${d.strategy}</span>`;
});

const ws=new WebSocket('ws://127.0.0.1:8000/ws/trading_status');
ws.onmessage=(e)=>{
  const d=JSON.parse(e.data);
  statusDiv.textContent=`✅ ${d.broker} | Strat:${d.strategy} | Eq:${d.equity.toFixed(2)} | Sig:${d.signal.toFixed(3)} | DD:${d.drawdown.toFixed(2)} | Trades:${d.analytics.count}`;
  chart.data.labels.push(new Date().toLocaleTimeString());
  chart.data.datasets[0].data.push(d.equity);
  chart.data.datasets[1].data.push(d.signal);
  chart.data.datasets[2].data.push(d.drawdown);
  if(chart.data.labels.length>80){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
  chart.update();
  fetch('/api/fills').then(r=>r.json()).then(f=>{
    fillsDiv.textContent = 'Last fills: ' + (f||[]).slice(0,3).map(x=>`${x.side} ${x.symbol} @${x.price}`).join(' | ');
  });
};
</script>
</body></html>
EOF

# ---------- Launch ----------
chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard || true
echo "🎯 Phases 53–57 complete — broker router + webhooks + A/B strategy live."

