#!/bin/bash
# ============================================================
# 🚀 AI Money Web :: Phase 341–360
# Real-Time Dashboard Trade Viewer Autopilot
# ============================================================
set -e

echo "🧩 Starting Real-Time Dashboard Autopilot..."
sleep 1

# 1️⃣  Kill anything on port 8000
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# 2️⃣  Create backend/main.py
mkdir -p backend static runtime logs

cat > backend/main.py <<'PYCODE'
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os, json, datetime, uuid, time

app = FastAPI(title="AI Money Web :: Real-Time Trade Dashboard")

@app.get("/")
def root():
    return {"message": "AI Money Web backend online 🚀"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = """
    <html>
      <head>
        <title>📊 AI Money Web Dashboard</title>
        <script>
          async function fetchTrades() {
            const res = await fetch('/api/live_trades');
            const data = await res.json();
            const table = document.getElementById('trades');
            table.innerHTML = '';
            data.trades.forEach(t => {
              const row = document.createElement('tr');
              row.innerHTML = '<td>' + t.timestamp + '</td><td>' + t.symbol + '</td><td>' + t.action + '</td><td>' + t.price + '</td><td>' + t.qty + '</td>';
              table.appendChild(row);
            });
          }
          setInterval(fetchTrades, 3000);
          window.onload = fetchTrades;
        </script>
      </head>
      <body>
        <h1>🚀 AI Money Web :: Live Trades</h1>
        <table border="1" cellpadding="5" cellspacing="0">
          <thead><tr><th>Timestamp</th><th>Symbol</th><th>Action</th><th>Price</th><th>Qty</th></tr></thead>
          <tbody id="trades"></tbody>
        </table>
        <p>Auto-refreshing every 3 seconds 🔄</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/live_trades")
def live_trades():
    os.makedirs("runtime", exist_ok=True)
    trades_file = "runtime/orders.jsonl"
    trades = []
    if os.path.exists(trades_file):
        with open(trades_file, "r") as f:
            for line in f:
                try:
                    trades.append(json.loads(line.strip()))
                except:
                    continue
    trades = sorted(trades, key=lambda x: x.get("timestamp", ""), reverse=True)[:25]
    return {"trades": trades}

@app.post("/api/paper_trade")
def paper_trade(req: dict):
    os.makedirs("runtime", exist_ok=True)
    trade = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": req.get("symbol", "UNKNOWN"),
        "price": req.get("price", 0.0),
        "action": req.get("action", "hold"),
        "qty": req.get("qty", 1)
    }
    with open("runtime/orders.jsonl", "a") as f:
        f.write(json.dumps(trade) + "\n")
    return {"status": "executed", "trade": trade}
PYCODE

# 3️⃣  Start the backend
echo "🚀 Launching backend..."
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Backend running at http://127.0.0.1:8000"
echo "💡 Dashboard live at: http://127.0.0.1:8000/dashboard"
echo "💰 To test a trade:"
echo "curl -X POST http://127.0.0.1:8000/api/paper_trade -H 'Content-Type: application/json' -d '{\"symbol\":\"BTC/USD\",\"price\":62000,\"action\":\"buy\",\"qty\":0.01}'"

