#!/bin/bash
# ----------------------------------------------------
# AI Money Web :: Safe Paper-Trading Bridge (301–320)
# ----------------------------------------------------
set -e
echo "🚀 Starting safe paper-trading setup..."

# --- clean any server on port 8000 ---
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# --- ensure structure ---
mkdir -p backend static logs ai/strategies runtime tools

# --- backend/main.py ---
cat > backend/main.py <<'PYCODE'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import json, os, datetime, uuid

app = FastAPI(title="AI Money Web :: Paper Trading Bridge")

@app.get("/")
def root():
    return {"message": "paper-trading backend online 🚀"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = "<h1>Paper Trading Dashboard</h1><p>Phase 301–320 running.</p>"
    return HTMLResponse(content=html)

class PaperTradeRequest(BaseModel):
    symbol: str
    price: float
    action: str
    qty: int = 1

@app.post("/api/paper_trade")
def paper_trade(req: PaperTradeRequest):
    os.makedirs("runtime", exist_ok=True)
    trade = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": req.symbol,
        "price": req.price,
        "action": req.action,
        "qty": req.qty
    }
    with open("runtime/orders.jsonl", "a") as f:
        f.write(json.dumps(trade) + "\n")
    return {"status": "executed", "trade": trade}
PYCODE

# --- dashboard.html ---
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html>
<html>
<head><title>Paper Trading Dashboard</title></head>
<body>
<h1>Paper Trading Bridge</h1>
<p>Use /api/paper_trade to simulate live orders 📈</p>
</body>
</html>
HTML

# --- sample strategies ---
mkdir -p ai/strategies
cat > ai/strategies/momentum.py <<'PYCODE'
def run(data, config):
    if data["close"][-1] > data["close"][0]: return {"action":"buy"}
    if data["close"][-1] < data["close"][0]: return {"action":"sell"}
    return None
PYCODE

cat > ai/strategies/crossover.py <<'PYCODE'
def run(data, config):
    fast, slow = config.get("fast",2), config.get("slow",4)
    if len(data["close"])<slow: return None
    fast_avg=sum(data["close"][-fast:])/fast
    slow_avg=sum(data["close"][-slow:])/slow
    if fast_avg>slow_avg: return {"action":"buy"}
    if fast_avg<slow_avg: return {"action":"sell"}
    return None
PYCODE

cat > ai/strategies/mean_reversion.py <<'PYCODE'
def run(data, config):
    mid=sum(data["close"])/len(data["close"])
    if data["close"][-1]<0.95*mid: return {"action":"buy"}
    if data["close"][-1]>1.05*mid: return {"action":"sell"}
    return None
PYCODE

# --- paper daemon CLI ---
cat > tools/paper_daemon.py <<'PYCODE'
#!/usr/bin/env python3
import time, json, random, requests

def mock_price(base):
    return base + random.uniform(-1,1)

symbols = ["AAPL","TSLA","MSFT"]
while True:
    for sym in symbols:
        price = mock_price(100)
        action = random.choice(["buy","sell"])
        payload={"symbol":sym,"price":price,"action":action,"qty":1}
        try:
            r = requests.post("http://127.0.0.1:8000/api/paper_trade",json=payload,timeout=3)
            print(r.json())
        except Exception as e:
            print("Error:", e)
    time.sleep(5)
PYCODE
chmod +x tools/paper_daemon.py

# --- start backend ---
source venv/bin/activate
pkill -f uvicorn || true
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Paper-trading backend running → http://127.0.0.1:8000"
echo "💡 Test trade example:"
echo "curl -X POST http://127.0.0.1:8000/api/paper_trade -H 'Content-Type: application/json' -d '{\"symbol\":\"AAPL\",\"price\":190.0,\"action\":\"buy\"}'"
echo "💡 Or run daemon: python tools/paper_daemon.py"
 
