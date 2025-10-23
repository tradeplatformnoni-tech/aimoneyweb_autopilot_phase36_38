#!/bin/bash
# -----------------------------------------------
# AI Money Web :: Safe Backtest + Strategy Setup
# -----------------------------------------------
set -e

echo "🚀 Starting scaffold..."

# --- Clean up any running uvicorn on 8000 ---
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# --- Project structure ---
mkdir -p backend static logs ai/strategies results runtime

# --- backend/main.py ---
cat > backend/main.py <<'PYCODE'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import json, importlib, uuid, statistics, os

app = FastAPI(title="AI Money Web :: Backtest Module")

@app.get("/")
def root():
    return {"message": "AI Money Web backend running 🚀"}

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    with open("static/dashboard.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

class BacktestRequest(BaseModel):
    strategy: str
    config: dict
    data_file: str

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    if not os.path.exists(req.data_file):
        return JSONResponse(status_code=400, content={"error": "data file not found"})

    with open(req.data_file) as f:
        data = json.load(f)
    strategy = importlib.import_module(f"ai.strategies.{req.strategy}")
    balance, positions, trades, curve = 10000, 0, [], []

    for i, price in enumerate(data["close"]):
        window = {k: v[:i+1] for k, v in data.items()}
        sig = strategy.run(window, req.config)
        if not sig: continue
        if sig["action"] == "buy" and balance >= price:
            balance -= price; positions += 1; trades.append({"type":"buy","price":price})
        elif sig["action"] == "sell" and positions>0:
            balance += price; positions -= 1; trades.append({"type":"sell","price":price})
        curve.append(balance + positions * price)

    pnl = curve[-1]-10000 if curve else 0
    sharpe = (statistics.mean([(curve[i+1]-curve[i])/curve[i] for i in range(len(curve)-1)]) /
              statistics.stdev([(curve[i+1]-curve[i])/curve[i] for i in range(len(curve)-1)])) \
              * (252**0.5) if len(curve)>2 else 0
    result = {"pnl": pnl, "sharpe": sharpe, "trades": trades}
    os.makedirs("results", exist_ok=True)
    out = f"results/backtest_{uuid.uuid4().hex[:6]}.json"
    with open(out,"w") as f: json.dump(result,f,indent=2)
    return {"status":"ok","output_file":out}
PYCODE

# --- dashboard.html ---
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html>
<html>
<head><title>AI Money Web Dashboard</title></head>
<body>
<h1>Dashboard</h1>
<p>Autopilot + Backtester live 🚀</p>
</body>
</html>
HTML

# --- momentum strategy ---
cat > ai/strategies/momentum.py <<'PYCODE'
def run(data, config):
    w = config.get("window", 3)
    if len(data["close"]) < w:
        return None
    if data["close"][-1] > data["close"][-w]:
        return {"action": "buy"}
    elif data["close"][-1] < data["close"][-w]:
        return {"action": "sell"}
    return None
PYCODE

# --- sample data ---
mkdir -p historical_data
cat > historical_data/sample_data.json <<'JSON'
{"close":[100,101,102,103,102,104,105],
 "open":[99,100,101,102,101,103,104],
 "high":[101,102,103,104,103,105,106],
 "low":[98,99,100,101,100,102,103]}
JSON

# --- start server ---
source venv/bin/activate
pkill -f uvicorn || true
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Backend with /api/backtest running at http://127.0.0.1:8000"
echo "💡 Dashboard: http://127.0.0.1:8000/dashboard"

