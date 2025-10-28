#!/bin/bash
# -----------------------------------------------
# AI Money Web :: Safe Portfolio Allocator (281–300)
# -----------------------------------------------
set -e
echo "🚀 Starting safe portfolio allocator setup..."

# --- clean port 8000 ---
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# --- create structure ---
mkdir -p backend static logs ai/strategies results runtime tools

# --- backend/main.py ---
cat > backend/main.py <<'PYCODE'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import json, os, statistics

app = FastAPI(title="AI Money Web :: Portfolio Allocator")

@app.get("/")
def root():
    return {"message": "portfolio allocator online 🚀"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = "<h1>Portfolio Allocator</h1><p>Phase 281–300 ready.</p>"
    return HTMLResponse(content=html)

class PortfolioRequest(BaseModel):
    strategies: list
    weights: dict
    data_files: dict

@app.post("/api/portfolio_optimize")
def portfolio_optimize(req: PortfolioRequest):
    results = {}
    for strat in req.strategies:
        df = req.data_files.get(strat)
        if not df or not os.path.exists(df):
            results[strat] = {"error": "data missing"}
            continue
        with open(df) as f: data=json.load(f)
        pnl=sum(data["close"][-3:]) - sum(data["close"][:3])
        results[strat] = {"pnl": pnl, "weight": req.weights.get(strat, 0)}
    total = sum(v["weight"]*v.get("pnl",0) for v in results.values())
    alloc = {"strategies": results, "portfolio_pnl": total}
    os.makedirs("results",exist_ok=True)
    with open("results/portfolio_alloc.json","w") as f: json.dump(alloc,f,indent=2)
    return alloc
PYCODE

# --- dashboard.html ---
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html>
<html>
<head><title>Portfolio Dashboard</title></head>
<body>
<h1>Portfolio Allocator</h1>
<p>Use /api/portfolio_optimize to test multi-strategy weights 🧩</p>
</body>
</html>
HTML

# --- example strategies ---
mkdir -p ai/strategies
cat > ai/strategies/momentum.py <<'PYCODE'
def run(data, config):
    return {"action": "buy"} if data["close"][-1]>data["close"][0] else {"action":"sell"}
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

# --- sample data files ---
mkdir -p historical_data
for s in momentum crossover mean_reversion; do
cat > historical_data/${s}_data.json <<'JSON'
{"close":[100,101,102,103,104,105],"open":[99,100,101,102,103,104]}
JSON
done

# --- CLI tool ---
cat > tools/portfolio_cli.py <<'PYCODE'
#!/usr/bin/env python3
import requests, json
payload={
 "strategies":["momentum","crossover","mean_reversion"],
 "weights":{"momentum":0.4,"crossover":0.4,"mean_reversion":0.2},
 "data_files":{
   "momentum":"historical_data/momentum_data.json",
   "crossover":"historical_data/crossover_data.json",
   "mean_reversion":"historical_data/mean_reversion_data.json"
 }
}
r=requests.post("http://127.0.0.1:8000/api/portfolio_optimize",json=payload)
print(json.dumps(r.json(),indent=2))
PYCODE
chmod +x tools/portfolio_cli.py

# --- launch server ---
source venv/bin/activate
pkill -f uvicorn || true
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Portfolio Allocator backend running → http://127.0.0.1:8000"
echo "💡 Run: python tools/portfolio_cli.py"

