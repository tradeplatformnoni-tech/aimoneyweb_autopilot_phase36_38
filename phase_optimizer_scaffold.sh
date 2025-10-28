#!/bin/bash
# -----------------------------------------------
# AI Money Web :: Safe Optimizer (Phase 261–280)
# -----------------------------------------------
set -e

echo "🚀 Starting safe optimizer setup..."

# --- kill any process using port 8000 ---
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# --- ensure directories exist ---
mkdir -p backend static logs ai/strategies results runtime tools

# --- backend/main.py ---
cat > backend/main.py <<'PYCODE'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import json, importlib, uuid, os, statistics, itertools

app = FastAPI(title="AI Money Web :: Auto-Strategy Optimizer")

@app.get("/")
def root():
    return {"message": "optimizer phase online 🚀"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = "<h1>AI Money Web Optimizer</h1><p>Phase 261-280 ready.</p>"
    return HTMLResponse(content=html, status_code=200)

class OptimizeRequest(BaseModel):
    strategy: str
    grid: dict
    data_file: str

@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    if not os.path.exists(req.data_file):
        return JSONResponse(status_code=400, content={"error": "data file not found"})

    with open(req.data_file) as f:
        data = json.load(f)
    strategy = importlib.import_module(f"ai.strategies.{req.strategy}")

    keys = list(req.grid.keys())
    combos = list(itertools.product(*req.grid.values()))
    results = []
    for c in combos:
        cfg = dict(zip(keys, c))
        bal, pos, curve = 10000, 0, []
        for i, price in enumerate(data["close"]):
            window = {k: v[:i+1] for k, v in data.items()}
            sig = strategy.run(window, cfg)
            if not sig: continue
            if sig["action"]=="buy" and bal>=price:
                bal -= price; pos += 1
            elif sig["action"]=="sell" and pos>0:
                bal += price; pos -= 1
            curve.append(bal + pos*price)
        if len(curve)<2: continue
        pnl = curve[-1]-10000
        rets=[(curve[i+1]-curve[i])/curve[i] for i in range(len(curve)-1)]
        sharpe=(statistics.mean(rets)/statistics.stdev(rets))*252**0.5 if len(rets)>1 else 0
        results.append({"config":cfg,"pnl":pnl,"sharpe":sharpe})
    if not results:
        return {"status":"ok","best":None}

    best=max(results,key=lambda r:r["sharpe"])
    os.makedirs("runtime",exist_ok=True)
    with open("runtime/strategy_config.json","w") as f: json.dump(best,f,indent=2)
    return {"status":"ok","best":best}
PYCODE

# --- dashboard.html ---
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html>
<html>
<head><title>Optimizer Dashboard</title></head>
<body>
<h1>Optimizer Autopilot Phase 261–280</h1>
<p>Run /api/optimize to test parameter search 🧩</p>
</body>
</html>
HTML

# --- sample strategy (momentum.py) ---
mkdir -p ai/strategies
cat > ai/strategies/momentum.py <<'PYCODE'
def run(data, config):
    w = config.get("window", 3)
    if len(data["close"]) < w: return None
    if data["close"][-1] > data["close"][-w]: return {"action": "buy"}
    if data["close"][-1] < data["close"][-w]: return {"action": "sell"}
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

# --- CLI tool for optimization ---
cat > tools/optimizer_cli.py <<'PYCODE'
#!/usr/bin/env python3
import requests, json, sys
payload={
  "strategy":"momentum",
  "grid":{"window":[2,3,4,5]},
  "data_file":"historical_data/sample_data.json"
}
resp=requests.post("http://127.0.0.1:8000/api/optimize",json=payload)
print(json.dumps(resp.json(),indent=2))
PYCODE
chmod +x tools/optimizer_cli.py

# --- start backend ---
source venv/bin/activate
pkill -f uvicorn || true
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Optimizer backend running → http://127.0.0.1:8000"
echo "💡 Run optimizer CLI with: python tools/optimizer_cli.py"

