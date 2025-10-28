#!/bin/bash
echo "🚀 PHASE 241–260: Backtester + Optimizer Autopilot Starting..."

mkdir -p results runtime historical_data logs

# === 1. Patch backend/main.py ===
if ! grep -q "/api/backtest" backend/main.py; then
cat >> backend/main.py <<EOF

from pydantic import BaseModel
import datetime
import statistics

class BacktestRequest(BaseModel):
    strategy: str
    config: dict
    data_file: str

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    import json, importlib, uuid
    with open(req.data_file) as f:
        data = json.load(f)

    strategy = importlib.import_module(f"ai.strategies.{req.strategy}")
    balance = 10000
    positions = 0
    trades = []
    equity_curve = []

    for i in range(len(data["close"])):
        window = {
            k: v[:i+1] for k, v in data.items()
        }
        signal = strategy.run(window, req.config)
        if not signal: continue

        if signal["action"] == "buy" and balance >= data["close"][i]:
            balance -= data["close"][i]
            positions += 1
            trades.append({"type": "buy", "price": data["close"][i]})
        elif signal["action"] == "sell" and positions > 0:
            balance += data["close"][i]
            positions -= 1
            trades.append({"type": "sell", "price": data["close"][i]})
        
        equity_curve.append(balance + positions * data["close"][i])

    pnl = equity_curve[-1] - 10000
    returns = [((equity_curve[i+1]-equity_curve[i])/equity_curve[i]) for i in range(len(equity_curve)-1)]
    sharpe = (statistics.mean(returns)/statistics.stdev(returns))* (252 ** 0.5) if len(returns) > 1 else 0
    max_drawdown = max([(max(equity_curve[:i+1]) - equity_curve[i]) for i in range(len(equity_curve))])

    result = {
        "final_balance": equity_curve[-1],
        "pnl": pnl,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "trades": trades
    }

    result_path = f"results/backtest_{uuid.uuid4().hex[:6]}.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    return {"status": "ok", "output_file": result_path}
EOF
else
  echo "⚠️ /api/backtest already exists. Skipping patch."
fi

# === 2. Create CLI tool: tools/backtest_cli.py ===
mkdir -p tools
cat > tools/backtest_cli.py <<EOF
import requests, sys, json

if len(sys.argv) != 4:
    print("Usage: python backtest_cli.py <strategy> <config_json> <ohlcv_data_json>")
    sys.exit(1)

strategy = sys.argv[1]
config = json.loads(sys.argv[2])
data_file = sys.argv[3]

resp = requests.post("http://localhost:8000/api/backtest", json={
    "strategy": strategy,
    "config": config,
    "data_file": data_file
})

print("🧪 Backtest Results:")
print(json.dumps(resp.json(), indent=2))
EOF

# === 3. Create example OHLCV data ===
cat > historical_data/sample_data.json <<EOF
{
  "open": [100, 102, 101, 105, 106, 107, 108, 110, 108, 109],
  "high": [102, 103, 103, 106, 108, 108, 110, 111, 109, 110],
  "low":  [99, 101, 100, 104, 105, 106, 107, 109, 107, 108],
  "close":[101, 102, 102, 106, 107, 108, 109, 110, 108, 109],
  "volume":[1000,1100,900,1200,1300,1250,1100,1050,1150,1000]
}
EOF

# === 4. Make backtest CLI executable ===
chmod +x tools/backtest_cli.py

# === 5. Restart backend ===
echo "🔁 Restarting FastAPI backend..."
pkill -f uvicorn || true
source venv/bin/activate && nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &

# === 6. DONE ===
echo "✅ Phase 241–260 COMPLETE!"
echo "🧪 Test CLI with:"
echo "python tools/backtest_cli.py momentum '{\"window\": 3}' historical_data/sample_data.json"

