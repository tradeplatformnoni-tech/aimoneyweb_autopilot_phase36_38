#!/bin/bash
# ==========================================================
# 🧠 NeoLight Goal Engine :: Autopilot Setup Script
# ==========================================================
echo "🚀 Installing Wealth Goal Engine..."
mkdir -p backend runtime tools logs

# 1. Create goal config
cat > runtime/goal_config.json <<'JSON'
{
  "target_milestones": {
    "2_years": 1000000,
    "5_years": 10000000,
    "10_years": 50000000
  },
  "current_equity": 25000,
  "growth_target": 0.035,
  "risk_tolerance": "medium"
}
JSON

# 2. Add backend endpoint
cat > backend/main.py <<'PY'
from fastapi import FastAPI
from backend.goal_engine import update_progress

app = FastAPI()

@app.get("/api/goal")
def read_goal():
    # placeholder equity value for testing
    return update_progress(current_equity=25000)
PY

# 3. Create goal engine module
cat > backend/goal_engine.py <<'PY'
import json, datetime

def update_progress(current_equity: float):
    with open("runtime/goal_config.json") as f:
        cfg = json.load(f)
    out = {"equity": current_equity, "report": []}
    for yr, tgt in cfg["target_milestones"].items():
        pct = round((current_equity/tgt)*100, 2)
        out["report"].append({"year": yr, "target": tgt, "progress": pct})
    out["timestamp"] = datetime.datetime.utcnow().isoformat()
    return out
PY

# 4. Launch backend safely
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
echo "✅ Goal Engine backend started on http://localhost:8000/api/goal"
echo "💾 Config: runtime/goal_config.json"

