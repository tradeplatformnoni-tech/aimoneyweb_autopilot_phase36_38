#!/bin/bash
# ============================================================
# 🚀 AI Money Web :: Phase 361–380
# Trade Performance Analytics Engine Autopilot
# ============================================================
set -e

echo "🧩 Launching Performance Analytics Autopilot..."
sleep 1

# 1️⃣  Kill anything still running on :8000
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️ Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# 2️⃣  Ensure project folders
mkdir -p backend static runtime logs

# 3️⃣  Generate backend/main.py
cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os, json, datetime, math, statistics, uuid

app = FastAPI(title="AI Money Web :: Trade Performance Analytics Engine")

@app.get("/")
def root():
    return {"message": "AI Money Web backend online 🚀"}

# -------- Dashboard --------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = """
    <html>
      <head>
        <title>📈 AI Money Web Performance Dashboard</title>
        <script>
          async function refreshData(){
            const perf = await fetch('/api/performance');
            const perfData = await perf.json();
            const trades = await fetch('/api/live_trades');
            const tradesData = await trades.json();

            document.getElementById('pnl').innerText = perfData.pnl.toFixed(2);
            document.getElementById('winrate').innerText = (perfData.win_rate*100).toFixed(1)+'%';
            document.getElementById('sharpe').innerText = perfData.sharpe.toFixed(2);

            const tBody = document.getElementById('trades');
            tBody.innerHTML='';
            tradesData.trades.forEach(t=>{
              const row=document.createElement('tr');
              row.innerHTML='<td>'+t.timestamp+'</td><td>'+t.symbol+'</td><td>'+t.action+'</td><td>'+t.price+'</td><td>'+t.qty+'</td>';
              tBody.appendChild(row);
            });
          }
          setInterval(refreshData,3000);
          window.onload=refreshData;
        </script>
      </head>
      <body>
        <h1>🚀 AI Money Web :: Performance Dashboard</h1>
        <h2>📊 Live Metrics</h2>
        <ul>
          <li><b>PnL:</b> $<span id='pnl'>0</span></li>
          <li><b>Win Rate:</b> <span id='winrate'>0%</span></li>
          <li><b>Sharpe Ratio:</b> <span id='sharpe'>0.0</span></li>
        </ul>
        <h2>🧾 Recent Trades</h2>
        <table border="1" cellpadding="5" cellspacing="0">
          <thead><tr><th>Timestamp</th><th>Symbol</th><th>Action</th><th>Price</th><th>Qty</th></tr></thead>
          <tbody id="trades"></tbody>
        </table>
        <p>Auto-refresh every 3 seconds 🔄</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

# -------- Live Trades --------
@app.get("/api/live_trades")
def live_trades():
    os.makedirs("runtime", exist_ok=True)
    trades_file = "runtime/orders.jsonl"
    trades=[]
    if os.path.exists(trades_file):
        with open(trades_file,"r") as f:
            for line in f:
                try:
                    trades.append(json.loads(line.strip()))
                except: continue
    trades = sorted(trades,key=lambda x:x.get("timestamp",""),reverse=True)[:25]
    return {"trades":trades}

# -------- Paper Trade Handler --------
@app.post("/api/paper_trade")
def paper_trade(req: dict):
    os.makedirs("runtime", exist_ok=True)
    trade={
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": req.get("symbol","UNKNOWN"),
        "price": req.get("price", 0.0),
        "action": req.get("action","hold"),
        "qty": req.get("qty", 1)
    }
    with open("runtime/orders.jsonl","a") as f:
        f.write(json.dumps(trade)+"\n")
    return {"status":"executed","trade":trade}

# -------- Performance Analytics --------
@app.get("/api/performance")
def performance():
    trades_file = "runtime/orders.jsonl"
    if not os.path.exists(trades_file): return {"pnl":0,"win_rate":0,"sharpe":0}
    prices, actions = [], []
    with open(trades_file,"r") as f:
        for line in f:
            try:
                t = json.loads(line.strip())
                prices.append(t["price"])
                actions.append(t["action"])
            except: continue
    if len(prices)<2: return {"pnl":0,"win_rate":0,"sharpe":0}
    pnl = sum([prices[i+1]-prices[i] if actions[i]=="buy" else prices[i]-prices[i+1] for i in range(len(prices)-1)])
    gains = [max(0,p) for p in [p2-p1 for p1,p2 in zip(prices,prices[1:])]]
    losses = [abs(p) for p in [p2-p1 for p1,p2 in zip(prices,prices[1:])] if p<0]
    win_rate = len(gains)/(len(gains)+len(losses)) if (gains or losses) else 0
    ret = [p2/p1-1 for p1,p2 in zip(prices,prices[1:]) if p1>0]
    sharpe = statistics.mean(ret)/statistics.stdev(ret)*math.sqrt(252) if len(ret)>1 and statistics.stdev(ret)>0 else 0
    return {"pnl":pnl,"win_rate":win_rate,"sharpe":sharpe}
PYCODE

# 4️⃣  Launch backend
echo "🚀 Starting backend..."
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Backend running → http://127.0.0.1:8000"
echo "💡 Dashboard → http://127.0.0.1:8000/dashboard"
echo "💰 Example Trade:"
echo "curl -X POST http://127.0.0.1:8000/api/paper_trade -H 'Content-Type: application/json' -d '{\"symbol\":\"BTC/USD\",\"price\":62800,\"action\":\"buy\",\"qty\":0.01}'"

